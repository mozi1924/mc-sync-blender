"""Regression tests for topology-independent voxel sync storage."""

from pathlib import Path
import sys
import unittest


PLUGIN_ROOT = Path(__file__).resolve().parent.parent / "dcc_plugins" / "yefira_blender"
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from core.storage import VoxelStorage, block_key


class TestVoxelStorage(unittest.TestCase):
    def setUp(self):
        self.storage = VoxelStorage()
        # Encoder order is x -> y -> z.
        self.palette = ["minecraft:air", "minecraft:stone", "minecraft:dirt"]
        self.storage.set_full_snapshot(
            -2, -1, 4,
            2, 2, 2,
            self.palette,
            [1, 0, 2, 1, 0, 2, 1, 0],
        )

    def test_absolute_coordinate_identity_is_stable(self):
        self.assertEqual(block_key(-2, -1, 4), "-2,-1,4")
        self.assertEqual(self.storage.block_map[(-2, -1, 4)], "minecraft:stone")
        self.assertEqual(self.storage.block_map[(-1, 0, 5)], "minecraft:air")
        self.assertTrue(self.storage.contains(-1, 0, 5))
        self.assertFalse(self.storage.contains(0, 0, 5))

    def test_delta_for_other_selection_is_rejected_atomically(self):
        before = dict(self.storage.block_map)
        applied = self.storage.apply_delta_update(
            99, -1, 4,
            [(-2, -1, 4, "minecraft:dirt")],
        )
        self.assertFalse(applied)
        self.assertEqual(self.storage.block_map, before)

    def test_delta_outside_selection_is_rejected_atomically(self):
        before = dict(self.storage.block_map)
        applied = self.storage.apply_delta_update(
            -2, -1, 4,
            [(-2, -1, 4, "minecraft:dirt"), (17, 0, 4, "minecraft:stone")],
        )
        self.assertFalse(applied)
        self.assertEqual(self.storage.block_map, before)

    def test_matching_delta_updates_coordinates_and_crc(self):
        old_crc = dict(self.storage.section_crc_map)
        applied = self.storage.apply_delta_update(
            -2, -1, 4,
            [(-2, -1, 4, "minecraft:dirt")],
        )
        self.assertTrue(applied)
        self.assertEqual(self.storage.block_map[(-2, -1, 4)], "minecraft:dirt")
        self.assertNotEqual(self.storage.section_crc_map, old_crc)


if __name__ == "__main__":
    unittest.main()
