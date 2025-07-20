import time
import os
import threading
import queue
import sys
import traceback
import re
import math
from application.config import config

# --- Platform-specific and input handling code remains the same ---
if sys.platform == "win32":
    import msvcrt
else:
    import tty, termios, select

from application.game_service import GameService

# --- Game Configuration ---
GRID_WIDTH = config.get("simulation", "grid_width")
GRID_HEIGHT = config.get("simulation", "grid_height")
TICK_SECONDS = config.get("simulation", "tick_seconds")
TILE_SIZE_METERS = config.get("simulation", "tile_size_meters")
CLEAR_METHOD = "ansi"


class NonBlockingInput:
    def __init__(self):
        if not sys.platform == "win32":
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())

    def get_char(self):
        if sys.platform == "win32":
            if msvcrt.kbhit():
                return msvcrt.getch().decode("utf-8")
            return None
        else:
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                return sys.stdin.read(1)
            return None

    def restore_terminal(self):
        if not sys.platform == "win32":
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)


def input_handler(command_queue, shared_state):
    nb_input = NonBlockingInput()
    try:
        while True:
            if sys.platform == "win32":
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
                # Basic Linux input for arrow keys and special keys would go here
                pass
            time.sleep(0.01)
    finally:
        nb_input.restore_terminal()


