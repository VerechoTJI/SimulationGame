# cli_main.py
import time
import os
import threading
import queue
import sys
import traceback

# --- Platform-specific and input handling code remains the same ---
# (NonBlockingInput class, ON_WINDOWS check, etc.)
try:
    import tty, termios, select

    ON_WINDOWS = False
except ImportError:
    import msvcrt

    ON_WINDOWS = True

# --- All game logic has been moved. We now import our service ---
from application.game_service import GameService

# --- Game Configuration ---
GRID_WIDTH = 64
GRID_HEIGHT = 32
TICK_SECONDS = 1
TILE_SIZE_METERS = 10
CLEAR_METHOD = "ansi"


# --- NonBlockingInput and input_handler() function remain completely unchanged ---
class NonBlockingInput:
    # ... (identical to original)
    def __init__(self):
        if not ON_WINDOWS:
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())

    def get_char(self):
        if ON_WINDOWS:
            if msvcrt.kbhit():
                return msvcrt.getch().decode("utf-8")
            return None
        else:
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                return sys.stdin.read(1)
            return None

    def restore_terminal(self):
        if not ON_WINDOWS:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)


def input_handler(command_queue, shared_state):
    # ... (function is identical to original)
    nb_input = NonBlockingInput()
    try:
        while True:
            # This logic for handling raw keys is a presentation concern and stays here
            # ... (identical logic for Windows/Linux)
            if ON_WINDOWS:
                if msvcrt.kbhit():
                    byte = msvcrt.getch()
                    if byte in (b"\xe0", b"\x00"):
                        second_byte = msvcrt.getch()
                        with shared_state["lock"]:
                            if second_byte == b"K":
                                shared_state["cursor_pos"] = max(
                                    0, shared_state["cursor_pos"] - 1
                                )
                            elif second_byte == b"M":
                                shared_state["cursor_pos"] = min(
                                    len(shared_state["input_buffer"]),
                                    shared_state["cursor_pos"] + 1,
                                )
                        continue
                    with shared_state["lock"]:
                        if byte == b"\r":
                            command = "".join(shared_state["input_buffer"])
                            if command:
                                command_queue.put(command)
                            shared_state["input_buffer"].clear()
                            shared_state["cursor_pos"] = 0
                        elif byte == b"\x08":
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
                time.sleep(0.01)
                pass  # Placeholder for Linux input logic
            time.sleep(0.01)
    finally:
        nb_input.restore_terminal()


def display(render_data, current_input_list, cursor_pos):
    """The display function, which is stateless and only renders data it's given."""
    output_buffer = []
    Colors = render_data["colors"]

    output_buffer.append("--- Simulation Game (DDD Refactor) ---")
    for row in render_data["display_grid"]:
        output_buffer.append(" ".join(row) + Colors.RESET)

    output_buffer.append("-" * (render_data["width"] * 2))
    output_buffer.append(
        f"Tick: {render_data['tick']} | Entities: {render_data['entity_count']}"
    )

    # --- NEW: Display the Human Statuses section ---
    output_buffer.append("--- Humans ---")
    human_statuses = render_data.get("human_statuses", [])
    if human_statuses:
        # Sort humans by name for a consistent display order
        human_statuses.sort()
        for status in human_statuses:
            output_buffer.append(status)
    else:
        output_buffer.append("No humans in the world.")

    # We can adjust the layout slightly to make room
    output_buffer.append("--- Log ---")
    for msg in render_data["logs"]:
        output_buffer.append(msg)
    # Adjust padding to keep the screen size consistent
    # Total lines for Humans and Log area = 1 (Humans header) + num_humans + 1 (Log header) + num_logs
    padding_lines = max(0, 8 - len(human_statuses) - len(render_data.get("logs", [])))
    for _ in range(padding_lines):
        output_buffer.append("")

    # --- Command prompt logic is unchanged ---
    output_buffer.append(f"Commands: sp [human|rice] [x] [y] | q to quit")
    prompt_parts = ["> "]
    for i, char in enumerate(current_input_list):
        if i == cursor_pos:
            prompt_parts.append(f"\033[7m{char}\033[27m")
        else:
            prompt_parts.append(char)
    if cursor_pos == len(current_input_list):
        prompt_parts.append(f"\033[7m \033[27m")

    output_buffer.append("".join(prompt_parts))
    final_output = "\n".join(output_buffer)

    if CLEAR_METHOD == "ansi":
        sys.stdout.write("\033[H\033[J" + final_output)
    else:
        os.system("cls")
        sys.stdout.write(final_output)
    sys.stdout.flush()


def game_loop(game_service, command_queue, shared_state):
    """The main game thread, now interacting with the GameService."""
    last_tick_time = time.time()

    # Universal crash handler remains a good idea
    try:
        while True:
            try:
                command = command_queue.get_nowait()
                if command.lower() in ["q", "quit", "exit"]:
                    return
                # Command processing is now handled by the service
                game_service.process_command(command)
            except queue.Empty:
                pass

            current_time = time.time()
            if current_time - last_tick_time >= TICK_SECONDS:
                game_service.tick()  # Tell the service to advance the world state
                last_tick_time = current_time

            with shared_state["lock"]:
                current_input_list = list(shared_state["input_buffer"])
                cursor_pos = shared_state["cursor_pos"]

            # Get all data needed for rendering from the service
            render_data = game_service.get_render_data()
            display(render_data, current_input_list, cursor_pos)

            time.sleep(0.1)

    except Exception as e:
        # Crash handler can be simplified or enhanced, but the principle is the same
        nb_input_for_cleanup.restore_terminal()
        print("\n" * 5)
        print("=" * 20, " A FATAL ERROR OCCURRED ", "=" * 20)
        traceback.print_exc()
        print("=" * 60)
        print("Game has been terminated.")
        return


if __name__ == "__main__":
    if ON_WINDOWS:
        os.system("")

    shared_state = {"input_buffer": [], "cursor_pos": 0, "lock": threading.Lock()}
    cmd_queue = queue.Queue()

    # Instantiate our new application service
    game_service = GameService(GRID_WIDTH, GRID_HEIGHT, TILE_SIZE_METERS)
    game_service.initialize_world()

    nb_input_for_cleanup = NonBlockingInput()
    try:
        # Initial display
        render_data = game_service.get_render_data()
        display(render_data, [], 0)

        input_thread = threading.Thread(
            target=input_handler, args=(cmd_queue, shared_state), daemon=True
        )
        input_thread.start()

        game_loop(game_service, cmd_queue, shared_state)

    except KeyboardInterrupt:
        print("\nGame interrupted by user.")
    finally:
        print("Restoring terminal and exiting.")
        nb_input_for_cleanup.restore_terminal()
        os._exit(0)
