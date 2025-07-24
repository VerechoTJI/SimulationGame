# domain/rice.py

from .entity import Entity


class Rice(Entity):
    def __init__(
        self, pos_y, pos_x, max_age: int, mature_age: int, saturation_yield: int
    ):
        super().__init__("Rice", "r", pos_y, pos_x, max_age=max_age)
        self.mature_age = mature_age
        self.saturation_yield = saturation_yield
        self.is_eaten = False

    def reset(self, pos_y, pos_x, max_age: int, mature_age: int, saturation_yield: int):
        """Resets the Rice plant's state for object pooling."""
        super().reset("Rice", "r", pos_y, pos_x, max_age=max_age)
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
        # Store maturity state *before* the tick increments the age
        was_matured_before_tick = self.matured

        super().tick(world)  # This increments self.age

        if self.is_alive():
            is_matured_after_tick = self.matured

            # --- NEW STATE TRANSITION LOGIC ---
            # If it just became mature on this tick, it must announce itself as a new goal.
            if is_matured_after_tick and not was_matured_before_tick:
                grid_pos = world.get_grid_position(self.position)
                world.flow_field_manager.add_goal(grid_pos)

            # Update symbol based on current state
            self.symbol = "R" if is_matured_after_tick else "r"

    def get_eaten(self):
        """Marks the rice as eaten, flagging it for removal and pooling."""
        self.is_eaten = True
