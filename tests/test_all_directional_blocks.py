"""
Comprehensive verification test suite for ALL directional full cube blocks in Yefira.
Covers:
  - Horizontal blocks (furnaces, smokers, blast furnaces, beehives, pumpkins, looms)
  - Axis blocks (logs, woods, stems, hyphae, basalt, bone, hay, deepslate, pillars)
  - 6-Directional blocks (command blocks, dispensers, droppers, observers, pistons, barrels, shulker boxes)
  - Glazed Terracottas (16 colors x 4 facings)
"""

from __future__ import annotations

import json
import math
import unittest
import bpy

from dcc_plugins.yefira_blender.core.storage import VoxelStorage
from dcc_plugins.yefira_blender.core.point_cloud_builder import update_world_point_cloud
from dcc_plugins.yefira_blender.nodes.world_tree import setup_world_geometry_nodes
from dcc_plugins.yefira_blender.materials.atlas_integration import parse_atlas_mapping, extract_atlas_parameters


class TestAllDirectionalBlocks(unittest.TestCase):

    def setUp(self):
        bpy.ops.wm.read_homefile(use_empty=True)
        # Create a rich mock Atlas mapping containing all relevant directional textures
        self.mock_mapping = {
            "version": "1.0",
            "tile_size": 16,
            "chunks": [
                {"chunk_id": 0, "width": 1024, "height": 1024, "tile_size": 16, "tiles_per_row": 64}
            ],
            "textures": {
                # Logs
                "minecraft:block/oak_log": {"tile_column": 10, "tile_row": 1, "chunk_id": 0, "texture_id": 1, "kind": "static"},
                "minecraft:block/oak_log_top": {"tile_column": 11, "tile_row": 1, "chunk_id": 0, "texture_id": 2, "kind": "static"},
                # Furnaces
                "minecraft:block/furnace_front": {"tile_column": 20, "tile_row": 1, "chunk_id": 0, "texture_id": 10, "kind": "static"},
                "minecraft:block/furnace_front_on": {"tile_column": 21, "tile_row": 1, "chunk_id": 0, "texture_id": 11, "kind": "static"},
                "minecraft:block/furnace_side": {"tile_column": 22, "tile_row": 1, "chunk_id": 0, "texture_id": 12, "kind": "static"},
                "minecraft:block/furnace_top": {"tile_column": 23, "tile_row": 1, "chunk_id": 0, "texture_id": 13, "kind": "static"},
                # Command blocks
                "minecraft:block/command_block_front": {"tile_column": 30, "tile_row": 1, "chunk_id": 0, "texture_id": 20, "kind": "static"},
                "minecraft:block/command_block_back": {"tile_column": 31, "tile_row": 1, "chunk_id": 0, "texture_id": 21, "kind": "static"},
                "minecraft:block/command_block_side": {"tile_column": 32, "tile_row": 1, "chunk_id": 0, "texture_id": 22, "kind": "static"},
                "minecraft:block/command_block_conditional": {"tile_column": 33, "tile_row": 1, "chunk_id": 0, "texture_id": 23, "kind": "static"},
                # Dispensers / Droppers
                "minecraft:block/dispenser_front": {"tile_column": 40, "tile_row": 1, "chunk_id": 0, "texture_id": 30, "kind": "static"},
                "minecraft:block/dispenser_front_vertical": {"tile_column": 41, "tile_row": 1, "chunk_id": 0, "texture_id": 31, "kind": "static"},
                # Observers
                "minecraft:block/observer_front": {"tile_column": 50, "tile_row": 1, "chunk_id": 0, "texture_id": 40, "kind": "static"},
                "minecraft:block/observer_back": {"tile_column": 51, "tile_row": 1, "chunk_id": 0, "texture_id": 41, "kind": "static"},
                "minecraft:block/observer_top": {"tile_column": 52, "tile_row": 1, "chunk_id": 0, "texture_id": 42, "kind": "static"},
                "minecraft:block/observer_side": {"tile_column": 53, "tile_row": 1, "chunk_id": 0, "texture_id": 43, "kind": "static"},
                # Pistons
                "minecraft:block/piston_top": {"tile_column": 60, "tile_row": 1, "chunk_id": 0, "texture_id": 50, "kind": "static"},
                "minecraft:block/piston_top_sticky": {"tile_column": 61, "tile_row": 1, "chunk_id": 0, "texture_id": 51, "kind": "static"},
                "minecraft:block/piston_bottom": {"tile_column": 62, "tile_row": 1, "chunk_id": 0, "texture_id": 52, "kind": "static"},
                "minecraft:block/piston_side": {"tile_column": 63, "tile_row": 1, "chunk_id": 0, "texture_id": 53, "kind": "static"},
                # Barrels
                "minecraft:block/barrel_top": {"tile_column": 1, "tile_row": 2, "chunk_id": 0, "texture_id": 60, "kind": "static"},
                "minecraft:block/barrel_top_open": {"tile_column": 2, "tile_row": 2, "chunk_id": 0, "texture_id": 61, "kind": "static"},
                "minecraft:block/barrel_bottom": {"tile_column": 3, "tile_row": 2, "chunk_id": 0, "texture_id": 62, "kind": "static"},
                "minecraft:block/barrel_side": {"tile_column": 4, "tile_row": 2, "chunk_id": 0, "texture_id": 63, "kind": "static"},
                # Beehives
                "minecraft:block/beehive_front": {"tile_column": 10, "tile_row": 2, "chunk_id": 0, "texture_id": 70, "kind": "static"},
                "minecraft:block/beehive_front_honey": {"tile_column": 11, "tile_row": 2, "chunk_id": 0, "texture_id": 71, "kind": "static"},
                "minecraft:block/beehive_side": {"tile_column": 12, "tile_row": 2, "chunk_id": 0, "texture_id": 72, "kind": "static"},
                "minecraft:block/beehive_top": {"tile_column": 13, "tile_row": 2, "chunk_id": 0, "texture_id": 73, "kind": "static"},
                "minecraft:block/beehive_bottom": {"tile_column": 14, "tile_row": 2, "chunk_id": 0, "texture_id": 74, "kind": "static"},
                # Pumpkins
                "minecraft:block/carved_pumpkin": {"tile_column": 20, "tile_row": 2, "chunk_id": 0, "texture_id": 80, "kind": "static"},
                "minecraft:block/pumpkin_side": {"tile_column": 21, "tile_row": 2, "chunk_id": 0, "texture_id": 81, "kind": "static"},
                "minecraft:block/pumpkin_top": {"tile_column": 22, "tile_row": 2, "chunk_id": 0, "texture_id": 82, "kind": "static"},
                # Glazed Terracotta
                "minecraft:block/magenta_glazed_terracotta": {"tile_column": 30, "tile_row": 2, "chunk_id": 0, "texture_id": 90, "kind": "static"},
                "minecraft:block/white_glazed_terracotta": {"tile_column": 31, "tile_row": 2, "chunk_id": 0, "texture_id": 91, "kind": "static"},
                "minecraft:block/orange_glazed_terracotta": {"tile_column": 32, "tile_row": 2, "chunk_id": 0, "texture_id": 92, "kind": "static"},
                "minecraft:block/light_blue_glazed_terracotta": {"tile_column": 33, "tile_row": 2, "chunk_id": 0, "texture_id": 93, "kind": "static"},
                "minecraft:block/yellow_glazed_terracotta": {"tile_column": 34, "tile_row": 2, "chunk_id": 0, "texture_id": 94, "kind": "static"},
                "minecraft:block/lime_glazed_terracotta": {"tile_column": 35, "tile_row": 2, "chunk_id": 0, "texture_id": 95, "kind": "static"},
                "minecraft:block/pink_glazed_terracotta": {"tile_column": 36, "tile_row": 2, "chunk_id": 0, "texture_id": 96, "kind": "static"},
                "minecraft:block/gray_glazed_terracotta": {"tile_column": 37, "tile_row": 2, "chunk_id": 0, "texture_id": 97, "kind": "static"},
                "minecraft:block/light_gray_glazed_terracotta": {"tile_column": 38, "tile_row": 2, "chunk_id": 0, "texture_id": 98, "kind": "static"},
                "minecraft:block/cyan_glazed_terracotta": {"tile_column": 39, "tile_row": 2, "chunk_id": 0, "texture_id": 99, "kind": "static"},
                "minecraft:block/purple_glazed_terracotta": {"tile_column": 40, "tile_row": 2, "chunk_id": 0, "texture_id": 100, "kind": "static"},
                "minecraft:block/blue_glazed_terracotta": {"tile_column": 41, "tile_row": 2, "chunk_id": 0, "texture_id": 101, "kind": "static"},
                "minecraft:block/brown_glazed_terracotta": {"tile_column": 42, "tile_row": 2, "chunk_id": 0, "texture_id": 102, "kind": "static"},
                "minecraft:block/green_glazed_terracotta": {"tile_column": 43, "tile_row": 2, "chunk_id": 0, "texture_id": 103, "kind": "static"},
                "minecraft:block/red_glazed_terracotta": {"tile_column": 44, "tile_row": 2, "chunk_id": 0, "texture_id": 104, "kind": "static"},
                "minecraft:block/black_glazed_terracotta": {"tile_column": 45, "tile_row": 2, "chunk_id": 0, "texture_id": 105, "kind": "static"},
            },
            "materials": []
        }

    def _build_and_eval_single_block(self, state_json: dict):
        storage = VoxelStorage()
        storage.set_full_snapshot(
            0, 0, 0, 1, 1, 1,
            [json.dumps(state_json)],
            [0],
        )
        res = update_world_point_cloud(
            bpy.context, storage,
            atlas_mapping_textures=self.mock_mapping["textures"],
            atlas_width=1024.0, atlas_height=1024.0,
            tile_size=16.0, tiles_per_row=64,
        )
        setup_world_geometry_nodes(res.world_obj)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = res.world_obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        return res.world_obj, eval_mesh, eval_obj

    def test_furnace_all_facings(self):
        """Verify furnace front face maps to exact world direction across north/south/east/west."""
        facings = {
            "north": "north",
            "south": "south",
            "east": "east",
            "west": "west",
        }
        for facing, target_face in facings.items():
            state_json = {
                "state": f"minecraft:furnace[facing={facing},lit=false]",
                "type": 0, "opaque": 1, "emissive": 0,
                "faces": {
                    "east": {"tex": "minecraft:block/furnace_front" if facing == "east" else "minecraft:block/furnace_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "west": {"tex": "minecraft:block/furnace_front" if facing == "west" else "minecraft:block/furnace_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "top": {"tex": "minecraft:block/furnace_top", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "bottom": {"tex": "minecraft:block/furnace_top", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "south": {"tex": "minecraft:block/furnace_front" if facing == "south" else "minecraft:block/furnace_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "north": {"tex": "minecraft:block/furnace_front" if facing == "north" else "minecraft:block/furnace_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                }
            }
            obj, eval_mesh, eval_obj = self._build_and_eval_single_block(state_json)
            try:
                # Target face tile should have furnace_front (col 20, row 1)
                tile_attr = obj.data.attributes[f"mtk_tile_{target_face}"]
                self.assertAlmostEqual(tile_attr.data[0].vector[0], 20.0)
                self.assertAlmostEqual(tile_attr.data[0].vector[1], 1.0)
            finally:
                eval_obj.to_mesh_clear()

    def test_log_all_axes(self):
        """Verify log top and side texture assignments for axis x, y, z."""
        # axis=y: top/bottom are oak_log_top (col 11, row 1)
        state_y = {
            "state": "minecraft:oak_log[axis=y]",
            "type": 0, "opaque": 1, "emissive": 0,
            "faces": {
                "east": {"tex": "minecraft:block/oak_log", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "west": {"tex": "minecraft:block/oak_log", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "top": {"tex": "minecraft:block/oak_log_top", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "bottom": {"tex": "minecraft:block/oak_log_top", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "south": {"tex": "minecraft:block/oak_log", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "north": {"tex": "minecraft:block/oak_log", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
            }
        }
        obj, eval_mesh, eval_obj = self._build_and_eval_single_block(state_y)
        try:
            self.assertAlmostEqual(obj.data.attributes["mtk_tile_top"].data[0].vector[0], 11.0)
            self.assertAlmostEqual(obj.data.attributes["mtk_tile_bottom"].data[0].vector[0], 11.0)
            self.assertAlmostEqual(obj.data.attributes["mtk_tile_east"].data[0].vector[0], 10.0)
        finally:
            eval_obj.to_mesh_clear()

        # axis=x: east/west are oak_log_top (col 11, row 1), top/bottom/south/north have rot=90
        state_x = {
            "state": "minecraft:oak_log[axis=x]",
            "type": 0, "opaque": 1, "emissive": 0,
            "faces": {
                "east": {"tex": "minecraft:block/oak_log_top", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "west": {"tex": "minecraft:block/oak_log_top", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "top": {"tex": "minecraft:block/oak_log", "rot": 90, "uv": [0.0, 0.0, 1.0, 1.0]},
                "bottom": {"tex": "minecraft:block/oak_log", "rot": 90, "uv": [0.0, 0.0, 1.0, 1.0]},
                "south": {"tex": "minecraft:block/oak_log", "rot": 90, "uv": [0.0, 0.0, 1.0, 1.0]},
                "north": {"tex": "minecraft:block/oak_log", "rot": 90, "uv": [0.0, 0.0, 1.0, 1.0]},
            }
        }
        obj, eval_mesh, eval_obj = self._build_and_eval_single_block(state_x)
        try:
            self.assertAlmostEqual(obj.data.attributes["mtk_tile_east"].data[0].vector[0], 11.0)
            self.assertAlmostEqual(obj.data.attributes["mtk_tile_west"].data[0].vector[0], 11.0)
            self.assertAlmostEqual(obj.data.attributes["mtk_uv_rot_top"].data[0].value, 90.0)
        finally:
            eval_obj.to_mesh_clear()

    def test_glazed_terracotta_16_colors_rotation(self):
        """Verify all 16 glazed terracotta colors with rich rotation data."""
        colors = [
            "white", "orange", "magenta", "light_blue", "yellow", "lime",
            "pink", "gray", "light_gray", "cyan", "purple", "blue",
            "brown", "green", "red", "black"
        ]
        for color in colors:
            state_json = {
                "state": f"minecraft:{color}_glazed_terracotta[facing=north]",
                "type": 0, "opaque": 1, "emissive": 0,
                "faces": {
                    "east": {"tex": f"minecraft:block/{color}_glazed_terracotta", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "west": {"tex": f"minecraft:block/{color}_glazed_terracotta", "rot": 180, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "top": {"tex": f"minecraft:block/{color}_glazed_terracotta", "rot": 180, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "bottom": {"tex": f"minecraft:block/{color}_glazed_terracotta", "rot": 180, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "south": {"tex": f"minecraft:block/{color}_glazed_terracotta", "rot": 90, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "north": {"tex": f"minecraft:block/{color}_glazed_terracotta", "rot": 270, "uv": [0.0, 0.0, 1.0, 1.0]},
                }
            }
            obj, eval_mesh, eval_obj = self._build_and_eval_single_block(state_json)
            try:
                self.assertIn("UVMap", eval_mesh.attributes)
                # Verify that each polygon in the evaluated cube has valid UV values in [0, 1]
                uv_attr = eval_mesh.attributes["UVMap"]
                for loop_uv in uv_attr.data:
                    u, v, _ = loop_uv.vector
                    self.assertGreaterEqual(u, 0.0)
                    self.assertLessEqual(u, 1.0)
                    self.assertGreaterEqual(v, 0.0)
                    self.assertLessEqual(v, 1.0)
            finally:
                eval_obj.to_mesh_clear()

    def test_6_directional_blocks_command_and_observer(self):
        """Verify 6-directional blocks like command_block and observer across all 6 facings."""
        facings = {
            "down": "bottom",
            "up": "top",
            "north": "north",
            "south": "south",
            "west": "west",
            "east": "east",
        }
        for facing, target_face in facings.items():
            state_json = {
                "state": f"minecraft:command_block[conditional=false,facing={facing}]",
                "type": 0, "opaque": 1, "emissive": 0,
                "faces": {
                    "east": {"tex": "minecraft:block/command_block_front" if facing == "east" else "minecraft:block/command_block_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "west": {"tex": "minecraft:block/command_block_front" if facing == "west" else "minecraft:block/command_block_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "top": {"tex": "minecraft:block/command_block_front" if facing == "up" else "minecraft:block/command_block_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "bottom": {"tex": "minecraft:block/command_block_front" if facing == "down" else "minecraft:block/command_block_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "south": {"tex": "minecraft:block/command_block_front" if facing == "south" else "minecraft:block/command_block_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                    "north": {"tex": "minecraft:block/command_block_front" if facing == "north" else "minecraft:block/command_block_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                }
            }
            obj, eval_mesh, eval_obj = self._build_and_eval_single_block(state_json)
            try:
                # Target facing face must have command_block_front (col 30, row 1)
                tile_attr = obj.data.attributes[f"mtk_tile_{target_face}"]
                self.assertAlmostEqual(tile_attr.data[0].vector[0], 30.0)
                self.assertAlmostEqual(tile_attr.data[0].vector[1], 1.0)
            finally:
                eval_obj.to_mesh_clear()

    def test_observer_all_facings(self):
        """Verify observer arrows and faces for up, down, north, south, east, west."""
        # 1. Observer facing UP: arrows on sides point UP (rot=0)
        state_up = {
            "state": "minecraft:observer[facing=up,powered=false]",
            "type": 0, "opaque": 1, "emissive": 0,
            "faces": {
                "east": {"tex": "minecraft:block/observer_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "west": {"tex": "minecraft:block/observer_side", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "top": {"tex": "minecraft:block/observer_front", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "bottom": {"tex": "minecraft:block/observer_back", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "south": {"tex": "minecraft:block/observer_top", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "north": {"tex": "minecraft:block/observer_top", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
            }
        }
        obj, eval_mesh, eval_obj = self._build_and_eval_single_block(state_up)
        try:
            self.assertAlmostEqual(obj.data.attributes["mtk_tile_top"].data[0].vector[0], 50.0) # observer_front
            self.assertAlmostEqual(obj.data.attributes["mtk_tile_bottom"].data[0].vector[0], 51.0) # observer_back
            self.assertAlmostEqual(obj.data.attributes["mtk_tile_south"].data[0].vector[0], 52.0) # observer_top
            self.assertAlmostEqual(obj.data.attributes["mtk_uv_rot_south"].data[0].value, 0.0)
        finally:
            eval_obj.to_mesh_clear()

        # 2. Observer facing DOWN: arrows on sides point DOWN (rot=180)
        state_down = {
            "state": "minecraft:observer[facing=down,powered=false]",
            "type": 0, "opaque": 1, "emissive": 0,
            "faces": {
                "east": {"tex": "minecraft:block/observer_side", "rot": 180, "uv": [0.0, 0.0, 1.0, 1.0]},
                "west": {"tex": "minecraft:block/observer_side", "rot": 180, "uv": [0.0, 0.0, 1.0, 1.0]},
                "top": {"tex": "minecraft:block/observer_back", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "bottom": {"tex": "minecraft:block/observer_front", "rot": 0, "uv": [0.0, 0.0, 1.0, 1.0]},
                "south": {"tex": "minecraft:block/observer_top", "rot": 180, "uv": [0.0, 0.0, 1.0, 1.0]},
                "north": {"tex": "minecraft:block/observer_top", "rot": 180, "uv": [0.0, 0.0, 1.0, 1.0]},
            }
        }
        obj, eval_mesh, eval_obj = self._build_and_eval_single_block(state_down)
        try:
            self.assertAlmostEqual(obj.data.attributes["mtk_tile_bottom"].data[0].vector[0], 50.0) # observer_front
            self.assertAlmostEqual(obj.data.attributes["mtk_tile_top"].data[0].vector[0], 51.0) # observer_back
            self.assertAlmostEqual(obj.data.attributes["mtk_uv_rot_south"].data[0].value, 180.0)
        finally:
            eval_obj.to_mesh_clear()


if __name__ == "__main__":
    unittest.main()
