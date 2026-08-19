"""Transfers Point Cloud render attributes to the Instance domain for instances."""

from __future__ import annotations

import bpy
from ..core import ensure_gn_group, ensure_socket, finalize_group

GROUP_NAME_INSTANCE_ATTRIBUTES = "Yefira_Transfer_Instance_Attributes"
INSTANCE_ATTRIBUTES_VERSION = 4

FACE_NAMES = ("top", "bottom", "east", "west", "south", "north")
FACE_TILE_ATTRIBUTES = tuple(f"mtk_tile_{face}" for face in FACE_NAMES)
FACE_INT_ATTRIBUTES = tuple(
    f"mtk_{kind}_{face}"
    for kind in ("chunk", "texture")
    for face in FACE_NAMES
)
INSTANCE_INT_ATTRIBUTES = (
    "block_type",
    "mtk_material_id",
    "is_opaque",
    "mtk_is_opaque",
    *FACE_INT_ATTRIBUTES,
)
ATLAS_FLOAT_ATTRIBUTES = (
    "mtk_atlas_width",
    "mtk_atlas_height",
    "mtk_tile_size",
    "mtk_tiles_per_row",
    "mtk_anim_atlas_width",
    "mtk_anim_atlas_height",
    "mtk_anim_frame_width",
    "mtk_anim_frame_height",
)
FACE_TINT_ATTRIBUTES = tuple(f"mtk_tint_data_{face}" for face in FACE_NAMES)
FACE_ANIM_ATTRIBUTES = tuple(
    f"mtk_anim_{kind}_{face}"
    for kind in ("timing", "frame_size")
    for face in FACE_NAMES
)


def get_or_create_instance_attribute_transfer_group() -> bpy.types.GeometryNodeTree:
    """
    Copy all point-cloud rendering fields to the instance domain once.
    Both cube and collection-instance branches use this exact same contract,
    ensuring that instances carry full Minecraft metadata through realization.
    """
    tree, needs_build = ensure_gn_group(GROUP_NAME_INSTANCE_ATTRIBUTES, INSTANCE_ATTRIBUTES_VERSION)
    if not needs_build:
        return tree

    ensure_socket(tree, "Geometry", "INPUT", "NodeSocketGeometry")
    ensure_socket(tree, "Geometry", "OUTPUT", "NodeSocketGeometry")

    nodes, links = tree.nodes, tree.links
    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-150, 0)
    last_geometry = group_in.outputs["Geometry"]

    specs = (
        *((name, "INT") for name in INSTANCE_INT_ATTRIBUTES),
        *((name, "FLOAT_VECTOR") for name in FACE_TILE_ATTRIBUTES),
        *((name, "FLOAT") for name in ATLAS_FLOAT_ATTRIBUTES),
        *((name, "FLOAT_COLOR") for name in FACE_TINT_ATTRIBUTES),
        *((name, "FLOAT_COLOR") for name in FACE_ANIM_ATTRIBUTES),
    )

    col_width = 160
    for index, (attribute, data_type) in enumerate(specs):
        x_pos = 100 + index * col_width

        reader = nodes.new("GeometryNodeInputNamedAttribute")
        reader.data_type = data_type
        reader.inputs["Name"].default_value = attribute
        reader.location = (x_pos, 220)

        store = nodes.new("GeometryNodeStoreNamedAttribute")
        store.data_type = data_type
        store.domain = "INSTANCE"
        store.inputs["Name"].default_value = attribute
        store.location = (x_pos, 0)

        links.new(last_geometry, store.inputs["Geometry"])
        links.new(reader.outputs["Attribute"], store.inputs["Value"])
        last_geometry = store.outputs["Geometry"]

    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (100 + len(specs) * col_width + 80, 0)
    links.new(last_geometry, group_out.inputs["Geometry"])

    tree["yefira_role"] = "instance_attribute_transfer"
    return finalize_group(tree)
