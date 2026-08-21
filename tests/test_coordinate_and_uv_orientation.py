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
        for obj in list(bpy.data.objects):
            if obj.name.startswith("Test") or obj.name == "Yefira_World":
                bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in list(bpy.data.meshes):
            if mesh.name.startswith("Test") or mesh.name == "Yefira_World_Mesh":
                bpy.data.meshes.remove(mesh, do_unlink=True)

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

        mc_pos_attr = mesh.attributes["yefira_mc_position"]

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

        self.assertIn("yefira_local_uv", eval_mesh.attributes)
        self.assertIn("yefira_cube_face_normal", eval_mesh.attributes)

        local_uv = eval_mesh.attributes["yefira_local_uv"]
        cube_norm = eval_mesh.attributes["yefira_cube_face_normal"]

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

    def test_cube_face_uv_no_mirroring(self):
        from yefira_blender.nodes.groups.cube_surface import get_or_create_cube_surface_group

        tree = get_or_create_cube_surface_group()
        mesh = bpy.data.meshes.new("TestCubeMesh2")
        obj = bpy.data.objects.new("TestCubeObj2", mesh)
        bpy.context.scene.collection.objects.link(obj)

        mod = obj.modifiers.new("GeoNodes", "NODES")
        mod.node_group = tree

        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()

        local_uv = eval_mesh.attributes["yefira_local_uv"]
        cube_norm = eval_mesh.attributes["yefira_cube_face_normal"]

        for poly in eval_mesh.polygons:
            fn = cube_norm.data[poly.index].vector
            for l_idx in poly.loop_indices:
                vi = eval_mesh.loops[l_idx].vertex_index
                v_co = eval_mesh.vertices[vi].co
                uv = local_uv.data[l_idx].vector

                # Test West face (-X)
                if fn.x < -0.5:
                    expected_u = 0.5 - v_co.y  # North (+Y) is Left (U=0), South (-Y) is Right (U=1)
                    expected_v = v_co.z + 0.5
                    self.assertAlmostEqual(uv.x, expected_u, places=4)
                    self.assertAlmostEqual(uv.y, expected_v, places=4)
                # Test East face (+X)
                elif fn.x > 0.5:
                    expected_u = v_co.y + 0.5  # South (-Y) is Left (U=0), North (+Y) is Right (U=1)
                    expected_v = v_co.z + 0.5
                    self.assertAlmostEqual(uv.x, expected_u, places=4)
                    self.assertAlmostEqual(uv.y, expected_v, places=4)
                # Test Bottom face (-Z)
                elif fn.z < -0.5:
                    expected_u = v_co.x + 0.5
                    expected_v = 0.5 - v_co.y  # South (-Y) is Top (V=1)
                    self.assertAlmostEqual(uv.x, expected_u, places=4)
                    self.assertAlmostEqual(uv.y, expected_v, places=4)

        eval_obj.to_mesh_clear()

    def test_directional_block_rotations(self):
        import math
        from yefira_blender.core.block_classifier import parse_and_classify

        # 1. Command block (Vertical-base: Front points Up before rotation)
        cb_north = parse_and_classify("minecraft:command_block[facing=north]")
        self.assertAlmostEqual(cb_north.rot_euler[0], -math.pi / 2.0)
        cb_south = parse_and_classify("minecraft:command_block[facing=south]")
        self.assertAlmostEqual(cb_south.rot_euler[0], math.pi / 2.0)
        cb_up = parse_and_classify("minecraft:command_block[facing=up]")
        self.assertEqual(cb_up.rot_euler, (0.0, 0.0, 0.0))
        cb_down = parse_and_classify("minecraft:command_block[facing=down]")
        self.assertAlmostEqual(cb_down.rot_euler[0], math.pi)

        # 2. Barrel (Vertical-base: Up = top)
        barrel_up = parse_and_classify("minecraft:barrel[facing=up]")
        self.assertEqual(barrel_up.rot_euler, (0.0, 0.0, 0.0))
        barrel_down = parse_and_classify("minecraft:barrel[facing=down]")
        self.assertAlmostEqual(barrel_down.rot_euler[0], math.pi)
        barrel_north = parse_and_classify("minecraft:barrel[facing=north]")
        self.assertAlmostEqual(barrel_north.rot_euler[0], -math.pi / 2.0)

        # 3. Piston (Vertical-base: Up = top)
        piston_up = parse_and_classify("minecraft:piston[facing=up]")
        self.assertEqual(piston_up.rot_euler, (0.0, 0.0, 0.0))
        piston_north = parse_and_classify("minecraft:piston[facing=north]")
        self.assertAlmostEqual(piston_north.rot_euler[0], -math.pi / 2.0)

        # 4. Axis logs
        log_y = parse_and_classify("minecraft:oak_log[axis=y]")
        self.assertEqual(log_y.rot_euler, (0.0, 0.0, 0.0))
        log_x = parse_and_classify("minecraft:oak_log[axis=x]")
        self.assertAlmostEqual(log_x.rot_euler[1], math.pi / 2.0)
        log_z = parse_and_classify("minecraft:oak_log[axis=z]")
        self.assertAlmostEqual(log_z.rot_euler[0], -math.pi / 2.0)

    def test_rotated_cube_face_addressing_uses_local_faces(self):
        """Each world-space face must retain the texture of its pre-rotation face.

        This guards the critical distinction between the cube's local face
        identity (used to choose a Minecraft block texture) and its realised
        world-space polygon normal (used for rendering/culling).
        """
        import mathutils
        from yefira_blender.core.point_cloud_builder import update_world_point_cloud
        from yefira_blender.core.storage import VoxelStorage
        from yefira_blender.nodes.world_tree import setup_world_geometry_nodes

        facings = ("north", "east", "south", "west", "up", "down")
        states = [f"minecraft:command_block[facing={facing}]" for facing in facings]
        storage = VoxelStorage()
        # Keep one empty cell between blocks so the culling group does not
        # remove a face that is needed for this mapping assertion.
        storage.set_full_snapshot(
            0, 0, 0, len(facings) * 2, 1, 1,
            ["minecraft:air"], [0] * (len(facings) * 2),
        )

        # set_full_snapshot's payload is x-major; write the sparse fixture
        # explicitly to keep this test independent from its packing details.
        storage.block_map = {
            (index * 2, 0, 0): state for index, state in enumerate(states)
        }
        face_texture_ids = (101, 102, 103, 104, 105, 106)  # +X, -X, +Y, -Y, +Z, -Z
        result = update_world_point_cloud(
            bpy.context, storage, filter_air=True,
            block_face_texture_lut={"command_block": list(face_texture_ids)},
        )
        setup_world_geometry_nodes(result.world_obj)

        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_mesh = result.world_obj.evaluated_get(depsgraph).to_mesh()
        texture_ids = eval_mesh.attributes["mtk_atlas_texture_id"]

        # The face table uses Minecraft axes (+Y = top, +Z = south), while
        # the generated mesh uses Blender axes (+Z = top, -Y = south).
        normal_to_texture = {
            (1, 0, 0): 101, (-1, 0, 0): 102,
            (0, 0, 1): 103, (0, 0, -1): 104,
            (0, -1, 0): 105, (0, 1, 0): 106,
        }
        for poly in eval_mesh.polygons:
            poly_key = tuple(int(round(value)) for value in poly.normal)
            self.assertEqual(
                texture_ids.data[poly.index].value,
                normal_to_texture[poly_key],
                f"face {poly.index} used {poly_key}",
            )

        result.world_obj.evaluated_get(depsgraph).to_mesh_clear()

    def test_templates_have_local_uv_and_normals(self):
        from yefira_blender.core.template_catalog import get_or_create_template_collection

        col = get_or_create_template_collection(bpy.context)
        self.assertGreater(len(col.objects), 0)

        for obj in col.objects:
            if obj.type == 'MESH' and obj.data:
                self.assertIn("yefira_cube_face_normal", obj.data.attributes, f"Template {obj.name} missing yefira_cube_face_normal")
                self.assertIn("yefira_local_uv", obj.data.attributes, f"Template {obj.name} missing yefira_local_uv")


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
