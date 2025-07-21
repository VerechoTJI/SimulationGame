# presentation/renderer.py
import os
import re
import sys

CLEAR_METHOD = "ansi"  # or "system"


def get_visible_length(s: str) -> int:
    """Calculates the visible length of a string by removing ANSI escape codes."""
    return len(re.sub(r"\033\[[0-9;]*m", "", s))


def display(
    render_data: dict,
    current_input_list: list,
    cursor_pos: int,
    camera_x: int,
    camera_y: int,
) -> tuple[int, int]:
    """
    Renders the entire game screen, including map, stats, logs, and input prompt.
    Returns the clamped camera coordinates.
    """
    output_buffer = []
    Colors = render_data["colors"]
    full_map_grid = render_data["display_grid"]
    full_map_height = len(full_map_grid)
    full_map_width = len(full_map_grid[0]) if full_map_height > 0 else 0
    terminal_width, terminal_height = os.get_terminal_size()

    # --- 1. Calculate Viewport & Panel Dimensions ---
    header_height = 1
    map_border_height = 1
    log_header_height = 1
    footer_height = 2
    vertical_chrome = (
        header_height + map_border_height + log_header_height + footer_height
    )

    human_statuses = render_data.get("human_statuses", [])
    human_statuses.sort()
    base_col_width = max((get_visible_length(s) for s in human_statuses), default=10)
    col_separator_width = 3

    right_panel_width = base_col_width
    if terminal_width > (base_col_width * 2 + col_separator_width + 50):
        right_panel_width = base_col_width * 2 + col_separator_width

    map_viewport_width_chars = (
        terminal_width - right_panel_width - col_separator_width - 1
    )
    map_viewport_width = max(10, map_viewport_width_chars // 2)
    map_viewport_height = max(5, terminal_height - vertical_chrome - 3)

    # --- 2. Clamp Camera & Create Map Slice ---
    clamped_camera_x = max(0, min(camera_x, full_map_width - map_viewport_width))
    clamped_camera_y = max(0, min(camera_y, full_map_height - map_viewport_height))

    visible_map_slice = []
    if full_map_width > 0:
        for y in range(map_viewport_height):
            row_y = clamped_camera_y + y
            if row_y < full_map_height:
                row = full_map_grid[row_y][
                    clamped_camera_x : clamped_camera_x + map_viewport_width
                ]
                visible_map_slice.append(row)

    # --- 3. Assemble Header ---
    status = "PAUSED" if render_data.get("is_paused", False) else "RUNNING"
    base_tick = render_data.get("base_tick_seconds", 0.3)
    current_tick = render_data.get("tick_seconds", 0.3)
    speed_multiplier = base_tick / current_tick if current_tick > 0 else float("inf")

    perf_stats = f"Render:{render_data.get('render_fps', 0.0):.1f}fps|Logic:{render_data.get('logic_tps', 0.0):.1f}tps"
    camera_stats = f"Cam:({clamped_camera_x},{clamped_camera_y})"
    status_stats = f"Status:{status}|Spd:{speed_multiplier:.1f}x"
    title_text = "--- Simulation ---"

    full_title_line = f"{title_text} | {perf_stats} | {camera_stats} | {status_stats}"
    if len(full_title_line) > terminal_width:
        full_title_line = full_title_line[:terminal_width]
    output_buffer.append(full_title_line)

    # --- 4. Assemble Right-hand Panel ---
    right_panel_lines = []
    right_panel_lines.append(
        f"Tick: {render_data['tick']} | Ent: {render_data['entity_count']}"
    )
    right_panel_lines.append("--- Humans ---")

    map_slice_width_chars = (
        get_visible_length(" ".join(visible_map_slice[0])) if visible_map_slice else 0
    )
    available_width = terminal_width - map_slice_width_chars - 3
    max_cols = max(1, available_width // (base_col_width + col_separator_width))
    data_rows = map_viewport_height - 2  # 2 header lines in panel

    display_list = []
    if data_rows > 0:
        display_capacity = data_rows * max_cols
        display_list = human_statuses
        if len(human_statuses) > display_capacity:
            num_to_show = display_capacity - 1
            num_hidden = len(human_statuses) - num_to_show
            display_list = human_statuses[:num_to_show]
            summary_msg = f"+{num_hidden} more"
            if get_visible_length(summary_msg) > base_col_width:
                summary_msg = f"+... more"
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
        right_panel_lines.append(" | ".join(row_parts))

    # --- 5. Combine Map and Panel, then add Logs and Footer ---
    for i in range(map_viewport_height):
        map_part = (
            " ".join(visible_map_slice[i]) + Colors.RESET
            if i < len(visible_map_slice)
            else ""
        )
        status_part = right_panel_lines[i] if i < len(right_panel_lines) else ""
        output_buffer.append(f"{map_part} | {status_part}")

    output_buffer.append("-" * (map_slice_width_chars + 1))

    lines_used_so_far = len(output_buffer)
    available_log_lines = max(0, terminal_height - lines_used_so_far - footer_height)
    display_logs = render_data.get("logs", [])[-available_log_lines:]
    output_buffer.append("--- Log ---")
    output_buffer.extend(display_logs)

    padding_needed = terminal_height - len(output_buffer) - footer_height + 1
    for _ in range(max(0, padding_needed)):
        output_buffer.append("")

    output_buffer.append(
        "Hotkeys: wasd(scroll) p(pause) n(next) +/-(speed) | Cmd: sp <type> <x> <y> | q(quit)"
    )

    prompt_parts = ["> "]
    for i, char in enumerate(current_input_list):
        prompt_parts.append(f"\033[7m{char}\033[27m" if i == cursor_pos else char)
    if cursor_pos == len(current_input_list):
        prompt_parts.append(f"\033[7m \033[27m")  # Cursor at the end
    output_buffer.append("".join(prompt_parts))

    # --- 6. Print to Console ---
    if CLEAR_METHOD == "ansi":
        write_buffer = ["\033[?25l", "\033[H"]  # Hide cursor, move to top-left
        for i, line in enumerate(output_buffer):
            write_buffer.append(line)
            write_buffer.append("\033[K")  # Clear rest of line
            if i < len(output_buffer) - 1:
                write_buffer.append("\n")
        write_buffer.append("\033[3J")  # Clear scroll
        write_buffer.append("\033[J")  # Clear screen below cursor
        write_buffer.append("\033[?25h")  # Show cursor
        sys.stdout.write("".join(write_buffer))
    else:
        os.system("cls" if os.name == "nt" else "clear")
        sys.stdout.write("\n".join(output_buffer))

    sys.stdout.flush()

    return clamped_camera_x, clamped_camera_y
