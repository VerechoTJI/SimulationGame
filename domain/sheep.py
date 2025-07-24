# domain/sheep.py
import numpy as np
import random

from .entity import Entity
from .rice import Rice


class Sheep(Entity):
    def __init__(
        self,
        pos_y,
        pos_x,
        move_speed,
        max_saturation,
        hungry_threshold,
        reproduction_threshold,
        reproduction_cost,
        reproduction_cooldown,
        newborn_saturation_endowment,
        max_age,
        search_radius,  # <-- Add new parameter
    ):
        super().__init__(
            name="Sheep", symbol="S", pos_y=pos_y, pos_x=pos_x, max_age=max_age
        )
        self.move_speed = move_speed
        self.max_saturation = max_saturation
        self.saturation = max_saturation
        self.hungry_threshold = hungry_threshold
        self.reproduction_threshold = reproduction_threshold
        self.reproduction_cost = reproduction_cost
        self.reproduction_cooldown_max = reproduction_cooldown
        self.reproduction_cooldown = 0
        self.newborn_saturation_endowment = newborn_saturation_endowment
        self.search_radius = search_radius  # <-- Store the radius

        # AI-related state
        self.path = []
        self.target_food = None

    def reset(
        self,
        pos_y,
        pos_x,
        move_speed,
        max_saturation,
        hungry_threshold,
        reproduction_threshold,
        reproduction_cost,
        reproduction_cooldown,
        newborn_saturation_endowment,
        max_age,
        search_radius,  # <-- Add new parameter
    ):
        """Resets the sheep's state when recycled from an object pool."""
        super().reset(
            name="Sheep", symbol="S", pos_y=pos_y, pos_x=pos_x, max_age=max_age
        )
        self.move_speed = move_speed
        self.max_saturation = max_saturation
        self.saturation = max_saturation
        self.hungry_threshold = hungry_threshold
        self.reproduction_threshold = reproduction_threshold
        self.reproduction_cost = reproduction_cost
        self.reproduction_cooldown_max = reproduction_cooldown
        self.reproduction_cooldown = 0
        self.newborn_saturation_endowment = newborn_saturation_endowment
        self.search_radius = search_radius  # <-- Store the radius
        self.path = []
        self.target_food = None

    def can_reproduce(self) -> bool:
        """Checks if the sheep has enough saturation and is not on cooldown."""
        return (
            self.saturation >= self.reproduction_threshold
            and self.reproduction_cooldown <= 0
        )

    def reproduce(self) -> int:
        """Reduces saturation, sets cooldown, and returns newborn's saturation value."""
        self.saturation -= self.reproduction_cost
        self.reproduction_cooldown = self.reproduction_cooldown_max
        return self.newborn_saturation_endowment

    def is_alive(self):
        return self.age <= self.max_age and self.saturation > 0

    def is_hungry(self):
        return self.saturation < self.hungry_threshold

    def eat(self, eatable_entity):
        """Consumes an eatable entity to replenish saturation."""
        self.saturation = min(
            self.max_saturation, self.saturation + eatable_entity.saturation_yield
        )
        if hasattr(eatable_entity, "get_eaten"):
            eatable_entity.get_eaten()
        self.path = []  # Clear path after eating

    def tick(self, world):
        """
        Main logic update for the Sheep.
        Orchestrates aging, saturation decay, and AI behaviors.
        """
        super().tick(world)
        self.saturation = max(0, self.saturation - 1)
        if self.reproduction_cooldown > 0:
            self.reproduction_cooldown -= 1
        if not self.is_alive():
            return

        if self.is_hungry():
            self._handle_hunger(world)
            return  # End tick after hunger logic

        # Fallback to wandering if not hungry
        self._wander(world)

    def _handle_hunger(self, world):
        """Logic for finding and moving towards food when hungry."""
        is_mature_rice = lambda rice: isinstance(rice, Rice) and rice.matured

        # --- THIS IS THE CORE CHANGE ---
        # Use the new radius-based search method from the entity manager
        nearest_food = world.entity_manager.find_closest_entity_in_radius(
            origin_pos_yx=self.position,
            entity_type_class=Rice,
            search_radius=self.search_radius,
            predicate=is_mature_rice,
        )

        if nearest_food:
            eat_distance = world.tile_size_meters * 1.5
            if np.linalg.norm(self.position - nearest_food.position) < eat_distance:
                self.eat(nearest_food)
            else:
                # Food found, but it's too far. Path to it.
                start_grid_pos = world.get_grid_position(self.position)
                end_grid_pos = world.get_grid_position(nearest_food.position)
                path_to_food = world.find_path(start_grid_pos, end_grid_pos)
                if path_to_food:
                    self.path = path_to_food
                    self._move_along_path(world)
                else:  # No path found, wander instead
                    self._wander(world)
        else:
            # No food found within search radius, so wander
            self._wander(world)

    def _wander(self, world):
        """Default wandering behavior."""
        if not self.path:
            self._find_new_path(world)
        self._move_along_path(world)

        # Boundary checks
        max_y = world.height * world.tile_size_meters
        max_x = world.width * world.tile_size_meters
        self.position[0] = np.clip(self.position[0], 0, max_y - 0.01)
        self.position[1] = np.clip(self.position[1], 0, max_x - 0.01)

    def _move_along_path(self, world):
        """Moves the sheep one step along its current path."""
        if not self.path:
            return

        target_grid_pos_yx = self.path[0]
        target_pos_yx = np.array(
            [
                (target_grid_pos_yx[0] + 0.5) * world.tile_size_meters,
                (target_grid_pos_yx[1] + 0.5) * world.tile_size_meters,
            ]
        )

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
        """Finds a new random, valid destination and sets the path."""
        self.path = []
        start_grid_pos_yx = world.get_grid_position(self.position)

        if (
            world.get_tile_at_pos(
                self.position[0], self.position[1]
            ).tile_move_speed_factor
            == 0
        ):
            return

        for _ in range(10):
            dest_y = random.randint(0, world.height - 1)
            dest_x = random.randint(0, world.width - 1)
            dest_tile = world.get_tile_at_pos(dest_y, dest_x)

            if dest_tile.tile_move_speed_factor > 0:
                path = world.find_path(start_grid_pos_yx, (dest_y, dest_x))
                if path:
                    self.path = path
                    return
