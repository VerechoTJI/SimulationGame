# domain/flow_field_manager.py
import numpy as np
from queue import PriorityQueue
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
        Generates a flow field pointing towards the nearest goal positions
        using Dijkstra's algorithm to account for tile costs.

        Args:
            goal_positions_yx: A list of (y, x) tuples representing the goals.
            return_cost_field: If True, returns a tuple (flow_field, cost_field).
        """
        cost_field = np.full((self.height, self.width), np.inf, dtype=np.float32)
        flow_field = np.zeros((self.height, self.width, 2), dtype=np.int8)

        if not goal_positions_yx:
            return (flow_field, cost_field) if return_cost_field else flow_field

        pq = PriorityQueue()
        for y, x in goal_positions_yx:
            if 0 <= y < self.height and 0 <= x < self.width:
                tile = self.grid[y][x]
                if tile.tile_move_speed_factor > 0:
                    cost_field[y, x] = 0
                    pq.put((0, (y, x)))

        while not pq.empty():
            current_cost, (y, x) = pq.get()

            # If we've found a cheaper path already, skip
            if current_cost > cost_field[y, x]:
                continue

            for dy, dx in self.NEIGHBORS:
                ny, nx = y + dy, x + dx

                if 0 <= ny < self.height and 0 <= nx < self.width:
                    neighbor_tile = self.grid[ny][nx]
                    if neighbor_tile.tile_move_speed_factor > 0:
                        # Cost is inversely proportional to speed factor
                        tile_cost = 1.0 / neighbor_tile.tile_move_speed_factor
                        move_cost = (
                            self.DIAGONAL_COST
                            if dx != 0 and dy != 0
                            else self.CARDINAL_COST
                        )
                        new_cost = current_cost + (move_cost * tile_cost)

                        if new_cost < cost_field[ny, nx]:
                            cost_field[ny, nx] = new_cost
                            pq.put((new_cost, (ny, nx)))

        # Vector field generation remains the same
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
