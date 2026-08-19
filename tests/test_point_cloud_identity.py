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

    def test_door_half_uses_the_corresponding_atlas_texture(self):
        storage = VoxelStorage()
        storage.set_full_snapshot(
            0, 0, 0,
            1, 2, 1,
            [
                "minecraft:spruce_door[facing=north,half=lower,hinge=left,open=false,powered=false]",
                "minecraft:spruce_door[facing=north,half=upper,hinge=left,open=false,powered=false]",
            ],
            [0, 1],
        )
        faces = [(193, 3)] * 6
        top_faces = [(194, 3)] * 6
        result = update_world_point_cloud(
            bpy.context,
            storage,
            block_face_lut={"spruce_door_bottom": faces, "spruce_door_top": top_faces},
            block_face_chunk_lut={"spruce_door_bottom": [0] * 6, "spruce_door_top": [0] * 6},
            block_face_texture_lut={"spruce_door_bottom": [961] * 6, "spruce_door_top": [962] * 6},
        )
        mesh = result.world_obj.data
        states = mesh.attributes["block_state"].data
        tiles = mesh.attributes["mtk_tile_top"].data
        texture_ids = mesh.attributes["mtk_texture_top"].data
        values = {
            state.value.decode("utf-8").split("half=", 1)[1].split(",", 1)[0]:
            (tuple(tiles[index].vector), texture_ids[index].value)
            for index, state in enumerate(states)
        }
        self.assertEqual(values["lower"], ((193.0, 3.0, 0.0), 961))
        self.assertEqual(values["upper"], ((194.0, 3.0, 0.0), 962))


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
