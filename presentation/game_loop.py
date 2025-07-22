# presentation/game_loop.py
import time
import queue
import traceback

from presentation.renderer import display

# Removed NonBlockingInput import


def game_loop(
    game_service, command_queue, shared_state, camera_move_increment
):  # MODIFIED signature
    """
    The main loop of the game, handling ticks, rendering, and command processing.
    """
    last_timed_tick_time = time.time()
    last_fps_update_time = time.time()
    render_frame_count = 0
    logic_tick_count = 0
    render_fps = 0.0
    logic_tps = 0.0

    # Local camera state for smooth movement
    with shared_state["lock"]:
        camera_x = shared_state["camera_x"]
        camera_y = shared_state["camera_y"]

    try:
        while True:
            current_time = time.time()
            tick_occurred_this_frame = False

            # --- NEW: Process camera movement based on key state every frame ---
            with shared_state["lock"]:
                keys = shared_state["keys_down"]
                if keys["w"]:
                    camera_y -= camera_move_increment
                if keys["s"]:
                    camera_y += camera_move_increment
                if keys["a"]:
                    camera_x -= camera_move_increment
                if keys["d"]:
                    camera_x += camera_move_increment

            # Process all pending non-movement commands
            while not command_queue.empty():
                try:
                    command = command_queue.get_nowait()
                    # --- REFACTORED: Removed UI camera commands ---
                    if command == "__PAUSE_TOGGLE__":
                        game_service.toggle_pause()
                    elif command == "__FORCE_TICK__":
                        if game_service.force_tick():
                            tick_occurred_this_frame = True
                    elif command == "__SPEED_UP__":
                        game_service.speed_up()
                    elif command == "__SPEED_DOWN__":
                        game_service.speed_down()
                    elif command.lower() in ["q", "quit", "exit"]:
                        raise SystemExit()  # Use SystemExit for clean shutdown
                    else:
                        game_service.execute_user_command(command)
                except queue.Empty:
                    break

            # Scheduled game tick logic
            current_tick_seconds = game_service.get_render_data()["tick_seconds"]
            if (
                not game_service.is_paused()
                and current_time - last_timed_tick_time >= current_tick_seconds
            ):
                game_service.tick()
                tick_occurred_this_frame = True
                last_timed_tick_time = current_time

            # Update performance metrics
            render_frame_count += 1
            if tick_occurred_this_frame:
                logic_tick_count += 1

            elapsed_time = current_time - last_fps_update_time
            if elapsed_time >= 1.0:
                render_fps = render_frame_count / elapsed_time
                logic_tps = logic_tick_count / elapsed_time
                render_frame_count = 0
                logic_tick_count = 0
                last_fps_update_time = current_time

            # Rendering using local and shared state
            final_render_data = game_service.get_render_data()
            final_render_data["render_fps"] = render_fps
            final_render_data["logic_tps"] = logic_tps

            with shared_state["lock"]:
                current_input_list = list(shared_state["input_buffer"])
                cursor_pos = shared_state["cursor_pos"]

            clamped_x, clamped_y = display(
                final_render_data, current_input_list, cursor_pos, camera_x, camera_y
            )

            camera_x, camera_y = clamped_x, clamped_y
            with shared_state["lock"]:
                shared_state["camera_x"] = camera_x
                shared_state["camera_y"] = camera_y
            sleep_time = max(0, 0.00833 - time.time() + current_time)
            time.sleep(sleep_time)

    except Exception:
        # Using sys.exit() or os._exit() might not allow the main finally block to run
        # So we print the error here and then re-raise to be caught by main.
        print("\n" * 5)
        print("=" * 20, " A FATAL ERROR OCCURRED IN GAME LOOP ", "=" * 20)
        traceback.print_exc()
        print("=" * 60)
        print("Game has been terminated.")
        # Re-raise the exception so the main thread's finally block is triggered
        raise
