"""
Block state classification, rotation calculation, and Atlas material ID resolver.
Designed for ultra-fast Point Cloud attribute evaluation in Blender Geometry Nodes.
"""

from __future__ import annotations
import math
from typing import NamedTuple, Optional

class BlockTypeEnum:
    CUBE = 0          # Standard full 1x1x1 cube (dirt, stone, planks, ores, glass, etc.)
    CROSS_PLANT = 1   # X-shaped cross planes (flowers, tall grass, saplings, crops)
    SLAB = 2          # Half-block slab (bottom, top, double)
    STAIRS = 3        # Stairs (straight, inner, outer)
    TORCH = 4         # Torch, wall torch, lantern
    PROP_TEMPLATE = 5 # Pick instance from MC_Block_Templates Collection (doors, beds, chests, etc.)
    FLUID = 6         # Water and Lava surface planes
    AIR = 7           # Air (skipped)

# Known Air blocks
AIR_BLOCKS = {
    "minecraft:air",
    "minecraft:cave_air",
    "minecraft:void_air",
}

# Known Fluid blocks
FLUID_BLOCKS = {
    "minecraft:water",
    "minecraft:flowing_water",
    "minecraft:lava",
    "minecraft:flowing_lava",
}

# Transparent and Translucent blocks (fallback classification when atlas mapping lacks per-texture alpha)
TRANSPARENT_BLOCKS = {
    "minecraft:glass",
    "minecraft:tinted_glass",
    "minecraft:white_stained_glass",
    "minecraft:orange_stained_glass",
    "minecraft:magenta_stained_glass",
    "minecraft:light_blue_stained_glass",
    "minecraft:yellow_stained_glass",
    "minecraft:lime_stained_glass",
    "minecraft:pink_stained_glass",
    "minecraft:gray_stained_glass",
    "minecraft:light_gray_stained_glass",
    "minecraft:cyan_stained_glass",
    "minecraft:purple_stained_glass",
    "minecraft:blue_stained_glass",
    "minecraft:brown_stained_glass",
    "minecraft:green_stained_glass",
    "minecraft:red_stained_glass",
    "minecraft:black_stained_glass",
    "minecraft:ice",
    "minecraft:packed_ice",
    "minecraft:blue_ice",
    "minecraft:frosted_ice",
    "minecraft:water",
    "minecraft:flowing_water",
    "minecraft:slime_block",
    "minecraft:honey_block",
    "minecraft:beacon",
    "minecraft:barrier",
    "minecraft:structure_void",
    "minecraft:light",
    "minecraft:oak_leaves",
    "minecraft:spruce_leaves",
    "minecraft:birch_leaves",
    "minecraft:jungle_leaves",
    "minecraft:acacia_leaves",
    "minecraft:dark_oak_leaves",
    "minecraft:mangrove_leaves",
    "minecraft:cherry_leaves",
    "minecraft:azalea_leaves",
    "minecraft:flowering_azalea_leaves",
}

# Cross Plant blocks (rendered with X-shaped quad)
CROSS_PLANTS = {
    "minecraft:short_grass", "minecraft:tall_grass", "minecraft:fern", "minecraft:large_fern",
    "minecraft:dandelion", "minecraft:poppy", "minecraft:blue_orchid", "minecraft:allium",
    "minecraft:azure_bluet", "minecraft:red_tulip", "minecraft:orange_tulip", "minecraft:white_tulip",
    "minecraft:pink_tulip", "minecraft:oxeye_daisy", "minecraft:cornflower", "minecraft:lily_of_the_valley",
    "minecraft:wither_rose", "minecraft:sunflower", "minecraft:lilac", "minecraft:rose_bush",
    "minecraft:peony", "minecraft:dead_bush", "minecraft:sapling", "minecraft:wheat",
    "minecraft:carrots", "minecraft:potatoes", "minecraft:beetroots", "minecraft:sweet_berry_bush",
    "minecraft:nether_wart", "minecraft:crimson_roots", "minecraft:warped_roots",
}

# Biome Tint categories
BIOME_TINT_GRASS = {
    "minecraft:grass_block", "minecraft:short_grass", "minecraft:tall_grass",
    "minecraft:fern", "minecraft:large_fern", "minecraft:sugar_cane",
}
BIOME_TINT_FOLIAGE = {
    "minecraft:oak_leaves", "minecraft:jungle_leaves", "minecraft:acacia_leaves",
    "minecraft:dark_oak_leaves", "minecraft:mangrove_leaves", "minecraft:vine",
}
BIOME_TINT_WATER = {
    "minecraft:water", "minecraft:flowing_water", "minecraft:water_cauldron",
}

