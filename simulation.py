import time
import os
import random
import math
import numpy as np
from perlin_noise import PerlinNoise
import threading
import queue
import sys

# --- Platform-specific modules for non-blocking input ---
try:
    # Unix-like systems (Linux, macOS)
    import tty
    import termios
    import select

    ON_WINDOWS = False
except ImportError:
    # Windows
    import msvcrt

    ON_WINDOWS = True

# --- Game Configuration ---
GRID_WIDTH = 64
GRID_HEIGHT = 32
TICK_SECONDS = 3
TILE_SIZE_METERS = 10


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


# --- NEW: Non-Blocking Input Class ---
class NonBlockingInput:
    """A class to handle non-blocking keyboard input."""

    def __init__(self):
        if not ON_WINDOWS:
            # Save the old terminal settings
            self.old_settings = termios.tcgetattr(sys.stdin)
            # Set the terminal to cbreak mode (reads characters instantly)
            tty.setcbreak(sys.stdin.fileno())

    def get_char(self):
        """Gets a single character from stdin without blocking."""
        if ON_WINDOWS:
            if msvcrt.kbhit():
                return msvcrt.getch().decode("utf-8")
            return None
        else:
            # Check if there is data to be read on stdin
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                return sys.stdin.read(1)
            return None

    def restore_terminal(self):
        """Restores the terminal to its original state."""
        if not ON_WINDOWS:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)


