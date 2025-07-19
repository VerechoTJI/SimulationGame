# domain/rice.py
from .entity import Entity


class Rice(Entity):
    def __init__(self, pos_x, pos_y):
        super().__init__("Rice", "r", pos_x, pos_y, max_age=16)

    @property
    def matured(self):
        return self.age >= (self.max_age / 2)

    def tick(self, world):
        super().tick(world)
        self.symbol = "R" if self.matured else "r"

    def replant(self):
        self.age = 0
