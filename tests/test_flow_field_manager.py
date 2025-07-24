# tests/test_flow_field_manager.py
import pytest
import numpy as np
import math
from domain.flow_field_manager import FlowFieldManager
from domain.tile import TILES


@pytest.fixture
def test_grid():
    """
    Provides a 5x5 grid with a 'U' shaped obstacle.
    L L L L L
    L W W W L
    L L G W L  (G = Goal will be at (2,2))
    L W W W L
    L L L L L
    """
    grid = [
        [TILES["land"]] * 5,
        [TILES["land"], TILES["water"], TILES["water"], TILES["water"], TILES["land"]],
        [TILES["land"], TILES["land"], TILES["land"], TILES["water"], TILES["land"]],
        [TILES["land"], TILES["water"], TILES["water"], TILES["water"], TILES["land"]],
        [TILES["land"]] * 5,
    ]
    return grid


@pytest.fixture
def flow_manager(test_grid):
    # This fixture now provides a standard, chunked manager. The tests
    # validate that the final output of the new system is identical to the old one.
    return FlowFieldManager(test_grid)


@pytest.fixture
def chunked_flow_manager():
    """Provides a 10x10 grid and a manager with a chunk size of 4."""
    grid = [[TILES["land"]] * 10 for _ in range(10)]
    return FlowFieldManager(grid, chunk_size=4)


# --- Test Class for Legacy monolithic generation (Now tests new system's output) ---
class TestFlowFieldManager:
    def test_field_generation_single_goal(self, flow_manager):
        # ARRANGE
        goal_pos = [(2, 2)]  # The 'G' in the diagram

        # ACT
        flow_field = flow_manager.generate_flow_field(goal_pos)

        # ASSERT
        assert np.array_equal(
            flow_field[0, 0], [1, 0]
        ), "From (0,0) should be S (dy=1, dx=0)"
        assert np.array_equal(
            flow_field[1, 0], [1, 0]
        ), "From (1,0) should be S (dy=1, dx=0), not SE, to avoid water corner"
        assert np.array_equal(
            flow_field[2, 0], [0, 1]
        ), "From (2,0) should be E (dy=0, dx=1)"
        assert np.array_equal(
            flow_field[4, 4], [0, -1]
        ), "From (4,4) should be W (dy=0, dx=-1)"
        assert np.array_equal(
            flow_field[2, 2], [0, 0]
        ), "Goal tile vector should be zero"
        assert np.array_equal(
            flow_field[1, 1], [0, 0]
        ), "Impassable tile vector should be zero"
        assert np.array_equal(
            flow_field[1, 2], [0, 0]
        ), "Impassable tile vector should be zero"

    def test_no_goals_results_in_zero_field(self, flow_manager):
        goal_pos = []
        flow_field = flow_manager.generate_flow_field(goal_pos)
        assert np.all(flow_field == 0)

    def test_unreachable_area_has_zero_vector(self):
        grid = [
            [TILES["land"], TILES["water"], TILES["land"]],
            [TILES["land"], TILES["water"], TILES["land"]],
            [TILES["land"], TILES["water"], TILES["land"]],
        ]
        manager = FlowFieldManager(grid)
        goal_pos = [(1, 2)]
        flow_field = manager.generate_flow_field(goal_pos)
        assert np.array_equal(flow_field[0, 0], [0, 0])
        assert np.array_equal(flow_field[1, 0], [0, 0])
        assert np.array_equal(flow_field[2, 0], [0, 0])
        assert np.array_equal(flow_field[0, 2], [1, 0])
        assert np.array_equal(flow_field[1, 2], [0, 0])
        assert np.array_equal(flow_field[2, 2], [-1, 0])

    def test_field_generation_multiple_goals(self, flow_manager):
        goal_positions = [(0, 4), (4, 0)]
        flow_field = flow_manager.generate_flow_field(goal_positions)
        assert np.array_equal(flow_field[0, 3], [0, 1])
        assert np.array_equal(flow_field[1, 4], [-1, 0])
        assert np.array_equal(flow_field[4, 1], [0, -1])
        assert np.array_equal(flow_field[3, 0], [1, 0])
        assert np.array_equal(flow_field[2, 2], [0, -1])
        vector_at_0_0 = flow_field[0, 0]
        is_valid_vector = np.array_equal(vector_at_0_0, [1, 0]) or np.array_equal(
            vector_at_0_0, [0, 1]
        )
        assert is_valid_vector
        assert np.array_equal(flow_field[0, 4], [0, 0])
        assert np.array_equal(flow_field[4, 0], [0, 0])

    def test_differentiated_cardinal_diagonal_cost(self):
        grid = [[TILES["land"]] * 3 for _ in range(3)]
        manager = FlowFieldManager(grid)
        goal_pos = [(1, 1)]
        _, cost_field = manager.generate_flow_field(goal_pos, return_cost_field=True)
        assert cost_field[1, 1] == 0
        assert np.isclose(cost_field[1, 0], 1.0)
        sqrt_2 = math.sqrt(2)
        assert np.isclose(cost_field[0, 0], sqrt_2)

    def test_generate_flow_field_with_tile_costs(self):
        grid = [
            [TILES["land"], TILES["land"], TILES["land"]],
            [TILES["land"], TILES["mountain"], TILES["land"]],
            [TILES["land"], TILES["land"], TILES["land"]],
        ]
        manager = FlowFieldManager(grid)
        goal_pos = [(1, 2)]
        flow_field = manager.generate_flow_field(goal_pos)
        vector_at_1_0 = flow_field[1, 0]
        is_correct_vector = np.array_equal(vector_at_1_0, [-1, 1]) or np.array_equal(
            vector_at_1_0, [1, 1]
        )
        assert is_correct_vector

    def test_flow_field_avoids_diagonal_corner_cutting(self):
        grid = [
            [TILES["land"], TILES["land"], TILES["land"]],
            [TILES["land"], TILES["water"], TILES["land"]],
            [TILES["land"], TILES["land"], TILES["land"]],
        ]
        manager = FlowFieldManager(grid)
        goal_pos = [(0, 2)]
        flow_field = manager.generate_flow_field(goal_pos)
        vector_at_1_0 = flow_field[1, 0]
        expected_vector = np.array([-1, 0])
        assert np.array_equal(vector_at_1_0, expected_vector)


