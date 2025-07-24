import numpy as np
from .entity import Entity
from .human import Human
from .rice import Rice
from .sheep import Sheep  # Import Sheep
from .object_pool import ObjectPool
from .spatial_hash import SpatialHash


class EntityManager:
    """Manages the lifecycle of all entities in the world."""

    # Map entity type strings from config to their respective classes
    ENTITY_TYPE_MAP = {
        "human": Human,
        "rice": Rice,
        "sheep": Sheep,
    }

    def __init__(self, config_data: dict, tile_size: int):
        self.config = config_data
        self.tile_size_meters = tile_size
        self.entities = []

        self.entity_pools = {}
        self.spatial_hashes = {}

        entity_configs = self._get_config("entities", default={})
        cell_size = self._get_config(
            "performance", "spatial_hash_cell_size", default=20
        )

        for entity_type_str, entity_class in self.ENTITY_TYPE_MAP.items():
            if entity_type_str in entity_configs:
                attrs = self._get_config("entities", entity_type_str, "attributes")

                # Create a factory that captures the correct attributes
                def factory(attrs=attrs, cls=entity_class):
                    return cls(0, 0, **attrs)

                self.entity_pools[entity_type_str] = ObjectPool(factory=factory)
                self.spatial_hashes[entity_type_str] = SpatialHash(cell_size=cell_size)

    def _get_config(self, *keys, default=None):
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def create_entity(
        self, entity_type: str, pos_y: int, pos_x: int, **kwargs
    ) -> Entity:
        """
        Generic entity creation method.
        """
        if entity_type not in self.entity_pools:
            raise ValueError(f"Unknown entity type: {entity_type}")

        world_pos_x = (pos_x + 0.5) * self.tile_size_meters
        world_pos_y = (pos_y + 0.5) * self.tile_size_meters

        attrs = self._get_config("entities", entity_type, "attributes")
        entity = self.entity_pools[entity_type].get(
            pos_y=world_pos_y, pos_x=world_pos_x, **attrs
        )

        # Apply any override kwargs (e.g., initial_saturation)
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)

        self.entities.append(entity)
        self.spatial_hashes[entity_type].add(entity)
        return entity

    def update_entity_position(
        self, entity: Entity, old_position: np.ndarray, new_position: np.ndarray
    ):
        entity_type_str = entity.name.split("_")[0].lower()
        if entity_type_str in self.spatial_hashes:
            self.spatial_hashes[entity_type_str].update(
                entity, old_position, new_position
            )

    def cleanup_dead_entities(self) -> list[Entity]:
        removed_entities = [e for e in self.entities if not e.is_alive()]
        if removed_entities:
            self.entities[:] = [e for e in self.entities if e.is_alive()]
            for entity in removed_entities:
                entity_type_str = entity.name.split("_")[0].lower()
                if entity_type_str in self.spatial_hashes:
                    self.spatial_hashes[entity_type_str].remove(entity)

                # The entity knows which pool it belongs to via the mixin
                entity.release()
        return removed_entities

    def find_nearest_entity_in_vicinity(
        self, origin_pos_yx, entity_type_class, predicate=None
    ):
        """
        Finds the nearest entity of a given type within the local vicinity.
        Uses spatial hashing for optimized searching.
        """
        # Find the string key for the given class
        entity_type_str = None
        for key, cls in self.ENTITY_TYPE_MAP.items():
            if cls == entity_type_class:
                entity_type_str = key
                break

        if entity_type_str not in self.spatial_hashes:
            # Fallback to a linear scan for any type not in the hash map (should be rare)
            candidate_entities = [
                e for e in self.entities if isinstance(e, entity_type_class)
            ]
        else:
            candidate_entities = self.spatial_hashes[entity_type_str].find_nearby(
                origin_pos_yx
            )

        closest_entity = None
        min_dist_sq = float("inf")

        for entity in candidate_entities:
            # Check instance type just in case of hash collisions or other errors
            if not isinstance(entity, entity_type_class):
                continue

            if predicate and not predicate(entity):
                continue

            dist_sq = np.sum((entity.position - origin_pos_yx) ** 2)
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_entity = entity

        return closest_entity
