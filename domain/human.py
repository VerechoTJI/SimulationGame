# domain/human.py
import numpy as np
from .entity import Entity, Colors
from .rice import Rice


class Human(Entity):
    def __init__(
        self,
        pos_x,
        pos_y,
        max_age: int,
        move_speed: float,
        max_saturation: int,
        hungry_threshold: int,
    ):
        super().__init__("Human", "H", pos_x, pos_y, max_age=max_age)
        self.move_speed = move_speed
        self.path = []
        self.max_saturation = max_saturation
        self.saturation = self.max_saturation
        self.is_hungry_threshold = hungry_threshold

    # --- MODIFIED: is_alive() now checks saturation ---
    def is_alive(self):
        """A human is alive if not too old AND not starved."""
        return self.age <= self.max_age and self.saturation > 0

    # --- NEW: Method to check hunger status ---
    def is_hungry(self):
        return self.saturation < self.is_hungry_threshold

    # --- NEW: Eating action ---
    def eat(self, eatable_entity):
        # Assumes the entity has a 'saturation_yield' and a 'replant' or similar method.
        # This is a form of "duck typing".
        if hasattr(eatable_entity, "saturation_yield") and callable(
            getattr(eatable_entity, "replant", None)
        ):
            self.saturation = min(
                self.max_saturation, self.saturation + eatable_entity.saturation_yield
            )
            eatable_entity.replant()

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
            return

        if self.is_hungry():
            eat_distance = world.tile_size_meters * 1.5
            for entity in world.entities:
                if isinstance(entity, Rice) and entity.matured:
                    if np.linalg.norm(self.position - entity.position) < eat_distance:
                        world.add_log(
                            f"{Colors.GREEN}{self.name} ate {entity.name}.{Colors.RESET}"
                        )
                        # --- CLEANER: Just tell the human to eat the entity ---
                        self.eat(entity)
                        self.path = []
                        return

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
