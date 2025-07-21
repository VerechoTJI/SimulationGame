# domain/world.py

import random
import numpy as np
from perlin_noise import PerlinNoise

from .entity import Entity, Colors
from .tile import TILES
from .pathfinder import Pathfinder
from .entity_manager import EntityManager
from .spawning_manager import SpawningManager


class World:
    def __init__(self, width, height, tile_size, config_data: dict):
        self.width = width
        self.height = height
        self.tile_size_meters = tile_size
        self.config = config_data
        self.grid = self._generate_map()
        self.tick_count = 0
        self.log_messages = []
        self.pathfinder = Pathfinder(self.grid)
        self.entity_manager = EntityManager(config_data, self.tile_size_meters)
        self.spawning_manager = SpawningManager(self.grid, self.config)

    def spawn_entity(self, entity_type, x, y):
        """A simplified spawner that only delegates to the EntityManager."""
        if entity_type.lower() == "human":
            self.entity_manager.create_human(x, y)
        elif entity_type.lower() == "rice":
            self.entity_manager.create_rice(x, y)

    def game_tick(self):
        self.tick_count += 1
        entities_to_process = list(self.entity_manager.entities)

        # --- Spawning Phase ---
        # Get all currently occupied tiles once.
        occupied_tiles = {
            self.get_grid_position(e.position) for e in self.entity_manager.entities
        }

        # 1. Process replanting from the previous tick.
        for x, y in self.spawning_manager.process_replant_queue():
            new_rice = self.entity_manager.create_rice(x, y)
            self.add_log(
                f"{Colors.GREEN}A Rice plant was replanted at ({x}, {y}).{Colors.RESET}"
            )

        # 2. Process natural spawning for this tick.
        natural_spawn_coord = self.spawning_manager.get_natural_rice_spawn_location(
            occupied_tiles
        )
        if natural_spawn_coord:
            x, y = natural_spawn_coord
            new_rice = self.entity_manager.create_rice(x, y)
            self.add_log(
                f"{Colors.GREEN}A new Rice plant sprouted at ({x}, {y}).{Colors.RESET}"
            )

        # --- Action Phase ---
        for entity in entities_to_process:
            if entity.is_alive():
                entity.tick(self)

                # Handle Reproduction (Human-specific logic)
                if hasattr(entity, "can_reproduce") and entity.can_reproduce():
                    parent_grid_pos = self.get_grid_position(entity.position)

                    # Update occupied tiles for this check, in case new rice spawned
                    current_occupied = {
                        self.get_grid_position(e.position)
                        for e in self.entity_manager.entities
                    }

                    spawn_pos = self.spawning_manager.get_reproduction_spawn_location(
                        parent_grid_pos, current_occupied
                    )
                    if spawn_pos:
                        newborn_saturation = entity.reproduce()
                        spawn_x, spawn_y = spawn_pos
                        newborn = self.entity_manager.create_human(
                            spawn_x, spawn_y, initial_saturation=newborn_saturation
                        )
                        self.add_log(
                            f"{Colors.MAGENTA}{entity.name} has given birth to {newborn.name}!{Colors.RESET}"
                        )

        # --- Cleanup Phase ---
        removed_entities = self.entity_manager.cleanup_dead_entities()
        for entity in removed_entities:
            # If an eaten rice is removed, queue it for replanting on the NEXT tick.
            if hasattr(entity, "is_eaten") and entity.is_eaten:
                grid_pos = self.get_grid_position(entity.position)
                self.spawning_manager.add_to_replant_queue(grid_pos)

            # Log deaths
            if hasattr(entity, "saturation"):  # It's a Human
                death_reason = (
                    "of old age" if entity.age > entity.max_age else "from starvation"
                )
                self.add_log(
                    f"{Colors.RED}{entity.name} has died {death_reason}.{Colors.RESET}"
                )

    def add_log(self, message):
        self.log_messages.append(message)
        if len(self.log_messages) > 99:
            self.log_messages.pop(0)

    def _generate_map(self):
        # Use a fixed seed from config if available, otherwise a random one.
        seed = self._get_config(
            "simulation", "map_seed", default=random.randint(1, 10000)
        )
        noise = PerlinNoise(octaves=4, seed=seed)
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

    def _get_config(self, *keys, default=None):
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
