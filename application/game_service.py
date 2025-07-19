# application/game_service.py
from domain.world import World
from domain.entity import Colors
from domain.human import Human


class GameService:
    def __init__(self, width, height, tile_size):
        self.world = World(width, height, tile_size)

    def initialize_world(self):
        """Add initial welcome messages."""
        self.world.add_log("Welcome to the simulation!")
        self.world.add_log("The world has been generated.")
        self.world.add_log("Use the command 'sp human 32 15' to start.")

    def process_command(self, command_text):
        """Parses and executes a command."""
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
        """Advances the simulation by one tick."""
        self.world.game_tick()

    def get_render_data(self):
        """
        Provides all necessary data for the Presentation Layer to draw the world.
        This is a key method for separating Domain from Presentation.
        """
        display_grid = [
            [(tile.color + tile.symbol) for tile in row] for row in self.world.grid
        ]

        for entity in self.world.entities:
            grid_x = int(entity.position[0] / self.world.tile_size_meters)
            grid_y = int(entity.position[1] / self.world.tile_size_meters)
            if 0 <= grid_y < self.world.height and 0 <= grid_x < self.world.width:
                color = Colors.MAGENTA if isinstance(entity, Human) else Colors.YELLOW
                display_grid[grid_y][grid_x] = color + entity.symbol

        return {
            "display_grid": display_grid,
            "width": self.world.width,
            "tick": self.world.tick_count,
            "entity_count": len(self.world.entities),
            "logs": self.world.log_messages,
            "colors": Colors,
        }
