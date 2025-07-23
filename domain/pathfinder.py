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

        def get_tile(pos_yx):
            y, x = pos_yx
            return self.grid[y][x]

        def is_passable(pos_yx):
            return get_tile(pos_yx).tile_move_speed_factor > 0

        def get_move_cost(pos_yx):
            if not is_passable(pos_yx):
                return float("inf")
            return 1.0 / get_tile(pos_yx).tile_move_speed_factor

        if not is_passable(start_node) or not is_passable(end_node):
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

            # Define potential neighbors
            neighbors_to_check = [
                (0, 1),
                (0, -1),
                (1, 0),
                (-1, 0),  # Cardinals
                (-1, -1),
                (-1, 1),
                (1, -1),
                (1, 1),  # Diagonals
            ]

            for dy, dx in neighbors_to_check:
                neighbor_y, neighbor_x = current_y + dy, current_x + dx
                neighbor = (neighbor_y, neighbor_x)

                if not (0 <= neighbor_y < self.height and 0 <= neighbor_x < self.width):
                    continue

                if not is_passable(neighbor):
                    continue

                # --- START OF THE FIX ---
                # For diagonal movement, check if the corners are passable
                if dy != 0 and dx != 0:
                    corner1 = (current_y + dy, current_x)
                    corner2 = (current_y, current_x + dx)
                    if not is_passable(corner1) or not is_passable(corner2):
                        continue
                # --- END OF THE FIX ---

                move_cost = get_move_cost(neighbor)

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
