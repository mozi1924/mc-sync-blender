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

if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])

