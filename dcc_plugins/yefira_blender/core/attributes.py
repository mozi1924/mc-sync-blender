"""The Blender attribute contract owned by Yefira.

Yefira and MoziToolKit are separate add-ons.  Names beginning with ``mtk_``
are therefore an explicit, versioned interchange contract; every other name
in this module is private to Yefira and begins with ``yefira_``.  Do not add
attribute literals to node builders or mesh writers: add them here first.
"""

from __future__ import annotations

from typing import Final


CONTRACT_VERSION: Final = 4
FACES: Final = ("east", "west", "top", "bottom", "south", "north")

# Yefira-private point-cloud and procedural-template fields.
BLOCK_TYPE: Final = "yefira_block_type"
TEMPLATE_INDEX: Final = "yefira_template_index"
INSTANCE_ROTATION: Final = "yefira_instance_rotation"
BLOCK_CENTER: Final = "yefira_block_center"
MC_POSITION: Final = "yefira_mc_position"
BLOCK_STATE: Final = "yefira_block_state"
BLOCK_KEY: Final = "yefira_block_key"
CUBE_FACE_NORMAL: Final = "yefira_cube_face_normal"
LOCAL_FACE_ID: Final = "yefira_local_face_id"
LOCAL_UV: Final = "yefira_local_uv"
# Per-point opt-in for the vanilla command-block top/bottom V correction.
DIRECTIONAL_FACE_V_FLIP: Final = "yefira_directional_face_v_flip"

# Stable MoziToolKit interchange fields.  These names intentionally remain
# unchanged so either add-on can update or consume a point cloud independently.
MTK_MATERIAL_ID: Final = "mtk_material_id"
MTK_IS_OPAQUE: Final = "mtk_is_opaque"
MTK_EMISSIVE: Final = "mtk_emissive"
MTK_ATLAS_WIDTH: Final = "mtk_atlas_width"
MTK_ATLAS_HEIGHT: Final = "mtk_atlas_height"
MTK_TILE_SIZE: Final = "mtk_tile_size"
MTK_TILES_PER_ROW: Final = "mtk_tiles_per_row"
MTK_ANIM_ATLAS_WIDTH: Final = "mtk_anim_atlas_width"
MTK_ANIM_ATLAS_HEIGHT: Final = "mtk_anim_atlas_height"
MTK_ANIM_FRAME_WIDTH: Final = "mtk_anim_frame_width"
MTK_ANIM_FRAME_HEIGHT: Final = "mtk_anim_frame_height"
MTK_BIOME_TINT_COLOR: Final = "mtk_biome_tint_color"
MTK_BIOME_TINT_DATA: Final = "mtk_biome_tint_data"
MTK_UV_TILING_TRANSFORM: Final = "mtk_uv_tiling_transform"
MTK_UV_ROTATION: Final = "mtk_uv_rotation"
MTK_ATLAS_CHUNK_ID: Final = "mtk_atlas_chunk_id"
MTK_ATLAS_TEXTURE_ID: Final = "mtk_atlas_texture_id"
MTK_ANIM_TIMING: Final = "mtk_anim_timing"
MTK_ANIM_FRAME_SIZE: Final = "mtk_anim_frame_size"
UV_MAP: Final = "UVMap"  # Blender's conventional, material-facing UV name.


def face_attribute(kind: str, face: str) -> str:
    """Return a validated MTK per-face interchange attribute name."""
    if face not in FACES:
        raise ValueError(f"Unknown cube face: {face}")
    return f"mtk_{kind}_{face}"


FACE_TILE_ATTRIBUTES: Final = tuple(face_attribute("tile", face) for face in FACES)
FACE_CHUNK_ATTRIBUTES: Final = tuple(face_attribute("chunk", face) for face in FACES)
FACE_TEXTURE_ATTRIBUTES: Final = tuple(face_attribute("texture", face) for face in FACES)
FACE_TINT_ATTRIBUTES: Final = tuple(face_attribute("tint_data", face) for face in FACES)
FACE_ANIM_TIMING_ATTRIBUTES: Final = tuple(face_attribute("anim_timing", face) for face in FACES)
FACE_ANIM_FRAME_SIZE_ATTRIBUTES: Final = tuple(face_attribute("anim_frame_size", face) for face in FACES)
FACE_UV_ROT_ATTRIBUTES: Final = tuple(face_attribute("uv_rot", face) for face in FACES)
FACE_UV_BOUNDS_ATTRIBUTES: Final = tuple(face_attribute("uv_bounds", face) for face in FACES)

