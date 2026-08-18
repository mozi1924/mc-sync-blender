"""Blender integration test for persistent Yefira block identities.

Run with:
    blender -b --factory-startup --python tests/test_point_cloud_identity.py
"""

from pathlib import Path
import sys
import unittest

try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False


PLUGIN_PARENT = Path(__file__).resolve().parent.parent / "dcc_plugins"
if str(PLUGIN_PARENT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PARENT))

if HAS_BPY:
    from yefira_blender.core.point_cloud_builder import update_world_point_cloud
    from yefira_blender.core.storage import VoxelStorage


class TestPointCloudIdentity(unittest.TestCase):
    def setUp(self):
        if not HAS_BPY:
            self.skipTest("bpy module not available")
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_mc_block_key_is_absolute_and_independent_of_point_index(self):
        storage = VoxelStorage()
        storage.set_full_snapshot(
            -1, 10, 3,
            2, 1, 1,
            ["minecraft:stone", "minecraft:dirt"],
            [0, 1],
        )

        result = update_world_point_cloud(bpy.context, storage, filter_air=True)
        self.assertEqual(result.point_count, 2)
        attr = result.world_obj.data.attributes["mc_block_key"]
        self.assertEqual(attr.domain, "POINT")
        self.assertEqual({entry.value.decode("utf-8") for entry in attr.data}, {"-1,10,3", "0,10,3"})

        # Remove the first point.  Blender may choose a different point
        # ordering after the rebuild, but the persistent identity remains
        # the MC coordinate, not a transient point index.
        self.assertTrue(storage.apply_delta_update(-1, 10, 3, [(-1, 10, 3, "minecraft:air")]))
        result = update_world_point_cloud(bpy.context, storage, filter_air=True)
        attr = result.world_obj.data.attributes["mc_block_key"]
        self.assertEqual(result.point_count, 1)
        self.assertEqual(attr.data[0].value.decode("utf-8"), "0,10,3")


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