# Yaw rotation map (radians) for standard Minecraft facing
YAW_MAP = {
    "north": 0.0,
    "east": math.radians(-90),
    "south": math.radians(180),
    "west": math.radians(90),
    "up": 0.0,
    "down": math.radians(180),
}


class ParsedBlock:
    __slots__ = (
        'full_state', 'block_id', 'namespace', 'name', 'props',
        'block_type', 'template_name', 'rot_euler', 'offset',
        'tint_color', 'tint_data', 'is_waterlogged', 'is_opaque'
    )

    def __init__(
        self,
        full_state: str,
        block_id: str,
        namespace: str,
        name: str,
        props: dict[str, str],
        block_type: int,
        template_name: str,
        rot_euler: tuple[float, float, float],
        offset: tuple[float, float, float],
        tint_color: tuple[float, float, float, float],
        tint_data: tuple[float, float, float, float],
        is_waterlogged: bool,
        is_opaque: int = 1,
    ):
        self.full_state = full_state
        self.block_id = block_id
        self.namespace = namespace
        self.name = name
        self.props = props
        self.block_type = block_type
        self.template_name = template_name
        self.rot_euler = rot_euler
        self.offset = offset
        self.tint_color = tint_color
        self.tint_data = tint_data
        self.is_waterlogged = is_waterlogged
        self.is_opaque = is_opaque


# In-memory parsing cache to avoid re-parsing identical state strings
_STATE_PARSE_CACHE: dict[str, ParsedBlock] = {}


