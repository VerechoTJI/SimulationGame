# tests/test_domain_logic.py
import unittest
import numpy as np

# We import directly from the domain to test it in isolation
from domain.rice import Rice


# A dummy "mock" world class, just enough for the test to run
class MockWorld:
    pass


class TestRiceMaturation(unittest.TestCase):

    def test_rice_matures_at_half_max_age(self):
        """
        Test that a Rice plant's 'matured' property becomes True
        at the correct age.
        """
        # --- Setup ---
        rice = Rice(pos_x=0, pos_y=0)  # max_age is 16
        mock_world = MockWorld()

        # --- Pre-condition Assertions (RED) ---
        # A brand new plant should not be mature
        self.assertFalse(rice.matured, "New rice plant should not be mature")
        self.assertEqual(rice.age, 0)

        # --- Action (GREEN) ---
        # Tick the rice plant until it's just about to mature
        for _ in range(7):  # Age becomes 1, 2, 3, 4, 5, 6, 7
            rice.tick(mock_world)

        self.assertFalse(rice.matured, "Rice at age 7 should not be mature")

        # The tick that makes it mature (age 8, which is 16 / 2)
        rice.tick(mock_world)

        # --- Post-condition Assertions ---
        self.assertTrue(rice.matured, "Rice at age 8 should be mature")
        self.assertEqual(rice.age, 8)


if __name__ == "__main__":
    unittest.main()
