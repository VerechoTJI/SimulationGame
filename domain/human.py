# domain/human.py
import numpy as np
from .entity import Entity, Colors
from .rice import Rice


class Human(Entity):
    def __init__(self, pos_x, pos_y):
        super().__init__("Human", "H", pos_x, pos_y, max_age=1200)
        self.move_speed = 1.4
        self.path = []
        # --- NEW: Saturation Attributes ---
        self.max_saturation = 100
        self.saturation = self.max_saturation
        self.is_hungry_threshold = 40

    # --- MODIFIED: is_alive() now checks saturation ---
    def is_alive(self):
        """A human is alive if not too old AND not starved."""
        return self.age <= self.max_age and self.saturation > 0

    # --- NEW: Method to check hunger status ---
    def is_hungry(self):
        return self.saturation < self.is_hungry_threshold

    # --- NEW: Eating action ---
    def eat(self, rice_plant, saturation_gain=50):
        """Increases saturation and replants the rice."""
        self.saturation = min(self.max_saturation, self.saturation + saturation_gain)
        rice_plant.replant()

    def _find_food_and_path(self, world):
        """Finds the nearest mature rice and sets a path to it."""
        nearest_food = world.find_nearest_entity(
            self.position, Rice, lambda r: r.matured
        )

        if nearest_food:
            start_grid_pos = (
                int(self.position[0] / world.tile_size_meters),
                int(self.position[1] / world.tile_size_meters),
            )
            end_grid_pos = (
                int(nearest_food.position[0] / world.tile_size_meters),
                int(nearest_food.position[1] / world.tile_size_meters),
            )

            # Ensure we don't try to pathfind from an invalid start
            start_tile = world.get_tile_at_pos(self.position[0], self.position[1])
            if start_tile.tile_move_speed_factor == 0:
                return False

            path = world.find_path(start_grid_pos, end_grid_pos)
            if path:
                self.path = path
                world.add_log(
                    f"{Colors.RED}{self.name} is hungry and is heading to {nearest_food.name}.{Colors.RESET}"
                )
                return True
        return False

    def tick(self, world):
        super().tick(world)
        self.saturation -= 1
        if not self.is_alive():
            return  # No further actions if dead

        # --- AI Decision Making ---

        # Priority 1: EAT if hungry and next to food.
        if self.is_hungry():
            eat_distance = world.tile_size_meters * 1.5
            for entity in world.entities:
                if isinstance(entity, Rice) and entity.matured:
                    if np.linalg.norm(self.position - entity.position) < eat_distance:
                        world.add_log(
                            f"{Colors.GREEN}{self.name} ate {entity.name}.{Colors.RESET}"
                        )
                        self.eat(entity)
                        self.path = []  # Clear path after eating.
                        # After eating, the turn is over. Do not move or plan.
                        return  # <--- KEY FIX: Exit the tick method.

        # Priority 2: PLAN a path if one is needed.
        # This block is now only reached if the human did NOT eat this tick.
        if not self.path:
            # If hungry, the only goal is to find food.
            if self.is_hungry():
                if not self._find_food_and_path(world):
                    # If no food found, wander aimlessly as a last resort.
                    self._find_new_path(world)
            # If not hungry, just wander.
            else:
                self._find_new_path(world)

        # Priority 3: MOVE if a path exists.
        # This block is only reached if no eating occurred.
        if self.path:
            # This entire movement block is unchanged.
            target_grid_pos = self.path[0]
            target_pos = np.array(
                [
                    (target_grid_pos[0] + 0.5) * world.tile_size_meters,
                    (target_grid_pos[1] + 0.5) * world.tile_size_meters,
                ]
            )
            current_tile = world.get_tile_at_pos(self.position[0], self.position[1])
            effective_speed = self.move_speed * current_tile.tile_move_speed_factor
            if effective_speed > 0:
                direction_vector = target_pos - self.position
                distance_to_target = np.linalg.norm(direction_vector)
                if distance_to_target < effective_speed:
                    self.position = target_pos
                    self.path.pop(0)
                    if not self.path:
                        world.add_log(
                            f"{Colors.GREEN}{self.name} has reached their destination.{Colors.RESET}"
                        )
                else:
                    normalized_direction = direction_vector / distance_to_target
                    move_vector = normalized_direction * effective_speed
                    self.position += move_vector

            max_x = world.width * world.tile_size_meters
            max_y = world.height * world.tile_size_meters
            self.position[0] = np.clip(self.position[0], 0, max_x - 0.01)
            self.position[1] = np.clip(self.position[1], 0, max_y - 0.01)

    # _find_new_path method is unchanged
    def _find_new_path(self, world):
        # ... (identical to previous version)
        self.path = []
        start_grid_x = np.clip(
            int(self.position[0] / world.tile_size_meters), 0, world.width - 1
        )
        start_grid_y = np.clip(
            int(self.position[1] / world.tile_size_meters), 0, world.height - 1
        )
        if world.grid[start_grid_y][start_grid_x].tile_move_speed_factor == 0:
            world.add_log(
                f"{Colors.RED}{self.name} is stuck on an impassable tile!{Colors.RESET}"
            )
            return
        import random

        for _ in range(10):
            dest_x = random.randint(0, world.width - 1)
            dest_y = random.randint(0, world.height - 1)
            path = world.find_path((start_grid_x, start_grid_y), (dest_x, dest_y))
            if path:
                self.path = path
                world.add_log(
                    f"{Colors.CYAN}{self.name} is now heading to grid cell ({dest_x}, {dest_y}).{Colors.RESET}"
                )
                return
        world.add_log(
            f"{Colors.YELLOW}{self.name} couldn't find a path and is wandering.{Colors.RESET}"
        )
