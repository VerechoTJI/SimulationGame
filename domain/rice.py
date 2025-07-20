# domain/rice.py
from .entity import Entity


class Rice(Entity):
    def __init__(self, pos_x, pos_y, max_age: int, saturation_yield: int):
        super().__init__("Rice", "r", pos_x, pos_y, max_age=max_age)
        self.saturation_yield = saturation_yield  # The amount of saturation it provides

    @property
    def matured(self):
        return self.age >= (self.max_age / 2)

    def tick(self, world):
        super().tick(world)
        self.symbol = "R" if self.matured else "r"

    def replant(self):
        self.age = 0
