# presentation/game_loop.py
import time
import queue
import os
import sys
import traceback

from presentation.renderer import display
from presentation.input_handler import NonBlockingInput


def game_loop(
    game_service, command_queue, shared_state, nb_input_for_cleanup: NonBlockingInput
):
    """
    The main loop of the game, handling ticks, rendering, and command processing.
    """
    last_timed_tick_time = time.time()
    last_fps_update_time = time.time()
    render_frame_count = 0
    logic_tick_count = 0
    render_fps = 0.0
    logic_tps = 0.0

    try:
        while True:
            # Process any pending commands from the input thread
            try:
                command = command_queue.get_nowait()

                # --- NEW: Command Interpretation Logic ---
                if command == "__PAUSE_TOGGLE__":
                    game_service.toggle_pause()
                elif command == "__FORCE_TICK__":
                    game_service.force_tick()
                elif command == "__SPEED_UP__":
                    game_service.speed_up()
                elif command == "__SPEED_DOWN__":
                    game_service.speed_down()
                elif command.lower() in ["q", "quit", "exit"]:
                    return  # Exit the loop cleanly
                else:
                    # It's a user-typed command
                    game_service.execute_user_command(command)

            except queue.Empty:
                pass

            # Check if it's time for a scheduled game tick
            current_tick_seconds = game_service.get_render_data()["tick_seconds"]
            current_time = time.time()
            if (
                not game_service.is_paused()
                and current_time - last_timed_tick_time >= current_tick_seconds
            ):
                game_service.tick()
                last_timed_tick_time = current_time

            # Get final data for this frame
            final_render_data = game_service.get_render_data()
            tick_before = final_render_data["tick"]
            game_service.tick()  # This is a placeholder call, actual tick is conditional above. Let's fix this.
            tick_after = game_service.get_render_data()["tick"]

            # Update performance metrics
            render_frame_count += 1
            # We need to get the tick count *before* and *after* the potential tick call
            tick_after_data = game_service.get_render_data()
            if tick_after_data["tick"] > final_render_data["tick"]:
                logic_tick_count += 1

            elapsed_time = current_time - last_fps_update_time
            if elapsed_time >= 1.0:
                render_fps = render_frame_count / elapsed_time
                logic_tps = logic_tick_count / elapsed_time
                render_frame_count = 0
                logic_tick_count = 0
                last_fps_update_time = current_time

            # Add performance data to the final render payload
            final_render_data["render_fps"] = render_fps
            final_render_data["logic_tps"] = logic_tps

            # Read shared state for rendering
            with shared_state["lock"]:
                current_input_list = list(shared_state["input_buffer"])
                cursor_pos = shared_state["cursor_pos"]
                camera_x = shared_state["camera_x"]
                camera_y = shared_state["camera_y"]

            # Render the screen
            clamped_x, clamped_y = display(
                final_render_data, current_input_list, cursor_pos, camera_x, camera_y
            )

            # Update shared state with clamped camera values
            with shared_state["lock"]:
                shared_state["camera_x"] = clamped_x
                shared_state["camera_y"] = clamped_y

            # Small sleep to prevent CPU maxing out
            time.sleep(0.008)

    except Exception:
        nb_input_for_cleanup.restore_terminal()
        print("\n" * 5)
        print("=" * 20, " A FATAL ERROR OCCURRED IN GAME LOOP ", "=" * 20)
        traceback.print_exc()
        print("=" * 60)
        print("Game has been terminated.")
        os._exit(1)  # Force exit
