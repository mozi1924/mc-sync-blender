"""
MoziToolKit Atlas Material integration and Shader setup for Yefira Blender Plugin.
"""

from __future__ import annotations
import json
import logging
from typing import Optional, Any
try:
    import bpy
    HAS_BPY = True
except ImportError:
    bpy = None
    HAS_BPY = False

logger = logging.getLogger("Yefira")

MASTER_MATERIAL_NAME = "Yefira_Atlas_Master"
FALLBACK_MATERIAL_NAME = "Yefira_Fallback_PBR"

# Standard 6-face cubic order
FACE_ORDER = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]


def _fallback_texture_location(mapping: dict, block_name: str) -> Optional[dict]:
    """Resolve generated-model textures that have no explicit six-face map."""
    textures = mapping.get("textures", {})
    short_name = block_name.split(":", 1)[-1]
    if short_name.startswith("block/"):
        short_name = short_name[6:]
    for key in (short_name, f"minecraft:{short_name}", f"minecraft:block/{short_name}"):
        location = textures.get(key)
        if isinstance(location, dict):
            return location
    return None


def _atlas_name_aliases(name: str) -> tuple[str, ...]:
    """Return stable mapping aliases for a Minecraft block/texture name."""
    short_name = name.split(":", 1)[-1]
    if short_name.startswith("block/"):
        short_name = short_name[6:]
    return tuple(dict.fromkeys((name, short_name, f"minecraft:{short_name}", f"minecraft:block/{short_name}")))


def _atlas_short_name(name: str) -> str:
    """Return ``grass_block_top`` for every supported resource-key spelling."""
    name = name.split(":", 1)[-1]
    return name.removeprefix("block/")


BLOCK_TO_TEXTURE_ALIASES: dict[str, list[str]] = {
    "water": ["water_still", "water_flow"],
    "lava": ["lava_still", "lava_flow"],
    "magma_block": ["magma"],
    "fire": ["fire_0", "fire_1"],
    "soul_fire": ["soul_fire_0", "soul_fire_1"],
    "campfire": ["campfire_fire", "campfire_log"],
    "soul_campfire": ["soul_campfire_fire", "soul_campfire_log"],
    "portal": ["nether_portal"],
    "nether_portal": ["nether_portal"],
    "kelp": ["kelp", "kelp_plant"],
    "kelp_plant": ["kelp_plant", "kelp"],
    "sea_pickle": ["sea_pickle"],
    "sea_lantern": ["sea_lantern"],
    "prismarine": ["prismarine"],
    "prismarine_bricks": ["prismarine_bricks"],
    "dark_prismarine": ["dark_prismarine"],
    "lantern": ["lantern"],
    "soul_lantern": ["soul_lantern"],
    "sculk_sensor": ["sculk_sensor_top", "sculk_sensor_side", "sculk_sensor_bottom"],
    "sculk_catalyst": ["sculk_catalyst_top", "sculk_catalyst_side", "sculk_catalyst_bottom"],
    "sculk_shrieker": ["sculk_shrieker_top", "sculk_shrieker_side", "sculk_shrieker_bottom"],
    "respawn_anchor": ["respawn_anchor_top_off", "respawn_anchor_side0", "respawn_anchor_bottom"],
    "smoker": ["smoker_front", "smoker_side", "smoker_top", "smoker_bottom"],
    "furnace": ["furnace_front", "furnace_side", "furnace_top", "furnace_bottom"],
    "blast_furnace": ["blast_furnace_front", "blast_furnace_side", "blast_furnace_top", "blast_furnace_bottom"],
}


