# presentation/renderer.py
import os
import re
import sys

CLEAR_METHOD = "ansi"  # or "system"

# --- Constants for layout ---
MIN_WIDTH = 80
MIN_HEIGHT = 20
HEADER_HEIGHT = 1
# Specific constants for footer components for clarity and accurate calculation
FOOTER_CONTROLS_HEIGHT = 2  # Hotkeys + command prompt
FOOTER_SEPARATOR_HEIGHT = 1  # The '---' line above the log
FOOTER_LOG_HEADER_HEIGHT = 1  # The '--- Log ---' line


def get_visible_length(s: str) -> int:
    """Calculates the visible length of a string by removing ANSI escape codes."""
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def _render_minimal_view(
    render_data: dict,
    current_input_list: list,
    cursor_pos: int,
    terminal_width: int,
    terminal_height: int,
) -> list[str]:
    """Renders a simple, static view for small terminals."""
    status = "PAUSED" if render_data.get("is_paused", False) else "RUNNING"
    base_tick = render_data.get("base_tick_seconds", 0.3)
    current_tick = render_data.get("tick_seconds", 0.3)
    speed_multiplier = base_tick / current_tick if current_tick > 0 else float("inf")
    logic_tps = render_data.get("logic_tps", 0.0)

    buffer = [
        "--- Simulation ---",
        "Terminal too small for full view.",
        "-" * terminal_width,
        f"Status: {status} | Speed: {speed_multiplier:.1f}x",
        f"Tick: {render_data['tick']} ({logic_tps:.1f} tps) | Entities: {render_data['entity_count']}",
        "-" * terminal_width,
        "Hotkeys: p(pause) +/- (speed) q(quit)",
    ]

    # Pad to fill vertical space, leaving room for prompt
    padding_needed = terminal_height - len(buffer) - 1
    buffer.extend([""] * max(0, padding_needed))

    # Add input prompt
    prompt_parts = ["> "]
    for i, char in enumerate(current_input_list):
        prompt_parts.append(f"\033[7m{char}\033[27m" if i == cursor_pos else char)
    if cursor_pos == len(current_input_list):
        prompt_parts.append(f"\033[7m \033[27m")  # Cursor at the end
    buffer.append("".join(prompt_parts))

    return buffer


def _render_header(
    render_data: dict, terminal_width: int, clamped_camera_x: int, clamped_camera_y: int
) -> str:
    """Renders the top status bar."""
    status = "PAUSED" if render_data.get("is_paused", False) else "RUNNING"
    base_tick = render_data.get("base_tick_seconds", 0.3)
    current_tick = render_data.get("tick_seconds", 0.3)
    speed_multiplier = base_tick / current_tick if current_tick > 0 else float("inf")

    perf_stats = f"Render: {render_data.get('render_fps', 0.0):.1f}fps | Logic: {render_data.get('logic_tps', 0.0):.1f} tps"
    camera_stats = f"Camera: ({clamped_camera_x}, {clamped_camera_y})"
    status_stats = f"Status: {status} | Speed: {speed_multiplier:.1f}x"
    title_text = "--- Simulation ---"

    full_title_line = f"{title_text} | {perf_stats} | {camera_stats} | {status_stats}"
    if len(full_title_line) > terminal_width:
        full_title_line = full_title_line[:terminal_width]
    return full_title_line


