# presentation/main.py

import sys
import os
import threading
import queue
import pygetwindow as gw
from presentation.input_handler import input_handler
from application.game_service import GameService
from application.config import config
from presentation.game_loop import game_loop
from presentation.renderer import display


def run():
    """Initializes and runs the entire simulation application."""
    if sys.platform == "win32":
        os.system("cls")

    # Initialize shared state
    shared_state = {
        "input_buffer": [],
        "cursor_pos": 0,
        "lock": threading.Lock(),
        "command_history": [],
        "history_index": 0,
        "camera_x": 0,
        "camera_y": 0,
        "keys_down": {"w": False, "a": False, "s": False, "d": False},
    }

    # Capture terminal window title
    try:
        active_window = gw.getActiveWindow()
        terminal_window_title = active_window.title if active_window else "Terminal"
    except Exception:
        terminal_window_title = "Terminal"

    shared_state["terminal_window_title"] = terminal_window_title

    command_queue = queue.Queue()

    game_service = GameService(
        grid_width=config.get("simulation", "grid_width"),
        grid_height=config.get("simulation", "grid_height"),
        tile_size=config.get("simulation", "tile_size_meters"),
    )
    game_service.initialize_world()

    camera_move_increment = config.get("controls", "camera_move_increment")

    try:
        # Initial render
        render_data = game_service.get_render_data()
        with shared_state["lock"]:
            clamped_x, clamped_y = display(
                render_data, [], 0, shared_state["camera_x"], shared_state["camera_y"]
            )
            shared_state["camera_x"] = clamped_x
            shared_state["camera_y"] = clamped_y

        # Start input handler
        input_thread = threading.Thread(
            target=input_handler, args=(command_queue, shared_state), daemon=True
        )
        input_thread.start()

        # Start game loop
        game_loop(game_service, command_queue, shared_state, camera_move_increment)

    except (KeyboardInterrupt, SystemExit):
        print("\nGame interrupted by user. Exiting.")
    finally:
        try:
            import termios

            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except ImportError:
            try:
                import msvcrt

                while msvcrt.kbhit():
                    msvcrt.getch()
            except ImportError:
                pass
        os._exit(0)
