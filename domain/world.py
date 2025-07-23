# domain/world.py

import random
import numpy as np
from perlin_noise import PerlinNoise

from .entity import Entity, Colors
from .tile import TILES
from .pathfinder import Pathfinder
from .entity_manager import EntityManager
from .spawning_manager import SpawningManager
from .flow_field_manager import FlowFieldManager
from .rice import Rice


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
        self.flow_field_manager = FlowFieldManager(self.grid)

        self.food_flow_field = np.zeros((self.height, self.width, 2), dtype=np.int8)
        self._flow_field_update_interval = self._get_config(
            "simulation", "flow_field_update_interval", default=100
        )
        self._ticks_since_flow_field_update = self._flow_field_update_interval

    def spawn_entity(self, entity_type, pos_y, pos_x):
        """A simplified spawner that delegates to the EntityManager using (y, x) format."""
        if entity_type.lower() == "human":
            self.entity_manager.create_human(pos_y, pos_x)
        elif entity_type.lower() == "rice":
            self.entity_manager.create_rice(pos_y, pos_x)

    def game_tick(self):
        self.tick_count += 1
        entities_to_process = list(self.entity_manager.entities)

        if self._ticks_since_flow_field_update >= self._flow_field_update_interval:
            self._ticks_since_flow_field_update = 0
            self._update_food_flow_field()
        else:
            self._ticks_since_flow_field_update += 1

        occupied_tiles = {
            self.get_grid_position(e.position) for e in self.entity_manager.entities
        }

        for pos_y, pos_x in self.spawning_manager.process_replant_queue():
            self.entity_manager.create_rice(pos_y, pos_x)
            self.add_log(
                f"{Colors.GREEN}A Rice plant was replanted at ({pos_y}, {pos_x}).{Colors.RESET}"
            )

        natural_spawn_coord = self.spawning_manager.get_natural_rice_spawn_location(
            occupied_tiles
        )
        if natural_spawn_coord:
            pos_y, pos_x = natural_spawn_coord
            self.entity_manager.create_rice(pos_y, pos_x)
            self.add_log(
                f"{Colors.GREEN}A new Rice plant sprouted at ({pos_y}, {pos_x}).{Colors.RESET}"
            )

        for entity in entities_to_process:
            if entity.is_alive():
                entity.tick(self)

                if hasattr(entity, "can_reproduce") and entity.can_reproduce():
                    parent_grid_pos_yx = self.get_grid_position(entity.position)
                    current_occupied = {
                        self.get_grid_position(e.position)
                        for e in self.entity_manager.entities
                    }
                    spawn_pos_yx = (
                        self.spawning_manager.get_reproduction_spawn_location(
                            parent_grid_pos_yx, current_occupied
                        )
                    )
                    if spawn_pos_yx:
                        newborn_saturation = entity.reproduce()
                        spawn_y, spawn_x = spawn_pos_yx
                        newborn = self.entity_manager.create_human(
                            spawn_y, spawn_x, initial_saturation=newborn_saturation
                        )
                        self.add_log(
                            f"{Colors.MAGENTA}{entity.name} has given birth to {newborn.name}!{Colors.RESET}"
                        )

        removed_entities = self.entity_manager.cleanup_dead_entities()
        for entity in removed_entities:
            if hasattr(entity, "is_eaten") and entity.is_eaten:
                grid_pos_yx = self.get_grid_position(entity.position)
                self.spawning_manager.add_to_replant_queue(grid_pos_yx)

            if hasattr(entity, "saturation"):
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

    def get_tile_at_pos(self, pos_y, pos_x):
        """Gets tile using (y, x) world coordinates."""
        grid_y = int(pos_y / self.tile_size_meters)
        grid_x = int(pos_x / self.tile_size_meters)
        grid_y = np.clip(grid_y, 0, self.height - 1)
        grid_x = np.clip(grid_x, 0, self.width - 1)
        return self.grid[grid_y][grid_x]

    def find_path(self, start_pos_yx, end_pos_yx):
        """Delegates pathfinding to the Pathfinder service using (y, x) tuples."""
        return self.pathfinder.find_path(start_pos_yx, end_pos_yx)

    def get_grid_position(self, world_position_yx):
        """Converts world position [y, x] to grid tuple (y, x)."""
        grid_y = int(world_position_yx[0] / self.tile_size_meters)
        grid_x = int(world_position_yx[1] / self.tile_size_meters)
        grid_y = np.clip(grid_y, 0, self.height - 1)
        grid_x = np.clip(grid_x, 0, self.width - 1)
        return (grid_y, grid_x)

    def _get_config(self, *keys, default=None):
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def _update_food_flow_field(self):
        """Finds all mature rice and regenerates the food flow field using (y, x)."""
        food_sources_yx = [
            self.get_grid_position(e.position)
            for e in self.entity_manager.entities
            if isinstance(e, Rice) and e.matured
        ]
        self.food_flow_field = self.flow_field_manager.generate_flow_field(
            food_sources_yx
        )
        self.add_log(f"{Colors.BLUE}Food flow field recalculated.{Colors.RESET}")

    def get_flow_vector_at_position(self, world_position_yx):
        """Gets the flow vector at a world position using (y, x) format."""
        grid_y, grid_x = self.get_grid_position(world_position_yx)
        return self.food_flow_field[grid_y, grid_x]
