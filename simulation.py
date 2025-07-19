import time
import os
import random
import math
import numpy as np
from perlin_noise import PerlinNoise
import threading
import queue
import sys
import traceback

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
TICK_SECONDS = 1
TILE_SIZE_METERS = 10
CLEAR_METHOD = (
    "ansi"  # Use 'ansi' for modern terminals (PowerShell/Linux/macOS) for no flicker.
)
# Use 'cls' for old Windows CMD if 'ansi' doesn't work.


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

        # --- MODIFICATION START ---
        # Get the human's current grid position, ensuring it's safely within bounds
        start_grid_x = np.clip(
            int(self.position[0] / TILE_SIZE_METERS), 0, world.width - 1
        )
        start_grid_y = np.clip(
            int(self.position[1] / TILE_SIZE_METERS), 0, world.height - 1
        )
        # --- MODIFICATION END ---

        # Make sure we don't try to pathfind from an impassable tile
        if world.grid[start_grid_y][start_grid_x].tile_move_speed_factor == 0:
            world.add_log(
                f"{Colors.RED}{self.name} is stuck on an impassable tile!{Colors.RESET}"
            )
            return

        # Try a few times to find a path to a random valid location
        for _ in range(10):
            dest_x = random.randint(0, world.width - 1)
            dest_y = random.randint(0, world.height - 1)

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

        # Find a path if we don't have one
        if not self.path:
            self._find_new_path(world)
            if not self.path:
                return  # Can't move without a path

        # Get the next step in our path
        target_grid_pos = self.path[0]
        target_pos = np.array(
            [
                (target_grid_pos[0] + 0.5) * TILE_SIZE_METERS,
                (target_grid_pos[1] + 0.5) * TILE_SIZE_METERS,
            ]
        )

        # Move towards the next step
        current_tile = world.get_tile_at_pos(self.position[0], self.position[1])
        effective_speed = self.move_speed * current_tile.tile_move_speed_factor

        if effective_speed > 0:
            direction_vector = target_pos - self.position
            distance_to_target = np.linalg.norm(direction_vector)

            if distance_to_target < effective_speed:
                self.position = target_pos
                self.path.pop(0)
                if not self.path:
                    world.add_log(
                        f"{Colors.GREEN}{self.name} has reached their destination.{Colors.RESET}"
                    )
            else:
                normalized_direction = direction_vector / distance_to_target
                move_vector = normalized_direction * effective_speed
                self.position += move_vector

        # --- DEFINITIVE CRASH FIX ---
        # After every potential move, clamp the position to be strictly within the
        # valid world boundaries. This prevents floating point errors from ever
        # causing a position like 640.0, which leads to an IndexError.
        max_x = world.width * TILE_SIZE_METERS
        max_y = world.height * TILE_SIZE_METERS
        self.position[0] = np.clip(self.position[0], 0, max_x - 0.01)
        self.position[1] = np.clip(self.position[1], 0, max_y - 0.01)
        # --- END OF FIX ---

        # Interaction (Harvesting) logic
        for entity in world.entities:
            if isinstance(entity, Rice) and entity.matured:
                if np.linalg.norm(self.position - entity.position) <= 10.0:
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
        """Gets the tile at a specific meter-based coordinate, now with extra safety."""
        # Convert and clamp the coordinates to be strictly within the valid grid indices
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

                    move_cost = get_move_cost(neighbor)
                    if move_cost == float("inf"):
                        continue  # Impassable terrain

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

        return None  # No path found

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

    def display(self, current_input_list, cursor_pos):
        """Clears the screen and draws the world state, including a visible cursor."""
        output_buffer = []

        display_grid = [
            [(tile.color + tile.symbol) for tile in row] for row in self.grid
        ]
        for entity in self.entities:
            grid_x = int(entity.position[0] / TILE_SIZE_METERS)
            grid_y = int(entity.position[1] / TILE_SIZE_METERS)
            if 0 <= grid_y < self.height and 0 <= grid_x < self.width:
                color = Colors.MAGENTA if isinstance(entity, Human) else Colors.YELLOW
                display_grid[grid_y][grid_x] = color + entity.symbol

        output_buffer.append("--- Simulation Game ---")
        for row in display_grid:
            output_buffer.append(" ".join(row) + Colors.RESET)

        output_buffer.append("-" * (self.width * 2))
        output_buffer.append(
            f"Tick: {self.tick_count} | Entities: {len(self.entities)}"
        )
        output_buffer.append(f"Commands: sp [human|rice] [x] [y] | q to quit")
        output_buffer.append("Log messages:")
        for msg in self.log_messages:
            output_buffer.append(msg)
        for _ in range(10 - len(self.log_messages)):
            output_buffer.append("")

        # --- NEW CURSOR DRAWING LOGIC ---
        prompt_parts = ["> "]
        for i, char in enumerate(current_input_list):
            if i == cursor_pos:
                # Render the character under the cursor with an inverted background
                prompt_parts.append(f"\033[7m{char}\033[27m")  # Invert/Revert colors
            else:
                prompt_parts.append(char)

        # If cursor is at the end of the line, show it as an inverted space
        if cursor_pos == len(current_input_list):
            prompt_parts.append(f"\033[7m \033[27m")

        output_buffer.append("".join(prompt_parts))
        # --- END OF NEW LOGIC ---

        final_output = "\n".join(output_buffer)

        if CLEAR_METHOD == "ansi":
            sys.stdout.write("\033[H\033[J" + final_output)
        else:
            os.system("cls")
            sys.stdout.write(final_output)

        sys.stdout.flush()


