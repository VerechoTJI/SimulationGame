import time
import os
import random
import math
import numpy as np
from perlin_noise import PerlinNoise
import threading
import queue

# --- Game Configuration ---
GRID_WIDTH = 64
GRID_HEIGHT = 32  # <-- Changed from 64 to 32
TICK_SECONDS = 3
TILE_SIZE_METERS = 10  # Each tile is 10x10 meters


# --- Helper for colored output ---
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


# --- 1. Tile Definitions ---
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


# --- 2. Entity Definitions ---
class Entity:
    id_counter = 0

    def __init__(self, name, symbol, pos_x, pos_y, max_age):
        self.id = Entity.id_counter
        Entity.id_counter += 1
        self.name = f"{name}_{self.id}"
        self.symbol = symbol
        self.position = np.array([float(pos_x), float(pos_y)])
        self.age = 0
        self.max_age = max_age

    def tick(self, world):
        self.age += 1

    def is_alive(self):
        return self.age <= self.max_age

    def __str__(self):
        return f"{self.name} at {self.position.round(1)}"


class Human(Entity):
    def __init__(self, pos_x, pos_y):
        super().__init__("Human", "H", pos_x, pos_y, max_age=1200)
        self.move_speed = 1.4
        self.destination = None  # <-- NEW: Human now has a destination

    def _pick_new_destination(self, world):
        """Picks a new random destination within the world boundaries."""
        max_x = world.width * TILE_SIZE_METERS
        max_y = world.height * TILE_SIZE_METERS
        dest_x = random.uniform(0, max_x)
        dest_y = random.uniform(0, max_y)
        self.destination = np.array([dest_x, dest_y])

    def tick(self, world):
        super().tick(world)

        # --- NEW MOVEMENT LOGIC ---

        # 1. Check for a destination. If there isn't one, or we've arrived, pick a new one.
        if self.destination is None:
            self._pick_new_destination(world)
            print(
                f"{Colors.CYAN}{self.name} decided to travel to a new destination: {self.destination.round(1)}{Colors.RESET}"
            )

        # 2. Calculate movement towards destination
        current_tile = world.get_tile_at_pos(self.position[0], self.position[1])
        effective_speed = self.move_speed * current_tile.tile_move_speed_factor

        if effective_speed > 0 and self.destination is not None:
            direction_vector = self.destination - self.position
            distance_to_destination = np.linalg.norm(direction_vector)

            # 3. Check if we have arrived at the destination
            if distance_to_destination < effective_speed:
                self.position = self.destination
                self.destination = None
                print(
                    f"{Colors.GREEN}{self.name} has reached their destination.{Colors.RESET}"
                )
            else:
                # Move towards the destination
                # Normalize the direction vector (make its length 1) and multiply by speed
                normalized_direction = direction_vector / distance_to_destination
                move_vector = normalized_direction * effective_speed
                self.position += move_vector

        # Boundary check remains a good safety measure
        max_x = GRID_WIDTH * TILE_SIZE_METERS
        max_y = GRID_HEIGHT * TILE_SIZE_METERS
        self.position[0] = np.clip(self.position[0], 0, max_x - 0.01)
        self.position[1] = np.clip(self.position[1], 0, max_y - 0.01)

        # 4. Interaction (Harvesting) - this logic is unchanged
        for entity in world.entities:
            if isinstance(entity, Rice) and entity.matured:
                distance = np.linalg.norm(self.position - entity.position)
                if distance <= 1.0:
                    print(
                        f"{Colors.YELLOW}{self.name} harvested and replanted {entity.name}.{Colors.RESET}"
                    )
                    entity.replant()
                    break


class Rice(Entity):
    def __init__(self, pos_x, pos_y):
        super().__init__("Rice", "r", pos_x, pos_y, max_age=16)

    @property
    def matured(self):
        return self.age >= (self.max_age / 2)

    def tick(self, world):
        super().tick(world)
        self.symbol = "R" if self.matured else "r"

    def replant(self):
        self.age = 0


