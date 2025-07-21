# domain/entity_manager.py

import numpy as np
from .entity import Entity
from .human import Human
from .rice import Rice
from .object_pool import ObjectPool


class EntityManager:
    """Manages the lifecycle of all entities in the world."""

    def __init__(self, config_data: dict, tile_size: int):
        self.config = config_data
        self.tile_size_meters = tile_size
        self.entities = []

        # Initialize object pools based on config
        self._human_pool = ObjectPool(
            factory=lambda: Human(
                0, 0, **self._get_config("entities", "human", "attributes")
            )
        )
        self._rice_pool = ObjectPool(
            factory=lambda: Rice(
                0, 0, **self._get_config("entities", "rice", "attributes")
            )
        )

    def _get_config(self, *keys, default=None):
        """Helper to safely access nested config values."""
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def create_human(self, x: int, y: int, initial_saturation: int = None) -> Human:
        """Creates a Human at a grid location, adding it to the entity list."""
        pos_x = (x + 0.5) * self.tile_size_meters
        pos_y = (y + 0.5) * self.tile_size_meters

        human_attrs = self._get_config("entities", "human", "attributes")
        human = self._human_pool.get(pos_x=pos_x, pos_y=pos_y, **human_attrs)

        if initial_saturation is not None:
            human.saturation = initial_saturation

        self.entities.append(human)
        return human

    def create_rice(self, x: int, y: int) -> Rice:
        """Creates a Rice plant at a grid location, adding it to the entity list."""
        pos_x = (x + 0.5) * self.tile_size_meters
        pos_y = (y + 0.5) * self.tile_size_meters

        rice_attrs = self._get_config("entities", "rice", "attributes")
        rice = self._rice_pool.get(pos_x=pos_x, pos_y=pos_y, **rice_attrs)

        self.entities.append(rice)
        return rice

    def cleanup_dead_entities(self) -> list[Entity]:
        """
        Removes dead entities from the simulation and returns them to their object pools.
        Returns the list of entities that were removed.
        """
        removed_entities = [e for e in self.entities if not e.is_alive()]

        if removed_entities:
            # Filter the main list in-place to keep only the living
            self.entities[:] = [e for e in self.entities if e.is_alive()]
            for entity in removed_entities:
                entity.release()  # Return to pool

        return removed_entities

    def find_nearest_entity(self, origin_pos, entity_type, predicate=None):
        """Finds the nearest entity of a given type that satisfies a predicate."""
        closest_entity = None
        min_dist_sq = float("inf")

        for entity in self.entities:
            if isinstance(entity, entity_type):
                if predicate and not predicate(entity):
                    continue
                dist_sq = np.sum((entity.position - origin_pos) ** 2)
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    closest_entity = entity

        return closest_entity