# --- Main Game Loop and Input Handling ---
def game_loop(world, command_queue, shared_state):
    """The main game thread, with a universal crash handler for debugging."""
    last_tick_time = time.time()

    while True:
        try:  # --- START OF UNIVERSAL CATCH BLOCK ---
            # Check for commands from the input thread
            try:
                command = command_queue.get_nowait()
                if command.lower() in ["q", "quit", "exit"]:
                    return
                parts = command.split()
                if len(parts) == 4 and parts[0].lower() == "sp":
                    world.spawn_entity(parts[1], int(parts[2]), int(parts[3]))
                else:
                    world.add_log(
                        f"{Colors.RED}Unknown command: '{command}'{Colors.RESET}"
                    )
            except (queue.Empty, ValueError, IndexError):
                pass

            # Check if it's time for a game logic tick
            current_time = time.time()
            if current_time - last_tick_time >= TICK_SECONDS:
                world.game_tick()
                last_tick_time = current_time

            # Get the current input state to display it
            with shared_state["lock"]:
                current_input_list = list(shared_state["input_buffer"])
                cursor_pos = shared_state["cursor_pos"]

            # Display/render on every loop iteration, now with cursor info
            world.display(current_input_list, cursor_pos)  # <-- MODIFIED LINE

            time.sleep(0.1)

        except Exception as e:
            # --- THIS IS THE UNIVERSAL CRASH HANDLER ---
            # It caught an error, so we will print a full report.
            nb_input_for_cleanup.restore_terminal()
            print("\n" * 5)
            print("=" * 60)
            print(f"{Colors.RED}>>> A FATAL ERROR OCCURRED! <<<")
            print(f"ERROR TYPE: {type(e).__name__}{Colors.RESET}")
            print(f"ERROR DETAILS: {e}")
            print("=" * 60)
            print("\n--- TRACEBACK (Shows where the error happened) ---")
            # This prints the full "call stack", pointing to the exact line
            traceback.print_exc()
            print("--------------------------------------------------")

            print("\n--- ENTITY STATE AT TIME OF CRASH ---")
            for i, entity in enumerate(world.entities):
                pos = entity.position
                grid_x = int(pos[0] / TILE_SIZE_METERS)
                grid_y = int(pos[1] / TILE_SIZE_METERS)
                print(
                    f" Entity {i}: {entity.name} | Pos: ({pos[0]:.2f}, {pos[1]:.2f}) | Grid: ({grid_x}, {grid_y})"
                )

            print("\n" + "=" * 60)
            print("Game has been terminated. Please copy ALL the text from the")
            print("'>>> A FATAL ERROR OCCURRED! <<<' line downwards and share it.")
            return


def input_handler(command_queue, shared_state):
    """The dedicated input thread, now with full cursor movement and editing."""
    nb_input = NonBlockingInput()
    try:
        while True:
            if ON_WINDOWS:
                if msvcrt.kbhit():
                    byte = msvcrt.getch()

                    # --- Special Key Handling ---
                    if byte in (b"\xe0", b"\x00"):
                        second_byte = msvcrt.getch()
                        with shared_state["lock"]:
                            if second_byte == b"K":  # Left Arrow
                                shared_state["cursor_pos"] = max(
                                    0, shared_state["cursor_pos"] - 1
                                )
                            elif second_byte == b"M":  # Right Arrow
                                cursor = shared_state["cursor_pos"]
                                buf_len = len(shared_state["input_buffer"])
                                shared_state["cursor_pos"] = min(buf_len, cursor + 1)
                        continue

                    # --- Normal Key Handling ---
                    with shared_state["lock"]:
                        if byte == b"\r":  # Enter key
                            command = "".join(shared_state["input_buffer"])
                            if command:
                                command_queue.put(command)
                            shared_state["input_buffer"].clear()
                            shared_state["cursor_pos"] = 0
                        elif byte == b"\x08":  # Backspace
                            cursor = shared_state["cursor_pos"]
                            if cursor > 0:
                                shared_state["input_buffer"].pop(cursor - 1)
                                shared_state["cursor_pos"] = cursor - 1
                        else:
                            try:
                                char = byte.decode("utf-8")
                                if char.isprintable():
                                    cursor = shared_state["cursor_pos"]
                                    shared_state["input_buffer"].insert(cursor, char)
                                    shared_state["cursor_pos"] = cursor + 1
                            except UnicodeDecodeError:
                                pass
            else:
                # This is the placeholder for Linux/macOS
                time.sleep(0.01)  # Add sleep here to avoid busy-loop if not on windows
                pass

            time.sleep(0.01)
    finally:
        nb_input.restore_terminal()


if __name__ == "__main__":
    # Enable ANSI escape codes on Windows
    if ON_WINDOWS:
        os.system("")

    # Add heapq for our pathfinding algorithm's priority queue
    import heapq

    # A shared dictionary to pass state between threads
    shared_state = {"input_buffer": [], "cursor_pos": 0, "lock": threading.Lock()}

    world = World(GRID_WIDTH, GRID_HEIGHT)
    cmd_queue = queue.Queue()

    # We must restore the terminal even if the program crashes
    nb_input_for_cleanup = NonBlockingInput()

    try:
        # --- START OF FIX ---
        # Initial display calls must now match the new display() signature
        # by providing an empty list and a cursor position of 0.
        world.display([], 0)
        world.add_log("Welcome to the simulation!")
        world.add_log("The world has been generated.")
        world.add_log("Use the command 'sp human 32 15' to start.")
        world.display([], 0)  # Display welcome messages
        # --- END OF FIX ---

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
