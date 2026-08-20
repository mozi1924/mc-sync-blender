"""
Unit tests for Animation Texture Integration in Yefira:
- Alias resolution for animated blocks (water, lava, magma_block, campfire, sea_lantern, etc.)
- Multi-chunk Atlas LUT extraction and anim timing / frame size generation
- Geometry Nodes multi-chunk UV calculation for Chunk 1 animation faces
"""

import unittest
import bpy
import sys
import os

dcc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dcc_plugins"))
if dcc_path not in sys.path:
    sys.path.insert(0, dcc_path)

from yefira_blender.materials.atlas_integration import (
    _build_block_face_location_lut,
    build_block_face_lut,
    build_block_face_atlas_ids,
    build_block_face_anim_lut,
    extract_atlas_parameters,
    setup_material_slots_for_object,
)
from yefira_blender.core.storage import VoxelStorage
from yefira_blender.core.point_cloud_builder import update_world_point_cloud
from yefira_blender.nodes.world_tree import setup_world_geometry_nodes


class TestAnimationAtlasIntegration(unittest.TestCase):
    def setUp(self):
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for mesh in list(bpy.data.meshes):
            bpy.data.meshes.remove(mesh, do_unlink=True)
        for mat in list(bpy.data.materials):
            bpy.data.materials.remove(mat, do_unlink=True)

        self.mock_mapping = {
            "format_version": 11,
            "chunks": [
                {
                    "chunk_id": 0,
                    "kind": "static",
                    "width": 4096,
                    "height": 80,
                    "tile_size": 16,
                    "tiles_per_row": 256,
                },
                {
                    "chunk_id": 1,
                    "kind": "animation",
                    "width": 896,
                    "height": 1024,
                    "tile_size": 16,
                    "tiles_per_row": 56,
                },
            ],
            "textures": {
                "minecraft:block/stone": {
                    "texture_key": "minecraft:block/stone",
                    "namespace": "minecraft",
                    "chunk_id": 0,
                    "texture_id": 1,
                    "tile_column": 1,
                    "tile_row": 0,
                    "kind": "static",
                    "tile_size": 16,
                },
                "minecraft:block/sea_lantern": {
                    "texture_key": "minecraft:block/sea_lantern",
                    "namespace": "minecraft",
                    "chunk_id": 1,
                    "texture_id": 38,
                    "kind": "animation",
                    "pixel_x": 624,
                    "pixel_y": 0,
                    "frame_width": 16,
                    "frame_height": 16,
                    "frame_count": 5,
                    "frametime": 5,
                    "interpolate": False,
                },
                "minecraft:block/water_still": {
                    "texture_key": "minecraft:block/water_still",
                    "namespace": "minecraft",
                    "chunk_id": 1,
                    "texture_id": 10,
                    "kind": "animation",
                    "pixel_x": 160,
                    "pixel_y": 0,
                    "frame_width": 16,
                    "frame_height": 16,
                    "frame_count": 32,
                    "frametime": 2,
                    "interpolate": True,
                },
                "minecraft:block/magma": {
                    "texture_key": "minecraft:block/magma",
                    "namespace": "minecraft",
                    "chunk_id": 1,
                    "texture_id": 5,
                    "kind": "animation",
                    "pixel_x": 80,
                    "pixel_y": 0,
                    "frame_width": 16,
                    "frame_height": 16,
                    "frame_count": 3,
                    "frametime": 8,
                    "interpolate": False,
                },
            },
        }

    def test_alias_and_anim_lut_resolution(self):
        """Verify alias resolution for water, magma_block, and sea_lantern."""
        locs, _ = _build_block_face_location_lut(self.mock_mapping)
        self.assertIn("sea_lantern", locs)
        self.assertIn("water", locs)
        self.assertIn("magma_block", locs)

        face_lut, _ = build_block_face_lut(self.mock_mapping)
        chunk_lut, tex_lut = build_block_face_atlas_ids(self.mock_mapping)
        timing_lut, frame_size_lut = build_block_face_anim_lut(self.mock_mapping)

        self.assertEqual(chunk_lut["sea_lantern"][0], 1)
        self.assertEqual(tex_lut["sea_lantern"][0], 38)
        self.assertEqual(face_lut["sea_lantern"][0], (39, 0))
        self.assertEqual(timing_lut["sea_lantern"][0], (5.0, 5.0, 0.0, 0.0))
        self.assertEqual(frame_size_lut["sea_lantern"][0], (16.0, 16.0, 0.0, 0.0))

        self.assertEqual(chunk_lut["water"][0], 1)
        self.assertEqual(tex_lut["water"][0], 10)
        self.assertEqual(face_lut["water"][0], (10, 0))
        self.assertEqual(timing_lut["water"][0], (32.0, 2.0, 1.0, 0.0))

        self.assertEqual(chunk_lut["stone"][0], 0)
        self.assertEqual(face_lut["stone"][0], (1, 0))

    def test_point_cloud_and_geometry_nodes_animation_uv_evaluation(self):
        """Verify point cloud builder and evaluated mesh UVMap values for animation chunk."""
        mat0 = bpy.data.materials.new("mtk:minecraft:atlas_chunk_000_albedo:test:attr:UVMap")
        mat1 = bpy.data.materials.new("mtk:minecraft:atlas_chunk_001_albedo:test:attr:UVMap")
        import json
        mat0["mtk_atlas_mapping"] = json.dumps(self.mock_mapping)

        atlas_params = extract_atlas_parameters(mat0)

        storage = VoxelStorage()
        storage.min_x = 0
        storage.min_y = 0
        storage.min_z = 0
        storage.size_x = 2
        storage.size_y = 1
        storage.size_z = 1
        storage.block_map[(0, 0, 0)] = "minecraft:sea_lantern"
        storage.block_map[(1, 0, 0)] = "minecraft:stone"

        build_res = update_world_point_cloud(
            bpy.context,
            storage,
            filter_air=True,
            atlas_mapping_dict=atlas_params.get("material_id_map", {}),
            block_face_lut=atlas_params.get("block_face_lut", {}),
            block_face_chunk_lut=atlas_params.get("block_face_chunk_lut", {}),
            block_face_texture_lut=atlas_params.get("block_face_texture_lut", {}),
            block_face_tint_lut=atlas_params.get("block_face_tint_lut", {}),
            block_face_anim_timing_lut=atlas_params.get("block_face_anim_timing_lut", {}),
            block_face_anim_frame_size_lut=atlas_params.get("block_face_anim_frame_size_lut", {}),
            atlas_width=atlas_params["width"],
            atlas_height=atlas_params["height"],
            tile_size=atlas_params["tile_size"],
            tiles_per_row=atlas_params["tiles_per_row"],
            anim_atlas_width=atlas_params["chunk_1_width"],
            anim_atlas_height=atlas_params["chunk_1_height"],
            anim_frame_width=atlas_params["chunk_1_tile_size"],
            anim_frame_height=atlas_params["chunk_1_tile_size"],
        )

        self.assertIsNotNone(build_res.world_obj)
        setup_material_slots_for_object(build_res.world_obj, mat0, self.mock_mapping)
        setup_world_geometry_nodes(build_res.world_obj)

        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = build_res.world_obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()

        eval_mat_names = [m.name for m in eval_mesh.materials if m]
        self.assertIn(mat0.name, eval_mat_names)
        self.assertIn(mat1.name, eval_mat_names)

        uv_attr = eval_mesh.attributes.get("UVMap")
        self.assertIsNotNone(uv_attr)
        self.assertEqual(uv_attr.domain, "CORNER")

        timing_attr = eval_mesh.attributes.get("mtk_anim_timing")
        self.assertIsNotNone(timing_attr)

        chunk_attr = eval_mesh.attributes.get("mtk_atlas_chunk_id")
        self.assertIsNotNone(chunk_attr)

        expected_u_min = 624.0 / 896.0
        expected_v_max = 1.0

        found_anim_quad = False
        for p in eval_mesh.polygons:
            mat = eval_mesh.materials[p.material_index]
            if mat and mat.name == mat1.name:
                corners_uv = [uv_attr.data[loop_idx].vector for loop_idx in p.loop_indices]
                for uv in corners_uv:
                    self.assertAlmostEqual(uv.x, expected_u_min, delta=0.03)
                    self.assertAlmostEqual(uv.y, expected_v_max, delta=0.03)
                found_anim_quad = True
                break

        self.assertTrue(found_anim_quad, "Expected at least one polygon to be assigned to Chunk 1 material")
        eval_obj.to_mesh_clear()


if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'])
