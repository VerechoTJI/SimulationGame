# domain/entity_manager.py
import numpy as np
from .entity import Entity
from .human import Human
from .rice import Rice
from .object_pool import ObjectPool
from .spatial_hash import SpatialHash


class EntityManager:
    """Manages the lifecycle of all entities in the world."""

    def __init__(self, config_data: dict, tile_size: int):
        self.config = config_data
        self.tile_size_meters = tile_size
        self.entities = []

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

        cell_size = self._get_config(
            "performance", "spatial_hash_cell_size", default=20
        )
        self._rice_spatial_hash = SpatialHash(cell_size=cell_size)
        self._human_spatial_hash = SpatialHash(cell_size=cell_size)

    def _get_config(self, *keys, default=None):
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def create_human(
        self, pos_y: int, pos_x: int, initial_saturation: int = None
    ) -> Human:
        world_pos_x = (pos_x + 0.5) * self.tile_size_meters
        world_pos_y = (pos_y + 0.5) * self.tile_size_meters
        human_attrs = self._get_config("entities", "human", "attributes")
        human = self._human_pool.get(
            pos_y=world_pos_y, pos_x=world_pos_x, **human_attrs
        )
        if initial_saturation is not None:
            human.saturation = initial_saturation
        self.entities.append(human)
        self._human_spatial_hash.add(human)
        return human

    def create_rice(self, pos_y: int, pos_x: int) -> Rice:
        world_pos_x = (pos_x + 0.5) * self.tile_size_meters
        world_pos_y = (pos_y + 0.5) * self.tile_size_meters
        rice_attrs = self._get_config("entities", "rice", "attributes")
        rice = self._rice_pool.get(pos_y=world_pos_y, pos_x=world_pos_x, **rice_attrs)
        self.entities.append(rice)
        self._rice_spatial_hash.add(rice)
        return rice

    def update_entity_position(
        self, entity: Entity, old_position: np.ndarray, new_position: np.ndarray
    ):
        if isinstance(entity, Rice):
            self._rice_spatial_hash.update(entity, old_position, new_position)
        if isinstance(entity, Human):
            self._human_spatial_hash.update(entity, old_position, new_position)

    def cleanup_dead_entities(self) -> list[Entity]:
        removed_entities = [e for e in self.entities if not e.is_alive()]
        if removed_entities:
            self.entities[:] = [e for e in self.entities if e.is_alive()]
            for entity in removed_entities:
                if isinstance(entity, Rice):
                    self._rice_spatial_hash.remove(entity)
                elif isinstance(entity, Human):
                    self._rice_spatial_hash.remove(entity)
                entity.release()
        return removed_entities

    def find_nearest_entity_in_vicinity(
        self, origin_pos_yx, entity_type, predicate=None
    ):
        """
        Finds the nearest entity of a given type within the local vicinity.
        Uses spatial hashing for optimized searching of Rice and Human entities.
        """
        closest_entity = None
        min_dist_sq = float("inf")

        candidate_entities = []
        if entity_type == Rice:
            # OPTIMIZED PATH: Use the spatial hash to get local candidates only.
            candidate_entities = self._rice_spatial_hash.find_nearby(origin_pos_yx)
        elif entity_type == Human:
            candidate_entities = self._human_spatial_hash.find_nearby(origin_pos_yx)
        else:
            # UNOPTIMIZED PATH: Fallback to a linear scan for other types
            candidate_entities = [
                e for e in self.entities if isinstance(e, entity_type)
            ]

        for entity in candidate_entities:
            if not isinstance(entity, entity_type):
                continue

            if predicate and not predicate(entity):
                continue

            dist_sq = np.sum((entity.position - origin_pos_yx) ** 2)
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_entity = entity

        return closest_entity
