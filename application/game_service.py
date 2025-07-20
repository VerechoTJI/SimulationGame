# application/game_service.py
from domain.world import World
from domain.entity import Colors
from domain.human import Human
from domain.rice import Rice
from .config import config


class GameService:
    def __init__(self, width, height, tile_size):
        self.world = World(width, height, tile_size, config_data=config.data)

        # --- NEW: Simulation Control State ---
        self._is_paused = False
        self._base_tick_seconds = config.get("simulation", "tick_seconds")
        self._tick_seconds = self._base_tick_seconds

        # --- NEW: Control Parameters from Config ---
        self._speed_adjust_factor = config.get("controls", "speed_adjust_factor")
        self._min_tick_seconds = config.get("controls", "min_tick_seconds")
        self._max_tick_seconds = config.get("controls", "max_tick_seconds")

    def initialize_world(self):
        """Add initial welcome messages."""
        self.world.add_log("Welcome to the simulation!")
        self.world.add_log("The world has been generated.")
        self.world.add_log("Use hotkeys to control: p=pause, n=next, +/-=speed")

    def _adjust_speed(self, up=True):
        """Private helper to adjust and clamp the simulation speed."""
        if up:
            self._tick_seconds *= self._speed_adjust_factor
        else:
            self._tick_seconds /= self._speed_adjust_factor

        # Clamp the value to the configured min/max
        self._tick_seconds = max(
            self._min_tick_seconds, min(self._max_tick_seconds, self._tick_seconds)
        )

        speed_multiplier = self._base_tick_seconds / self._tick_seconds
        self.world.add_log(
            f"Speed set to {speed_multiplier:.2f}x ({self._tick_seconds:.3f}s/tick)"
        )

    def process_command(self, command_text):
        """Parses and executes both internal hotkey commands and user-typed commands."""

        # --- Handle Internal Hotkey Commands FIRST ---
        if command_text == "__PAUSE_TOGGLE__":
            self._is_paused = not self._is_paused
            status = "PAUSED" if self._is_paused else "RUNNING"
            self.world.add_log(f"Simulation {status}.")
            return

        if command_text == "__FORCE_TICK__":
            if self._is_paused:
                self.world.add_log("Advancing simulation by one tick.")
                self.world.game_tick()
            else:
                self.world.add_log(
                    f"{Colors.YELLOW}Cannot use 'next' unless paused.{Colors.RESET}"
                )
            return

        if command_text == "__SPEED_UP__":
            self._adjust_speed(up=True)
            return

        if command_text == "__SPEED_DOWN__":
            self._adjust_speed(up=False)
            return

        # --- Handle User-Typed Commands (existing logic) ---
        parts = command_text.split()
        try:
            if len(parts) == 4 and parts[0].lower() == "sp":
                entity_type = parts[1]
                x = int(parts[2])
                y = int(parts[3])
                self.world.spawn_entity(entity_type, x, y)
            else:
                self.world.add_log(
                    f"{Colors.RED}Unknown command: '{command_text}'{Colors.RESET}"
                )
        except (ValueError, IndexError):
            self.world.add_log(
                f"{Colors.RED}Invalid command format: '{command_text}'{Colors.RESET}"
            )

    def tick(self):
        """
        Advances the simulation by one tick, but only if the simulation is not paused.
        This is called by the main game loop on a timer.
        """
        # --- The Pause Gate ---
        if self._is_paused:
            return
        self.world.game_tick()

    def get_render_data(self):
        """
        Provides all necessary data for the Presentation Layer to draw the world.
        This now includes the simulation control state.
        """
        display_grid = [
            [(tile.color + tile.symbol) for tile in row] for row in self.world.grid
        ]

        human_statuses = []
        for entity in self.world.entities:
            grid_x = int(entity.position[0] / self.world.tile_size_meters)
            grid_y = int(entity.position[1] / self.world.tile_size_meters)

            if 0 <= grid_y < self.world.height and 0 <= grid_x < self.world.width:
                if isinstance(entity, Human):
                    color = Colors.RED if entity.is_hungry() else Colors.MAGENTA
                    human_statuses.append(
                        f"{color}{entity.name:<10s}{Colors.RESET}"
                        f" Sat: {entity.saturation:>3}/{entity.max_saturation}"
                    )
                elif isinstance(entity, Rice):
                    color = Colors.GREEN if entity.matured else Colors.YELLOW
                else:
                    color = Colors.WHITE
                display_grid[grid_y][grid_x] = color + entity.symbol

        return {
            "display_grid": display_grid,
            "width": self.world.width,
            "tick": self.world.tick_count,
            "entity_count": len(self.world.entities),
            "logs": self.world.log_messages,
            "colors": Colors,
            "human_statuses": human_statuses,
            # --- NEW: Pass simulation control state to the presenter ---
            "is_paused": self._is_paused,
            "tick_seconds": self._tick_seconds,
            "base_tick_seconds": self._base_tick_seconds,
        }
