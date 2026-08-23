"""
Test suite for Minecraft BakedModel Face UV & Orientation pipeline.
Tests rich JSON model state handling, UV rotation dispatch, and evaluated Geometry Nodes UVMap.
"""

from __future__ import annotations

import json
import unittest
import bpy

from dcc_plugins.yefira_blender.core.storage import VoxelStorage
from dcc_plugins.yefira_blender.core.point_cloud_builder import update_world_point_cloud
from dcc_plugins.yefira_blender.nodes.world_tree import setup_world_geometry_nodes
from dcc_plugins.yefira_blender.materials.atlas_integration import parse_atlas_mapping, extract_atlas_parameters


class TestBlockModelUVAndOrientation(unittest.TestCase):

    def setUp(self):
        bpy.ops.wm.read_homefile(use_empty=True)
        self.mock_mapping = {
            "version": "1.0",
            "tile_size": 16,
            "chunks": [
                {"chunk_id": 0, "width": 1024, "height": 1024, "tile_size": 16, "tiles_per_row": 64}
            ],
            "textures": {
                "minecraft:block/furnace_front": {
                    "tile_column": 10,
                    "tile_row": 5,
                    "chunk_id": 0,
                    "texture_id": 1,
                    "kind": "static",
                },
                "minecraft:block/furnace_side": {
                    "tile_column": 11,
                    "tile_row": 5,
                    "chunk_id": 0,
                    "texture_id": 2,
                    "kind": "static",
                },
                "minecraft:block/furnace_top": {
                    "tile_column": 12,
                    "tile_row": 5,
                    "chunk_id": 0,
                    "texture_id": 3,
                    "kind": "static",
                },
                "minecraft:block/oak_log": {
                    "tile_column": 20,
                    "tile_row": 8,
                    "chunk_id": 0,
                    "texture_id": 4,
                    "kind": "static",
                },
                "minecraft:block/oak_log_top": {
                    "tile_column": 21,
                    "tile_row": 8,
                    "chunk_id": 0,
                    "texture_id": 5,
                    "kind": "static",
                },
            },
            "materials": []
        }

    def test_json_model_state_parsing_and_attributes(self):
        storage = VoxelStorage()

        # JSON serialized BlockStateModelData from Minecraft mod
        log_json = {
            "state": "minecraft:oak_log[axis=x]",
            "type": 0,
            "opaque": 1,
            "emissive": 0,
            "faces": {
                "east": {"tex": "minecraft:block/oak_log_top", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0], "tint": -1},
                "west": {"tex": "minecraft:block/oak_log_top", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0], "tint": -1},
                "top": {"tex": "minecraft:block/oak_log", "rot": 90, "uv": [0.0, 0.0, 1.0, 1.0], "tint": -1},
                "bottom": {"tex": "minecraft:block/oak_log", "rot": 90, "uv": [0.0, 0.0, 1.0, 1.0], "tint": -1},
                "south": {"tex": "minecraft:block/oak_log", "rot": 90, "uv": [0.0, 0.0, 1.0, 1.0], "tint": -1},
                "north": {"tex": "minecraft:block/oak_log", "rot": 90, "uv": [0.0, 0.0, 1.0, 1.0], "tint": -1},
            }
        }
        storage.set_full_snapshot(
            0, 0, 0,
            1, 1, 1,
            [json.dumps(log_json)],
            [0],
        )

        res = update_world_point_cloud(
            bpy.context,
            storage,
            atlas_mapping_textures=self.mock_mapping["textures"],
            atlas_width=1024.0,
            atlas_height=1024.0,
            tile_size=16.0,
            tiles_per_row=64,
        )

        mesh = res.world_obj.data
        self.assertEqual(len(mesh.vertices), 1)

        # Verify UV rotation attributes written to mesh
        self.assertIn("mtk_uv_rot_east", mesh.attributes)
        self.assertIn("mtk_uv_rot_top", mesh.attributes)
        self.assertAlmostEqual(mesh.attributes["mtk_uv_rot_east"].data[0].value, 270.0)
        self.assertAlmostEqual(mesh.attributes["mtk_uv_rot_top"].data[0].value, 90.0)
        self.assertAlmostEqual(mesh.attributes["mtk_uv_rot_north"].data[0].value, 270.0)

        # Verify tile coordinates
        # East: oak_log_top (col 21, row 8)
        self.assertAlmostEqual(mesh.attributes["mtk_tile_east"].data[0].vector[0], 21.0)
        self.assertAlmostEqual(mesh.attributes["mtk_tile_east"].data[0].vector[1], 8.0)
        # Top: oak_log (col 20, row 8)
        self.assertAlmostEqual(mesh.attributes["mtk_tile_top"].data[0].vector[0], 20.0)
        self.assertAlmostEqual(mesh.attributes["mtk_tile_top"].data[0].vector[1], 8.0)

    def test_geometry_nodes_evaluation_with_rotated_uv(self):
        storage = VoxelStorage()

        furnace_json = {
            "state": "minecraft:furnace[facing=north]",
            "type": 0,
            "opaque": 1,
            "emissive": 0,
            "faces": {
                "east": {"tex": "minecraft:block/furnace_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0], "tint": -1},
                "west": {"tex": "minecraft:block/furnace_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0], "tint": -1},
                "top": {"tex": "minecraft:block/furnace_top", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0], "tint": -1},
                "bottom": {"tex": "minecraft:block/furnace_top", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0], "tint": -1},
                "south": {"tex": "minecraft:block/furnace_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0], "tint": -1},
                "north": {"tex": "minecraft:block/furnace_front", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0], "tint": -1},
            }
        }
        storage.set_full_snapshot(
            0, 0, 0,
            1, 1, 1,
            [json.dumps(furnace_json)],
            [0],
        )

        res = update_world_point_cloud(
            bpy.context,
            storage,
            atlas_mapping_textures=self.mock_mapping["textures"],
            atlas_width=1024.0,
            atlas_height=1024.0,
            tile_size=16.0,
            tiles_per_row=64,
        )

        # Attach Geometry Nodes
        mod = setup_world_geometry_nodes(res.world_obj)
        self.assertIsNotNone(mod)

        # Evaluate dependency graph
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = res.world_obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()

        try:
            self.assertGreater(len(eval_mesh.polygons), 0)
            self.assertIn("UVMap", eval_mesh.attributes)
            uv_attr = eval_mesh.attributes["UVMap"]
            self.assertEqual(len(uv_attr.data), len(eval_mesh.loops))
            # Verify valid UVs are within [0, 1] range in Atlas
            for loop_uv in uv_attr.data:
                u, v, _ = loop_uv.vector
                self.assertGreaterEqual(u, 0.0)
                self.assertLessEqual(u, 1.0)
                self.assertGreaterEqual(v, 0.0)
                self.assertLessEqual(v, 1.0)
        finally:
            eval_obj.to_mesh_clear()


if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'])
