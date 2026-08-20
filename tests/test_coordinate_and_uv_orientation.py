"""
Unit test to verify coordinate transformation and 6-face UV orientations in Yefira Blender.
"""

import sys
import os
import unittest
from pathlib import Path

try:
    import bpy
    import mathutils
    HAS_BPY = True
except ImportError:
    HAS_BPY = False

PLUGIN_PARENT_DIR = Path(__file__).resolve().parent.parent / "dcc_plugins"
if str(PLUGIN_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PARENT_DIR))


class TestCoordinateAndUVOrientation(unittest.TestCase):

    def setUp(self):
        if not HAS_BPY:
            self.skipTest("bpy not available")
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_point_cloud_coordinate_right_handedness(self):
        from yefira_blender.core.point_cloud_builder import update_world_point_cloud
        from yefira_blender.core.storage import VoxelStorage

        storage = VoxelStorage()
        # Create a 3x3x3 selection: X from 10..12, Y from 64..66, Z from 20..22
        # Center should be around 0, 0, 0
        storage.set_full_snapshot(
            10, 64, 20,
            3, 3, 3,
            ["minecraft:stone"],
            [0] * 27,
        )

        res = update_world_point_cloud(bpy.context, storage, filter_air=False)
        self.assertIsNotNone(res.world_obj)
        mesh = res.world_obj.data
        self.assertEqual(len(mesh.vertices), 27)

        mc_pos_attr = mesh.attributes["mc_pos"]

        # Check vertex mapping
        for i, vert in enumerate(mesh.vertices):
            mc_x, mc_y, mc_z = mc_pos_attr.data[i].vector
            expected_vx = (mc_x - 10) - 3 / 2.0 + 0.5
            expected_vy = -((mc_z - 20) - 3 / 2.0 + 0.5)
            expected_vz = (mc_y - 64) + 0.5

            self.assertAlmostEqual(vert.co.x, expected_vx, places=4)
            self.assertAlmostEqual(vert.co.y, expected_vy, places=4)
            self.assertAlmostEqual(vert.co.z, expected_vz, places=4)

    def test_cube_6_face_uv_orientation(self):
        from yefira_blender.nodes.groups.cube_surface import get_or_create_cube_surface_group

        tree = get_or_create_cube_surface_group()
        self.assertIsNotNone(tree)

        # Create an object with this node tree
        mesh = bpy.data.meshes.new("TestCubeMesh")
        obj = bpy.data.objects.new("TestCubeObj", mesh)
        bpy.context.scene.collection.objects.link(obj)

        mod = obj.modifiers.new("GeoNodes", "NODES")
        mod.node_group = tree

        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()

        self.assertIsNotNone(eval_mesh)
        self.assertEqual(len(eval_mesh.polygons), 6)
        self.assertEqual(len(eval_mesh.loops), 24)

        self.assertIn("LocalUV", eval_mesh.attributes)
        self.assertIn("CubeFaceNorm", eval_mesh.attributes)

        local_uv = eval_mesh.attributes["LocalUV"]
        cube_norm = eval_mesh.attributes["CubeFaceNorm"]

        # Check each polygon
        for poly in eval_mesh.polygons:
            fn = cube_norm.data[poly.index].vector
            uvs = [local_uv.data[l_idx].vector for l_idx in poly.loop_indices]

            for uv in uvs:
                # U and V must be within [0, 1]
                self.assertGreaterEqual(uv.x, -1e-4)
                self.assertLessEqual(uv.x, 1.0 + 1e-4)
                self.assertGreaterEqual(uv.y, -1e-4)
                self.assertLessEqual(uv.y, 1.0 + 1e-4)

        eval_obj.to_mesh_clear()


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
