# domain/rice.py

from .entity import Entity


class Rice(Entity):
    def __init__(
        self, pos_x, pos_y, max_age: int, mature_age: int, saturation_yield: int
    ):
        super().__init__("Rice", "r", pos_x, pos_y, max_age=max_age)
        self.mature_age = mature_age
        self.saturation_yield = saturation_yield
        self.is_eaten = False

    def reset(self, pos_x, pos_y, max_age: int, mature_age: int, saturation_yield: int):
        """Resets the Rice plant's state for object pooling."""
        super().reset("Rice", "r", pos_x, pos_y, max_age=max_age)
        self.mature_age = mature_age
        self.saturation_yield = saturation_yield
        self.is_eaten = False
        self.symbol = "r"  # Ensure it resets to immature symbol

    @property
    def matured(self):
        return self.age >= self.mature_age

    def is_alive(self):
        """A rice plant is alive if it's not too old and hasn't been eaten."""
        return super().is_alive() and not self.is_eaten

    def tick(self, world):
        super().tick(world)
        if self.is_alive():
            self.symbol = "R" if self.matured else "r"

    def get_eaten(self):
        """Marks the rice as eaten, flagging it for removal and pooling."""
        self.is_eaten = True