def _build_block_face_location_lut(mapping: Optional[dict]) -> tuple[dict[str, list[dict]], dict[str, int]]:
    """Build point-cloud face locations from atlas data, not material names.

    Normal meshes preserve a source texture per polygon.  Yefira instead has
    a Minecraft block state at each point, so a texture-only pack needs a
    small, deterministic bridge from common ``*_side/top/bottom/end`` texture
    sets to the logical block name.  Explicit six-face mappings always win.
    """
    locations_by_name: dict[str, list[dict]] = {}
    material_ids: dict[str, int] = {}
    if not mapping:
        return locations_by_name, material_ids

    textures = mapping.get("textures", {})
    texture_by_stem: dict[str, dict] = {}
    for texture_key, location in textures.items():
        if not isinstance(location, dict):
            continue
        for alias in _atlas_name_aliases(texture_key):
            texture_by_stem.setdefault(_atlas_short_name(alias), location)

    def add(name: str, face_locations: list[dict], material_id: int) -> None:
        for alias in _atlas_name_aliases(name):
            locations_by_name[alias] = face_locations
            material_ids[alias] = material_id

    # First consume the authoritative material mapping.  A real model can
    # encode arbitrary face layouts that texture-name conventions cannot.
    for index, material in enumerate(mapping.get("materials", [])):
        name = material.get("name", "")
        if not name:
            continue
        fallback = _fallback_texture_location(mapping, name) or {}
        faces = material.get("faces", {})
        face_locations = [faces.get(face_name) or fallback for face_name in FACE_ORDER]
        add(name, face_locations, int(material.get("material_id", index)))

    # Direct texture entries represent an all-face block unless a material
    # mapping already supplied a more precise answer.
    for texture_key, location in textures.items():
        if not isinstance(location, dict):
            continue
        stem = _atlas_short_name(texture_key)
        if stem not in locations_by_name:
            add(stem, [location] * 6, int(location.get("texture_id", 0)))

    # Block name to texture aliases (e.g. water -> water_still, lava -> lava_still, magma_block -> magma)
    for block_name, target_stems in BLOCK_TO_TEXTURE_ALIASES.items():
        if block_name in locations_by_name:
            continue
        found_loc = next((texture_by_stem.get(s) for s in target_stems if texture_by_stem.get(s)), None)
        if found_loc:
            # Check for side/top/bottom differentiation among stems
            top_loc = next((texture_by_stem.get(s) for s in target_stems if s.endswith(("_top", "_top_off"))), found_loc)
            bottom_loc = next((texture_by_stem.get(s) for s in target_stems if s.endswith("_bottom")), found_loc)
            front_loc = next((texture_by_stem.get(s) for s in target_stems if s.endswith(("_front", "_front_on"))), found_loc)
            side_loc = next((texture_by_stem.get(s) for s in target_stems if s.endswith(("_side", "_side0"))), found_loc)
            face_locations = [side_loc, side_loc, top_loc, bottom_loc, front_loc, side_loc]
            add(block_name, face_locations, int(found_loc.get("texture_id", 0)))

    # Texture-only PBR packs expose components such as grass_block_top and
    # oak_log_top but not a logical grass_block/oak_log material entry.  Build
    # a face map from those components.  This intentionally replaces a
    # uniform fallback but never an already differentiated six-face mapping.
    base_names = set(texture_by_stem)
    for stem in tuple(texture_by_stem):
        for suffix in ("_side", "_top", "_bottom", "_end"):
            if stem.endswith(suffix):
                base_names.add(stem[:-len(suffix)])

    for base_name in base_names:
        base = texture_by_stem.get(base_name)
        side = texture_by_stem.get(f"{base_name}_side") or base
        top = texture_by_stem.get(f"{base_name}_top") or texture_by_stem.get(f"{base_name}_end") or side
        bottom = texture_by_stem.get(f"{base_name}_bottom") or texture_by_stem.get(f"{base_name}_end") or top
        if not side or not top or not bottom:
            continue
        if base_name == "grass_block":
            bottom = texture_by_stem.get("dirt") or bottom
        face_locations = [side, side, top, bottom, side, side]
        existing = locations_by_name.get(base_name)
        has_differentiated_faces = existing and len({loc.get("texture_key") for loc in existing if loc}) > 1
        has_named_variants = any(texture_by_stem.get(f"{base_name}{suffix}") for suffix in ("_side", "_top", "_bottom", "_end"))
        if has_named_variants and not has_differentiated_faces:
            add(base_name, face_locations, material_ids.get(base_name, int(side.get("texture_id", 0))))

    return locations_by_name, material_ids


def find_active_atlas_material() -> Optional[bpy.types.Material]:
    """Find the best active Atlas material in Blender scene."""
    if not HAS_BPY:
        return None

    # 1. First priority: MoziToolKit Atlas chunk materials (e.g. mtk:minecraft:atlas_chunk_000...)
    for mat in bpy.data.materials:
        if not mat:
            continue
        if "mtk:atlas_chunk_id" in mat or "mtk_atlas_chunk_id" in mat or (mat.name.startswith("mtk:") and "atlas_chunk" in mat.name):
            return mat

    # 2. Second priority: Materials with explicit atlas width/mapping properties
    for mat in bpy.data.materials:
        if not mat:
            continue
        if "mtk_atlas_width" in mat or "mtk:atlas_mapping" in mat or "mtk_atlas_mapping" in mat:
            return mat
        if mat.node_tree and ("mtk:atlas_mapping" in mat.node_tree or "mtk_atlas_mapping" in mat.node_tree):
            return mat

    # 3. Explicit named master materials
    for name in ("MTK_Atlas_Master", "MC_Atlas_Material"):
        if name in bpy.data.materials:
            return bpy.data.materials[name]

    # 4. Fallback to Yefira_Atlas_Master
    if MASTER_MATERIAL_NAME in bpy.data.materials:
        return bpy.data.materials[MASTER_MATERIAL_NAME]

    return None


def find_bound_atlas_material(obj: Optional[bpy.types.Object]) -> Optional[bpy.types.Material]:
    """Return the Atlas material deliberately assigned to a Yefira object.

    ``bpy.data.materials`` is global and iteration order is not a material
    selection policy.  Looking there during every live update could replace a
    freshly applied MoziToolKit atlas with an unrelated chunk from another
    scene/object.  Slot zero is the primary chunk and the authoritative
    source for this world object's dimensions.
    """
    if not obj or not getattr(obj, "data", None):
        return None
    for mat in obj.data.materials:
        if not mat:
            continue
        if (
            "mtk:atlas_mapping" in mat
            or "mtk_atlas_mapping" in mat
            or "mtk:atlas_chunk_id" in mat
            or "mtk_atlas_chunk_id" in mat
        ):
            return mat
    return None


def parse_atlas_mapping(mat: Optional[bpy.types.Material]) -> Optional[dict]:
    """Extract and parse atlas mapping JSON from a material or its node tree."""
    if not mat:
        return None
    raw = None
    for key in ("mtk_atlas_mapping", "mtk:atlas_mapping"):
        if key in mat:
            raw = mat[key]
            break
        if mat.node_tree and key in mat.node_tree:
            raw = mat.node_tree[key]
            break

    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Failed to parse atlas mapping JSON: {e}")
        return None


def build_block_face_lut(mapping: Optional[dict]) -> tuple[dict[str, list[tuple[int, int]]], dict[str, int]]:
    """
    Build lookup table for block stem -> 6 face tile (col, row) coordinates,
    and block stem -> material_id integer mapping.
    Face order: 0: +X, 1: -X, 2: +Y (Top), 3: -Y (Bottom), 4: +Z (South), 5: -Z (North).
    """
    face_lut: dict[str, list[tuple[int, int]]] = {}
    material_id_map: dict[str, int] = {}

    if not mapping:
        return face_lut, material_id_map

    locations_by_name, material_ids = _build_block_face_location_lut(mapping)
    for name, locations in locations_by_name.items():
        coords = []
        for location in locations:
            if location and location.get("kind") == "animation":
                px = int(location.get("pixel_x", 0))
                fw = max(1, int(location.get("frame_width", 16)))
                coords.append((px // fw, 0))
            elif location:
                coords.append((int(location.get("tile_column", 0)), int(location.get("tile_row", 0))))
            else:
                coords.append((0, 0))
        face_lut[name] = coords
    material_id_map.update(material_ids)

    return face_lut, material_id_map


def build_block_face_atlas_ids(mapping: Optional[dict]) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    """Return per-face atlas chunk and texture IDs using MoziToolKit's mapping.

    A tile coordinate is only meaningful within one atlas chunk.  Keeping the
    two IDs alongside the tile LUT lets Geometry Nodes choose the right
    material after it realizes a cube face.
    """
    chunk_lut: dict[str, list[int]] = {}
    texture_lut: dict[str, list[int]] = {}
    if not mapping:
        return chunk_lut, texture_lut

    locations_by_name, _ = _build_block_face_location_lut(mapping)
    for name, locations in locations_by_name.items():
        chunk_lut[name] = [int(location.get("chunk_id", 0)) if location else 0 for location in locations]
        texture_lut[name] = [int(location.get("texture_id", 0)) if location else 0 for location in locations]

    return chunk_lut, texture_lut


def build_block_face_tint_lut(mapping: Optional[dict]) -> dict[str, list[tuple[float, float, float, float]]]:
    """Build face-domain biome-tint weights from Mozi's atlas metadata."""
    tint_lut: dict[str, list[tuple[float, float, float, float]]] = {}
    if not mapping:
        return tint_lut

    locations_by_name, _ = _build_block_face_location_lut(mapping)
    for name, locations in locations_by_name.items():
        tint_lut[name] = [
            (
                float(location.get("default_base_tint_weight", 0.0)),
                float(location.get("default_overlay_tint_weight", 0.0)),
                float(location.get("default_tint_weight", 0.0)),
                1.0 if location.get("is_hardcoded", False) else 0.0,
            )
            if location else (0.0, 0.0, 0.0, 0.0)
            for location in locations
        ]

    return tint_lut


def build_block_face_anim_lut(
    mapping: Optional[dict],
) -> tuple[dict[str, list[tuple[float, float, float, float]]], dict[str, list[tuple[float, float, float, float]]]]:
    """Build per-face animation timing (frame_count, frametime, interpolate, 0) and frame_size LUTs."""
    timing_lut: dict[str, list[tuple[float, float, float, float]]] = {}
    frame_size_lut: dict[str, list[tuple[float, float, float, float]]] = {}
    if not mapping:
        return timing_lut, frame_size_lut

    locations_by_name, _ = _build_block_face_location_lut(mapping)
    for name, locations in locations_by_name.items():
        timing_lut[name] = [
            (
                float(loc.get("frame_count", 1)),
                float(loc.get("frametime", 1)),
                1.0 if loc.get("interpolate", False) else 0.0,
                0.0,
            )
            if loc else (1.0, 1.0, 0.0, 0.0)
            for loc in locations
        ]
        frame_size_lut[name] = [
            (
                float(loc.get("frame_width", loc.get("tile_size", 16))),
                float(loc.get("frame_height", loc.get("tile_size", 16))),
                0.0,
                0.0,
            )
            if loc else (16.0, 16.0, 0.0, 0.0)
            for loc in locations
        ]

    return timing_lut, frame_size_lut


def extract_atlas_parameters(mat: Optional[bpy.types.Material] = None) -> dict[str, Any]:
    """
    Extract complete Atlas parameters: width, height, tile_size, tiles_per_row, chunk dimensions and LUTs.
    """
    if mat is None:
        mat = find_active_atlas_material()

    res = {
        "material": mat,
        "width": 1024.0,
        "height": 1024.0,
        "tile_size": 16.0,
        "tiles_per_row": 64,
        "chunk_0_width": 4096.0,
        "chunk_0_height": 80.0,
        "chunk_0_tile_size": 16.0,
        "chunk_0_tiles_per_row": 256.0,
        "chunk_1_width": 896.0,
        "chunk_1_height": 1024.0,
        "chunk_1_tile_size": 16.0,
        "mapping": None,
        "block_face_lut": {},
        "block_face_chunk_lut": {},
        "block_face_texture_lut": {},
        "block_face_tint_lut": {},
        "block_face_anim_timing_lut": {},
        "block_face_anim_frame_size_lut": {},
        "material_id_map": {},
    }

    if not mat:
        return res

    mapping = parse_atlas_mapping(mat)
    res["mapping"] = mapping

    if "mtk_atlas_width" in mat:
        res["width"] = float(mat["mtk_atlas_width"])
    if "mtk_atlas_height" in mat:
        res["height"] = float(mat["mtk_atlas_height"])
    if "mtk_tile_size" in mat:
        res["tile_size"] = float(mat["mtk_tile_size"])
    if "mtk_tiles_per_row" in mat:
        res["tiles_per_row"] = int(mat["mtk_tiles_per_row"])

    if mapping:
        if "tile_size" in mapping and "mtk_tile_size" not in mat:
            res["tile_size"] = float(mapping["tile_size"])
        chunks = mapping.get("chunks", [])
        chunks_by_id = {c.get("chunk_id", i): c for i, c in enumerate(chunks)}

        if 0 in chunks_by_id:
            c0 = chunks_by_id[0]
            res["chunk_0_width"] = float(c0.get("width", res["width"]))
            res["chunk_0_height"] = float(c0.get("height", res["height"]))
            res["chunk_0_tile_size"] = float(c0.get("tile_size", res["tile_size"]))
            res["chunk_0_tiles_per_row"] = float(c0.get("tiles_per_row", res["tiles_per_row"]))
            res["width"] = res["chunk_0_width"]
            res["height"] = res["chunk_0_height"]
            res["tile_size"] = res["chunk_0_tile_size"]
            res["tiles_per_row"] = int(res["chunk_0_tiles_per_row"])

        if 1 in chunks_by_id:
            c1 = chunks_by_id[1]
            res["chunk_1_width"] = float(c1.get("width", 896.0))
            res["chunk_1_height"] = float(c1.get("height", 1024.0))
            res["chunk_1_tile_size"] = float(c1.get("tile_size", 16.0))

        face_lut, mat_id_map = build_block_face_lut(mapping)
        face_chunk_lut, face_texture_lut = build_block_face_atlas_ids(mapping)
        face_tint_lut = build_block_face_tint_lut(mapping)
        anim_timing_lut, anim_frame_size_lut = build_block_face_anim_lut(mapping)

        res["block_face_lut"] = face_lut
        res["block_face_chunk_lut"] = face_chunk_lut
        res["block_face_texture_lut"] = face_texture_lut
        res["block_face_tint_lut"] = face_tint_lut
        res["block_face_anim_timing_lut"] = anim_timing_lut
        res["block_face_anim_frame_size_lut"] = anim_frame_size_lut
        res["material_id_map"] = mat_id_map

    return res


def get_or_create_atlas_material() -> Optional[bpy.types.Material]:
    """
    Get existing active Atlas Master Material or create a unified Yefira Atlas Master.
    """
    if not HAS_BPY:
        return None

    active = find_active_atlas_material()
    if active:
        return active

    if MASTER_MATERIAL_NAME in bpy.data.materials:
        return bpy.data.materials[MASTER_MATERIAL_NAME]

    # Build default unified Atlas Master material
    mat = bpy.data.materials.new(name=MASTER_MATERIAL_NAME)
    mat.use_nodes = True
    mat["mtk_atlas_width"] = 1024.0
    mat["mtk_atlas_height"] = 1024.0
    mat["mtk_tile_size"] = 16.0
    mat["mtk_tiles_per_row"] = 64

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Output Node
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (600, 0)

    # Principled BSDF
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (300, 0)
    links.new(bsdf.outputs['BSDF'], output_node.inputs['Surface'])

    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = 0.8

    # Shared Texture Coordinate Node
    tex_coord = nodes.new(type='ShaderNodeTexCoord')
    tex_coord.location = (-600, 100)

    # Albedo Image Texture Node
    tex_image = nodes.new(type='ShaderNodeTexImage')
    tex_image.name = "Atlas Albedo"
    tex_image.interpolation = "Closest"
    tex_image.extension = "CLIP"
    tex_image.location = (-350, 200)
    links.new(tex_coord.outputs['UV'], tex_image.inputs['Vector'])

    # Auto-bind existing atlas image from blender data if available
    atlas_img = None
    for img in bpy.data.images:
        if "atlas_chunk" in img.name and "albedo" in img.name:
            atlas_img = img
            break
        elif "atlas_albedo" in img.name:
            atlas_img = img
            break
    if atlas_img:
        tex_image.image = atlas_img

    # Attribute Node: Biome Tint Color
    attr_tint = nodes.new(type='ShaderNodeAttribute')
    attr_tint.name = "Attr Biome Tint Color"
    attr_tint.attribute_name = "mtk_biome_tint_color"
    attr_tint.location = (-350, -50)

    # Attribute Node: Biome Tint Data
    attr_data = nodes.new(type='ShaderNodeAttribute')
    attr_data.name = "Attr Biome Tint Data"
    attr_data.attribute_name = "mtk_biome_tint_data"
    attr_data.location = (-350, -250)

    # Mix Color Node (Multiply Tint with Base)
    mix_node = nodes.new(type='ShaderNodeMix')
    mix_node.data_type = 'RGBA'
    mix_node.blend_type = 'MULTIPLY'
    mix_node.inputs[0].default_value = 1.0  # Factor
    mix_node.location = (-50, 100)

    links.new(tex_image.outputs['Color'], mix_node.inputs[6]) # Color A
    links.new(attr_tint.outputs['Color'], mix_node.inputs[7]) # Color B

    links.new(mix_node.outputs[2], bsdf.inputs['Base Color'])
    links.new(tex_image.outputs['Alpha'], bsdf.inputs['Alpha'])

    return mat


def find_all_atlas_chunk_materials(mapping: Optional[dict] = None) -> dict[int, bpy.types.Material]:
    """Find all Atlas chunk materials in Blender data, keyed by chunk_id."""
    if not HAS_BPY:
        return {}

    chunk_materials: dict[int, bpy.types.Material] = {}

    # Sort materials to prefer ones specialized with :attr:UVMap or :attr:
    mats_sorted = sorted(
        [m for m in bpy.data.materials if m],
        key=lambda m: (
            0 if ":attr:UVMap" in m.name else (1 if ":attr:" in m.name else 2)
        )
    )

    # 1. First priority: Match materials by explicit custom property mtk:atlas_chunk_id
    for mat in mats_sorted:
        for key in ("mtk:atlas_chunk_id", "mtk_atlas_chunk_id"):
            if key in mat:
                try:
                    cid = int(mat[key])
                    if cid not in chunk_materials:
                        chunk_materials[cid] = mat
                    break
                except (ValueError, TypeError):
                    pass

    # 2. Second priority: Match materials by naming pattern (e.g., mtk:minecraft:atlas_chunk_000...)
    for mat in mats_sorted:
        if "atlas_chunk_" in mat.name:
            import re
            m = re.search(r"atlas_chunk_(\d+)", mat.name)
            if m:
                cid = int(m.group(1))
                if cid not in chunk_materials:
                    chunk_materials[cid] = mat

    # 3. Check mapping chunks metadata
    if mapping and "chunks" in mapping:
        for chunk in mapping["chunks"]:
            cid = int(chunk.get("chunk_id", 0))
            if cid not in chunk_materials:
                if cid == 0:
                    active = find_active_atlas_material()
                    if active:
                        chunk_materials[0] = active

    if not chunk_materials:
        active = find_active_atlas_material() or get_or_create_atlas_material()
        if active:
            chunk_materials[0] = active

    return chunk_materials


def setup_material_slots_for_object(
    obj: bpy.types.Object,
    mat: Optional[bpy.types.Material] = None,
    mapping: Optional[dict] = None,
):
    """Ensure object has all chunk materials assigned to slots 0..N in order.

    Slot index directly corresponds to mtk_atlas_chunk_id, enabling Geometry Nodes
    to use Set Material Index without overwriting via a single Set Material node.
    """
    if not obj or not getattr(obj, "data", None) or not HAS_BPY:
        return

    if mat is None:
        mat = find_bound_atlas_material(obj) or find_active_atlas_material() or get_or_create_atlas_material()

    if mapping is None and mat:
        mapping = parse_atlas_mapping(mat)

    chunk_materials = find_all_atlas_chunk_materials(mapping)
    if not chunk_materials and mat:
        chunk_materials[0] = mat

    max_chunk_id = max(chunk_materials.keys()) if chunk_materials else 0
    needed_slots = max(1, max_chunk_id + 1)

    while len(obj.data.materials) < needed_slots:
        obj.data.materials.append(None)

    for cid in range(needed_slots):
        target_mat = chunk_materials.get(cid) or mat
        obj.data.materials[cid] = target_mat