def parse_and_classify(state_str: str) -> ParsedBlock:
    """Parse serialized block state string into structured Geometry Nodes attributes."""
    if not state_str:
        return _make_air("")

    if state_str in _STATE_PARSE_CACHE:
        return _STATE_PARSE_CACHE[state_str]

    state_str_clean = state_str.strip()
    bracket_idx = state_str_clean.find("[")
    if bracket_idx == -1:
        block_id = state_str_clean
        props = {}
    else:
        block_id = state_str_clean[:bracket_idx]
        props_str = state_str_clean[bracket_idx + 1:].rstrip("]")
        props = {}
        if props_str:
            for pair in props_str.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    props[k.strip()] = v.strip()

    if ":" in block_id:
        namespace, name = block_id.split(":", 1)
    else:
        namespace, name = "minecraft", block_id
        block_id = f"minecraft:{name}"

    if block_id in AIR_BLOCKS:
        parsed = _make_air(state_str_clean)
        _STATE_PARSE_CACHE[state_str] = parsed
        return parsed

    # 1. Determine Biome Tint
    if block_id in BIOME_TINT_GRASS:
        tint_color = (0.35, 0.72, 0.22, 1.0)
        tint_data = (1.0, 1.0, 1.0, 0.0)
    elif block_id in BIOME_TINT_FOLIAGE:
        tint_color = (0.28, 0.65, 0.18, 1.0)
        tint_data = (1.0, 1.0, 1.0, 0.0)
    elif block_id in BIOME_TINT_WATER or "water" in block_id:
        tint_color = (0.24, 0.45, 0.85, 0.8)
        tint_data = (1.0, 1.0, 1.0, 0.0)
    else:
        tint_color = (1.0, 1.0, 1.0, 1.0)
        tint_data = (0.0, 0.0, 0.0, 0.0)

    # 2. Check Waterlogged
    is_waterlogged = props.get("waterlogged", "false") == "true"

    # 3. Determine Block Type, Rotation & Template Name
    rot_x, rot_y, rot_z = 0.0, 0.0, 0.0
    off_x, off_y, off_z = 0.0, 0.0, 0.0
    facing = props.get("facing", "north")
    axis = props.get("axis", "y")

    if "command_block" in name or name in ("piston", "sticky_piston", "piston_head"):
        # Vertical-base blocks (Base template naturally points UP at +Z in Blender)
        if facing == "up":
            rot_x, rot_y, rot_z = 0.0, 0.0, 0.0
        elif facing == "down":
            rot_x, rot_y, rot_z = math.radians(180), 0.0, 0.0
        elif facing == "north":
            rot_x, rot_y, rot_z = math.radians(90), 0.0, 0.0
        elif facing == "south":
            rot_x, rot_y, rot_z = math.radians(-90), 0.0, 0.0
        elif facing == "west":
            rot_x, rot_y, rot_z = 0.0, math.radians(-90), 0.0
        elif facing == "east":
            rot_x, rot_y, rot_z = 0.0, math.radians(90), 0.0
    elif "axis" in props:
        # Axis-aligned blocks (Logs, Pillars, Basalt, Hay, Bone)
        if axis == "x":
            rot_y = math.radians(90)
        elif axis == "z":
            rot_x = math.radians(90)
    else:
        # Standard horizontal-base blocks (Base template points NORTH at -Y in Blender)
        if facing == "north":
            rot_z = 0.0
        elif facing == "south":
            rot_z = math.radians(180)
        elif facing == "east":
            rot_z = math.radians(90)
        elif facing == "west":
            rot_z = math.radians(-90)
        elif facing == "up":
            rot_x = math.radians(-90)
        elif facing == "down":
            rot_x = math.radians(90)

    if block_id in FLUID_BLOCKS:
        block_type = BlockTypeEnum.FLUID
        template_name = "fluid_plane"

    elif block_id in CROSS_PLANTS or name.endswith("_sapling") or name.endswith("_flower"):
        block_type = BlockTypeEnum.CROSS_PLANT
        template_name = "cross_plant"

    elif name.endswith("_stairs"):
        block_type = BlockTypeEnum.STAIRS
        template_name = name
        half = props.get("half", "bottom")
        if half == "top":
            rot_x = math.radians(180)
            rot_z = -rot_z

    elif name.endswith("_slab"):
        slab_type = props.get("type", "bottom")
        if slab_type == "double":
            block_type = BlockTypeEnum.CUBE
            template_name = "cube"
        else:
            block_type = BlockTypeEnum.SLAB
            template_name = name
            if slab_type == "top":
                off_z = 0.5

    elif "torch" in name or name in ("lantern", "soul_lantern"):
        block_type = BlockTypeEnum.TORCH
        template_name = name
        if "wall" in name or facing in ("north", "south", "east", "west"):
            rot_x = math.radians(20)

    elif name.endswith(("_bed", "_door", "_trapdoor", "_fence", "_fence_gate", "_wall", "_carpet", "_chest", "_bell", "_anvil")) or name in ("chest", "trapped_chest", "ender_chest", "bell", "anvil", "bed", "carpet", "trapdoor"):
        block_type = BlockTypeEnum.PROP_TEMPLATE
        template_name = name
        if name.endswith("_bed"):
            part = props.get("part", "foot")
            template_name = f"{name}_{part}"
        elif name.endswith("_door"):
            half = props.get("half", "lower")
            template_name = f"{name}_{half}"
        elif name.endswith("_carpet"):
            off_z = -0.46875

    else:
        # Standard Cube
        block_type = BlockTypeEnum.CUBE
        template_name = "cube"

    # Determine opacity
    if block_id in TRANSPARENT_BLOCKS or name.endswith(("_glass", "_stained_glass", "_leaves", "_pane")) or name in ("glass", "tinted_glass", "ice", "water", "slime_block", "honey_block", "beacon"):
        is_opaque = 0
    else:
        is_opaque = 1

    parsed = ParsedBlock(
        full_state=state_str_clean,
        block_id=block_id,
        namespace=namespace,
        name=name,
        props=props,
        block_type=block_type,
        template_name=template_name,
        rot_euler=(rot_x, rot_y, rot_z),
        offset=(off_x, off_y, off_z),
        tint_color=tint_color,
        tint_data=tint_data,
        is_waterlogged=is_waterlogged,
        is_opaque=is_opaque,
    )
    _STATE_PARSE_CACHE[state_str] = parsed
    return parsed


def _make_air(state_str: str) -> ParsedBlock:
    return ParsedBlock(
        full_state=state_str,
        block_id="minecraft:air",
        namespace="minecraft",
        name="air",
        props={},
        block_type=BlockTypeEnum.AIR,
        template_name="air",
        rot_euler=(0.0, 0.0, 0.0),
        offset=(0.0, 0.0, 0.0),
        tint_color=(1.0, 1.0, 1.0, 1.0),
        tint_data=(0.0, 0.0, 0.0, 0.0),
        is_waterlogged=False,
        is_opaque=0,
    )

# Alias for backwards compatibility
parse_block_state = parse_and_classify
