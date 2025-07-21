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

    def add_to_replant_queue(self, grid_pos: tuple):
        """Adds a grid coordinate to the queue for rice replanting."""
        if grid_pos not in self.replant_queue:
            self.replant_queue.append(grid_pos)

    def process_replant_queue(self) -> list[tuple]:
        """Returns all coordinates in the replant queue and clears it."""
        if not self.replant_queue:
            return []

        coords_to_replant = list(self.replant_queue)
        self.replant_queue.clear()
        return coords_to_replant

    def get_reproduction_spawn_location(
        self, parent_grid_pos: tuple, occupied_tiles: set
    ) -> tuple | None:
        """Finds a valid adjacent walkable tile for a newborn."""
        x, y = parent_grid_pos
        possible_spawns = []
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                if (nx, ny) in occupied_tiles:
                    continue

                tile = self.grid[ny][nx]
                if tile.tile_move_speed_factor > 0:  # Is walkable
                    possible_spawns.append((nx, ny))

        return random.choice(possible_spawns) if possible_spawns else None

    def get_natural_rice_spawn_location(self, occupied_tiles: set) -> tuple | None:
        """Determines if and where a new rice plant should spawn naturally."""
        if random.random() > self.rice_spawn_chance_per_tick:
            return None

        valid_spawn_tiles = []
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x].name == "Land" and (x, y) not in occupied_tiles:
                    is_adjacent_to_water = False
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < self.width and 0 <= ny < self.height:
                                if self.grid[ny][nx].name == "Water":
                                    is_adjacent_to_water = True
                                    break
                        if is_adjacent_to_water:
                            break
                    if is_adjacent_to_water:
                        valid_spawn_tiles.append((x, y))

        return random.choice(valid_spawn_tiles) if valid_spawn_tiles else None
