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

    textures = mapping.get("textures", {})
    materials = mapping.get("materials", [])

    # 1. Populate from explicit 6-face material definitions
    for idx, mat_entry in enumerate(materials):
        name = mat_entry.get("name", "")
        if not name:
            continue
        mat_id = int(mat_entry.get("material_id", idx))
        material_id_map[name] = mat_id
        if ":" in name:
            material_id_map[name.split(":", 1)[1]] = mat_id

        faces_dict = mat_entry.get("faces", {})
        face_coords = []
        for face_name in FACE_ORDER:
            loc = faces_dict.get(face_name)
            if loc and isinstance(loc, dict) and "tile_column" in loc and "tile_row" in loc:
                face_coords.append((int(loc["tile_column"]), int(loc["tile_row"])))
            elif loc and isinstance(loc, dict) and "texture_id" in loc:
                # If chunk has tiles_per_row
                t_id = int(loc["texture_id"])
                tiles_per_row = int(loc.get("tiles_per_row", 64))
                face_coords.append((t_id % tiles_per_row, t_id // tiles_per_row))
            else:
                face_coords.append((0, 0))

        face_lut[name] = face_coords
        if ":" in name:
            face_lut[name.split(":", 1)[1]] = face_coords

    # 2. Populate fallback textures from textures map
    for tex_key, loc in textures.items():
        if not loc or not isinstance(loc, dict):
            continue
        col = int(loc.get("tile_column", 0))
        row = int(loc.get("tile_row", 0))
        stem = tex_key
        if ":" in stem:
            stem = stem.split(":", 1)[1]
        if stem.startswith("block/"):
            stem = stem[6:]

        if stem not in face_lut:
            face_lut[stem] = [(col, row)] * 6
            face_lut[tex_key] = [(col, row)] * 6
        if stem not in material_id_map:
            t_id = int(loc.get("texture_id", len(material_id_map)))
            material_id_map[stem] = t_id
            material_id_map[tex_key] = t_id

    return face_lut, material_id_map


def extract_atlas_parameters(mat: Optional[bpy.types.Material] = None) -> dict[str, Any]:
    """
    Extract complete Atlas parameters: width, height, tile_size, tiles_per_row, and LUTs.
    """
    if mat is None:
        mat = find_active_atlas_material()

    res = {
        "material": mat,
        "width": 1024.0,
        "height": 1024.0,
        "tile_size": 16.0,
        "tiles_per_row": 64,
        "mapping": None,
        "block_face_lut": {},
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
        if chunks:
            chunk = chunks[0]
            if "width" in chunk and "mtk_atlas_width" not in mat:
                res["width"] = float(chunk["width"])
            if "height" in chunk and "mtk_atlas_height" not in mat:
                res["height"] = float(chunk["height"])
            if "tile_size" in chunk and "mtk_tile_size" not in mat:
                res["tile_size"] = float(chunk["tile_size"])
            if "tiles_per_row" in chunk and "mtk_tiles_per_row" not in mat:
                res["tiles_per_row"] = int(chunk["tiles_per_row"])

        face_lut, mat_id_map = build_block_face_lut(mapping)
        res["block_face_lut"] = face_lut
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


def setup_material_slots_for_object(obj: bpy.types.Object, mat: bpy.types.Material):
    """Ensure object has the specified material assigned to slot 0."""
    if not obj:
        return
    if not obj.data.materials:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat
