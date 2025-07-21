# domain/tile.py

from .entity import Colors


class Tile:
    """Represents a single tile on the world grid."""

    def __init__(self, name, symbol, color, move_speed_factor):
        self.name = name
        self.symbol = symbol
        self.color = color
        self.tile_move_speed_factor = move_speed_factor


# Global dictionary of available tile types.
TILES = {
    "land": Tile("Land", ".", Colors.GREEN, 1.0),
    "water": Tile("Water", "~", Colors.BLUE, 0.0),  # Impassable
    "mountain": Tile("Mountain", "^", Colors.WHITE, 0.5),  # Slow to cross
}