ATLAS_FLOAT_ATTRIBUTES: Final = (
    MTK_ATLAS_WIDTH, MTK_ATLAS_HEIGHT, MTK_TILE_SIZE, MTK_TILES_PER_ROW,
    MTK_ANIM_ATLAS_WIDTH, MTK_ANIM_ATLAS_HEIGHT,
    MTK_ANIM_FRAME_WIDTH, MTK_ANIM_FRAME_HEIGHT,
)

# Attributes authored on the source point cloud.  Rebuilds remove this exact
# set before writing, which prevents stale schema fields from surviving an
# empty update or a contract migration.
POINT_ATTRIBUTE_NAMES: Final = frozenset((
    BLOCK_TYPE, TEMPLATE_INDEX, INSTANCE_ROTATION, BLOCK_CENTER, MC_POSITION,
    DIRECTIONAL_FACE_V_FLIP,
    BLOCK_STATE, BLOCK_KEY, MTK_MATERIAL_ID, MTK_IS_OPAQUE, MTK_EMISSIVE,
    *ATLAS_FLOAT_ATTRIBUTES, *FACE_TILE_ATTRIBUTES, *FACE_CHUNK_ATTRIBUTES,
    *FACE_TEXTURE_ATTRIBUTES, *FACE_TINT_ATTRIBUTES,
    *FACE_ANIM_TIMING_ATTRIBUTES, *FACE_ANIM_FRAME_SIZE_ATTRIBUTES,
    *FACE_UV_ROT_ATTRIBUTES, *FACE_UV_BOUNDS_ATTRIBUTES,
    MTK_BIOME_TINT_COLOR, MTK_BIOME_TINT_DATA,
))

# Names emitted by pre-contract Yefira builds.  They are removed rather than
# aliased: aliases would keep duplicate fields and obscure the ownership model.
LEGACY_POINT_ATTRIBUTE_NAMES: Final = frozenset((
    "block_type", "instance_index", "instance_rotation", "instance_offset",
    "block_center", "mc_pos", "block_state", "mc_block_key", "is_opaque",
    "mtk_uv_tiling_transform", "mtk_uv_rotation", "mtk_is_opaque",
))

LEGACY_TEMPLATE_ATTRIBUTE_NAMES: Final = frozenset((
    "CubeFaceNorm", "LocalFaceID", "LocalUV",
))

INSTANCE_TRANSFER_SPECS: Final = (
    *((name, "INT") for name in (BLOCK_TYPE, DIRECTIONAL_FACE_V_FLIP,
                                  MTK_MATERIAL_ID, MTK_IS_OPAQUE,
                                  *FACE_CHUNK_ATTRIBUTES, *FACE_TEXTURE_ATTRIBUTES)),
    *((name, "FLOAT_VECTOR") for name in (BLOCK_CENTER, *FACE_TILE_ATTRIBUTES)),
    *((name, "FLOAT") for name in (*ATLAS_FLOAT_ATTRIBUTES, *FACE_UV_ROT_ATTRIBUTES)),
    *((name, "FLOAT_COLOR") for name in (*FACE_TINT_ATTRIBUTES, *FACE_ANIM_TIMING_ATTRIBUTES,
                                         *FACE_ANIM_FRAME_SIZE_ATTRIBUTES, *FACE_UV_BOUNDS_ATTRIBUTES)),
)


def clear_point_attributes(mesh) -> None:
    """Delete source-point fields from a previous Yefira schema revision."""
    for name in POINT_ATTRIBUTE_NAMES | LEGACY_POINT_ATTRIBUTE_NAMES:
        attr = mesh.attributes.get(name)
        if attr is not None:
            mesh.attributes.remove(attr)
