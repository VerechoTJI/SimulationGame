# tests/test_object_pool.py

import pytest
from unittest.mock import Mock

# We are about to create these in the domain layer.
# These imports will fail until we create the file.
from domain.object_pool import ObjectPool, PooledObjectMixin


# --- Test Setup ---


class MockPooledObject(PooledObjectMixin):
    """A simple class for testing the pooling mechanism."""

    def __init__(self, value=0):
        self.value = value
        # The mixin should provide this attribute
        self.pool = None

    def reset(self, value=0):
        """Resets the object's state, as required by the pool."""
        self.value = value


@pytest.fixture
def mock_object_factory():
    """A factory fixture that creates MockPooledObject instances."""
    return lambda: MockPooledObject()


@pytest.fixture
def object_pool(mock_object_factory):
    """Provides an ObjectPool instance configured with our mock factory."""
    return ObjectPool(factory=mock_object_factory)


# --- Tests ---


class TestObjectPool:
    def test_pool_creates_new_object_with_factory(self, object_pool):
        """Tests that the pool uses its factory when it's empty."""
        assert len(object_pool._pool) == 0
        obj = object_pool.get()
        assert isinstance(obj, MockPooledObject)
        assert len(object_pool._pool) == 0

    def test_get_sets_pool_reference_on_new_object(self, object_pool):
        """Tests that a new object is correctly linked to its parent pool."""
        obj = object_pool.get()
        assert obj.pool is object_pool

    def test_release_adds_object_to_pool(self, object_pool):
        """Tests that releasing an object adds it to the pool's internal list."""
        obj = object_pool.get()
        assert len(object_pool._pool) == 0
        object_pool.release(obj)
        assert len(object_pool._pool) == 1
        assert object_pool._pool[0] is obj

    def test_get_reuses_released_object(self, object_pool):
        """The core test: ensures an object is recycled instead of creating a new one."""
        # Get an object, then release it
        obj1 = object_pool.get()
        obj1_id = id(obj1)
        object_pool.release(obj1)

        # Get an object again
        obj2 = object_pool.get()

        # It should be the *same instance* we released before
        assert id(obj2) == obj1_id
        # The pool should now be empty again
        assert len(object_pool._pool) == 0

    def test_mixin_release_method_works(self, object_pool):
        """Tests that obj.release() correctly calls pool.release(self)."""
        obj = object_pool.get()
        assert len(object_pool._pool) == 0

        # Use the mixin's method
        obj.release()

        # The object should be back in the pool
        assert len(object_pool._pool) == 1
        assert object_pool._pool[0] is obj

    def test_get_calls_reset_on_recycled_object(self, object_pool):
        """Ensures that recycled objects have their state reset."""
        # Get an object and set its state
        obj1 = object_pool.get(value=100)
        assert obj1.value == 100

        # Release it
        obj1.release()

        # Get an object again, but specify a new state via reset
        obj2 = object_pool.get(value=5)

        # Verify it's the same object, but its state has been reset
        assert id(obj1) == id(obj2)
        assert obj2.value == 5

    def test_get_calls_reset_on_new_object(self, object_pool):
        """Ensures that newly created objects also have their state set via reset."""
        obj = object_pool.get(value=50)
        assert obj.value == 50