def get_visible_length(s):
    """Calculates the visible length of a string by removing ANSI escape codes."""
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def display(render_data, current_input_list, cursor_pos):
    """The display function, which is stateless and only renders data it's given."""
    output_buffer = []
    Colors = render_data["colors"]
    map_grid = render_data["display_grid"]
    map_height = len(map_grid)
    terminal_width, terminal_height = os.get_terminal_size()

    # --- Map width calculation is unchanged ---
    map_width_chars = 0
    if map_height > 0 and len(map_grid[0]) > 0:
        first_row_string = " ".join(map_grid[0])
        map_width_chars = get_visible_length(first_row_string)

    # --- REFACTORED DYNAMIC STATUS PANEL ---
    right_panel_lines = []
    right_panel_lines.append(
        f"Tick: {render_data['tick']} | Entities: {render_data['entity_count']}"
    )
    right_panel_lines.append("")
    right_panel_lines.append("--- Humans ---")

    human_statuses = render_data.get("human_statuses", [])
    if not human_statuses:
        right_panel_lines.append("No humans in the world.")
    else:
        human_statuses.sort()
        # --- 1. Calculate column properties based on available width ---
        available_width = terminal_width - map_width_chars - 3
        base_col_width = max(get_visible_length(s) for s in human_statuses)
        col_separator = " | "
        max_cols = max(1, available_width // (base_col_width + len(col_separator)))

        # --- 2. Calculate display capacity and truncate if necessary ---
        # The panel is strictly constrained by the map's height.
        display_capacity = map_height * max_cols - 3
        display_list = human_statuses

        if len(human_statuses) > display_capacity:
            # Reserve the last slot for the summary message
            num_to_show = display_capacity - 1
            num_hidden = len(human_statuses) - num_to_show

            # Slice the list to make room for the summary
            display_list = human_statuses[:num_to_show]

            # Generate the robust summary message
            summary_msg = f"+{num_hidden} more"
            if get_visible_length(summary_msg) > base_col_width:
                num_digits = max(1, base_col_width - 7)
                max_num = 10**num_digits - 1
                summary_msg = f"+>{max_num} more"

            # Append the summary message to the final display list
            display_list.append(summary_msg)

        # --- 3. Build the multi-column rows, now constrained to map_height ---
        # We iterate exactly map_height times to build the rows.
        for i in range(map_height):
            row_parts = []
            for j in range(max_cols):
                # Correct index for a 'down-then-across' fill order
                item_index = i + j * map_height
                if item_index < len(display_list):
                    item = display_list[item_index]
                    padding = " " * (base_col_width - get_visible_length(item))
                    row_parts.append(item + padding)
                else:
                    # Pad with empty space if this slot is empty
                    row_parts.append(" " * base_col_width)
            right_panel_lines.append(col_separator.join(row_parts))

    # --- The rest of the function remains the same ---

    # Build the top part of the screen
    output_buffer.append("--- Simulation Game (DDD Refactor) ---")
    # This loop is now simpler, as right_panel_lines is guaranteed to be the right height
    for i in range(map_height):
        map_part = " ".join(map_grid[i]) + Colors.RESET
        status_part = right_panel_lines[i] if i < len(right_panel_lines) else ""
        output_buffer.append(f"{map_part} | {status_part}")

    output_buffer.append("-" * map_width_chars)

    # Dynamic Log Rendering logic is unchanged
    lines_used_so_far = len(output_buffer)
    footer_lines_needed = 3
    available_log_lines = terminal_height - lines_used_so_far - footer_lines_needed
    available_log_lines = max(0, available_log_lines)

    all_logs = render_data.get("logs", [])
    display_logs = []
    if available_log_lines > 0 and len(all_logs) > available_log_lines:
        num_hidden = len(all_logs) - (available_log_lines - 1)
        summary_line = f"[... {num_hidden} more older messages]"
        display_logs.append(summary_line)
        most_recent_logs = all_logs[-(available_log_lines - 1) :]
        display_logs.extend(most_recent_logs)
    else:
        display_logs = all_logs[-available_log_lines:]

    output_buffer.append("--- Log ---")
    output_buffer.extend(display_logs)

    current_buffer_len = len(output_buffer)
    padding_needed = terminal_height - current_buffer_len - footer_lines_needed + 1
    for _ in range(max(0, padding_needed)):
        output_buffer.append("")

    # Footer and Prompt logic is unchanged
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

    # Definitive flicker/residue-free rendering logic is unchanged
    if CLEAR_METHOD == "ansi":
        write_buffer = []
        write_buffer.append("\033[?25l")
        write_buffer.append("\033[H")
        for i, line in enumerate(output_buffer):
            write_buffer.append(line)
            write_buffer.append("\033[K")
            if i < len(output_buffer) - 1:
                write_buffer.append("\n")

        write_buffer.append("\033[J")
        write_buffer.append("\033[?25h")
        sys.stdout.write("".join(write_buffer))
    else:
        os.system("cls")
        sys.stdout.write("\n".join(output_buffer))

    sys.stdout.flush()


def game_loop(game_service, command_queue, shared_state):
    last_tick_time = time.time()
    try:
        while True:
            try:
                command = command_queue.get_nowait()
                if command.lower() in ["q", "quit", "exit"]:
                    return
                game_service.process_command(command)
            except queue.Empty:
                pass

            current_time = time.time()
            if current_time - last_tick_time >= TICK_SECONDS:
                game_service.tick()
                last_tick_time = current_time

            with shared_state["lock"]:
                current_input_list = list(shared_state["input_buffer"])
                cursor_pos = shared_state["cursor_pos"]

            render_data = game_service.get_render_data()
            display(render_data, current_input_list, cursor_pos)

            time.sleep(0.1)
    except Exception as e:
        nb_input_for_cleanup.restore_terminal()
        print("\n" * 5)
        print("=" * 20, " A FATAL ERROR OCCURRED ", "=" * 20)
        traceback.print_exc()
        print("=" * 60)
        print("Game has been terminated.")
        return


if __name__ == "__main__":
    if sys.platform == "win32":
        os.system("")
        print("platform: win32")
    else:
        print("platform: unix")

    shared_state = {"input_buffer": [], "cursor_pos": 0, "lock": threading.Lock()}
    cmd_queue = queue.Queue()
    game_service = GameService(GRID_WIDTH, GRID_HEIGHT, TILE_SIZE_METERS)
    game_service.initialize_world()
    nb_input_for_cleanup = NonBlockingInput()
    try:
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