# --- Tile and Entity Definitions (Unchanged) ---
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
        self.path = []  # <-- NEW: Human now has a path list

    def _find_new_path(self, world):
        """Picks a new random destination and asks the world to find a path to it."""
        self.path = []

        # Try a few times to find a path to a random valid location
        for _ in range(10):  # Try 10 times to prevent infinite loop
            dest_x = random.randint(0, world.width - 1)
            dest_y = random.randint(0, world.height - 1)

            start_grid_x = int(self.position[0] / TILE_SIZE_METERS)
            start_grid_y = int(self.position[1] / TILE_SIZE_METERS)

            # Make sure we don't try to pathfind from an invalid tile
            if world.grid[start_grid_y][start_grid_x].tile_move_speed_factor == 0:
                # If stuck in water, just wander randomly to hopefully get out
                self.destination = None  # Fallback to old random walk
                return

            path = world.find_path((start_grid_x, start_grid_y), (dest_x, dest_y))

            if path:
                self.path = path
                world.add_log(
                    f"{Colors.CYAN}{self.name} is now heading to grid cell ({dest_x}, {dest_y}).{Colors.RESET}"
                )
                return

        world.add_log(
            f"{Colors.YELLOW}{self.name} couldn't find a path and is wandering.{Colors.RESET}"
        )

    def tick(self, world):
        super().tick(world)

        # 1. If we don't have a path, find one.
        if not self.path:
            self._find_new_path(world)
            # If still no path after trying, do nothing this tick
            if not self.path:
                return

        # 2. Get the next step in our path
        target_grid_pos = self.path[0]
        # Convert grid coordinate to world meter coordinate (center of tile)
        target_pos = np.array(
            [
                (target_grid_pos[0] + 0.5) * TILE_SIZE_METERS,
                (target_grid_pos[1] + 0.5) * TILE_SIZE_METERS,
            ]
        )

        # 3. Move towards the next step
        current_tile = world.get_tile_at_pos(self.position[0], self.position[1])
        effective_speed = self.move_speed * current_tile.tile_move_speed_factor

        if effective_speed > 0:
            direction_vector = target_pos - self.position
            distance_to_target = np.linalg.norm(direction_vector)

            # 4. If we are close enough to the next step, pop it from the path
            if distance_to_target < effective_speed:
                self.position = target_pos  # Snap to target
                self.path.pop(0)
                if not self.path:
                    world.add_log(
                        f"{Colors.GREEN}{self.name} has reached their destination.{Colors.RESET}"
                    )
            else:
                # Move towards the target
                normalized_direction = direction_vector / distance_to_target
                move_vector = normalized_direction * effective_speed
                self.position += move_vector

        # Interaction (Harvesting) logic is unchanged
        for entity in world.entities:
            if isinstance(entity, Rice) and entity.matured:
                if np.linalg.norm(self.position - entity.position) <= 1.0:
                    world.add_log(
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


# --- The World Class ---
class World:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = self.generate_map()
        self.entities = []
        self.tick_count = 0
        self.log_messages = []  # <-- NEW: A buffer for log messages

    def add_log(self, message):
        """Adds a message to the log queue to be displayed on the next frame."""
        self.log_messages.append(message)
        # Keep the log from getting too long
        if len(self.log_messages) > 10:
            self.log_messages.pop(0)

    def generate_map(self):
        # ... (unchanged)
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
        # ... (unchanged)
        grid_x = int(pos_x / TILE_SIZE_METERS)
        grid_y = int(pos_y / TILE_SIZE_METERS)
        grid_x = np.clip(grid_x, 0, self.width - 1)
        grid_y = np.clip(grid_y, 0, self.height - 1)
        return self.grid[grid_y][grid_x]

    def spawn_entity(self, entity_type, x, y):
        # ... (unchanged, but now uses add_log)
        pos_x = (x + 0.5) * TILE_SIZE_METERS
        pos_y = (y + 0.5) * TILE_SIZE_METERS
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

    def game_tick(self):
        # ... (unchanged, but now uses add_log)
        self.tick_count += 1
        if self.entities:
            for entity in list(self.entities):
                entity.tick(self)
        dead_entities = [e for e in self.entities if not e.is_alive()]
        if dead_entities:
            for entity in dead_entities:
                self.add_log(
                    f"{Colors.RED}{entity.name} has died of old age.{Colors.RESET}"
                )
                self.entities.remove(entity)

    def display(self, current_input):
        """Clears the screen and draws the entire world state, including user input."""
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

        # Build the output string before printing for a flicker-free update
        output = "--- Simulation Game ---\n"
        for row in display_grid:
            output += " ".join(row) + Colors.RESET + "\n"

        output += "-" * (self.width * 2) + "\n"
        output += f"Tick: {self.tick_count} | Entities: {len(self.entities)}\n"
        output += f"Commands: sp [human|rice] [x] [y] | q to quit\n"
        output += "Log messages:\n"
        for msg in self.log_messages:
            output += msg + "\n"

        # Display the current user input at the bottom
        output += f"\n> {current_input}"

        # Print the entire buffer at once
        sys.stdout.write(output)
        sys.stdout.flush()


# --- Main Game Loop and Input Handling ---
def game_loop(world, command_queue, shared_state):
    """The main game thread. Now separates rendering from ticking."""
    last_tick_time = time.time()

    while True:
        # Check for commands from the input thread
        try:
            command = command_queue.get_nowait()
            if command.lower() in ["q", "quit", "exit"]:
                return  # Signal to main thread to exit gracefully

            parts = command.split()
            if len(parts) == 4 and parts[0].lower() == "sp":
                try:
                    world.spawn_entity(parts[1], int(parts[2]), int(parts[3]))
                except (ValueError, IndexError):
                    world.add_log(
                        f"{Colors.RED}Invalid spawn command. Use: sp [human|rice] [x] [y]{Colors.RESET}"
                    )
            else:
                world.add_log(f"{Colors.RED}Unknown command: '{command}'{Colors.RESET}")
        except queue.Empty:
            pass

        # Check if it's time for a game logic tick
        current_time = time.time()
        if current_time - last_tick_time >= TICK_SECONDS:
            world.game_tick()
            last_tick_time = current_time

        # Get the current input from the shared state to display it
        with shared_state["lock"]:
            current_input_str = "".join(shared_state["input_buffer"])

        # Display/render on every loop iteration for responsive input
        world.display(current_input_str)

        # Sleep for a short duration to prevent 100% CPU usage
        time.sleep(0.05)


def input_handler(command_queue, shared_state):
    """The dedicated input thread. Reads single chars and updates a shared buffer."""
    nb_input = NonBlockingInput()
    try:
        while True:
            char = nb_input.get_char()
            if char:
                with shared_state["lock"]:
                    if char in ("\r", "\n"):  # Enter key
                        command = "".join(shared_state["input_buffer"])
                        command_queue.put(command)
                        shared_state["input_buffer"].clear()
                    elif char in ("\x7f", "\b"):  # Backspace
                        if shared_state["input_buffer"]:
                            shared_state["input_buffer"].pop()
                    else:
                        shared_state["input_buffer"].append(char)

            # Small sleep to prevent this thread from using 100% CPU
            time.sleep(0.01)
    finally:
        nb_input.restore_terminal()


def find_path(self, start_pos, end_pos):
    """
    Finds a path from start_pos to end_pos using A* algorithm.
    Positions are in grid coordinates (e.g., (x, y)).
    """

    def get_move_cost(grid_pos):
        tile = self.grid[grid_pos[1]][grid_pos[0]]
        # Inverse of speed factor. Water (0) is infinite cost.
        if tile.tile_move_speed_factor == 0:
            return float("inf")
        return 1.0 / tile.tile_move_speed_factor

    start_node = (start_pos[0], start_pos[1])
    end_node = (end_pos[0], end_pos[1])

    # A* requires a priority queue (min-heap) for the open set
    open_set = []
    heapq.heappush(open_set, (0, start_node))  # (f_score, node)

    came_from = {}
    g_score = {start_node: 0}  # Cost from start to current node
    f_score = {
        start_node: np.linalg.norm(np.array(start_node) - np.array(end_node))
    }  # g_score + heuristic

    while open_set:
        current = heapq.heappop(open_set)[1]

        if current == end_node:
            # Reconstruct path
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            return path[::-1]  # Return reversed path

        # Check neighbors (including diagonals)
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue

                neighbor = (current[0] + dx, current[1] + dy)

                if not (
                    0 <= neighbor[0] < self.width and 0 <= neighbor[1] < self.height
                ):
                    continue

                # The cost to move to the neighbor
                move_cost = get_move_cost(neighbor)
                if move_cost == float("inf"):
                    continue  # Impassable terrain

                # Diagonal moves are slightly more expensive
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

    return None  # No path found


if __name__ == "__main__":
    # Add heapq for our pathfinding algorithm's priority queue
    import heapq

    # A shared dictionary to pass state between threads
    shared_state = {"input_buffer": [], "lock": threading.Lock()}

    world = World(GRID_WIDTH, GRID_HEIGHT)
    cmd_queue = queue.Queue()

    # We must restore the terminal even if the program crashes
    nb_input_for_cleanup = NonBlockingInput()

    try:
        # Initial display
        world.display("")
        world.add_log("Welcome to the simulation!")
        world.add_log("The world has been generated.")
        world.add_log("Use the command 'sp human 32 15' to start.")
        world.display("")  # Display welcome messages

        input_thread = threading.Thread(
            target=input_handler, args=(cmd_queue, shared_state), daemon=True
        )
        input_thread.start()

        game_loop(world, cmd_queue, shared_state)

    except KeyboardInterrupt:
        print("\nGame interrupted by user.")
    finally:
        # IMPORTANT: Always restore terminal settings on exit
        print("Restoring terminal and exiting.")
        nb_input_for_cleanup.restore_terminal()
        os._exit(0)
