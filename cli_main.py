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
            # --- PLATFORM-SPECIFIC KEY HANDLING (Code is identical to before) ---
            key_code = None
            if sys.platform == "win32":
                if msvcrt.kbhit():
                    byte = msvcrt.getch()
                    if byte in (b"\xe0", b"\x00"):
                        second_byte = msvcrt.getch()
                        if second_byte == b"H":
                            key_code = "UP"
                        elif second_byte == b"P":
                            key_code = "DOWN"
                        elif second_byte == b"K":
                            key_code = "LEFT"
                        elif second_byte == b"M":
                            key_code = "RIGHT"
                    elif byte == b"\r":
                        key_code = "ENTER"
                    elif byte == b"\x08":
                        key_code = "BACKSPACE"
                    else:
                        try:
                            key_code = byte.decode("utf-8")
                        except UnicodeDecodeError:
                            pass
            else:
                char = nb_input.get_char()
                if char:
                    if char == "\x1b":
                        if nb_input.get_char() == "[":
                            arrow_key = nb_input.get_char()
                            if arrow_key == "A":
                                key_code = "UP"
                            elif arrow_key == "B":
                                key_code = "DOWN"
                            elif arrow_key == "C":
                                key_code = "RIGHT"
                            elif arrow_key == "D":
                                key_code = "LEFT"
                    elif char in ("\n", "\r"):
                        key_code = "ENTER"
                    elif char == "\x7f":
                        key_code = "BACKSPACE"
                    else:
                        key_code = char

            if not key_code:
                time.sleep(0.01)
                continue

            # --- MODIFIED: UNIFIED INPUT PROCESSING LOGIC ---
            with shared_state["lock"]:
                history = shared_state["command_history"]

                # --- NEW: Context-sensitive hotkey handling ---
                # Hotkeys only work if the input buffer is empty.
                if len(shared_state["input_buffer"]) == 0:
                    hotkey_pressed = True
                    if key_code.lower() == "p":
                        command_queue.put("__PAUSE_TOGGLE__")
                    elif key_code.lower() == "n":
                        command_queue.put("__FORCE_TICK__")
                    elif key_code in ("=", "+"):
                        command_queue.put("__SPEED_UP__")
                    elif key_code == "-":
                        command_queue.put("__SPEED_DOWN__")
                    else:
                        hotkey_pressed = False

                    if hotkey_pressed:
                        continue  # Skip the rest of the processing

                # --- Existing logic for text entry and command history ---
                if key_code == "UP":
                    if history:
                        shared_state["history_index"] = max(
                            0, shared_state["history_index"] - 1
                        )
                        command = history[shared_state["history_index"]]
                        shared_state["input_buffer"] = list(command)
                        shared_state["cursor_pos"] = len(command)
                elif key_code == "DOWN":
                    if history:
                        shared_state["history_index"] = min(
                            len(history), shared_state["history_index"] + 1
                        )
                        if shared_state["history_index"] == len(history):
                            shared_state["input_buffer"].clear()
                            shared_state["cursor_pos"] = 0
                        else:
                            command = history[shared_state["history_index"]]
                            shared_state["input_buffer"] = list(command)
                            shared_state["cursor_pos"] = len(command)
                elif key_code == "LEFT":
                    shared_state["cursor_pos"] = max(0, shared_state["cursor_pos"] - 1)
                elif key_code == "RIGHT":
                    shared_state["cursor_pos"] = min(
                        len(shared_state["input_buffer"]),
                        shared_state["cursor_pos"] + 1,
                    )
                elif key_code == "ENTER":
                    command = "".join(shared_state["input_buffer"])
                    if command:
                        command_queue.put(command)
                        if not history or history[-1] != command:
                            history.append(command)
                        shared_state["history_index"] = len(history)
                    shared_state["input_buffer"].clear()
                    shared_state["cursor_pos"] = 0
                elif key_code == "BACKSPACE":
                    cursor = shared_state["cursor_pos"]
                    if cursor > 0:
                        shared_state["input_buffer"].pop(cursor - 1)
                        shared_state["cursor_pos"] = cursor - 1
                elif key_code and len(key_code) == 1 and key_code.isprintable():
                    cursor = shared_state["cursor_pos"]
                    shared_state["input_buffer"].insert(cursor, key_code)
                    shared_state["cursor_pos"] = cursor + 1
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

    # --- NEW: Dynamic title based on simulation state ---
    status = "PAUSED" if render_data.get("is_paused", False) else "RUNNING"
    base_tick = render_data.get("base_tick_seconds", 0.3)
    current_tick = render_data.get("tick_seconds", 0.3)
    speed_multiplier = base_tick / current_tick
    title_status = f"Status: {status} | Speed: {speed_multiplier:.2f}x"
    title_text = "--- Simulation Game ---"
    title_line = f"{title_text} | {title_status}"

    map_width_chars = 0
    if map_height > 0 and len(map_grid[0]) > 0:
        first_row_string = " ".join(map_grid[0])
        map_width_chars = get_visible_length(first_row_string)

    # --- The dynamic status panel for humans is unchanged ---
    right_panel_lines = []
    right_panel_lines.append(
        f"Tick: {render_data['tick']} | Entities: {render_data['entity_count']}"
    )
    right_panel_lines.append("")
    right_panel_lines.append("--- Humans ---")
    human_statuses = render_data.get("human_statuses", [])
    if not human_statuses:
        for _ in range(map_height - len(right_panel_lines)):
            right_panel_lines.append("")
    else:
        human_statuses.sort()
        available_width = terminal_width - map_width_chars - 3
        base_col_width = max(get_visible_length(s) for s in human_statuses)
        col_separator = " | "
        max_cols = max(1, available_width // (base_col_width + len(col_separator)))
        data_rows = map_height - 3
        if data_rows <= 0:
            display_list = []
        else:
            display_capacity = data_rows * max_cols
            display_list = human_statuses
            if len(human_statuses) > display_capacity:
                num_to_show = display_capacity - 1
                num_hidden = len(human_statuses) - num_to_show
                display_list = human_statuses[:num_to_show]
                summary_msg = f"+{num_hidden} more"
                if get_visible_length(summary_msg) > base_col_width:
                    num_digits = max(1, base_col_width - 7)
                    max_num = 10**num_digits - 1
                    summary_msg = f"+>{max_num} more"
                display_list.append(summary_msg)
        for i in range(data_rows):
            row_parts = []
            for j in range(max_cols):
                item_index = i + j * data_rows
                if item_index < len(display_list):
                    item = display_list[item_index]
                    padding = " " * (base_col_width - get_visible_length(item))
                    row_parts.append(item + padding)
                else:
                    row_parts.append(" " * base_col_width)
            right_panel_lines.append(col_separator.join(row_parts))

    # --- Build the screen using the new title ---
    output_buffer.append(title_line)  # <-- MODIFIED
    for i in range(map_height):
        map_part = " ".join(map_grid[i]) + Colors.RESET
        status_part = right_panel_lines[i] if i < len(right_panel_lines) else ""
        output_buffer.append(f"{map_part} | {status_part}")

    output_buffer.append("-" * (map_width_chars + 1))

    # --- Log rendering logic is unchanged ---
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

    # --- MODIFIED: Updated help text in footer ---
    output_buffer.append(
        f"Hotkeys: p(pause) n(next) +/-(speed) | Cmd: sp <type> <x> <y> | q(quit)"
    )

    # Prompt logic is unchanged
    prompt_parts = ["> "]
    for i, char in enumerate(current_input_list):
        if i == cursor_pos:
            prompt_parts.append(f"\033[7m{char}\033[27m")
        else:
            prompt_parts.append(char)
    if cursor_pos == len(current_input_list):
        prompt_parts.append(f"\033[7m \033[27m")
    output_buffer.append("".join(prompt_parts))

    # Rendering logic is unchanged
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
            # Process any commands from the queue
            try:
                command = command_queue.get_nowait()
                if command.lower() in ["q", "quit", "exit"]:
                    return
                game_service.process_command(command)
            except queue.Empty:
                pass

            # First, get the most up-to-date state from the service
            render_data = game_service.get_render_data()
            current_tick_seconds = render_data["tick_seconds"]

            # Then, check if it's time for the next automatic tick
            current_time = time.time()
            if current_time - last_tick_time >= current_tick_seconds:
                game_service.tick()  # This call respects the pause state internally
                last_tick_time = current_time

            # Get user input state and render the display
            with shared_state["lock"]:
                current_input_list = list(shared_state["input_buffer"])
                cursor_pos = shared_state["cursor_pos"]

            display(render_data, current_input_list, cursor_pos)

            time.sleep(0.05)  # A short sleep to prevent busy-waiting
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
        os.system("cls")
        print("platform: win32")
    else:
        print("platform: unix")

    shared_state = {
        "input_buffer": [],
        "cursor_pos": 0,
        "lock": threading.Lock(),
        "command_history": [],
        "history_index": -1,  # -1 indicates we are not currently browsing history
    }
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