# --- Tests for New Chunking System (Unchanged)---
class TestFlowFieldManagerChunking:
    def test_initialization_with_chunking(self, test_grid):
        manager = FlowFieldManager(test_grid, chunk_size=2)
        assert manager.chunk_size == 2
        assert manager.chunks_high == 3
        assert manager.chunks_wide == 3
        assert hasattr(manager, "recalculation_needed")
        assert hasattr(manager, "recalculation_in_progress")

    def test_add_and_remove_goal_flags_for_recalculation(self, chunked_flow_manager):
        # ARRANGE
        manager = chunked_flow_manager
        goal_pos = (5, 5)

        # ACT 1: Add a goal
        manager.add_goal(goal_pos)
        # ASSERT 1: Should be flagged for a new calculation
        assert manager.recalculation_needed

        # ACT 2: Start the process.
        manager.process_flow_field_update(node_budget=10)
        assert manager.recalculation_in_progress
        # The 'needed' flag is consumed when the process starts.
        assert not manager.recalculation_needed

        # ACT 3: Remove the goal while the first calc is running.
        manager.remove_goal(goal_pos)

        # ASSERT 3: This should immediately flag that another recalc is needed
        # as soon as the current one is done.
        assert manager.recalculation_needed

    def test_double_buffer_integration(self, chunked_flow_manager):
        """
        A full integration test for the new double-buffered state machine.
        """
        # ARRANGE
        manager = chunked_flow_manager  # 10x10 world, 4x4 chunks
        goal_pos = (5, 5)

        # ACT 1: Add a goal.
        manager.add_goal(goal_pos)
        assert manager.recalculation_needed

        # ACT 2: Process one small budget. This should start the back-buffer calc.
        manager.process_flow_field_update(node_budget=10)

        # ASSERT 2: Recalculation is in progress, but the *active* field is still empty.
        assert manager.recalculation_in_progress
        assert not manager.recalculation_needed
        assert np.all(manager.active_cost_field == np.inf)
        assert np.any(manager.recalculating_cost_field < np.inf)

        # ACT 3: Provide a large budget to finish the cost field calculation.
        # Run enough ticks for cost calc (100 tiles / 10 budget = 10 ticks) + buffer.
        for _ in range(15):
            manager.process_flow_field_update(node_budget=10)

        # ASSERT 3: Cost field is done, back-buffer is now active, and chunks are dirty.
        assert not manager.recalculation_in_progress
        assert np.all(manager.recalculating_cost_field == np.inf)
        assert np.any(manager.active_cost_field < np.inf)
        assert len(manager.dirty_chunks) > 0

        # ACT 4: Process all vector chunks.
        # Run enough ticks to clear the 9 dirty chunks.
        for _ in range(10):
            manager.process_flow_field_update(node_budget=0)

        # ASSERT 4: The final flow field is fully calculated and correct.
        assert not manager.dirty_chunks
        assert np.array_equal(manager.flow_field[4, 5], [1, 0])
        assert np.array_equal(manager.flow_field[6, 5], [-1, 0])
        assert np.array_equal(manager.flow_field[goal_pos], [0, 0])
