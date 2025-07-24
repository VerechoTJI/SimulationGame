# domain/entity_manager.py
import numpy as np
import inspect  # <-- Import the inspect module
from .entity import Entity
from .human import Human
from .rice import Rice
from .sheep import Sheep
from .object_pool import ObjectPool
from .spatial_hash import SpatialHash


class EntityManager:
    """Manages the lifecycle of all entities in the world."""

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
        self.class_to_type_str_map = {
            cls: key for key, cls in self.ENTITY_TYPE_MAP.items()
        }

        entity_configs = self._get_config("entities", default={})
        cell_size = self._get_config(
            "performance", "spatial_hash_cell_size", default=20
        )

        for entity_type_str, entity_class in self.ENTITY_TYPE_MAP.items():
            if entity_type_str in entity_configs:
                attrs = self._get_config("entities", entity_type_str, "attributes")

                # --- REFACTORED FACTORY ---
                def factory(cls=entity_class, initial_attrs=attrs):
                    # Filter attributes to match only what the class __init__ expects
                    filtered_attrs = self._filter_kwargs(cls.__init__, initial_attrs)
                    return cls(0, 0, **filtered_attrs)

                self.entity_pools[entity_type_str] = ObjectPool(factory=factory)
                self.spatial_hashes[entity_type_str] = SpatialHash(cell_size=cell_size)

    def _filter_kwargs(self, method, all_kwargs: dict) -> dict:
        """
        Inspects a method's signature and returns a dict containing only the
        kwargs that the method accepts.
        """
        sig = inspect.signature(method)
        accepted_keys = {p.name for p in sig.parameters.values()}

        filtered = {
            key: value for key, value in all_kwargs.items() if key in accepted_keys
        }
        return filtered

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
        if entity_type not in self.entity_pools:
            raise ValueError(f"Unknown entity type: {entity_type}")

        world_pos_x = (pos_x + 0.5) * self.tile_size_meters
        world_pos_y = (pos_y + 0.5) * self.tile_size_meters

        config_attrs = self._get_config("entities", entity_type, "attributes")

        # Get the pool for the entity type
        pool = self.entity_pools[entity_type]

        # --- REFACTORED POOL INTERACTION ---
        # We need the class to inspect its reset method
        entity_class = self.ENTITY_TYPE_MAP[entity_type]

        # Filter the attributes to match what the entity's reset method accepts
        reset_attrs = self._filter_kwargs(entity_class.reset, config_attrs)

        # The pool's get() method will call the object's reset() method.
        # We pass the filtered attributes along with position.
        entity = pool.get(pos_y=world_pos_y, pos_x=world_pos_x, **reset_attrs)

        # Apply any override kwargs passed directly to create_entity
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
                entity.release()
        return removed_entities

    def find_closest_entity_in_radius(
        self,
        origin_pos_yx: np.ndarray,
        entity_type_class,
        search_radius: float,
        predicate=None,
    ):
        entity_type_str = self.class_to_type_str_map.get(entity_type_class)
        if not entity_type_str or entity_type_str not in self.spatial_hashes:
            return None

        spatial_hash = self.spatial_hashes[entity_type_str]

        if predicate is None:
            return spatial_hash.find_closest_in_radius(origin_pos_yx, search_radius)
        else:
            candidate_entities = spatial_hash.find_in_radius(
                origin_pos_yx, search_radius
            )
            valid_targets = [e for e in candidate_entities if predicate(e)]
            if not valid_targets:
                return None
            closest_entity = min(
                valid_targets, key=lambda e: np.sum((e.position - origin_pos_yx) ** 2)
            )
            return closest_entity

    def find_nearest_entity_in_vicinity(
        self, origin_pos_yx, entity_type_class, predicate=None
    ):
        cell_size = self._get_config(
            "performance", "spatial_hash_cell_size", default=20
        )
        fixed_search_radius = cell_size * 1.5
        return self.find_closest_entity_in_radius(
            origin_pos_yx,
            entity_type_class,
            search_radius=fixed_search_radius,
            predicate=predicate,
        )
