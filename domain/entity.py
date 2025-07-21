# domain/entity.py

import numpy as np
from .object_pool import PooledObjectMixin


# --- Helper for colored output ---
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


class Entity(PooledObjectMixin):
    id_counter = 0

    def __init__(self, name, symbol, pos_x, pos_y, max_age):
        super().__init__()  # Initialize the PooledObjectMixin
        self.id = Entity.id_counter
        Entity.id_counter += 1
        self.name = f"{name}_{self.id}"
        self.symbol = symbol
        self.position = np.array([float(pos_x), float(pos_y)])
        self.age = 0
        self.max_age = max_age

    def reset(self, name, symbol, pos_x, pos_y, max_age):
        """Resets the entity's state when recycled from an object pool."""
        # Note: self.id and self.pool are NOT reset.
        self.name = f"{name}_{self.id}"
        self.symbol = symbol
        self.position = np.array([float(pos_x), float(pos_y)])
        self.age = 0
        self.max_age = max_age

    def tick(self, world):
        self.age += 1

    def is_alive(self):
        return self.age <= self.max_age

    def __str__(self):
        return f"{self.name} at {self.position.round(1)}"
