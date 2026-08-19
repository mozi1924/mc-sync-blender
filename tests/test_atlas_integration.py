"""
Unit tests for Yefira Atlas Material Integration, 6-face UV math, and Geometry Nodes attributes.
"""

import sys
import os
import unittest
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dcc_plugins", "yefira_blender")))

from materials.atlas_integration import (
    build_block_face_lut,
    extract_atlas_parameters,
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


if __name__ == "__main__":
    unittest.main()
