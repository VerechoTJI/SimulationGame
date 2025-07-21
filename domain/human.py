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
        reproduction_threshold: int,
        reproduction_cost: int,
        reproduction_cooldown: int,
        newborn_saturation_endowment: int,
    ):
        super().__init__("Human", "H", pos_x, pos_y, max_age=max_age)
        self.move_speed = move_speed
        self.path = []

        # Saturation Attributes
        self.max_saturation = max_saturation
        self.saturation = self.max_saturation
        self.is_hungry_threshold = hungry_threshold

        # Reproduction attributes
        self.reproduction_threshold = reproduction_threshold
        self.reproduction_cost = reproduction_cost
        self.reproduction_cooldown_period = reproduction_cooldown
        self.newborn_saturation_endowment = newborn_saturation_endowment
        self.reproduction_cooldown = 0

    def reset(
        self,
        pos_x,
        pos_y,
        max_age: int,
        move_speed: float,
        max_saturation: int,
        hungry_threshold: int,
        reproduction_threshold: int,
        reproduction_cost: int,
        reproduction_cooldown: int,
        newborn_saturation_endowment: int,
    ):
        """Resets the Human's state for object pooling."""
        super().reset("Human", "H", pos_x, pos_y, max_age=max_age)
        self.move_speed = move_speed
        self.path = []

        self.max_saturation = max_saturation
        self.saturation = self.max_saturation  # Newborns start at full saturation
        self.is_hungry_threshold = hungry_threshold

        self.reproduction_threshold = reproduction_threshold
        self.reproduction_cost = reproduction_cost
        self.reproduction_cooldown_period = reproduction_cooldown
        self.newborn_saturation_endowment = newborn_saturation_endowment
        self.reproduction_cooldown = 0

    def is_alive(self):
        """A human is alive if not too old AND not starved."""
        return self.age <= self.max_age and self.saturation > 0

    def is_hungry(self):
        return self.saturation < self.is_hungry_threshold

    def eat(self, eatable_entity):
        """Consumes an entity, gaining saturation and marking it as eaten."""
        self.saturation = min(
            self.max_saturation, self.saturation + eatable_entity.saturation_yield
        )
        # Instead of 'replanting', we mark it to be removed and pooled by the world
        if hasattr(eatable_entity, "get_eaten"):
            eatable_entity.get_eaten()

    # --- REPRODUCTION METHODS (UNCHANGED) ---
    def can_reproduce(self) -> bool:
        return (
            self.saturation >= self.reproduction_threshold
            and self.reproduction_cooldown <= 0
        )

    def reproduce(self) -> int:
        self.saturation -= self.reproduction_cost
        self.reproduction_cooldown = self.reproduction_cooldown_period
        return self.newborn_saturation_endowment

    # --- AI and Movement logic methods are unchanged ---
    def _find_food_and_path(self, world):
        nearest_food = world.entity_manager.find_nearest_entity(
            self.position, Rice, lambda r: r.matured
        )
        if nearest_food:
            start_grid_pos = world.get_grid_position(self.position)
            end_grid_pos = world.get_grid_position(nearest_food.position)
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
        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= 1
        if not self.is_alive():
            return

        if self.is_hungry():
            eat_distance = world.tile_size_meters * 1.5
            for entity in world.entity_manager.entities:
                if isinstance(entity, Rice) and entity.matured:
                    if np.linalg.norm(self.position - entity.position) < eat_distance:
                        world.add_log(
                            f"{Colors.GREEN}{self.name} ate {entity.name}.{Colors.RESET}"
                        )
                        self.eat(entity)
                        self.path = []
                        return

        if not self.path:
            if self.is_hungry():
                if not self._find_food_and_path(world):
                    self._find_new_path(world)
            else:
                self._find_new_path(world)

        if self.path:
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

    def _find_new_path(self, world):
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