def _render_main_view(
    render_data: dict,
    terminal_width: int,
    view_height: int,
    camera_x: int,
    camera_y: int,
) -> tuple[list[str], int, int]:
    """Renders the central view with the map and the right-hand status panel."""
    Colors = render_data["colors"]
    full_map_grid = render_data["display_grid"]
    full_map_height = len(full_map_grid)
    full_map_width = len(full_map_grid[0]) if full_map_height > 0 else 0

    # --- Panel Sizing ---
    human_statuses = sorted(render_data.get("human_statuses", []))
    base_col_width = max((get_visible_length(s) for s in human_statuses), default=12)
    col_separator_width = 3

    right_panel_width = base_col_width
    # Attempt to fit two columns if space allows
    if terminal_width > (base_col_width * 2 + col_separator_width + 60):
        right_panel_width = base_col_width * 2 + col_separator_width

    map_viewport_width_chars = terminal_width - right_panel_width - 3  # 3 for " | "
    map_viewport_width = max(10, map_viewport_width_chars // 2)

    # --- Camera Clamping & Map Slicing ---
    clamped_camera_x = max(0, min(camera_x, full_map_width - map_viewport_width))
    clamped_camera_y = max(0, min(camera_y, full_map_height - view_height))

    visible_map_slice = []
    if full_map_width > 0:
        for y in range(view_height):
            row_y = clamped_camera_y + y
            if row_y < full_map_height:
                row = full_map_grid[row_y][
                    clamped_camera_x : clamped_camera_x + map_viewport_width
                ]
                visible_map_slice.append(" ".join(row) + Colors.RESET)

    # --- Right Panel Content ---
    right_panel_lines = [
        f"Tick: {render_data['tick']} | Entities: {render_data['entity_count']}",
        "--- Humans ---",
    ]
    max_cols = 1 if right_panel_width == base_col_width else 2
    data_rows = view_height - 2  # 2 header lines in panel
    if data_rows > 0:
        display_capacity = data_rows * max_cols
        display_list = human_statuses
        if len(human_statuses) > display_capacity:
            num_to_show = display_capacity - 1
            num_hidden = len(human_statuses) - num_to_show
            display_list = human_statuses[:num_to_show] + [f"+{num_hidden} more"]

        for i in range(data_rows):
            row_parts = []
            for j in range(max_cols):
                item_index = i + j * data_rows
                item_str = (
                    display_list[item_index] if item_index < len(display_list) else ""
                )
                padding = " " * (base_col_width - get_visible_length(item_str))
                row_parts.append(item_str + padding)
            right_panel_lines.append(" | ".join(row_parts))

    # --- Combine Map and Panel ---
    combined_lines = []
    for i in range(view_height):
        map_part = visible_map_slice[i] if i < len(visible_map_slice) else ""
        map_padding = " " * (map_viewport_width_chars - get_visible_length(map_part))
        panel_part = right_panel_lines[i] if i < len(right_panel_lines) else ""
        combined_lines.append(f"{map_part}{map_padding} | {panel_part}")

    return combined_lines, clamped_camera_x, clamped_camera_y


def _render_footer(
    render_data: dict,
    current_input_list: list,
    cursor_pos: int,
    terminal_width: int,
    available_height: int,
) -> list[str]:
    """Renders the log panel, hotkeys, and input prompt."""
    buffer = []
    buffer.append("-" * terminal_width)
    buffer.append("--- Log ---")

    # CORRECTED: Calculate available log lines based on the space given,
    # accounting for all static footer elements.
    log_area_height = (
        available_height
        - FOOTER_SEPARATOR_HEIGHT
        - FOOTER_LOG_HEADER_HEIGHT
        - FOOTER_CONTROLS_HEIGHT
    )

    display_logs = render_data.get("logs", [])[-log_area_height:]
    buffer.extend(display_logs)

    # Pad to fill the remaining log area
    padding_needed = log_area_height - len(display_logs)
    buffer.extend([""] * max(0, padding_needed))

    buffer.append(
        "Hotkeys: wasd(scroll) p(pause) n(next) +/-(speed) | Cmd: sp <type> <x> <y> | q(quit)"
    )

    # Add input prompt
    prompt_parts = ["> "]
    for i, char in enumerate(current_input_list):
        prompt_parts.append(f"\033[7m{char}\033[27m" if i == cursor_pos else char)
    if cursor_pos == len(current_input_list):
        prompt_parts.append(f"\033[7m \033[27m")  # Cursor at the end
    buffer.append("".join(prompt_parts))

    return buffer


def display(
    render_data: dict,
    current_input_list: list,
    cursor_pos: int,
    camera_x: int,
    camera_y: int,
) -> tuple[int, int]:
    """
    Renders the entire game screen by dispatching to component-specific renderers.
    Returns the clamped camera coordinates.
    """
    terminal_width, terminal_height = os.get_terminal_size()
    output_buffer = []
    clamped_camera_x, clamped_camera_y = camera_x, camera_y  # Default if not calculated

    if terminal_width < MIN_WIDTH or terminal_height < MIN_HEIGHT:
        output_buffer = _render_minimal_view(
            render_data, current_input_list, cursor_pos, terminal_width, terminal_height
        )
    else:
        # --- 1. Define Layout ---
        # The main view gets all vertical space not used by the header or the footer.
        # The footer's height is dynamic, based on terminal size.
        footer_total_height = terminal_height // 4  # Let footer take 25% of the screen
        footer_total_height = max(
            footer_total_height,
            FOOTER_SEPARATOR_HEIGHT
            + FOOTER_LOG_HEADER_HEIGHT
            + FOOTER_CONTROLS_HEIGHT
            + 1,
        )  # Ensure footer has minimum space for 1 log line.

        main_view_height = terminal_height - HEADER_HEIGHT - footer_total_height

        # --- 2. Render Components ---
        main_view_lines, clamped_camera_x, clamped_camera_y = _render_main_view(
            render_data, terminal_width, main_view_height, camera_x, camera_y
        )

        header_line = _render_header(
            render_data, terminal_width, clamped_camera_x, clamped_camera_y
        )

        footer_lines = _render_footer(
            render_data,
            current_input_list,
            cursor_pos,
            terminal_width,
            footer_total_height,
        )

        # --- 3. Assemble Full Buffer ---
        output_buffer.append(header_line)
        output_buffer.extend(main_view_lines)
        output_buffer.extend(footer_lines)

    # --- 4. Print to Console ---
    if CLEAR_METHOD == "ansi":
        write_buffer = ["\033[?25l", "\033[H"]  # Hide cursor, move to top-left
        for i, line in enumerate(output_buffer):
            # Pad line to terminal width to prevent artifacts on resize
            padded_line = line + " " * (terminal_width - get_visible_length(line))
            write_buffer.append(padded_line)
            if i < terminal_height - 1:
                write_buffer.append("\n")

        write_buffer.append("\033[?25h")  # Show cursor
        write_buffer.append("\033[3J")  # Clear scroll
        sys.stdout.write("".join(write_buffer))
    else:
        os.system("cls" if os.name == "nt" else "clear")
        sys.stdout.write("\n".join(output_buffer))

    sys.stdout.flush()

    return clamped_camera_x, clamped_camera_y
