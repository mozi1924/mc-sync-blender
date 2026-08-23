"""
Unit tests for Yefira Atlas Material Integration, 6-face UV math, and Geometry Nodes attributes.
"""

import sys
import os
import unittest
try:
    import bpy
    HAS_BPY = True
except ImportError:
    bpy = None
    HAS_BPY = False

dcc_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dcc_plugins"))
if dcc_dir not in sys.path:
    sys.path.insert(0, dcc_dir)
plugin_dir = os.path.join(dcc_dir, "yefira_blender")
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

from materials.atlas_integration import (
    build_block_face_lut,
    extract_atlas_parameters,
    setup_material_slots_for_object,
    find_all_atlas_chunk_materials,
    FACE_ORDER,
)
from core.block_classifier import parse_and_classify, BlockTypeEnum


class TestYefiraAtlasIntegration(unittest.TestCase):

    def test_build_block_face_lut(self):
        sample_mapping = {
            "format_version": 10,
            "tile_size": 16,
            "face_order": FACE_ORDER,
            "chunks": [
                {
                    "chunk_id": 0,
                    "width": 1024,
                    "height": 512,
                    "tile_size": 16,
                    "tiles_per_row": 64,
                }
            ],
            "textures": {
                "minecraft:block/dirt": {
                    "tile_column": 5,
                    "tile_row": 1,
                    "tile_size": 16,
                    "texture_id": 69,
                },
                "minecraft:block/stone": {
                    "tile_column": 0,
                    "tile_row": 0,
                    "tile_size": 16,
                    "texture_id": 0,
                },
                "minecraft:block/grass_block_top": {
                    "tile_column": 12,
                    "tile_row": 0,
                    "tile_size": 16,
                    "texture_id": 12,
                },
                "minecraft:block/grass_block_side": {
                    "tile_column": 10,
                    "tile_row": 2,
                    "tile_size": 16,
                    "texture_id": 138,
                },
            },
            "materials": [
                {
                    "material_id": 0,
                    "name": "stone",
                    "faces": {
                        "+X": {"tile_column": 0, "tile_row": 0},
                        "-X": {"tile_column": 0, "tile_row": 0},
                        "+Y": {"tile_column": 0, "tile_row": 0},
                        "-Y": {"tile_column": 0, "tile_row": 0},
                        "+Z": {"tile_column": 0, "tile_row": 0},
                        "-Z": {"tile_column": 0, "tile_row": 0},
                    }
                },
                {
                    "material_id": 42,
                    "name": "grass_block",
                    "faces": {
                        "+X": {"tile_column": 10, "tile_row": 2},
                        "-X": {"tile_column": 10, "tile_row": 2},
                        "+Y": {"tile_column": 12, "tile_row": 0}, # Top (+Y in MC -> +Z in Blender)
                        "-Y": {"tile_column": 5, "tile_row": 1},  # Bottom (-Y in MC -> -Z in Blender)
                        "+Z": {"tile_column": 10, "tile_row": 2},
                        "-Z": {"tile_column": 10, "tile_row": 2},
                    }
                }
            ]
        }

        face_lut, mat_id_map = build_block_face_lut(sample_mapping)

        # 1. Verify stone
        self.assertIn("stone", face_lut)
        self.assertEqual(face_lut["stone"], [(0, 0)] * 6)
        self.assertEqual(mat_id_map["stone"], 0)

        # 2. Verify grass_block
        self.assertIn("grass_block", face_lut)
        grass_coords = face_lut["grass_block"]
        self.assertEqual(len(grass_coords), 6)
        self.assertEqual(grass_coords[0], (10, 2))  # +X
        self.assertEqual(grass_coords[1], (10, 2))  # -X
        self.assertEqual(grass_coords[2], (12, 0))  # +Y (Top)
        self.assertEqual(grass_coords[3], (5, 1))   # -Y (Bottom)
        self.assertEqual(grass_coords[4], (10, 2))  # +Z (South)
        self.assertEqual(grass_coords[5], (10, 2))  # -Z (North)
        self.assertEqual(mat_id_map["grass_block"], 42)

        # 3. Verify fallback dirt from textures map
        self.assertIn("dirt", face_lut)
        self.assertEqual(face_lut["dirt"], [(5, 1)] * 6)

    def test_texture_only_pbr_pack_derives_cube_faces(self):
        """Yefira must resolve logical blocks even when the pack has no models."""
        def location(column, row, texture_id, base=0.0, overlay=0.0):
            return {
                "tile_column": column,
                "tile_row": row,
                "chunk_id": 0,
                "texture_id": texture_id,
                "default_base_tint_weight": base,
                "default_overlay_tint_weight": overlay,
            }

        mapping = {
            "textures": {
                "minecraft:block/grass_block_side": location(205, 1, 461, overlay=1.0),
                "minecraft:block/grass_block_top": location(208, 1, 464, base=1.0, overlay=1.0),
                "minecraft:block/dirt": location(105, 1, 361),
                "minecraft:block/oak_log": location(127, 2, 639),
                "minecraft:block/oak_log_top": location(128, 2, 640),
            },
            # SPBR's generated entries are uniform.  They must not erase the
            # side/top decomposition available from its texture table.
            "materials": [{
                "material_id": 99,
                "name": "oak_log",
                "faces": {face: location(127, 2, 639) for face in FACE_ORDER},
            }],
        }

        face_lut, _ = build_block_face_lut(mapping)
        self.assertEqual(face_lut["grass_block"], [(205, 1), (205, 1), (208, 1), (105, 1), (205, 1), (205, 1)])
        self.assertEqual(face_lut["oak_log"], [(127, 2), (127, 2), (128, 2), (128, 2), (127, 2), (127, 2)])

    def test_non_square_atlas_uv_math(self):
        """
        Verify UV formulas for non-square Atlas textures and 16x16 / 32x32 resolutions.
        Formula:
          scale_u = tile_size / atlas_w
          scale_v = tile_size / atlas_h
          Atlas_U = (col + local_u) * scale_u
          Atlas_V = 1.0 - (row + 1.0 - local_v) * scale_v
        """
        # Test Case 1: 1024 x 512 with 16x16 tiles
        atlas_w, atlas_h, tile_size = 1024.0, 512.0, 16.0
        scale_u = tile_size / atlas_w  # 16/1024 = 0.015625
        scale_v = tile_size / atlas_h  # 16/512 = 0.03125

        col, row = 4, 2
        # Bottom-left of local tile (0, 0)
        u0 = (col + 0.0) * scale_u
        v0 = 1.0 - (row + 1.0 - 0.0) * scale_v
        self.assertAlmostEqual(u0, 64.0 / 1024.0)
        self.assertAlmostEqual(v0, 1.0 - 48.0 / 512.0)

        # Top-right of local tile (1, 1)
        u1 = (col + 1.0) * scale_u
        v1 = 1.0 - (row + 1.0 - 1.0) * scale_v
        self.assertAlmostEqual(u1, 80.0 / 1024.0)
        self.assertAlmostEqual(v1, 1.0 - 32.0 / 512.0)

        # Delta UV span covers exactly 16 pixels in both X and Y
        pixel_span_x = (u1 - u0) * atlas_w
        pixel_span_y = (v1 - v0) * atlas_h
        self.assertAlmostEqual(pixel_span_x, 16.0)
        self.assertAlmostEqual(pixel_span_y, 16.0)

        # Test Case 2: 2048 x 1024 with 32x32 HD tiles
        atlas_w, atlas_h, tile_size = 2048.0, 1024.0, 32.0
        scale_u = tile_size / atlas_w
        scale_v = tile_size / atlas_h

        col, row = 10, 5
        u0 = (col + 0.0) * scale_u
        v0 = 1.0 - (row + 1.0 - 0.0) * scale_v
        u1 = (col + 1.0) * scale_u
        v1 = 1.0 - (row + 1.0 - 1.0) * scale_v

        pixel_span_x = (u1 - u0) * atlas_w
        pixel_span_y = (v1 - v0) * atlas_h
        self.assertAlmostEqual(pixel_span_x, 32.0)
        self.assertAlmostEqual(pixel_span_y, 32.0)

    def test_multi_chunk_material_slots_setup(self):
        """Verify setup_material_slots_for_object populates slots for all chunks."""
        mesh = bpy.data.meshes.new("TestMultiChunkMesh")
        obj = bpy.data.objects.new("TestMultiChunkObj", mesh)
        bpy.context.scene.collection.objects.link(obj)

        mat0 = bpy.data.materials.new("mtk:minecraft:atlas_chunk_000_slots_test")
        mat0["mtk:atlas_chunk_id"] = 0
        mat0["mtk:pack_hash"] = "slots_setup_test"
        mat1 = bpy.data.materials.new("mtk:minecraft:atlas_chunk_001_slots_test")
        mat1["mtk:atlas_chunk_id"] = 1
        mat1["mtk:pack_hash"] = "slots_setup_test"
        mat2 = bpy.data.materials.new("mtk:minecraft:atlas_chunk_002_slots_test")
        mat2["mtk:atlas_chunk_id"] = 2
        mat2["mtk:pack_hash"] = "slots_setup_test"

        mapping = {
            "chunks": [
                {"chunk_id": 0, "kind": "static"},
                {"chunk_id": 1, "kind": "static"},
                {"chunk_id": 2, "kind": "animation"},
            ]
        }

        chunk_mats = find_all_atlas_chunk_materials(mapping, bound_material=mat0)
        self.assertEqual(len(chunk_mats), 3)
        self.assertIs(chunk_mats[0], mat0)
        self.assertIs(chunk_mats[1], mat1)
        self.assertIs(chunk_mats[2], mat2)

        setup_material_slots_for_object(obj, mat0, mapping)
        self.assertEqual(len(obj.data.materials), 3)
        self.assertIs(obj.data.materials[0], mat0)
        self.assertIs(obj.data.materials[1], mat1)
        self.assertIs(obj.data.materials[2], mat2)

    def test_multiface_block_state_resolution(self):
        """Verify build_block_face_lut assigns correct 6 faces for lit/unlit multi-face blocks."""
        def loc(col, row, tex_id):
            return {"tile_column": col, "tile_row": row, "chunk_id": 0, "texture_id": tex_id}

        mapping = {
            "textures": {
                "minecraft:block/furnace_top": loc(1, 0, 10),
                "minecraft:block/furnace_side": loc(2, 0, 20),
                "minecraft:block/furnace_front": loc(3, 0, 30),
                "minecraft:block/furnace_front_on": loc(4, 0, 40),
                "minecraft:block/beehive_top": loc(5, 0, 50),
                "minecraft:block/beehive_bottom": loc(6, 0, 60),
                "minecraft:block/beehive_side": loc(7, 0, 70),
                "minecraft:block/beehive_front": loc(8, 0, 80),
                "minecraft:block/beehive_front_honey": loc(9, 0, 90),
                "minecraft:block/respawn_anchor_top_off": loc(10, 0, 100),
                "minecraft:block/respawn_anchor_top": loc(11, 0, 110),
                "minecraft:block/respawn_anchor_bottom": loc(12, 0, 120),
                "minecraft:block/respawn_anchor_side0": loc(13, 0, 130),
                "minecraft:block/respawn_anchor_side4": loc(14, 0, 140),
                "minecraft:block/observer_top": loc(15, 0, 150),
                "minecraft:block/observer_side": loc(16, 0, 160),
                "minecraft:block/observer_back": loc(17, 0, 170),
                "minecraft:block/observer_front": loc(18, 0, 180),
                "minecraft:block/grass_block_top": loc(19, 0, 190),
                "minecraft:block/grass_block_side": loc(20, 0, 200),
                "minecraft:block/grass_block_snow": loc(21, 0, 210),
                "minecraft:block/dirt": loc(22, 0, 220),
            }
        }

        face_lut, _ = build_block_face_lut(mapping)

        # 1. Furnace unlit: [side, side, top, bottom/top, side, front]
        # Order: +X (East, 0), -X (West, 1), +Y (Top, 2), -Y (Bottom, 3), +Z (South, 4), -Z (North, 5)
        self.assertIn("furnace", face_lut)
        self.assertEqual(face_lut["furnace"][0], (2, 0))  # +X East: side
        self.assertEqual(face_lut["furnace"][1], (2, 0))  # -X West: side
        self.assertEqual(face_lut["furnace"][2], (1, 0))  # +Y Top: top
        self.assertEqual(face_lut["furnace"][3], (1, 0))  # -Y Bottom: top
        self.assertEqual(face_lut["furnace"][4], (2, 0))  # +Z South: side
        self.assertEqual(face_lut["furnace"][5], (3, 0))  # -Z North: front

        # 2. Furnace lit: [side, side, top, bottom/top, side, front_on]
        self.assertIn("furnace_front_on", face_lut)
        self.assertEqual(face_lut["furnace_front_on"][0], (2, 0))  # +X East: side (NOT front_on)
        self.assertEqual(face_lut["furnace_front_on"][1], (2, 0))  # -X West: side (NOT front_on)
        self.assertEqual(face_lut["furnace_front_on"][2], (1, 0))  # +Y Top: top (NOT front_on)
        self.assertEqual(face_lut["furnace_front_on"][3], (1, 0))  # -Y Bottom: top (NOT front_on)
        self.assertEqual(face_lut["furnace_front_on"][4], (2, 0))  # +Z South: side (NOT front_on)
        self.assertEqual(face_lut["furnace_front_on"][5], (4, 0))  # -Z North: front_on

        # 3. Beehive honey
        self.assertIn("beehive_front_honey", face_lut)
        self.assertEqual(face_lut["beehive_front_honey"][0], (7, 0))  # East
        self.assertEqual(face_lut["beehive_front_honey"][1], (7, 0))  # West
        self.assertEqual(face_lut["beehive_front_honey"][2], (5, 0))  # Top
        self.assertEqual(face_lut["beehive_front_honey"][3], (6, 0))  # Bottom
        self.assertEqual(face_lut["beehive_front_honey"][4], (7, 0))  # South
        self.assertEqual(face_lut["beehive_front_honey"][5], (9, 0))  # North: front_honey

        # 4. Observer
        self.assertIn("observer", face_lut)
        self.assertEqual(face_lut["observer"][0], (16, 0))  # +X: side
        self.assertEqual(face_lut["observer"][1], (16, 0))  # -X: side
        self.assertEqual(face_lut["observer"][2], (15, 0))  # +Y: top
        self.assertEqual(face_lut["observer"][3], (15, 0))  # -Y: top/bottom
        self.assertEqual(face_lut["observer"][4], (17, 0))  # +Z: back
        self.assertEqual(face_lut["observer"][5], (18, 0))  # -Z: front

        # 5. Grass block snowy
        self.assertIn("grass_block_snow", face_lut)
        self.assertEqual(face_lut["grass_block_snow"][0], (21, 0))  # East: snow
        self.assertEqual(face_lut["grass_block_snow"][1], (21, 0))  # West: snow
        self.assertEqual(face_lut["grass_block_snow"][2], (19, 0))  # Top: top
        self.assertEqual(face_lut["grass_block_snow"][3], (22, 0))  # Bottom: dirt
        self.assertEqual(face_lut["grass_block_snow"][4], (21, 0))  # South: snow
        self.assertEqual(face_lut["grass_block_snow"][5], (21, 0))  # North: snow

    def test_point_cloud_furnace_lit_resolution(self):
        """Verify Point Cloud Builder resolves exact 6 faces for lit furnace."""
        from core.point_cloud_builder import _resolve_face_values
        from core.block_classifier import parse_and_classify

        lut = {
            "furnace_top": (1, 0),
            "furnace_side": (2, 0),
            "furnace_front": (3, 0),
            "furnace_front_on": (4, 0),
        }

        # Test lit furnace
        parsed_lit = parse_and_classify("minecraft:furnace[facing=north,lit=true]")
        coords_lit = _resolve_face_values(lut, parsed_lit, (0, 0), is_coord=True)
        self.assertEqual(coords_lit[0], (2, 0))  # Face 0 (East / +X) -> furnace_side
        self.assertEqual(coords_lit[1], (2, 0))  # Face 1 (West / -X) -> furnace_side
        self.assertEqual(coords_lit[2], (1, 0))  # Face 2 (Top / +Y) -> furnace_top
        self.assertEqual(coords_lit[3], (1, 0))  # Face 3 (Bottom / -Y) -> furnace_top
        self.assertEqual(coords_lit[4], (2, 0))  # Face 4 (South / +Z) -> furnace_side
        self.assertEqual(coords_lit[5], (4, 0))  # Face 5 (North / -Z) -> furnace_front_on

        # Test unlit furnace
        parsed_unlit = parse_and_classify("minecraft:furnace[facing=north,lit=false]")
        coords_unlit = _resolve_face_values(lut, parsed_unlit, (0, 0), is_coord=True)
        self.assertEqual(coords_unlit[0], (2, 0))  # Face 0 (East / +X) -> furnace_side
        self.assertEqual(coords_unlit[1], (2, 0))  # Face 1 (West / -X) -> furnace_side
        self.assertEqual(coords_unlit[2], (1, 0))  # Face 2 (Top / +Y) -> furnace_top
        self.assertEqual(coords_unlit[3], (1, 0))  # Face 3 (Bottom / -Y) -> furnace_top
        self.assertEqual(coords_unlit[4], (2, 0))  # Face 4 (South / +Z) -> furnace_side
        self.assertEqual(coords_unlit[5], (3, 0))  # Face 5 (North / -Z) -> furnace_front


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