# --- 3. The World ---
class World:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = self.generate_map()
        self.entities = []
        self.tick_count = 0

    def generate_map(self):
        noise = PerlinNoise(octaves=4, seed=random.randint(1, 10000))
        world_map = [[None for _ in range(self.width)] for _ in range(self.height)]

        print("Generating map...")
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
        grid_x = int(pos_x / TILE_SIZE_METERS)
        grid_y = int(pos_y / TILE_SIZE_METERS)
        grid_x = np.clip(grid_x, 0, self.width - 1)
        grid_y = np.clip(grid_y, 0, self.height - 1)
        return self.grid[grid_y][grid_x]

    def spawn_entity(self, entity_type, x, y):
        pos_x = (x + 0.5) * TILE_SIZE_METERS
        pos_y = (y + 0.5) * TILE_SIZE_METERS

        new_entity = None
        if entity_type.lower() == "human":
            new_entity = Human(pos_x, pos_y)
        elif entity_type.lower() == "rice":
            new_entity = Rice(pos_x, pos_y)

        if new_entity:
            self.entities.append(new_entity)
            print(
                f"{Colors.CYAN}Spawned {new_entity.name} at grid ({x}, {y}).{Colors.RESET}"
            )
        else:
            print(f"{Colors.RED}Unknown entity type: {entity_type}{Colors.RESET}")

    def game_tick(self):
        self.tick_count += 1

        # Tick every entity
        if self.entities:
            for entity in list(self.entities):
                entity.tick(self)

        # Remove dead entities
        dead_entities = [e for e in self.entities if not e.is_alive()]
        if dead_entities:
            for entity in dead_entities:
                print(f"{Colors.RED}{entity.name} has died of old age.{Colors.RESET}")
                self.entities.remove(entity)

    def display(self):
        os.system("cls" if os.name == "nt" else "clear")

        display_grid = [
            [(tile.color + tile.symbol) for tile in row] for row in self.grid
        ]

        for entity in self.entities:
            grid_x = int(entity.position[0] / TILE_SIZE_METERS)
            grid_y = int(entity.position[1] / TILE_SIZE_METERS)

            if 0 <= grid_y < self.height and 0 <= grid_x < self.width:
                color = Colors.MAGENTA if isinstance(entity, Human) else Colors.YELLOW
                display_grid[grid_y][grid_x] = color + entity.symbol

        print("--- Simulation Game ---")
        for row in display_grid:
            print(" ".join(row) + Colors.RESET)

        print("-" * (self.width * 2))
        print(f"Tick: {self.tick_count} | Entities: {len(self.entities)}")
        print(
            f"Commands: sp [human|rice] [x] [y]  (e.g., 'sp human 32 15') | q to quit"
        )
        print("Log messages:")


# --- 4. Main Game Loop and Input Handling ---
def game_loop(world, command_queue):
    while True:
        try:
            command = command_queue.get_nowait()
            if command.lower() in ["q", "quit", "exit"]:
                print("Exiting game.")
                os._exit(0)

            parts = command.split()
            if len(parts) == 4 and parts[0].lower() == "sp":
                try:
                    entity_type = parts[1]
                    x = int(parts[2])
                    y = int(parts[3])
                    world.spawn_entity(entity_type, x, y)
                except (ValueError, IndexError):
                    print(
                        f"{Colors.RED}Invalid spawn command. Use: sp [human|rice] [x] [y]{Colors.RESET}"
                    )
            else:
                print(f"{Colors.RED}Unknown command: '{command}'{Colors.RESET}")

        except queue.Empty:
            pass

        world.game_tick()
        world.display()
        time.sleep(TICK_SECONDS)


def input_handler(command_queue):
    while True:
        command = input("> ")
        command_queue.put(command)


if __name__ == "__main__":
    world = World(GRID_WIDTH, GRID_HEIGHT)
    cmd_queue = queue.Queue()

    input_thread = threading.Thread(
        target=input_handler, args=(cmd_queue,), daemon=True
    )
    input_thread.start()

    world.display()
    print("\nWelcome to the simulation!")
    print(f"The world (64x32) has been generated.")
    print("Use the command 'sp human 32 15' to spawn your first human.")

    try:
        game_loop(world, cmd_queue)
    except KeyboardInterrupt:
        print("\nGame interrupted by user. Exiting.")
        os._exit(0)
