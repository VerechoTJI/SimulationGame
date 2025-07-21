# domain/world.py

import random
import numpy as np
from perlin_noise import PerlinNoise

from .entity import Entity, Colors
from .tile import TILES
from .pathfinder import Pathfinder
from .entity_manager import EntityManager


class World:
    def __init__(self, width, height, tile_size, config_data: dict):
        self.width = width
        self.height = height
        self.tile_size_meters = tile_size
        self.config = config_data
        self.grid = self._generate_map()
        self.tick_count = 0
        self.log_messages = []
        self.replant_queue = []  # <-- ADD THIS LINE
        self.rice_spawn_chance_per_tick = self.get_config_value(
            "entities", "rice", "spawning", "natural_spawn_chance"
        )

        self.pathfinder = Pathfinder(self.grid)
        self.entity_manager = EntityManager(config_data, self.tile_size_meters)

    def spawn_entity(self, entity_type, x, y):
        """Delegates entity creation to the EntityManager."""
        new_entity = None
        if entity_type.lower() == "human":
            new_entity = self.entity_manager.create_human(x, y)
        elif entity_type.lower() == "rice":
            new_entity = self.entity_manager.create_rice(x, y)

        if new_entity:
            self.add_log(
                f"{Colors.CYAN}Spawned {new_entity.name} at grid ({x}, {y}).{Colors.RESET}"
            )
        else:
            self.add_log(
                f"{Colors.RED}Unknown entity type: {entity_type}{Colors.RESET}"
            )

    def game_tick(self):
        # Snapshot entities from the manager at the start of the tick.
        entities_to_process = list(self.entity_manager.entities)

        # --- Spawning Phase (handled by World) ---
        if self.replant_queue:
            for x, y in self.replant_queue:
                self.spawn_entity("rice", x, y)
                self.log_messages[-1] = (
                    f"{Colors.GREEN}A new Rice plant was replanted at ({x}, {y}).{Colors.RESET}"
                )
            self.replant_queue.clear()
        self.natural_spawning_tick()

        # --- Action Phase (delegated to entities) ---
        self.tick_count += 1
        for entity in entities_to_process:
            if entity.is_alive():
                # NOTE: entity.tick() still needs access to the world for context
                entity.tick(self)

                # Handle Reproduction
                if hasattr(entity, "can_reproduce") and entity.can_reproduce():
                    parent_grid_pos = self.get_grid_position(entity.position)
                    spawn_grid_pos = self._find_adjacent_walkable_tile(parent_grid_pos)
                    if spawn_grid_pos:
                        newborn_saturation = entity.reproduce()
                        spawn_x, spawn_y = spawn_grid_pos
                        newborn = self.entity_manager.create_human(
                            spawn_x, spawn_y, initial_saturation=newborn_saturation
                        )
                        self.add_log(
                            f"{Colors.MAGENTA}{entity.name} has given birth to {newborn.name}!{Colors.RESET}"
                        )

        # --- Cleanup Phase (delegated to EntityManager) ---
        removed_entities = self.entity_manager.cleanup_dead_entities()
        if removed_entities:
            for entity in removed_entities:
                # Spawning logic remains in World: check if a removed rice needs replanting
                if hasattr(entity, "is_eaten") and entity.is_eaten:
                    grid_pos = self.get_grid_position(entity.position)
                    if grid_pos not in self.replant_queue:
                        self.replant_queue.append(grid_pos)

                # Logging remains in World
                if hasattr(entity, "saturation"):  # It's a Human
                    death_reason = "of old age"
                    if entity.saturation <= 0:
                        death_reason = "from starvation"
                    self.add_log(
                        f"{Colors.RED}{entity.name} has died {death_reason}.{Colors.RESET}"
                    )

    # --- All other methods are unchanged ---
    def _find_adjacent_walkable_tile(self, grid_pos):
        occupied_tiles = {
            self.get_grid_position(e.position) for e in self.entity_manager.entities
        }
        x, y = grid_pos
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
                if tile.tile_move_speed_factor > 0:
                    possible_spawns.append((nx, ny))
        if possible_spawns:
            return random.choice(possible_spawns)
        return None

    def natural_spawning_tick(self):
        if random.random() > self.rice_spawn_chance_per_tick:
            return
        valid_spawn_tiles = []
        occupied_tiles = {
            self.get_grid_position(e.position) for e in self.entity_manager.entities
        }
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
        if valid_spawn_tiles:
            spawn_x, spawn_y = random.choice(valid_spawn_tiles)
            self.spawn_entity("rice", spawn_x, spawn_y)
            self.log_messages[-1] = (
                f"{Colors.GREEN}A new Rice plant sprouted at ({spawn_x}, {spawn_y}).{Colors.RESET}"
            )

    def add_log(self, message):
        self.log_messages.append(message)
        if len(self.log_messages) > 99:
            self.log_messages.pop(0)

    def _generate_map(self):
        noise = PerlinNoise(octaves=4, seed=random.randint(1, 10000))
        world_map = [[None for _ in range(self.width)] for _ in range(self.height)]
        for y in range(self.height):
            for x in range(self.width):
                noise_val = noise([x / self.width, y / self.height])
                if noise_val < -0.1:
                    world_map[y][x] = TILES["water"]
                elif noise_val > 0.25:
                    world_map[y][x] = TILES["mountain"]
                else:
                    world_map[y][x] = TILES["land"]
        return world_map

    def get_tile_at_pos(self, pos_x, pos_y):
        grid_x = int(pos_x / self.tile_size_meters)
        grid_y = int(pos_y / self.tile_size_meters)
        grid_x = np.clip(grid_x, 0, self.width - 1)
        grid_y = np.clip(grid_y, 0, self.height - 1)
        return self.grid[grid_y][grid_x]

    def find_path(self, start_pos, end_pos):
        """Delegates pathfinding to the Pathfinder service."""
        return self.pathfinder.find_path(start_pos, end_pos)

    def get_grid_position(self, world_position):
        grid_x = int(world_position[0] / self.tile_size_meters)
        grid_y = int(world_position[1] / self.tile_size_meters)
        grid_x = np.clip(grid_x, 0, self.width - 1)
        grid_y = np.clip(grid_y, 0, self.height - 1)
        return (grid_x, grid_y)
