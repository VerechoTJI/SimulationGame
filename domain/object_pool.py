# domain/object_pool.py


class PooledObjectMixin:
    """
    A mixin for domain objects that are managed by an ObjectPool.

    Provides a `release()` method to return the object to its pool.
    The ObjectPool is responsible for setting the `pool` attribute on the object.
    """

    def __init__(self, *args, **kwargs):
        # This allows the mixin to be safely used with classes that have their own __init__
        super().__init__(*args, **kwargs)
        self.pool = None

    def release(self):
        """Returns this object to the pool it originated from."""
        if not self.pool:
            raise RuntimeError("This object does not belong to a pool.")
        self.pool.release(self)


class ObjectPool:
    """
    A generic object pool that recycles objects to reduce instantiation overhead.
    """

    def __init__(self, factory):
        """
        Initializes the pool.

        Args:
            factory (callable): A no-argument function that returns a new object
                                instance when the pool is empty. The object should
                                inherit from PooledObjectMixin.
        """
        self._factory = factory
        self._pool = []

    def get(self, *args, **kwargs):
        """
        Gets an object from the pool.

        If the pool has an available object, it is recycled. Otherwise, a new
        one is created using the factory.

        In both cases, the object's `reset(*args, **kwargs)` method is called
        to ensure it is in a clean initial state.

        Args:
            *args: Positional arguments to pass to the object's `reset` method.
            **kwargs: Keyword arguments to pass to the object's `reset` method.

        Returns:
            An initialized or reset instance of the pooled object.
        """
        if self._pool:
            obj = self._pool.pop()
        else:
            obj = self._factory()
            obj.pool = self

        # Every object, new or recycled, must be reset to a known state.
        # We rely on the object having a `reset` method.
        obj.reset(*args, **kwargs)
        return obj

    def release(self, obj):
        """
        Returns an object to the pool, making it available for reuse.

        Args:
            obj: The object to release back into the pool.
        """
        self._pool.append(obj)
