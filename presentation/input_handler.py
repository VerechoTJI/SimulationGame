# presentation/input_handler.py
import sys
import time
import threading

if sys.platform == "win32":
    import msvcrt
else:
    import tty, termios, select


class NonBlockingInput:
    """A class to handle non-blocking keyboard input."""

    def __init__(self):
        if not sys.platform == "win32":
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())

    def get_char(self):
        if sys.platform == "win32":
            if msvcrt.kbhit():
                return msvcrt.getch().decode("utf-8", errors="ignore")
            return None
        else:
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                return sys.stdin.read(1)
            return None

    def restore_terminal(self):
        """Restores the terminal to its original settings."""
        if not sys.platform == "win32":
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)


def input_handler(command_queue, shared_state):
    """
    Runs in a separate thread to handle all user input without blocking the main loop.
    """
    nb_input = NonBlockingInput()
    try:
        while True:
            key_code = None
            if sys.platform == "win32":
                if msvcrt.kbhit():
                    byte = msvcrt.getch()
                    if byte in (b"\xe0", b"\x00"):  # Arrow keys
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
            else:  # Unix-like systems
                char = nb_input.get_char()
                if char:
                    if char == "\x1b":  # ANSI escape sequence
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

            with shared_state["lock"]:
                history = shared_state["command_history"]

                # Hotkeys are only processed if the input buffer is empty
                if len(shared_state["input_buffer"]) == 0:
                    hotkey_pressed = True
                    k = key_code.lower()
                    if k == "p":
                        command_queue.put("__PAUSE_TOGGLE__")
                    elif k == "n":
                        command_queue.put("__FORCE_TICK__")
                    elif k in ("=", "+"):
                        command_queue.put("__SPEED_UP__")
                    elif k == "-":
                        command_queue.put("__SPEED_DOWN__")
                    elif k == "w":
                        shared_state["camera_y"] -= 1
                    elif k == "s":
                        shared_state["camera_y"] += 1
                    elif k == "a":
                        shared_state["camera_x"] -= 1
                    elif k == "d":
                        shared_state["camera_x"] += 1
                    else:
                        hotkey_pressed = False

                    if hotkey_pressed:
                        continue

                # Command buffer manipulation
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
