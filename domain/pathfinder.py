# domain/pathfinder.py

import heapq
import numpy as np


class Pathfinder:
    """Encapsulates the A* pathfinding algorithm."""

    def __init__(self, grid):
        """
        Initializes the Pathfinder with the world's static grid.
        Args:
            grid (list[list[Tile]]): The 2D grid of the world.
        """
        self.grid = grid
        self.width = len(grid[0])
        self.height = len(grid)

    def find_path(self, start_pos, end_pos):
        """
        Finds the shortest path between two grid positions using A*.

        Args:
            start_pos (tuple[int, int]): The (x, y) starting grid coordinates.
            end_pos (tuple[int, int]): The (x, y) ending grid coordinates.

        Returns:
            list[tuple[int, int]]: A list of (x, y) coordinates representing the path,
                                   or None if no path is found. Returns [] if start==end.
        """
        start_node, end_node = tuple(start_pos), tuple(end_pos)

        if start_node == end_node:
            return []

        def get_move_cost(grid_pos):
            tile = self.grid[grid_pos[1]][grid_pos[0]]
            if tile.tile_move_speed_factor == 0:
                return float("inf")
            # Cost is inverse of speed factor
            return 1.0 / tile.tile_move_speed_factor

        # Check if start or end are on impassable tiles
        if get_move_cost(start_node) == float("inf") or get_move_cost(
            end_node
        ) == float("inf"):
            return None

        open_set = []
        heapq.heappush(open_set, (0, start_node))

        came_from = {}
        g_score = {start_node: 0}
        f_score = {
            start_node: np.linalg.norm(np.array(start_node) - np.array(end_node))
        }

        while open_set:
            current = heapq.heappop(open_set)[1]

            if current == end_node:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                return path[::-1]

            for dx, dy in [
                (0, 1),
                (0, -1),
                (1, 0),
                (-1, 0),
                (-1, -1),
                (-1, 1),
                (1, -1),
                (1, 1),
            ]:
                neighbor = (current[0] + dx, current[1] + dy)

                if not (
                    0 <= neighbor[0] < self.width and 0 <= neighbor[1] < self.height
                ):
                    continue

                move_cost = get_move_cost(neighbor)
                if move_cost == float("inf"):
                    continue

                # The cost for a diagonal move is sqrt(2) ~= 1.414 times the base cost
                tentative_g_score = g_score[current] + (
                    move_cost * (1.414 if dx != 0 and dy != 0 else 1.0)
                )

                if tentative_g_score < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    heuristic = np.linalg.norm(np.array(neighbor) - np.array(end_node))
                    f_score[neighbor] = tentative_g_score + heuristic

                    if neighbor not in [i[1] for i in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return None  # No path found
