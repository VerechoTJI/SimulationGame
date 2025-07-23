# domain/pathfinder.py

import heapq
import numpy as np


class Pathfinder:
    """Encapsulates the A* pathfinding algorithm."""

    def __init__(self, grid):
        self.grid = grid
        self.width = len(grid[0])
        self.height = len(grid)

    def find_path(self, start_pos_yx, end_pos_yx):
        """
        Finds the shortest path between two grid positions using A*.

        Args:
            start_pos_yx (tuple[int, int]): The (y, x) starting grid coordinates.
            end_pos_yx (tuple[int, int]): The (y, x) ending grid coordinates.

        Returns:
            list[tuple[int, int]]: A list of (y, x) coordinates for the path,
                                   or None if no path is found.
        """
        start_node, end_node = tuple(start_pos_yx), tuple(end_pos_yx)

        if start_node == end_node:
            return []

        def get_move_cost(grid_pos_yx):
            y, x = grid_pos_yx
            tile = self.grid[y][x]  # Correct (y,x) access
            if tile.tile_move_speed_factor == 0:
                return float("inf")
            return 1.0 / tile.tile_move_speed_factor

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

            current_y, current_x = current

            for dy, dx in [
                (0, 1),
                (0, -1),
                (1, 0),
                (-1, 0),
                (-1, -1),
                (-1, 1),
                (1, -1),
                (1, 1),
            ]:
                neighbor_y, neighbor_x = current_y + dy, current_x + dx
                neighbor = (neighbor_y, neighbor_x)

                if not (0 <= neighbor_y < self.height and 0 <= neighbor_x < self.width):
                    continue

                move_cost = get_move_cost(neighbor)
                if move_cost == float("inf"):
                    continue

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
        return None
