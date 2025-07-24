# application/game_service.py
from domain.world import World
from domain.entity import Colors
from domain.human import Human
from domain.rice import Rice
from domain.sheep import Sheep
from .config import config


class GameService:
    def __init__(self, grid_width, grid_height, tile_size):
        self.world = World(grid_width, grid_height, tile_size, config_data=config.data)
        self._is_paused = False
        self._show_flow_field = False
        self._base_tick_seconds = config.get("simulation", "tick_seconds")
        self._tick_seconds = self._base_tick_seconds
        self._speed_adjust_factor = config.get("controls", "speed_adjust_factor")
        self._min_tick_seconds = config.get("controls", "min_tick_seconds")
        self._max_tick_seconds = config.get("controls", "max_tick_seconds")

    def initialize_world(self):
        """Add initial welcome messages."""
        self.world.add_log("Welcome to the simulation!")
        self.world.add_log("The world has been generated.")
        self.world.add_log(
            "Use hotkeys to control: p=pause, n=next,  +/-=speed, f=flow"
        )

    def is_paused(self) -> bool:
        return self._is_paused

    def toggle_pause(self):
        self._is_paused = not self._is_paused
        status = "PAUSED" if self._is_paused else "RUNNING"
        self.world.add_log(f"Simulation {status}.")

    def toggle_flow_field_visibility(self):
        self._show_flow_field = not self._show_flow_field
        status = "shown" if self._show_flow_field else "hidden"
        self.world.add_log(
            f"{Colors.BLUE}Flow field visualization {status}.{Colors.RESET}"
        )

    def force_tick(self):
        if self._is_paused:
            self.world.add_log("Advancing simulation by one tick.")
            self.world.game_tick()
        else:
            self.world.add_log(
                f"{Colors.YELLOW}Cannot use 'next' unless paused.{Colors.RESET}"
            )

    def _adjust_speed(self, up=True):
        if up:
            self._tick_seconds /= self._speed_adjust_factor
        else:
            self._tick_seconds *= self._speed_adjust_factor
        self._tick_seconds = max(
            self._min_tick_seconds, min(self._max_tick_seconds, self._tick_seconds)
        )
        speed_multiplier = self._base_tick_seconds / self._tick_seconds
        self.world.add_log(
            f"Speed set to {speed_multiplier:.2f}x ({self._tick_seconds:.3f}s/tick)"
        )

    def speed_up(self):
        self._adjust_speed(up=True)

    def speed_down(self):
        self._adjust_speed(up=False)

    def execute_user_command(self, command_text: str):
        """Parses and executes commands, handling domain exceptions."""
        parts = command_text.strip().split()
        if not parts:
            return

        command = parts[0].lower()

        if command == "sp" and len(parts) == 4:
            try:
                entity_type = parts[1]
                # --- NOTE: The user provides (x, y), we use (y, x) internally ---
                x = int(parts[2])
                y = int(parts[3])

                # --- THIS IS THE ARCHITECTURAL FIX ---
                # 1. Call the domain method
                self.world.spawn_entity(entity_type, y, x)
                # 2. On success, the Application layer logs it
                self.world.add_log(
                    f"{Colors.GREEN}Successfully spawned a {entity_type} at ({y}, {x}).{Colors.RESET}"
                )

            except ValueError as e:
                # 3. On failure, the Application layer catches the domain error and logs it
                self.world.add_log(f"{Colors.RED}Command failed: {e}{Colors.RESET}")
            except IndexError:
                self.world.add_log(
                    f"{Colors.RED}Invalid command format for 'sp'. Use: sp <type> <x> <y>{Colors.RESET}"
                )
        else:
            self.world.add_log(
                f"{Colors.RED}Unknown command: '{command_text}'{Colors.RESET}"
            )

    def tick(self):
        if self._is_paused:
            return
        self.world.game_tick()

    def get_render_data(self) -> dict:
        """
        Provides all necessary data for the Presentation Layer to draw the world.
        """
        display_grid = [
            [(tile.color + tile.symbol) for tile in row] for row in self.world.grid
        ]

        human_statuses = []
        sheep_statuses = []  # Add a list for sheep
        for entity in self.world.entity_manager.entities:
            grid_y = int(entity.position[0] / self.world.tile_size_meters)
            grid_x = int(entity.position[1] / self.world.tile_size_meters)

            if 0 <= grid_y < self.world.height and 0 <= grid_x < self.world.width:
                color = Colors.WHITE
                if isinstance(entity, Human):
                    color = Colors.RED if entity.is_hungry() else Colors.MAGENTA
                    human_statuses.append(
                        f"{color}{entity.name:<10s}{Colors.RESET}"
                        f" Sat: {entity.saturation:>3}/{entity.max_saturation}"
                    )
                # --- NEW: Handle Sheep ---
                elif isinstance(entity, Sheep):
                    color = Colors.CYAN if not entity.is_hungry() else Colors.BLUE
                    sheep_statuses.append(
                        f"{color}{entity.name:<10s}{Colors.RESET}"
                        f" Sat: {entity.saturation:>3}/{entity.max_saturation}"
                    )
                elif isinstance(entity, Rice):
                    color = Colors.GREEN if entity.matured else Colors.YELLOW

                display_grid[grid_y][grid_x] = color + entity.symbol

        render_payload = {
            "display_grid": display_grid,
            "width": self.world.width,
            "tick": self.world.tick_count,
            "entity_count": len(self.world.entity_manager.entities),
            "logs": self.world.log_messages,
            "colors": Colors,
            "human_statuses": human_statuses,
            "sheep_statuses": sheep_statuses,  # Add sheep statuses to payload
            "is_paused": self._is_paused,
            "tick_seconds": self._tick_seconds,
            "base_tick_seconds": self._base_tick_seconds,
            "show_flow_field": self._show_flow_field,
        }
        if self._show_flow_field:
            render_payload["flow_field_data"] = self.world.food_flow_field
        return render_payload
