# domain/world.py

import random
import heapq
import numpy as np
from perlin_noise import PerlinNoise

from .entity import Entity, Colors
from .human import Human
from .rice import Rice
from .object_pool import ObjectPool


class World:
    def __init__(self, width, height, tile_size, config_data: dict):
        self.width = width
        self.height = height
        self.tile_size_meters = tile_size
        self.config = config_data
        self.grid = self._generate_map()
        self.entities = []
        self.tick_count = 0
        self.log_messages = []
        self.replant_queue = []  # <-- ADD THIS LINE
        self.rice_spawn_chance_per_tick = self.get_config_value(
            "entities", "rice", "spawning", "natural_spawn_chance"
        )

        # --- NEW: Initialize Object Pools ---
        # The factories create a single dummy instance that the pool uses for type info.
        # The objects are immediately configured via reset() when pool.get() is called.
        self._human_pool = ObjectPool(
            factory=lambda: Human(
                0, 0, **self.get_config_value("entities", "human", "attributes")
            )
        )
        self._rice_pool = ObjectPool(
            factory=lambda: Rice(
                0, 0, **self.get_config_value("entities", "rice", "attributes")
            )
        )

    def _create_human(self, pos_x, pos_y, initial_saturation=None):
        """Internal factory for creating a Human instance using the object pool."""
        human_attributes = self.get_config_value("entities", "human", "attributes")
        # Get a recycled or new Human, with its state correctly reset
        human = self._human_pool.get(pos_x=pos_x, pos_y=pos_y, **human_attributes)
        if initial_saturation is not None:
            # For newborns, override the default full saturation
            human.saturation = initial_saturation
        return human

    def spawn_entity(self, entity_type, x, y):
        """Creates an entity of a given type at a grid location using object pools."""
        pos_x = (x + 0.5) * self.tile_size_meters
        pos_y = (y + 0.5) * self.tile_size_meters
        new_entity = None

        if entity_type.lower() == "human":
            # Just call the existing factory method which now uses the pool
            new_entity = self._create_human(pos_x, pos_y)
        elif entity_type.lower() == "rice":
            rice_attributes = self.get_config_value("entities", "rice", "attributes")
            new_entity = self._rice_pool.get(
                pos_x=pos_x, pos_y=pos_y, **rice_attributes
            )

        if new_entity:
            self.entities.append(new_entity)
            self.add_log(
                f"{Colors.CYAN}Spawned {new_entity.name} at grid ({x}, {y}).{Colors.RESET}"
            )
        else:
            self.add_log(
                f"{Colors.RED}Unknown entity type: {entity_type}{Colors.RESET}"
            )

    def game_tick(self):
        # Snapshot entities at the very beginning of the tick.
        # Only these entities will perform actions and age this tick.
        entities_to_process = list(self.entities)

        # --- Spawning Phase ---
        # New entities are added to self.entities but will not be in `entities_to_process`.

        # 1. Process replanting from events of the PREVIOUS tick.
        if self.replant_queue:
            for x, y in self.replant_queue:
                self.spawn_entity("rice", x, y)
                # Overwrite the generic spawn message with a more specific one for clarity.
                self.log_messages[-1] = (
                    f"{Colors.GREEN}A new Rice plant was replanted at ({x}, {y}).{Colors.RESET}"
                )
            self.replant_queue.clear()

        # 2. Process this tick's natural spawning.
        self.natural_spawning_tick()

        # --- Action Phase ---
        # This phase processes ONLY the entities that existed at the start of the tick.
        self.tick_count += 1
        newly_born = []

        for entity in entities_to_process:
            if entity.is_alive():
                entity.tick(self)  # Aging and other actions happen here.

                # Handle Reproduction
                if isinstance(entity, Human) and entity.can_reproduce():
                    parent_grid_pos = self.get_grid_position(entity.position)
                    spawn_grid_pos = self._find_adjacent_walkable_tile(parent_grid_pos)
                    if spawn_grid_pos:
                        newborn_saturation = entity.reproduce()
                        spawn_x, spawn_y = spawn_grid_pos
                        pos_x = (spawn_x + 0.5) * self.tile_size_meters
                        pos_y = (spawn_y + 0.5) * self.tile_size_meters
                        newborn = self._create_human(
                            pos_x, pos_y, initial_saturation=newborn_saturation
                        )
                        newly_born.append(newborn)
                        self.add_log(
                            f"{Colors.MAGENTA}{entity.name} has given birth to {newborn.name}!{Colors.RESET}"
                        )

        # Add newborns to the main list now that the action phase is over.
        if newly_born:
            self.entities.extend(newly_born)

        # --- Cleanup Phase ---
        # This must check ALL entities, as a newly spawned rice could theoretically
        # be eaten by a Human in the same tick.
        removed_entities = [e for e in self.entities if not e.is_alive()]
        if removed_entities:
            for entity in removed_entities:
                # If an eaten rice is removed, queue it for replanting on the NEXT tick.
                if isinstance(entity, Rice) and entity.is_eaten:
                    grid_pos = self.get_grid_position(entity.position)
                    # This check prevents duplicate queueing in rare edge cases.
                    if grid_pos not in self.replant_queue:
                        self.replant_queue.append(grid_pos)

                if isinstance(entity, Human):
                    death_reason = "of old age"
                    if entity.saturation <= 0:
                        death_reason = "from starvation"
                    self.add_log(
                        f"{Colors.RED}{entity.name} has died {death_reason}.{Colors.RESET}"
                    )

                # Remove from active simulation and return to pool.
                self.entities.remove(entity)
                entity.release()

    # --- All other methods are unchanged ---
    def _find_adjacent_walkable_tile(self, grid_pos):
        occupied_tiles = {self.get_grid_position(e.position) for e in self.entities}
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

    def get_config_value(self, *keys, default=None):
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def natural_spawning_tick(self):
        if random.random() > self.rice_spawn_chance_per_tick:
            return
        valid_spawn_tiles = []
        occupied_tiles = {self.get_grid_position(e.position) for e in self.entities}
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

    def find_nearest_entity(self, origin_pos, entity_type, predicate=None):
        closest_entity = None
        min_dist_sq = float("inf")
        for entity in self.entities:
            if isinstance(entity, entity_type):
                if predicate and not predicate(entity):
                    continue
                dist_sq = np.sum((entity.position - origin_pos) ** 2)
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    closest_entity = entity
        return closest_entity

    def find_path(self, start_pos, end_pos):
        def get_move_cost(grid_pos):
            tile = self.grid[grid_pos[1]][grid_pos[0]]
            if tile.tile_move_speed_factor == 0:
                return float("inf")
            return 1.0 / tile.tile_move_speed_factor

        start_node, end_node = tuple(start_pos), tuple(end_pos)
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

    def get_grid_position(self, world_position):
        grid_x = int(world_position[0] / self.tile_size_meters)
        grid_y = int(world_position[1] / self.tile_size_meters)
        grid_x = np.clip(grid_x, 0, self.width - 1)
        grid_y = np.clip(grid_y, 0, self.height - 1)
        return (grid_x, grid_y)
