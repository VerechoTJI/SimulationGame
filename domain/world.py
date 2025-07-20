# domain/world.py
import random
import heapq
import numpy as np
from perlin_noise import PerlinNoise

from .entity import Entity, Colors
from .human import Human
from .rice import Rice


class Tile:
    def __init__(self, name, symbol, color, move_speed_factor):
        self.name = name
        self.symbol = symbol
        self.color = color
        self.tile_move_speed_factor = move_speed_factor


TILES = {
    "land": Tile("Land", ".", Colors.GREEN, 1.0),
    "water": Tile("Water", "~", Colors.BLUE, 0.0),
    "mountain": Tile("Mountain", "^", Colors.WHITE, 0.5),
}


class World:
    def __init__(self, width, height, tile_size):
        self.width = width
        self.height = height
        self.tile_size_meters = tile_size
        self.grid = self._generate_map()
        self.entities = []
        self.tick_count = 0
        self.log_messages = []

    def add_log(self, message):
        self.log_messages.append(message)
        if len(self.log_messages) > 10:
            self.log_messages.pop(0)

    def _generate_map(self):
        # ... (Method is identical to original)
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

    # All other methods from the original World class remain here:
    # get_tile_at_pos, spawn_entity, find_path, game_tick
    # They are unchanged, except they now live in this file.
    def get_tile_at_pos(self, pos_x, pos_y):
        grid_x = int(pos_x / self.tile_size_meters)
        grid_y = int(pos_y / self.tile_size_meters)
        grid_x = np.clip(grid_x, 0, self.width - 1)
        grid_y = np.clip(grid_y, 0, self.height - 1)
        return self.grid[grid_y][grid_x]

    def spawn_entity(self, entity_type, x, y):
        pos_x = (x + 0.5) * self.tile_size_meters
        pos_y = (y + 0.5) * self.tile_size_meters
        new_entity = None
        if entity_type.lower() == "human":
            new_entity = Human(pos_x, pos_y)
        elif entity_type.lower() == "rice":
            new_entity = Rice(pos_x, pos_y)
        if new_entity:
            self.entities.append(new_entity)
            self.add_log(
                f"{Colors.CYAN}Spawned {new_entity.name} at grid ({x}, {y}).{Colors.RESET}"
            )
        else:
            self.add_log(
                f"{Colors.RED}Unknown entity type: {entity_type}{Colors.RESET}"
            )

    def find_nearest_entity(self, origin_pos, entity_type, predicate=None):
        """
        Finds the closest entity of a given type to a position that satisfies a predicate.
        """
        closest_entity = None
        min_dist_sq = float("inf")

        for entity in self.entities:
            # Check if it's the right type
            if isinstance(entity, entity_type):
                # If there's a predicate, check if the entity satisfies it
                if predicate and not predicate(entity):
                    continue  # Skip if it doesn't meet the condition

                # If we get here, the entity is a valid candidate
                dist_sq = np.sum((entity.position - origin_pos) ** 2)
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    closest_entity = entity

        return closest_entity

    def find_path(self, start_pos, end_pos):
        # ... (Method is identical to original)
        def get_move_cost(grid_pos):
            tile = self.grid[grid_pos[1]][grid_pos[0]]
            if tile.tile_move_speed_factor == 0:
                return float("inf")
            return 1.0 / tile.tile_move_speed_factor

        start_node = (start_pos[0], start_pos[1])
        end_node = (end_pos[0], end_pos[1])
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
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
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
                        heuristic = np.linalg.norm(
                            np.array(neighbor) - np.array(end_node)
                        )
                        f_score[neighbor] = tentative_g_score + heuristic
                        if neighbor not in [i[1] for i in open_set]:
                            heapq.heappush(open_set, (f_score[neighbor], neighbor))
        return None

    def game_tick(self):
        self.tick_count += 1
        if self.entities:
            for entity in list(self.entities):
                entity.tick(self)

        dead_entities = [e for e in self.entities if not e.is_alive()]
        if dead_entities:
            for entity in dead_entities:
                death_reason = "of old age"
                # Check if the entity is a Human before checking its attributes
                if isinstance(entity, Human) and entity.saturation <= 0:
                    death_reason = "from starvation"

                self.add_log(
                    f"{Colors.RED}{entity.name} has died {death_reason}.{Colors.RESET}"
                )
                self.entities.remove(entity)
