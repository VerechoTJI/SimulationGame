# domain/human.py
import numpy as np
from .entity import Entity, Colors
from .rice import Rice
import random


class Human(Entity):
    def __init__(
        self,
        pos_y,
        pos_x,
        max_age: int,
        move_speed: float,
        max_saturation: int,
        hungry_threshold: int,
        reproduction_threshold: int,
        reproduction_cost: int,
        reproduction_cooldown: int,
        newborn_saturation_endowment: int,
    ):
        super().__init__("Human", "H", pos_y, pos_x, max_age=max_age)
        self.move_speed = move_speed
        self.path = []
        self.max_saturation = max_saturation
        self.saturation = self.max_saturation
        self.is_hungry_threshold = hungry_threshold
        self.reproduction_threshold = reproduction_threshold
        self.reproduction_cost = reproduction_cost
        self.reproduction_cooldown_period = reproduction_cooldown
        self.newborn_saturation_endowment = newborn_saturation_endowment
        self.reproduction_cooldown = 0

    def reset(
        self,
        pos_y,
        pos_x,
        max_age: int,
        move_speed: float,
        max_saturation: int,
        hungry_threshold: int,
        reproduction_threshold: int,
        reproduction_cost: int,
        reproduction_cooldown: int,
        newborn_saturation_endowment: int,
    ):
        super().reset("Human", "H", pos_y, pos_x, max_age=max_age)
        self.move_speed = move_speed
        self.path = []
        self.max_saturation = max_saturation
        self.saturation = self.max_saturation
        self.is_hungry_threshold = hungry_threshold
        self.reproduction_threshold = reproduction_threshold
        self.reproduction_cost = reproduction_cost
        self.reproduction_cooldown_period = reproduction_cooldown
        self.newborn_saturation_endowment = newborn_saturation_endowment
        self.reproduction_cooldown = 0

    def is_alive(self):
        return self.age <= self.max_age and self.saturation > 0

    def is_hungry(self):
        return self.saturation < self.is_hungry_threshold

    def eat(self, eatable_entity):
        self.saturation = min(
            self.max_saturation, self.saturation + eatable_entity.saturation_yield
        )
        if hasattr(eatable_entity, "get_eaten"):
            eatable_entity.get_eaten()
        self.path = []

    def can_reproduce(self) -> bool:
        return (
            self.saturation >= self.reproduction_threshold
            and self.reproduction_cooldown <= 0
        )

    def reproduce(self) -> int:
        self.saturation -= self.reproduction_cost
        self.reproduction_cooldown = self.reproduction_cooldown_period
        return self.newborn_saturation_endowment

    def tick(self, world):
        super().tick(world)
        self.saturation -= 1
        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= 1
        if not self.is_alive():
            return

        nearest_food = world.entity_manager.find_nearest_entity_in_vicinity(
            self.position, Rice, predicate=lambda r: r.matured
        )

        if nearest_food:
            eat_distance = world.tile_size_meters * 1.5
            if np.linalg.norm(self.position - nearest_food.position) < eat_distance:
                world.add_log(
                    f"{Colors.GREEN}{self.name} ate {nearest_food.name}.{Colors.RESET}"
                )
                self.eat(nearest_food)
                return

        if self.is_hungry():
            self.path = []
            self._move_along_flow_field(world)
        else:
            if not self.path:
                self._find_new_path(world)
            self._move_along_path(world)

        max_y = world.height * world.tile_size_meters
        max_x = world.width * world.tile_size_meters
        self.position[0] = np.clip(self.position[0], 0, max_y - 0.01)
        self.position[1] = np.clip(self.position[1], 0, max_x - 0.01)

    def _move_along_flow_field(self, world):
        flow_vector_yx = world.get_flow_vector_at_position(self.position)

        if np.all(flow_vector_yx == 0):
            if not self.path:
                self._find_new_path(world)
            self._move_along_path(world)
            return

        norm = np.linalg.norm(flow_vector_yx)
        if norm > 0:
            normalized_direction = flow_vector_yx / norm
            # CORRECTED call, adhering to (y, x) standard
            current_tile = world.get_tile_at_pos(self.position[0], self.position[1])
            effective_speed = self.move_speed * current_tile.tile_move_speed_factor

            if effective_speed > 0:
                self.position += normalized_direction * effective_speed

    def _move_along_path(self, world):
        if not self.path:
            return

        target_grid_pos_yx = self.path[0]
        target_pos_yx = np.array(
            [
                (target_grid_pos_yx[0] + 0.5) * world.tile_size_meters,
                (target_grid_pos_yx[1] + 0.5) * world.tile_size_meters,
            ]
        )

        # CORRECTED call, adhering to (y, x) standard
        current_tile = world.get_tile_at_pos(self.position[0], self.position[1])
        effective_speed = self.move_speed * current_tile.tile_move_speed_factor

        if effective_speed > 0:
            direction_vector_yx = target_pos_yx - self.position
            distance_to_target = np.linalg.norm(direction_vector_yx)

            if distance_to_target < effective_speed:
                self.position = target_pos_yx
                self.path.pop(0)
            else:
                normalized_direction = direction_vector_yx / distance_to_target
                self.position += normalized_direction * effective_speed

    def _find_new_path(self, world):
        self.path = []
        start_grid_pos_yx = world.get_grid_position(self.position)

        if (
            world.grid[start_grid_pos_yx[0]][
                start_grid_pos_yx[1]
            ].tile_move_speed_factor
            == 0
        ):
            return

        for _ in range(10):
            dest_y = random.randint(0, world.height - 1)
            dest_x = random.randint(0, world.width - 1)
            if world.grid[dest_y][dest_x].tile_move_speed_factor > 0:
                path = world.find_path(start_grid_pos_yx, (dest_y, dest_x))
                if path:
                    self.path = path
                    return
