# presentation/renderer.py
import os
import re
import sys
import numpy as np

CLEAR_METHOD = "ansi"

# --- Constants for layout ---
MIN_WIDTH = 90
MIN_HEIGHT = 20
HEADER_HEIGHT = 1
FOOTER_CONTROLS_HEIGHT = 2
FOOTER_SEPARATOR_HEIGHT = 1
FOOTER_LOG_HEADER_HEIGHT = 1


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
        "--- Log ---",
    ]
    display_logs = render_data.get("logs", [])[-(terminal_height - len(buffer) - 1) :]
    buffer.extend(display_logs)
    padding_needed = terminal_height - len(buffer) - 1
    buffer.extend([""] * max(0, padding_needed))
    prompt_parts = ["> "]
    for i, char in enumerate(current_input_list):
        prompt_parts.append(f"\033[7m{char}\033[27m" if i == cursor_pos else char)
    if cursor_pos == len(current_input_list):
        prompt_parts.append(f"\033[7m \033[27m")
    buffer.append("".join(prompt_parts))
    return buffer


def _render_header(
    render_data: dict, terminal_width: int, clamped_camera_x: int, clamped_camera_y: int
) -> str:
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
    Colors = render_data["colors"]
    full_map_grid = render_data["display_grid"]

    if render_data.get("show_flow_field", False):
        flow_field_data = render_data.get("flow_field_data")
        if flow_field_data is not None:
            flow_grid = [row[:] for row in full_map_grid]

            # --- FIX: Arrow map directions corrected for (dy, dx) format ---
            arrow_map = {
                (0, 0): "·",
                (-1, 0): "↑",  # dy = -1 (North)
                (1, 0): "↓",  # dy = +1 (South)
                (0, -1): "←",  # dx = -1 (West)
                (0, 1): "→",  # dx = +1 (East)
                (-1, -1): "↖",  # North-West
                (-1, 1): "↗",  # North-East
                (1, -1): "↙",  # South-West
                (1, 1): "↘",  # South-East
            }

            for y in range(flow_field_data.shape[0]):
                for x in range(flow_field_data.shape[1]):
                    if y < len(flow_grid) and x < len(flow_grid[y]):
                        vy, vx = flow_field_data[y, x]
                        vector_tuple = (int(vy), int(vx))
                        arrow = arrow_map.get(vector_tuple, "?")
                        flow_grid[y][x] = Colors.BLUE + arrow
            full_map_grid = flow_grid

    full_map_height = len(full_map_grid)
    full_map_width = len(full_map_grid[0]) if full_map_height > 0 else 0
    human_statuses = sorted(render_data.get("human_statuses", []))
    base_col_width = max((get_visible_length(s) for s in human_statuses), default=12)
    col_separator_width = 3
    right_panel_width = base_col_width
    if terminal_width > (base_col_width * 2 + col_separator_width + 60):
        right_panel_width = base_col_width * 2 + col_separator_width
    map_viewport_width_chars = terminal_width - right_panel_width - 2
    map_viewport_width = max(10, map_viewport_width_chars // 2)
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
    if len(visible_map_slice) > 0:
        map_viewport_width_chars = get_visible_length(visible_map_slice[0])
    right_panel_lines = [
        f"Tick: {render_data['tick']} | Entities: {render_data['entity_count']}",
        "--- Humans ---",
    ]
    extra_col = (terminal_width - map_viewport_width_chars - right_panel_width - 2) // (
        base_col_width + col_separator_width
    )
    max_cols = 1 if right_panel_width == base_col_width else 2 + extra_col
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
    combined_lines = []
    for i in range(view_height):
        map_part = visible_map_slice[i] if i < len(visible_map_slice) else ""
        panel_part = right_panel_lines[i] if i < len(right_panel_lines) else ""
        combined_lines.append(f"{map_part}| {panel_part}")
    return combined_lines, clamped_camera_x, clamped_camera_y


def _render_footer(
    render_data: dict,
    current_input_list: list,
    cursor_pos: int,
    terminal_width: int,
    available_height: int,
) -> list[str]:
    """Renders the log panel, hotkeys, and input prompt."""
    buffer = ["-" * terminal_width, "--- Log ---"]
    log_area_height = (
        available_height
        - FOOTER_SEPARATOR_HEIGHT
        - FOOTER_LOG_HEADER_HEIGHT
        - FOOTER_CONTROLS_HEIGHT
    )
    display_logs = render_data.get("logs", [])[-log_area_height:]
    buffer.extend(display_logs)
    padding_needed = log_area_height - len(display_logs)
    buffer.extend([""] * max(0, padding_needed))
    buffer.append(
        "Hotkeys: wasd(scroll) f(flow) p(pause) n(next) +/-(speed) | Cmd: sp <type> <x> <y> | q(quit)"
    )
    prompt_parts = ["> "]
    for i, char in enumerate(current_input_list):
        prompt_parts.append(f"\033[7m{char}\033[27m" if i == cursor_pos else char)
    if cursor_pos == len(current_input_list):
        prompt_parts.append(f"\033[7m \033[27m")
    buffer.append("".join(prompt_parts))
    return buffer


def display(
    render_data: dict,
    current_input_list: list,
    cursor_pos: int,
    camera_x: int,
    camera_y: int,
) -> tuple[int, int]:
    terminal_width, terminal_height = os.get_terminal_size()
    output_buffer = []
    clamped_camera_y, clamped_camera_x = camera_y, camera_x

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
        write_buffer.append("\033[3J")  # Clear scroll
        sys.stdout.write("".join(write_buffer))
    else:
        os.system("cls" if os.name == "nt" else "clear")
        sys.stdout.write("\n".join(output_buffer))
    sys.stdout.flush()
    return clamped_camera_x, clamped_camera_y
