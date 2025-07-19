# domain/human.py
import numpy as np
from .entity import Entity, Colors
from .rice import Rice


class Human(Entity):
    def __init__(self, pos_x, pos_y):
        super().__init__("Human", "H", pos_x, pos_y, max_age=1200)
        self.move_speed = 1.4
        self.path = []

    def _find_new_path(self, world):
        # ... (This method remains identical to the original, just needs world.width, etc.)
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

    def tick(self, world):
        # ... (This method remains identical to the original)
        super().tick(world)
        if not self.path:
            self._find_new_path(world)
            if not self.path:
                return
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
        for entity in world.entities:
            if isinstance(entity, Rice) and entity.matured:
                if np.linalg.norm(self.position - entity.position) <= 1.0:
                    world.add_log(
                        f"{Colors.YELLOW}{self.name} harvested and replanted {entity.name}.{Colors.RESET}"
                    )
                    entity.replant()
                    break
