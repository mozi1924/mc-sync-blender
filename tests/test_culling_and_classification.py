"""
Unit tests for Block Classifier and Geometry Nodes Point Cloud attribute encoding.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dcc_plugins", "yefira_blender")))

from core.block_classifier import parse_and_classify, BlockTypeEnum
from core.storage import VoxelStorage

class TestPointClassifier(unittest.TestCase):
    def test_parse_cube(self):
        p = parse_and_classify("minecraft:stone")
        self.assertEqual(p.block_type, BlockTypeEnum.CUBE)
        self.assertEqual(p.name, "stone")
        self.assertEqual(p.rot_euler, (0.0, 0.0, 0.0))

    def test_parse_stairs(self):
        p = parse_and_classify("minecraft:oak_stairs[facing=south,half=top,shape=straight,waterlogged=false]")
        self.assertEqual(p.block_type, BlockTypeEnum.STAIRS)
        self.assertEqual(p.template_name, "oak_stairs")
        self.assertAlmostEqual(p.rot_euler[0], 3.14159265, places=4) # Upside down flip (180 deg)
        self.assertAlmostEqual(p.rot_euler[2], -3.14159265, places=4) # South yaw

    def test_parse_plant(self):
        p = parse_and_classify("minecraft:poppy")
        self.assertEqual(p.block_type, BlockTypeEnum.CROSS_PLANT)
        self.assertEqual(p.template_name, "cross_plant")

    def test_parse_waterlogged(self):
        p = parse_and_classify("minecraft:oak_fence[waterlogged=true]")
        self.assertTrue(p.is_waterlogged)
        self.assertEqual(p.block_type, BlockTypeEnum.PROP_TEMPLATE)

    def test_parse_fluids(self):
        p = parse_and_classify("minecraft:water[level=0]")
        self.assertEqual(p.block_type, BlockTypeEnum.FLUID)
        self.assertEqual(p.tint_data, (1.0, 1.0, 1.0, 0.0))

    def test_lit_and_emissive(self):
        p_furnace_lit = parse_and_classify("minecraft:furnace[facing=north,lit=true]")
        self.assertEqual(p_furnace_lit.is_emissive, 1)
        self.assertEqual(p_furnace_lit.emissive_level, 1.0)

        p_furnace_unlit = parse_and_classify("minecraft:furnace[facing=north,lit=false]")
        self.assertEqual(p_furnace_unlit.is_emissive, 0)
        self.assertEqual(p_furnace_unlit.emissive_level, 0.0)

        p_lamp_lit = parse_and_classify("minecraft:redstone_lamp[lit=true]")
        self.assertEqual(p_lamp_lit.is_emissive, 1)

        p_torch_lit = parse_and_classify("minecraft:redstone_torch[lit=true]")
        self.assertEqual(p_torch_lit.is_emissive, 1)

        p_torch_unlit = parse_and_classify("minecraft:redstone_torch[lit=false]")
        self.assertEqual(p_torch_unlit.is_emissive, 0)

        p_glowstone = parse_and_classify("minecraft:glowstone")
        self.assertEqual(p_glowstone.is_emissive, 1)

        p_anchor = parse_and_classify("minecraft:respawn_anchor[charges=4]")
        self.assertEqual(p_anchor.is_emissive, 1)
        self.assertEqual(p_anchor.emissive_level, 1.0)

        p_wire = parse_and_classify("minecraft:redstone_wire[power=15]")
        self.assertEqual(p_wire.is_emissive, 1)
        self.assertEqual(p_wire.emissive_level, 1.0)

    def test_hardcoded_and_snowy_tints(self):
        p_spruce = parse_and_classify("minecraft:spruce_leaves")
        self.assertEqual(p_spruce.tint_data, (1.0, 1.0, 1.0, 1.0))

        p_birch = parse_and_classify("minecraft:birch_leaves")
        self.assertEqual(p_birch.tint_data, (1.0, 1.0, 1.0, 1.0))

        p_lily = parse_and_classify("minecraft:lily_pad")
        self.assertEqual(p_lily.tint_data, (1.0, 1.0, 1.0, 1.0))

        p_snowy_grass = parse_and_classify("minecraft:grass_block[snowy=true]")
        self.assertEqual(p_snowy_grass.tint_data, (0.0, 0.0, 0.0, 0.0))

        p_wire = parse_and_classify("minecraft:redstone_wire[power=15]")
        self.assertEqual(p_wire.tint_data, (1.0, 1.0, 1.0, 1.0))
        self.assertAlmostEqual(p_wire.tint_color[0], 1.0, places=2)

    def test_atlas_lookup_keys(self):
        from core.block_classifier import atlas_lookup_keys

        p_furnace = parse_and_classify("minecraft:furnace[facing=north,lit=true]")
        keys = atlas_lookup_keys(p_furnace)
        self.assertIn("furnace_front_on", keys)

        p_hive = parse_and_classify("minecraft:beehive[facing=north,honey_level=5]")
        keys = atlas_lookup_keys(p_hive)
        self.assertIn("beehive_front_honey", keys)

        p_anchor = parse_and_classify("minecraft:respawn_anchor[charges=4]")
        keys = atlas_lookup_keys(p_anchor)
        self.assertIn("respawn_anchor_top", keys)
        self.assertIn("respawn_anchor_side4", keys)

        p_wheat = parse_and_classify("minecraft:wheat[age=7]")
        keys = atlas_lookup_keys(p_wheat)
        self.assertIn("wheat_stage7", keys)

        p_snow = parse_and_classify("minecraft:grass_block[snowy=true]")
        keys = atlas_lookup_keys(p_snow)
        self.assertIn("grass_block_snow", keys)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])


