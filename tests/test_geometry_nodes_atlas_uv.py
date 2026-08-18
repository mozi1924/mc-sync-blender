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
    )


class TestGeometryNodesAtlasUV(unittest.TestCase):

    def setUp(self):
        if not HAS_BPY:
            self.skipTest("bpy module not available")

        # Clear scene
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def test_setup_world_geometry_nodes_and_uv_tree(self):
        # 1. Create Point Cloud mesh object
        mesh = bpy.data.meshes.new("Yefira_World_Mesh")
        obj = bpy.data.objects.new("Yefira_World", mesh)
        bpy.context.scene.collection.objects.link(obj)

        # Add 2 points: Stone (block_type=0, mat_id=0) and Grass Block (block_type=0, mat_id=42)
        mesh.from_pydata([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)], [], [])
        mesh.update()

        # Add attributes
        attr_type = mesh.attributes.new(name="block_type", type="INT", domain="POINT")
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

        # 4. Verify Node Group contains UV calculation nodes
        gn_tree = mod.node_group
        node_types = [n.type for n in gn_tree.nodes]
        self.assertTrue("MESH_PRIMITIVE_CUBE" in node_types or "MESH_CUBE" in node_types)
        self.assertIn("INSTANCE_ON_POINTS", node_types)
        self.assertIn("REALIZE_INSTANCES", node_types)
        self.assertIn("SET_MATERIAL", node_types)
        self.assertIn("STORE_NAMED_ATTRIBUTE", node_types)

        # Verify UVMap store node exists
        store_nodes = [n for n in gn_tree.nodes if n.type == "STORE_NAMED_ATTRIBUTE"]
        store_names = [n.inputs["Name"].default_value for n in store_nodes if "Name" in n.inputs]
        self.assertIn("UVMap", store_names)
        self.assertIn("LocalUV", store_names)

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


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
