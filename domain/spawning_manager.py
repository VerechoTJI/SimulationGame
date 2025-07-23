# domain/spawning_manager.py

import random


class SpawningManager:
    """
    Manages the rules and state for entity spawning, including natural
    spawning and replanting.
    """

    def __init__(self, grid: list, config_data: dict):
        self.grid = grid
        self.width = len(grid[0])
        self.height = len(grid)
        self.config = config_data

        self.replant_queue = []
        self.rice_spawn_chance_per_tick = self._get_config(
            "entities", "rice", "spawning", "natural_spawn_chance", default=0.1
        )

    def _get_config(self, *keys, default=None):
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def add_to_replant_queue(self, grid_pos_yx: tuple):
        """Adds a grid coordinate (y, x) to the queue for rice replanting."""
        if grid_pos_yx not in self.replant_queue:
            self.replant_queue.append(grid_pos_yx)

    def process_replant_queue(self) -> list[tuple]:
        """Returns all coordinates (y, x) in the replant queue and clears it."""
        if not self.replant_queue:
            return []

        coords_to_replant = list(self.replant_queue)
        self.replant_queue.clear()
        return coords_to_replant

    def get_reproduction_spawn_location(
        self, parent_grid_pos_yx: tuple, occupied_tiles: set
    ) -> tuple | None:
        """Finds a valid adjacent walkable tile (y, x) for a newborn."""
        parent_y, parent_x = parent_grid_pos_yx
        possible_spawns = []
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                ny, nx = parent_y + dy, parent_x + dx
                if not (0 <= ny < self.height and 0 <= nx < self.width):
                    continue
                if (ny, nx) in occupied_tiles:
                    continue

                tile = self.grid[ny][nx]
                if tile.tile_move_speed_factor > 0:  # Is walkable
                    possible_spawns.append((ny, nx))

        return random.choice(possible_spawns) if possible_spawns else None

    def get_natural_rice_spawn_location(self, occupied_tiles: set) -> tuple | None:
        """Determines if and where (y, x) a new rice plant should spawn naturally."""
        if random.random() > self.rice_spawn_chance_per_tick:
            return None

        valid_spawn_tiles = []
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x].name == "Land" and (y, x) not in occupied_tiles:
                    is_adjacent_to_water = False
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < self.height and 0 <= nx < self.width:
                                if self.grid[ny][nx].name == "Water":
                                    is_adjacent_to_water = True
                                    break
                        if is_adjacent_to_water:
                            break
                    if is_adjacent_to_water:
                        valid_spawn_tiles.append((y, x))

        return random.choice(valid_spawn_tiles) if valid_spawn_tiles else None
