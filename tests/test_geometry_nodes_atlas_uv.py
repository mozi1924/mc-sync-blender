"""
Integration tests for Yefira Geometry Nodes procedural Cube 6-Face Atlas UV Generation.
Executed in Blender:
blender -b --factory-startup --python tests/test_geometry_nodes_atlas_uv.py
"""

import sys
import os
import unittest
from pathlib import Path

try:
    import bpy
    HAS_BPY = True
except ImportError:
    HAS_BPY = False

# Add Yefira plugin parent dir to sys.path
PLUGIN_PARENT_DIR = Path(__file__).resolve().parent.parent / "dcc_plugins"
if str(PLUGIN_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_PARENT_DIR))

if HAS_BPY:
    from yefira_blender.materials.atlas_integration import (
        get_or_create_atlas_material,
        extract_atlas_parameters,
        MASTER_MATERIAL_NAME,
    )
    from yefira_blender.nodes.geo_nodes import (
        setup_world_geometry_nodes,
        WORLD_TREE_NAME,
        WORLD_MODIFIER_NAME,
        WORLD_TREE_SCHEMA_PROPERTY,
        WORLD_TREE_SCHEMA_VERSION,
    )


class TestGeometryNodesAtlasUV(unittest.TestCase):

    def setUp(self):
        if not HAS_BPY:
            self.skipTest("bpy module not available")

        for obj in list(bpy.data.objects):
            if obj.name.startswith("Test") or obj.name == "Yefira_World":
                bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in list(bpy.data.meshes):
            if mesh.name.startswith("Test") or mesh.name == "Yefira_World_Mesh":
                bpy.data.meshes.remove(mesh, do_unlink=True)
        for mat in list(bpy.data.materials):
            if mat.name.startswith("mtk:minecraft:atlas_chunk") or mat.name.startswith("Test"):
                bpy.data.materials.remove(mat, do_unlink=True)

    def test_setup_world_geometry_nodes_and_uv_tree(self):
        # 1. Create Point Cloud mesh object
        mesh = bpy.data.meshes.new("Yefira_World_Mesh")
        obj = bpy.data.objects.new("Yefira_World", mesh)
        bpy.context.scene.collection.objects.link(obj)

        # Add 2 points: Stone (block_type=0, mat_id=0) and Grass Block (block_type=0, mat_id=42)
        mesh.from_pydata([(0.0, 0.0, 0.0), (2.0, 0.0, 0.0)], [], [])
        mesh.update()

        # Add attributes
        attr_type = mesh.attributes.new(name="yefira_block_type", type="INT", domain="POINT")
        attr_type.data[0].value = 0
        attr_type.data[1].value = 0

        attr_mat = mesh.attributes.new(name="mtk_material_id", type="INT", domain="POINT")
        attr_mat.data[0].value = 0
        attr_mat.data[1].value = 42

        # 6-face tile coordinate attributes
        for face_name in ("mtk_tile_top", "mtk_tile_bottom", "mtk_tile_east", "mtk_tile_west", "mtk_tile_south", "mtk_tile_north"):
            attr_face = mesh.attributes.new(name=face_name, type="FLOAT_VECTOR", domain="POINT")
            attr_face.data[0].vector = (0.0, 0.0, 0.0)
            attr_face.data[1].vector = (10.0, 2.0, 0.0)

        attr_tint = mesh.attributes.new(name="mtk_biome_tint_color", type="FLOAT_COLOR", domain="POINT")
        attr_tint.data[0].color = (1.0, 1.0, 1.0, 1.0)
        attr_tint.data[1].color = (0.35, 0.72, 0.22, 1.0)

        # 2. Setup Atlas Material with non-square custom dimensions (e.g. 2048 x 1024, tile_size=32)
        mat = get_or_create_atlas_material()
        self.assertIsNotNone(mat)
        mat["mtk_atlas_width"] = 2048.0
        mat["mtk_atlas_height"] = 1024.0
        mat["mtk_tile_size"] = 32.0
        mat["mtk_tiles_per_row"] = 64

        # 3. Setup Geometry Nodes Modifier
        mod = setup_world_geometry_nodes(obj)
        self.assertIsNotNone(mod)
        self.assertEqual(mod.name, WORLD_MODIFIER_NAME)
        self.assertIsNotNone(mod.node_group)
        self.assertEqual(mod.node_group.name, WORLD_TREE_NAME)
        self.assertEqual(gn_tree_schema := mod.node_group.get(WORLD_TREE_SCHEMA_PROPERTY), WORLD_TREE_SCHEMA_VERSION)

        # A live point update invokes setup again.  It must preserve the
        # generated graph rather than clear/recreate it (which used to cause
        # visible stalls and transient addressing changes).
        original_tree = mod.node_group
        original_node_count = len(original_tree.nodes)
        second_mod = setup_world_geometry_nodes(obj)
        self.assertIs(second_mod.node_group, original_tree)
        self.assertEqual(len(second_mod.node_group.nodes), original_node_count)

        # 4. Verify Node Group contains UV calculation nodes
        gn_tree = second_mod.node_group
        node_types = [n.type for n in gn_tree.nodes]
        # The root tree is an orchestration layer; cube construction is packed
        # into a reusable group rather than expanded inline.
        cube_groups = [
            node for node in gn_tree.nodes
            if node.type == "GROUP" and node.node_tree
            and node.node_tree.name == "Yefira_Cube_Surface"
        ]
        self.assertTrue(cube_groups)
        self.assertTrue(
            "MESH_PRIMITIVE_CUBE" in [node.type for node in cube_groups[0].node_tree.nodes]
            or "MESH_CUBE" in [node.type for node in cube_groups[0].node_tree.nodes]
        )
        self.assertIn("INSTANCE_ON_POINTS", node_types)
        self.assertIn("REALIZE_INSTANCES", node_types)
        dispatcher_groups = [
            node for node in gn_tree.nodes
            if node.type == "GROUP" and node.node_tree
            and node.node_tree.name == "Yefira_Material_Dispatcher"
        ]
        self.assertTrue(dispatcher_groups)
        self.assertIn("SET_MATERIAL", [node.type for node in dispatcher_groups[0].node_tree.nodes])
        self.assertIn("STORE_NAMED_ATTRIBUTE", node_types)

        # Verify UVMap store node exists
        store_nodes = [n for n in gn_tree.nodes if n.type == "STORE_NAMED_ATTRIBUTE"]
        store_names = [n.inputs["Name"].default_value for n in store_nodes if "Name" in n.inputs]
        self.assertIn("UVMap", store_names)
        cube_store_names = [
            node.inputs["Name"].default_value
            for node in cube_groups[0].node_tree.nodes
            if node.type == "STORE_NAMED_ATTRIBUTE" and "Name" in node.inputs
        ]
        self.assertIn("yefira_local_uv", cube_store_names)

        # 5. Evaluate evaluated dependency graph (ensure no crashes or invalid sockets)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        self.assertIsNotNone(eval_mesh)

        # 2 cubes * 6 faces = 12 polygons, 2 * 24 = 48 corners
        self.assertEqual(len(eval_mesh.polygons), 12)
        self.assertEqual(len(eval_mesh.loops), 48)

        # Check UVMap attribute on evaluated realized mesh
        self.assertIn("UVMap", eval_mesh.attributes)
        uv_attr = eval_mesh.attributes["UVMap"]
        self.assertEqual(uv_attr.domain, "CORNER")
        self.assertEqual(len(uv_attr.data), 48)

        # Verify UV coordinates are within [0, 1] range and not NaN/Inf
        for item in uv_attr.data:
            u, v = item.vector[0], item.vector[1]
            self.assertFalse(any(c != c for c in (u, v)), f"NaN in UVMap: ({u}, {v})")
            self.assertGreaterEqual(u, -1e-5)
            self.assertLessEqual(u, 1.0 + 1e-5)
            self.assertGreaterEqual(v, -1e-5)
            self.assertLessEqual(v, 1.0 + 1e-5)

        eval_obj.to_mesh_clear()

    def test_full_pipeline_multi_chunk_dispatch(self):
        from yefira_blender.core.point_cloud_builder import update_world_point_cloud
        from yefira_blender.core.storage import VoxelStorage
        import json

        # 1. Setup multi-chunk materials
        mat0 = bpy.data.materials.new("mtk:minecraft:atlas_chunk_000")
        mat0["mtk:atlas_chunk_id"] = 0
        mat0["mtk_atlas_width"] = 1024.0
        mat0["mtk_atlas_height"] = 1024.0
        mat0["mtk_tile_size"] = 16.0
        mat0["mtk_tiles_per_row"] = 64

        mat1 = bpy.data.materials.new("mtk:minecraft:atlas_chunk_001")
        mat1["mtk:atlas_chunk_id"] = 1

        mat2 = bpy.data.materials.new("mtk:minecraft:atlas_chunk_002")
        mat2["mtk:atlas_chunk_id"] = 2

        mapping = {
            "format_version": 10,
            "tile_size": 16,
            "chunks": [
                {"chunk_id": 0, "kind": "static", "width": 1024, "height": 1024, "tile_size": 16, "tiles_per_row": 64},
                {"chunk_id": 1, "kind": "static", "width": 1024, "height": 1024, "tile_size": 16, "tiles_per_row": 64},
                {"chunk_id": 2, "kind": "animation", "width": 1024, "height": 2048, "tile_size": 16, "tiles_per_row": 64},
            ],
            "textures": {
                "minecraft:dirt": {"chunk_id": 0, "texture_id": 10, "tile_column": 10, "tile_row": 0},
                "minecraft:stone": {"chunk_id": 1, "texture_id": 20, "tile_column": 5, "tile_row": 1},
                "minecraft:water_still": {"chunk_id": 2, "texture_id": 30, "tile_column": 0, "tile_row": 0},
            }
        }
        mat0["mtk:atlas_mapping"] = json.dumps(mapping)

        # 2. Build VoxelStorage
        storage = VoxelStorage()
        storage.set_full_snapshot(
            0, 0, 0,
            3, 1, 1,
            ["minecraft:dirt", "minecraft:stone", "minecraft:water_still"],
            [0, 1, 2],
        )

        atlas_params = extract_atlas_parameters(mat0)
        res = update_world_point_cloud(
            bpy.context,
            storage,
            filter_air=False,
            atlas_mapping_dict=atlas_params.get("material_id_map", {}),
            block_face_lut=atlas_params.get("block_face_lut", {}),
            block_face_chunk_lut=atlas_params.get("block_face_chunk_lut", {}),
            block_face_texture_lut=atlas_params.get("block_face_texture_lut", {}),
            block_face_tint_lut=atlas_params.get("block_face_tint_lut", {}),
            atlas_width=atlas_params["width"],
            atlas_height=atlas_params["height"],
            tile_size=atlas_params["tile_size"],
            tiles_per_row=atlas_params["tiles_per_row"],
        )

        self.assertIsNotNone(res.world_obj)
        self.assertEqual(res.point_count, 3)

        # 3. Setup Geometry Nodes
        mod = setup_world_geometry_nodes(res.world_obj)
        self.assertIsNotNone(mod)

        # Verify object material slots are populated for all chunks
        self.assertGreaterEqual(len(res.world_obj.data.materials), 3)
        self.assertIs(res.world_obj.data.materials[0], mat0)
        self.assertIs(res.world_obj.data.materials[1], mat1)
        self.assertIs(res.world_obj.data.materials[2], mat2)

        # 4. Evaluate depsgraph and verify materialized mesh
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = res.world_obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()

        self.assertIsNotNone(eval_mesh)
        self.assertIn("UVMap", eval_mesh.attributes)
        self.assertIn("mtk_atlas_chunk_id", eval_mesh.attributes)
        self.assertIn("mtk_atlas_texture_id", eval_mesh.attributes)

        eval_obj.to_mesh_clear()


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
