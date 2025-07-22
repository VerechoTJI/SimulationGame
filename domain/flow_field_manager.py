import numpy as np
from collections import deque


class FlowFieldManager:
    """
    Manages the creation of flow fields (vector fields) for pathfinding.

    This service uses a Breadth-First Search (BFS) to first calculate an
    integration cost field (distance from the nearest goal) and then uses
    that to generate a flow field where each tile's vector points "downhill"
    along the cost gradient towards a goal.
    """

    def __init__(self, grid):
        self.grid = grid
        self.height = len(grid)
        self.width = len(grid[0]) if self.height > 0 else 0

    def generate_flow_field(self, goal_positions: list[tuple[int, int]]):
        """
        Generates a flow field pointing towards the nearest goal positions.

        Args:
            goal_positions: A list of (x, y) tuples representing the goals.

        Returns:
            A numpy array of shape (height, width, 2) where each element is
            an (dx, dy) vector pointing to the next tile on the path.
            Returns a zero-field if no goals are provided.
        """
        # 1. Initialize grids
        cost_field = np.full((self.height, self.width), np.inf, dtype=np.float32)
        flow_field = np.zeros((self.height, self.width, 2), dtype=np.int8)

        if not goal_positions:
            return flow_field

        # 2. Setup BFS queue with all goal positions
        queue = deque()
        for y, x in goal_positions:
            if 0 <= y < self.height and 0 <= x < self.width:
                if self.grid[y][x].tile_move_speed_factor > 0:
                    cost_field[y, x] = 0
                    queue.append((y, x))

        # 3. BFS to calculate integration cost (distance from a goal)
        while queue:
            y, x = queue.popleft()
            current_cost = cost_field[y, x]

            # Check neighbors (8 directions for smoother flow)
            for dx, dy in [
                (0, 1),
                (0, -1),
                (1, 0),
                (-1, 0),
                (1, 1),
                (1, -1),
                (-1, 1),
                (-1, -1),
            ]:
                ny, nx = y + dy, x + dx

                if 0 <= ny < self.height and 0 <= nx < self.width:
                    # Check if tile is passable and unvisited
                    if self.grid[ny][nx].tile_move_speed_factor > 0 and np.isinf(
                        cost_field[ny, nx]
                    ):
                        cost_field[ny, nx] = current_cost + 1
                        queue.append((ny, nx))

        # 4. Generate flow vectors from the cost field's gradient
        for y in range(self.height):
            for x in range(self.width):
                if np.isinf(cost_field[y, x]):
                    continue  # No path from here, vector remains (0, 0)

                min_cost = cost_field[y, x]
                best_move = (0, 0)

                # Check neighbors to find the one with the lowest cost ("downhill")
                for dx, dy in [
                    (0, 1),
                    (0, -1),
                    (1, 0),
                    (-1, 0),
                    (1, 1),
                    (1, -1),
                    (-1, 1),
                    (-1, -1),
                ]:
                    ny, nx = y + dy, x + dx

                    if 0 <= ny < self.height and 0 <= nx < self.width:
                        if cost_field[ny, nx] < min_cost:
                            min_cost = cost_field[ny, nx]
                            best_move = (dy, dx)

                flow_field[y, x] = best_move

        return flow_field
