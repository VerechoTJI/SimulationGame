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
GRID_HEIGHT = 64
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


# Define our tile types
TILES = {
    "land": Tile("Land", ".", Colors.GREEN, 1.0),
    "water": Tile("Water", "~", Colors.BLUE, 0.0),
    "mountain": Tile("Mountain", "^", Colors.WHITE, 0.5),
}


# --- 2. Entity Definitions ---
class Entity:
    """Base class for all entities in the game."""

    id_counter = 0

    def __init__(self, name, symbol, pos_x, pos_y, max_age):
        self.id = Entity.id_counter
        Entity.id_counter += 1
        self.name = f"{name}_{self.id}"
        self.symbol = symbol

        # Position is in meters, not grid cells
        self.position = np.array([float(pos_x), float(pos_y)])

        self.age = 0
        self.max_age = max_age

    def tick(self, world):
        """Called once per game tick."""
        self.age += 1

    def is_alive(self):
        return self.age <= self.max_age

    def __str__(self):
        return f"{self.name} at {self.position.round(1)}"


class Human(Entity):
    def __init__(self, pos_x, pos_y):
        super().__init__("Human", "H", pos_x, pos_y, max_age=1200)
        self.move_speed = 1.4  # meters per tick (avg human walking speed)

    def tick(self, world):
        super().tick(world)

        # 1. Movement
        current_tile = world.get_tile_at_pos(self.position[0], self.position[1])
        effective_speed = self.move_speed * current_tile.tile_move_speed_factor

        if effective_speed > 0:
            # Move in a random direction
            angle = random.uniform(0, 2 * math.pi)
            move_vector = np.array([math.cos(angle), math.sin(angle)]) * effective_speed
            self.position += move_vector

            # Boundary check to keep human on the map
            max_x = GRID_WIDTH * TILE_SIZE_METERS
            max_y = GRID_HEIGHT * TILE_SIZE_METERS
            self.position[0] = np.clip(self.position[0], 0, max_x - 0.01)
            self.position[1] = np.clip(self.position[1], 0, max_y - 0.01)

        # 2. Interaction (Harvesting)
        for entity in world.entities:
            if isinstance(entity, Rice) and entity.matured:
                distance = np.linalg.norm(self.position - entity.position)
                if distance <= 1.0:  # Close is defined as <= 1 meter
                    print(
                        f"{Colors.YELLOW}{self.name} harvested and replanted {entity.name}.{Colors.RESET}"
                    )
                    entity.replant()
                    break  # Harvest only one rice plant per tick


class Rice(Entity):
    def __init__(self, pos_x, pos_y):
        super().__init__("Rice", "r", pos_x, pos_y, max_age=16)

    @property
    def matured(self):
        # Matures halfway through its life
        return self.age >= (self.max_age / 2)

    def tick(self, world):
        super().tick(world)
        # Update symbol based on maturity
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
        """Generates a map using Perlin noise."""
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
        """Gets the tile at a specific meter-based coordinate."""
        grid_x = int(pos_x / TILE_SIZE_METERS)
        grid_y = int(pos_y / TILE_SIZE_METERS)
        grid_x = np.clip(grid_x, 0, self.width - 1)
        grid_y = np.clip(grid_y, 0, self.height - 1)
        return self.grid[grid_y][grid_x]

    def spawn_entity(self, entity_type, x, y):
        # Convert grid coords to meter coords for spawning
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
        """Processes one tick of the simulation."""
        self.tick_count += 1

        # Tick every entity
        for entity in self.entities:
            entity.tick(self)

        # Remove dead entities
        dead_entities = [e for e in self.entities if not e.is_alive()]
        for entity in dead_entities:
            print(f"{Colors.RED}{entity.name} has died of old age.{Colors.RESET}")
            self.entities.remove(entity)

    def display(self):
        """Clears the screen and draws the world state."""
        os.system("cls" if os.name == "nt" else "clear")

        # Create a character grid for display
        display_grid = [
            [(tile.color + tile.symbol) for tile in row] for row in self.grid
        ]

        # Place entities on the display grid
        for entity in self.entities:
            grid_x = int(entity.position[0] / TILE_SIZE_METERS)
            grid_y = int(entity.position[1] / TILE_SIZE_METERS)

            # Ensure entity is within bounds for display
            if 0 <= grid_y < self.height and 0 <= grid_x < self.width:
                color = Colors.MAGENTA if isinstance(entity, Human) else Colors.YELLOW
                display_grid[grid_y][grid_x] = color + entity.symbol

        # Print the grid
        print("--- Simulation Game ---")
        for row in display_grid:
            print(" ".join(row) + Colors.RESET)

        print("-" * (self.width * 2))
        print(f"Tick: {self.tick_count} | Entities: {len(self.entities)}")
        print(
            f"Commands: sp [human|rice] [x] [y]  (e.g., 'sp human 32 32') | q to quit"
        )
        print("Log messages:")


# --- 4. Main Game Loop and Input Handling ---
def game_loop(world, command_queue):
    while True:
        # Check for commands from the input thread
        try:
            command = command_queue.get_nowait()
            if command.lower() in ["q", "quit", "exit"]:
                print("Exiting game.")
                os._exit(0)  # Force exit to stop all threads

            parts = command.split()
            # sp [entity] [x] [y]
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
            pass  # No commands, just continue the loop

        world.game_tick()
        world.display()
        time.sleep(TICK_SECONDS)


def input_handler(command_queue):
    while True:
        command = input("> ")
        command_queue.put(command)


if __name__ == "__main__":
    # Initialize World
    world = World(GRID_WIDTH, GRID_HEIGHT)

    # Create a queue for communication between threads
    cmd_queue = queue.Queue()

    # Start the input handler in a separate thread
    input_thread = threading.Thread(
        target=input_handler, args=(cmd_queue,), daemon=True
    )
    input_thread.start()

    # Initial setup message
    world.display()
    print("\nWelcome to the simulation!")
    print("The world map has been generated.")
    print("Use the command 'sp human 32 32' to spawn your first human.")

    # Start the main game loop
    try:
        game_loop(world, cmd_queue)
    except KeyboardInterrupt:
        print("\nGame interrupted by user. Exiting.")
        os._exit(0)
