# presentation/main.py
import sys
import os
import threading
import queue

from application.game_service import GameService
from application.config import config
from presentation.input_handler import input_handler, NonBlockingInput
from presentation.game_loop import game_loop
from presentation.renderer import display


def run():
    """Initializes and runs the entire simulation application."""
    if sys.platform == "win32":
        os.system("cls")

    # Shared state between input thread and main loop
    shared_state = {
        "input_buffer": [],
        "cursor_pos": 0,
        "lock": threading.Lock(),
        "command_history": [],
        "history_index": 0,
        "camera_x": 0,
        "camera_y": 0,
    }

    command_queue = queue.Queue()

    game_service = GameService(
        grid_width=config.get("simulation", "grid_width"),
        grid_height=config.get("simulation", "grid_height"),
        tile_size=config.get("simulation", "tile_size_meters"),
    )
    game_service.initialize_world()

    # This instance is created here solely to be passed for cleanup in case of a crash.
    nb_input_for_cleanup = NonBlockingInput()

    try:
        # Initial render before starting loops
        render_data = game_service.get_render_data()
        with shared_state["lock"]:
            clamped_x, clamped_y = display(
                render_data, [], 0, shared_state["camera_x"], shared_state["camera_y"]
            )
            shared_state["camera_x"] = clamped_x
            shared_state["camera_y"] = clamped_y

        # Start the input handler in a separate thread
        input_thread = threading.Thread(
            target=input_handler, args=(command_queue, shared_state), daemon=True
        )
        input_thread.start()

        # Start the main game loop
        game_loop(game_service, command_queue, shared_state, nb_input_for_cleanup)

    except KeyboardInterrupt:
        print("\nGame interrupted by user.")
    finally:
        print("Restoring terminal and exiting.")
        nb_input_for_cleanup.restore_terminal()
        os._exit(0)
