# presentation/input_handler.py
import sys
import threading
import keyboard

# Define movement keys to avoid magic strings
MOVEMENT_KEYS = {"w", "a", "s", "d"}


def input_handler(command_queue, shared_state):
    """
    Runs in a separate thread to handle all user input using event-driven hooks.
    This function now handles key-down and key-up events for smooth camera movement.
    """
    stop_event = threading.Event()

    def handle_key_event(event: keyboard.KeyboardEvent):
        if event.event_type != keyboard.KEY_DOWN:
            # Handle key-up for movement keys
            if event.name in MOVEMENT_KEYS:
                with shared_state["lock"]:
                    shared_state["keys_down"][event.name] = False
            return

        # --- From here, we only handle KEY_DOWN events ---
        key_name = event.name
        # Use a consistent key name for special keys
        if key_name == "enter":
            key_name = "ENTER"
        if key_name == "space":
            key_name = " "  # Handle spacebar correctly

        with shared_state["lock"]:
            history = shared_state["command_history"]

            if key_name == "up":
                if history:
                    shared_state["history_index"] = max(
                        0, shared_state["history_index"] - 1
                    )
                    command = history[shared_state["history_index"]]
                    shared_state["input_buffer"] = list(command)
                    shared_state["cursor_pos"] = len(command)
            elif key_name == "down":
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
            elif key_name == "left":
                shared_state["cursor_pos"] = max(0, shared_state["cursor_pos"] - 1)
            elif key_name == "right":
                shared_state["cursor_pos"] = min(
                    len(shared_state["input_buffer"]),
                    shared_state["cursor_pos"] + 1,
                )
            elif key_name == "ENTER":
                command = "".join(shared_state["input_buffer"])
                if command:
                    command_queue.put(command)
                    if not history or history[-1] != command:
                        history.append(command)
                    shared_state["history_index"] = len(history)
                shared_state["input_buffer"].clear()
                shared_state["cursor_pos"] = 0
            elif key_name == "backspace":
                cursor = shared_state["cursor_pos"]
                if cursor > 0:
                    shared_state["input_buffer"].pop(cursor - 1)
                    shared_state["cursor_pos"] = cursor - 1

            # Event-based hotkeys
            # If buffer is empty, we are in "gameplay mode" ---
            if len(shared_state["input_buffer"]) == 0:
                k = key_name.lower()
                if k == "p":
                    command_queue.put("__PAUSE_TOGGLE__")
                    return
                elif k == "n":
                    command_queue.put("__FORCE_TICK__")
                    return
                elif k in ("=", "+"):
                    command_queue.put("__SPEED_UP__")
                    return
                elif k == "-":
                    command_queue.put("__SPEED_DOWN__")
                    return
                elif k == "f":  # <-- NEW HOTKEY
                    command_queue.put("__TOGGLE_FLOW_FIELD__")
                    return
                # State-based movement keys
                if key_name in MOVEMENT_KEYS:
                    shared_state["keys_down"][key_name] = True
                    return
                    return

            # --- Priority 3: If no hotkey was pressed, start text entry ---
            # --- FIX: Handle space and other printable characters ---
            if len(key_name) == 1 and (key_name.isprintable() or key_name == " "):
                cursor = shared_state["cursor_pos"]
                shared_state["input_buffer"].insert(cursor, key_name)
                shared_state["cursor_pos"] = cursor + 1

    # Hook the event handler
    hook = keyboard.hook(handle_key_event, suppress=True)

    # Keep the thread alive. The main thread will exit this daemon thread.
    while not stop_event.is_set():
        stop_event.wait(0.5)

    keyboard.unhook(hook)
