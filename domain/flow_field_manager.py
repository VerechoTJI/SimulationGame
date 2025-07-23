# domain/flow_field_manager.py
import numpy as np
from collections import deque
import math


class FlowFieldManager:
    """Manages the creation of flow fields (vector fields) for pathfinding."""

    def __init__(self, grid):
        self.grid = grid
        self.height = len(grid)
        self.width = len(grid[0]) if self.height > 0 else 0
        self.CARDINAL_COST = 1.0
        self.DIAGONAL_COST = math.sqrt(2)

        # Standardized neighbor directions, (dy, dx) format
        self.NEIGHBORS = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),  # Cardinals (N, S, W, E)
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),  # Diagonals (NW, NE, SW, SE)
        ]

    def generate_flow_field(
        self, goal_positions_yx: list[tuple[int, int]], return_cost_field=False
    ):
        """
        Generates a flow field pointing towards the nearest goal positions.

        Args:
            goal_positions_yx: A list of (y, x) tuples representing the goals.
            return_cost_field: If True, returns a tuple (flow_field, cost_field).
        """
        cost_field = np.full((self.height, self.width), np.inf, dtype=np.float32)
        flow_field = np.zeros((self.height, self.width, 2), dtype=np.int8)

        if not goal_positions_yx:
            return (flow_field, cost_field) if return_cost_field else flow_field

        queue = deque()
        for y, x in goal_positions_yx:
            if 0 <= y < self.height and 0 <= x < self.width:
                if self.grid[y][x].tile_move_speed_factor > 0:
                    cost_field[y, x] = 0
                    queue.append((y, x))

        while queue:
            y, x = queue.popleft()
            current_cost = cost_field[y, x]

            for dy, dx in self.NEIGHBORS:
                ny, nx = y + dy, x + dx

                if 0 <= ny < self.height and 0 <= nx < self.width:
                    if self.grid[ny][nx].tile_move_speed_factor > 0 and np.isinf(
                        cost_field[ny, nx]
                    ):
                        move_cost = (
                            self.DIAGONAL_COST
                            if dx != 0 and dy != 0
                            else self.CARDINAL_COST
                        )
                        cost_field[ny, nx] = current_cost + move_cost
                        queue.append((ny, nx))

        for y in range(self.height):
            for x in range(self.width):
                if np.isinf(cost_field[y, x]):
                    continue

                min_cost = cost_field[y, x]
                best_move = (0, 0)  # (dy, dx)

                for dy, dx in self.NEIGHBORS:
                    ny, nx = y + dy, x + dx

                    if 0 <= ny < self.height and 0 <= nx < self.width:
                        if cost_field[ny, nx] < min_cost:
                            min_cost = cost_field[ny, nx]
                            best_move = (dy, dx)

                flow_field[y, x] = best_move

        if return_cost_field:
            return flow_field, cost_field
        else:
            return flow_field
