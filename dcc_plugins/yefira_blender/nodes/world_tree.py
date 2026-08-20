"""Geometry Nodes World Tree Orchestrator for Yefira Blender Plugin.

Assembles reusable Geometry Node Groups into a high-performance procedural Minecraft world
evaluating on Point Cloud objects.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
import bpy

from ..core.template_catalog import (
    get_or_create_template_collection,
    TEMPLATE_COLLECTION_NAME,
)
from ..materials.atlas_integration import (
    extract_atlas_parameters,
    find_bound_atlas_material,
    find_all_atlas_chunk_materials,
    get_or_create_atlas_material,
    setup_material_slots_for_object,
)
from ..core.attributes import (
    BLOCK_CENTER, BLOCK_TYPE, INSTANCE_ROTATION, LOCAL_FACE_ID, LOCAL_UV,
    MTK_ANIM_ATLAS_HEIGHT, MTK_ANIM_ATLAS_WIDTH, MTK_ANIM_FRAME_HEIGHT,
    MTK_ANIM_FRAME_SIZE, MTK_ANIM_FRAME_WIDTH, MTK_ANIM_TIMING,
    MTK_ATLAS_CHUNK_ID, MTK_ATLAS_HEIGHT,
    MTK_ATLAS_TEXTURE_ID, MTK_BIOME_TINT_DATA, MTK_TILE_SIZE,
    MTK_TILES_PER_ROW, MTK_UV_ROTATION, MTK_UV_TILING_TRANSFORM,
    TEMPLATE_INDEX, UV_MAP, face_attribute,
)
from .core import ensure_socket, prune_unlinked_nodes
from .groups import (
    get_or_create_atlas_uv_calculator_group,
    get_or_create_cube_surface_group,
    get_or_create_face_selector_color_group,
    get_or_create_face_selector_int_group,
    get_or_create_face_selector_vector_group,
    get_or_create_instance_attribute_transfer_group,
    get_or_create_material_dispatcher_group,
    get_or_create_culling_merge_group,
)

logger = logging.getLogger("Yefira")

WORLD_TREE_NAME = "Yefira_WorldTree"
WORLD_MODIFIER_NAME = "Yefira_WorldModifier"
# Schema version 19: central attribute contract and Yefira-private face fields.
WORLD_TREE_SCHEMA_VERSION = 19
WORLD_TREE_SCHEMA_PROPERTY = "yefira:world_tree_schema"


def setup_world_geometry_nodes(
    world_obj: bpy.types.Object,
    template_col: Optional[bpy.types.Collection] = None,
) -> Optional[bpy.types.Modifier]:
    """
    Attach and configure the unified Geometry Nodes tree on the Yefira_World point cloud.
    Handles Cube instancing, Collection Info prop instancing, rotation, and multi-chunk Material binding.
    """
    if not world_obj:
        return None

    if not template_col:
        template_col = get_or_create_template_collection(bpy.context)

    # Resolve bound Atlas material and mapping
    mat = find_bound_atlas_material(world_obj) or get_or_create_atlas_material()
    atlas_params = extract_atlas_parameters(mat)

    # Populate all material slots on world_obj in chunk_id order (Slot 0 -> Chunk 0, Slot 1 -> Chunk 1...)
    setup_material_slots_for_object(world_obj, mat, atlas_params.get("mapping"))

    # Resolve all chunk materials and construct/update independent Material Dispatcher group
    chunk_mats = find_all_atlas_chunk_materials(atlas_params.get("mapping"))
    if not chunk_mats:
        fallback_mat = find_bound_atlas_material(None) or get_or_create_atlas_material()
        if fallback_mat:
            chunk_mats = {0: fallback_mat}

    group_mat_dispatcher = get_or_create_material_dispatcher_group(chunk_mats)

    mod = world_obj.modifiers.get(WORLD_MODIFIER_NAME)
    if not mod:
        mod = world_obj.modifiers.new(name=WORLD_MODIFIER_NAME, type="NODES")

    gn_tree = bpy.data.node_groups.get(WORLD_TREE_NAME)
    if gn_tree and gn_tree.get(WORLD_TREE_SCHEMA_PROPERTY) == WORLD_TREE_SCHEMA_VERSION:
        _update_tree_bindings(gn_tree, template_col, group_mat_dispatcher)
    elif gn_tree:
        gn_tree.nodes.clear()
        _remove_legacy_atlas_inputs(gn_tree)
        ensure_socket(gn_tree, "Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        ensure_socket(gn_tree, "Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        _build_tree_nodes_and_links(gn_tree, template_col, atlas_params, group_mat_dispatcher)
        gn_tree[WORLD_TREE_SCHEMA_PROPERTY] = WORLD_TREE_SCHEMA_VERSION
    else:
        gn_tree = _create_world_geometry_node_tree(WORLD_TREE_NAME, template_col, atlas_params, group_mat_dispatcher)
        gn_tree[WORLD_TREE_SCHEMA_PROPERTY] = WORLD_TREE_SCHEMA_VERSION

    mod.node_group = gn_tree
    return mod


def _update_tree_bindings(
    tree: bpy.types.GeometryNodeTree,
    template_col: bpy.types.Collection,
    group_mat_dispatcher: bpy.types.GeometryNodeTree,
) -> None:
    """Refresh external data-block references without rebuilding nodes."""
    for node in tree.nodes:
        if node.bl_idname == "GeometryNodeCollectionInfo" and "Collection" in node.inputs:
            node.inputs["Collection"].default_value = template_col
        elif node.bl_idname == "GeometryNodeGroup" and node.name == "Material Dispatcher":
            node.node_tree = group_mat_dispatcher
        elif node.bl_idname == "GeometryNodeGroup" and node.name == "Hidden Face Culling & Merge":
            node.node_tree = get_or_create_culling_merge_group()


def _remove_legacy_atlas_inputs(tree: bpy.types.GeometryNodeTree) -> None:
    """Remove former user-facing atlas controls during migration."""
    for item in list(tree.interface.items_tree):
        if (
            item.item_type == "SOCKET"
            and item.in_out == "INPUT"
            and item.name in {"Atlas Width", "Atlas Height", "Tile Size", "Tiles Per Row"}
        ):
            tree.interface.remove(item)


def _create_world_geometry_node_tree(
    tree_name: str,
    template_col: bpy.types.Collection,
    atlas_params: dict[str, Any],
    group_mat_dispatcher: bpy.types.GeometryNodeTree,
) -> bpy.types.GeometryNodeTree:
    gn_tree = bpy.data.node_groups.new(name=tree_name, type="GeometryNodeTree")
    ensure_socket(gn_tree, "Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ensure_socket(gn_tree, "Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    _build_tree_nodes_and_links(gn_tree, template_col, atlas_params, group_mat_dispatcher)
    return gn_tree


def _build_tree_nodes_and_links(
    gn_tree: bpy.types.GeometryNodeTree,
    template_col: bpy.types.Collection,
    atlas_params: dict[str, Any],
    group_mat_dispatcher: bpy.types.GeometryNodeTree,
) -> None:
    nodes = gn_tree.nodes
    links = gn_tree.links

    # 1. Ensure all reusable sub-groups exist
    group_vec_selector = get_or_create_face_selector_vector_group()
    group_int_selector = get_or_create_face_selector_int_group()
    group_color_selector = get_or_create_face_selector_color_group()
    group_uv_calc = get_or_create_atlas_uv_calculator_group()
    group_cube_surface = get_or_create_cube_surface_group()
    group_attribute_transfer = get_or_create_instance_attribute_transfer_group()
    group_culling_merge = get_or_create_culling_merge_group()

    # 2. Top-level Inputs & Outputs
    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-800, 100)

    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (2460, 100)

    # 3. Named Attribute Readers from Point Cloud
    attr_type = nodes.new("GeometryNodeInputNamedAttribute")
    attr_type.data_type = "INT"
    attr_type.inputs["Name"].default_value = BLOCK_TYPE
    attr_type.location = (-800, -100)

    attr_idx = nodes.new("GeometryNodeInputNamedAttribute")
    attr_idx.data_type = "INT"
    attr_idx.inputs["Name"].default_value = TEMPLATE_INDEX
    attr_idx.location = (-800, -250)

    attr_rot = nodes.new("GeometryNodeInputNamedAttribute")
    attr_rot.data_type = "FLOAT_VECTOR"
    attr_rot.inputs["Name"].default_value = INSTANCE_ROTATION
    attr_rot.location = (-800, -400)

    # 4. Compare block_type == 0 (Cubes)
    cmp_cube = nodes.new("FunctionNodeCompare")
    cmp_cube.data_type = "INT"
    cmp_cube.operation = "EQUAL"
    cmp_cube.inputs["B"].default_value = 0
    cmp_cube.location = (-600, 0)
    links.new(attr_type.outputs["Attribute"], cmp_cube.inputs["A"])

    # 5. Separate Geometry (Cubes vs Props)
    sep_geo = nodes.new("GeometryNodeSeparateGeometry")
    sep_geo.location = (-600, 100)
    links.new(group_in.outputs["Geometry"], sep_geo.inputs["Geometry"])
    links.new(cmp_cube.outputs["Result"], sep_geo.inputs["Selection"])

    # --- BRANCH A: Standard Cubes with Instance Attribute Transfer ---
    cube_surface = nodes.new("GeometryNodeGroup")
    cube_surface.node_tree = group_cube_surface
    cube_surface.name = "Minecraft Cube Surface"
    cube_surface.label = "Cube Surface + Local UV"
    cube_surface.location = (-400, 250)

    iop_cube = nodes.new("GeometryNodeInstanceOnPoints")
    iop_cube.location = (-200, 250)
    links.new(sep_geo.outputs["Selection"], iop_cube.inputs["Points"])
    links.new(cube_surface.outputs["Geometry"], iop_cube.inputs["Instance"])
    links.new(attr_rot.outputs["Attribute"], iop_cube.inputs["Rotation"])

    transfer_cube_attributes = nodes.new("GeometryNodeGroup")
    transfer_cube_attributes.node_tree = group_attribute_transfer
    transfer_cube_attributes.name = "Transfer Cube Instance Attributes"
    transfer_cube_attributes.label = "Transfer Instance Attributes"
    transfer_cube_attributes.location = (0, 250)
    links.new(iop_cube.outputs["Instances"], transfer_cube_attributes.inputs["Geometry"])
    last_cube_geo = transfer_cube_attributes.outputs["Geometry"]

    # --- BRANCH B: Collection Props with Instance Attribute Transfer ---
    col_info = nodes.new("GeometryNodeCollectionInfo")
    col_info.inputs["Collection"].default_value = template_col
    col_info.inputs["Separate Children"].default_value = True
    col_info.inputs["Reset Children"].default_value = True
    col_info.location = (-400, -150)

    iop_prop = nodes.new("GeometryNodeInstanceOnPoints")
    iop_prop.inputs["Pick Instance"].default_value = True
    iop_prop.location = (-200, -150)
    links.new(sep_geo.outputs["Inverted"], iop_prop.inputs["Points"])
    links.new(col_info.outputs["Instances"], iop_prop.inputs["Instance"])
    links.new(attr_idx.outputs["Attribute"], iop_prop.inputs["Instance Index"])
    links.new(attr_rot.outputs["Attribute"], iop_prop.inputs["Rotation"])

    transfer_prop_attributes = nodes.new("GeometryNodeGroup")
    transfer_prop_attributes.node_tree = group_attribute_transfer
    transfer_prop_attributes.name = "Transfer Prop Instance Attributes"
    transfer_prop_attributes.label = "Transfer Instance Attributes"
    transfer_prop_attributes.location = (0, -150)
    links.new(iop_prop.outputs["Instances"], transfer_prop_attributes.inputs["Geometry"])
    last_prop_geo = transfer_prop_attributes.outputs["Geometry"]

    # --- JOIN BRANCHES & REALIZE ---
    join_node = nodes.new("GeometryNodeJoinGeometry")
    join_node.location = (200, 100)
    links.new(last_cube_geo, join_node.inputs["Geometry"])
    links.new(last_prop_geo, join_node.inputs["Geometry"])

    realize_node = nodes.new("GeometryNodeRealizeInstances")
    realize_node.location = (380, 100)
    links.new(join_node.outputs["Geometry"], realize_node.inputs["Geometry"])

    # Read Realized LocalFaceID (INT on FACE domain)
    read_face_id = nodes.new("GeometryNodeInputNamedAttribute")
    read_face_id.data_type = "INT"
    read_face_id.inputs["Name"].default_value = LOCAL_FACE_ID
    read_face_id.location = (380, -100)

    # --- SUBGROUP: SELECT FACE TILE (VECTOR) ---
    call_tile_selector = nodes.new("GeometryNodeGroup")
    call_tile_selector.node_tree = group_vec_selector
    call_tile_selector.name = "Select Face Tile"
    call_tile_selector.location = (760, 500)
    links.new(read_face_id.outputs["Attribute"], call_tile_selector.inputs["Face ID"])

    for index, (socket_name, attr_name) in enumerate((
        ("Top (+Z)", face_attribute("tile", "top")),
        ("Bottom (-Z)", face_attribute("tile", "bottom")),
        ("East (+X)", face_attribute("tile", "east")),
        ("West (-X)", face_attribute("tile", "west")),
        ("North (+Y)", face_attribute("tile", "north")),
        ("South (-Y)", face_attribute("tile", "south")),
    )):
        reader = nodes.new("GeometryNodeInputNamedAttribute")
        reader.data_type = "FLOAT_VECTOR"
        reader.inputs["Name"].default_value = attr_name
        reader.location = (560, 600 - index * 40)
        links.new(reader.outputs["Attribute"], call_tile_selector.inputs[socket_name])

    # --- SUBGROUP: SELECT FACE CHUNK ID (INT) ---
    call_chunk_selector = nodes.new("GeometryNodeGroup")
    call_chunk_selector.node_tree = group_int_selector
    call_chunk_selector.name = "Select Face Chunk ID"
    call_chunk_selector.location = (760, 260)
    links.new(read_face_id.outputs["Attribute"], call_chunk_selector.inputs["Face ID"])

    for index, (socket_name, face) in enumerate((
        ("Top (+Z)", "top"),
        ("Bottom (-Z)", "bottom"),
        ("East (+X)", "east"),
        ("West (-X)", "west"),
        ("North (+Y)", "north"),
        ("South (-Y)", "south"),
    )):
        reader = nodes.new("GeometryNodeInputNamedAttribute")
        reader.data_type = "INT"
        reader.inputs["Name"].default_value = face_attribute("chunk", face)
        reader.location = (560, 320 - index * 40)
        links.new(reader.outputs["Attribute"], call_chunk_selector.inputs[socket_name])

    # --- SUBGROUP: ATLAS UV CALCULATOR ---
    call_uv_calc = nodes.new("GeometryNodeGroup")
    call_uv_calc.node_tree = group_uv_calc
    call_uv_calc.name = "Calculate Atlas UV"
    call_uv_calc.location = (960, 300)
    links.new(call_tile_selector.outputs["Selected"], call_uv_calc.inputs["Target Tile"])

    read_local_uv = nodes.new("GeometryNodeInputNamedAttribute")
    read_local_uv.data_type = "FLOAT_VECTOR"
    read_local_uv.inputs["Name"].default_value = LOCAL_UV
    read_local_uv.location = (560, 100)

    # Calculate upright world-aligned UV for Top (+Z) and Bottom (-Z) faces
    read_pos = nodes.new("GeometryNodeInputPosition")
    read_pos.location = (380, -250)

    read_block_center = nodes.new("GeometryNodeInputNamedAttribute")
    read_block_center.data_type = "FLOAT_VECTOR"
    read_block_center.inputs["Name"].default_value = BLOCK_CENTER
    read_block_center.location = (380, -380)

    sub_pos = nodes.new("ShaderNodeVectorMath")
    sub_pos.operation = "SUBTRACT"
    sub_pos.location = (560, -250)
    links.new(read_pos.outputs["Position"], sub_pos.inputs[0])
    links.new(read_block_center.outputs["Attribute"], sub_pos.inputs[1])

    sep_rel = nodes.new("ShaderNodeSeparateXYZ")
    sep_rel.location = (720, -250)
    links.new(sub_pos.outputs["Vector"], sep_rel.inputs["Vector"])

    add_u = nodes.new("ShaderNodeMath")
    add_u.operation = "ADD"
    add_u.inputs[1].default_value = 0.5
    add_u.location = (880, -200)
    links.new(sep_rel.outputs["X"], add_u.inputs[0])

    add_v = nodes.new("ShaderNodeMath")
    add_v.operation = "ADD"
    add_v.inputs[1].default_value = 0.5
    add_v.location = (880, -300)
    links.new(sep_rel.outputs["Y"], add_v.inputs[0])

    comb_upright_uv = nodes.new("ShaderNodeCombineXYZ")
    comb_upright_uv.location = (1040, -250)
    links.new(add_u.outputs["Value"], comb_upright_uv.inputs["X"])
    links.new(add_v.outputs["Value"], comb_upright_uv.inputs["Y"])

    # Condition: LocalFaceID in (0: Top, 1: Bottom) AND Realized Normal is vertical (|Normal.Z| > 0.5)
    cmp_fid = nodes.new("FunctionNodeCompare")
    cmp_fid.data_type = "INT"
    cmp_fid.operation = "LESS_EQUAL"
    cmp_fid.inputs["B"].default_value = 1
    cmp_fid.location = (560, -450)
    links.new(read_face_id.outputs["Attribute"], cmp_fid.inputs["A"])

    read_realized_norm = nodes.new("GeometryNodeInputNormal")
    read_realized_norm.location = (380, -550)

    sep_norm = nodes.new("ShaderNodeSeparateXYZ")
    sep_norm.location = (560, -550)
    links.new(read_realized_norm.outputs["Normal"], sep_norm.inputs["Vector"])

    abs_nz = nodes.new("ShaderNodeMath")
    abs_nz.operation = "ABSOLUTE"
    abs_nz.location = (720, -550)
    links.new(sep_norm.outputs["Z"], abs_nz.inputs[0])

    cmp_nz = nodes.new("FunctionNodeCompare")
    cmp_nz.data_type = "FLOAT"
    cmp_nz.operation = "GREATER_THAN"
    cmp_nz.inputs["B"].default_value = 0.5
    cmp_nz.location = (880, -550)
    links.new(abs_nz.outputs["Value"], cmp_nz.inputs["A"])

    bool_upright = nodes.new("FunctionNodeBooleanMath")
    bool_upright.operation = "AND"
    bool_upright.location = (1040, -500)
    links.new(cmp_fid.outputs["Result"], bool_upright.inputs[0])
    links.new(cmp_nz.outputs["Result"], bool_upright.inputs[1])

    switch_uv_in = nodes.new("GeometryNodeSwitch")
    switch_uv_in.input_type = "VECTOR"
    switch_uv_in.location = (1200, -200)
    links.new(bool_upright.outputs["Boolean"], switch_uv_in.inputs["Switch"])
    links.new(read_local_uv.outputs["Attribute"], switch_uv_in.inputs["False"])
    links.new(comb_upright_uv.outputs["Vector"], switch_uv_in.inputs["True"])

    # Link selected local UV into UV calculator
    links.new(switch_uv_in.outputs["Output"], call_uv_calc.inputs["Local UV"])

    # Link Chunk ID into UV calculator
    links.new(call_chunk_selector.outputs["Selected"], call_uv_calc.inputs["Chunk ID"])

    for index, (socket_name, attr_name) in enumerate((
        ("Tiles Per Row", MTK_TILES_PER_ROW),
        ("Tile Size", MTK_TILE_SIZE),
        ("Atlas Height", MTK_ATLAS_HEIGHT),
        ("Anim Atlas Width", MTK_ANIM_ATLAS_WIDTH),
        ("Anim Atlas Height", MTK_ANIM_ATLAS_HEIGHT),
        ("Anim Frame Width", MTK_ANIM_FRAME_WIDTH),
        ("Anim Frame Height", MTK_ANIM_FRAME_HEIGHT),
    )):
        reader = nodes.new("GeometryNodeInputNamedAttribute")
        reader.data_type = "FLOAT"
        reader.inputs["Name"].default_value = attr_name
        reader.location = (760, 160 - index * 40)
        links.new(reader.outputs["Attribute"], call_uv_calc.inputs[socket_name])

    # Store UVMap (CORNER)
    store_uv_final = nodes.new("GeometryNodeStoreNamedAttribute")
    store_uv_final.data_type = "FLOAT_VECTOR"
    store_uv_final.domain = "CORNER"
    store_uv_final.inputs["Name"].default_value = UV_MAP
    store_uv_final.location = (1180, 100)
    links.new(realize_node.outputs["Geometry"], store_uv_final.inputs["Geometry"])
    links.new(call_uv_calc.outputs["Atlas UV"], store_uv_final.inputs["Value"])

    # Store UV Tiling Transform
    store_tiling = nodes.new("GeometryNodeStoreNamedAttribute")
    store_tiling.data_type = "FLOAT_COLOR"
    store_tiling.domain = "CORNER"
    store_tiling.inputs["Name"].default_value = MTK_UV_TILING_TRANSFORM
    store_tiling.inputs["Value"].default_value = (1.0, 1.0, 0.0, 0.0)
    store_tiling.location = (1360, 100)
    links.new(store_uv_final.outputs["Geometry"], store_tiling.inputs["Geometry"])

    # Store UV Rotation
    store_rot = nodes.new("GeometryNodeStoreNamedAttribute")
    store_rot.data_type = "FLOAT"
    store_rot.domain = "CORNER"
    store_rot.inputs["Name"].default_value = MTK_UV_ROTATION
    store_rot.inputs["Value"].default_value = 0.0
    store_rot.location = (1540, 100)
    links.new(store_tiling.outputs["Geometry"], store_rot.inputs["Geometry"])

    # --- SUBGROUP: SELECT FACE TINT DATA (COLOR) ---
    call_tint_selector = nodes.new("GeometryNodeGroup")
    call_tint_selector.node_tree = group_color_selector
    call_tint_selector.name = "Select Biome Tint Data"
    call_tint_selector.location = (760, -100)
    links.new(read_face_id.outputs["Attribute"], call_tint_selector.inputs["Face ID"])

    for index, (socket_name, face) in enumerate((
        ("Top (+Z)", "top"),
        ("Bottom (-Z)", "bottom"),
        ("East (+X)", "east"),
        ("West (-X)", "west"),
        ("North (+Y)", "north"),
        ("South (-Y)", "south"),
    )):
        reader = nodes.new("GeometryNodeInputNamedAttribute")
        reader.data_type = "FLOAT_COLOR"
        reader.inputs["Name"].default_value = face_attribute("tint_data", face)
        reader.location = (560, -30 - index * 40)
        links.new(reader.outputs["Attribute"], call_tint_selector.inputs[socket_name])

    store_tint_data = nodes.new("GeometryNodeStoreNamedAttribute")
    store_tint_data.data_type = "FLOAT_COLOR"
    store_tint_data.domain = "FACE"
    store_tint_data.inputs["Name"].default_value = MTK_BIOME_TINT_DATA
    store_tint_data.location = (1720, 100)
    links.new(store_rot.outputs["Geometry"], store_tint_data.inputs["Geometry"])
    links.new(call_tint_selector.outputs["Selected"], store_tint_data.inputs["Value"])

    # --- SUBGROUP: SELECT FACE CHUNK ID (INT) ---
    store_chunk_id = nodes.new("GeometryNodeStoreNamedAttribute")
    store_chunk_id.data_type = "INT"
    store_chunk_id.domain = "FACE"
    store_chunk_id.inputs["Name"].default_value = MTK_ATLAS_CHUNK_ID
    store_chunk_id.location = (1900, 100)
    links.new(store_tint_data.outputs["Geometry"], store_chunk_id.inputs["Geometry"])
    links.new(call_chunk_selector.outputs["Selected"], store_chunk_id.inputs["Value"])

    # --- SUBGROUP: SELECT FACE TEXTURE ID (INT) ---
    call_texture_selector = nodes.new("GeometryNodeGroup")
    call_texture_selector.node_tree = group_int_selector
    call_texture_selector.name = "Select Face Texture ID"
    call_texture_selector.location = (760, -600)
    links.new(read_face_id.outputs["Attribute"], call_texture_selector.inputs["Face ID"])

    for index, (socket_name, face) in enumerate((
        ("Top (+Z)", "top"),
        ("Bottom (-Z)", "bottom"),
        ("East (+X)", "east"),
        ("West (-X)", "west"),
        ("North (+Y)", "north"),
        ("South (-Y)", "south"),
    )):
        reader = nodes.new("GeometryNodeInputNamedAttribute")
        reader.data_type = "INT"
        reader.inputs["Name"].default_value = face_attribute("texture", face)
        reader.location = (560, -530 - index * 40)
        links.new(reader.outputs["Attribute"], call_texture_selector.inputs[socket_name])

    store_texture_id = nodes.new("GeometryNodeStoreNamedAttribute")
    store_texture_id.data_type = "INT"
    store_texture_id.domain = "FACE"
    store_texture_id.inputs["Name"].default_value = MTK_ATLAS_TEXTURE_ID
    store_texture_id.location = (2080, 100)
    links.new(store_chunk_id.outputs["Geometry"], store_texture_id.inputs["Geometry"])
    links.new(call_texture_selector.outputs["Selected"], store_texture_id.inputs["Value"])

    # --- SUBGROUP: SELECT FACE ANIM TIMING (COLOR) ---
    call_timing_selector = nodes.new("GeometryNodeGroup")
    call_timing_selector.node_tree = group_color_selector
    call_timing_selector.name = "Select Face Anim Timing"
    call_timing_selector.location = (760, -850)
    links.new(read_face_id.outputs["Attribute"], call_timing_selector.inputs["Face ID"])

    for index, (socket_name, face) in enumerate((
        ("Top (+Z)", "top"),
        ("Bottom (-Z)", "bottom"),
        ("East (+X)", "east"),
        ("West (-X)", "west"),
        ("North (+Y)", "north"),
        ("South (-Y)", "south"),
    )):
        reader = nodes.new("GeometryNodeInputNamedAttribute")
        reader.data_type = "FLOAT_COLOR"
        reader.inputs["Name"].default_value = face_attribute("anim_timing", face)
        reader.location = (560, -780 - index * 40)
        links.new(reader.outputs["Attribute"], call_timing_selector.inputs[socket_name])

    store_timing = nodes.new("GeometryNodeStoreNamedAttribute")
    store_timing.data_type = "FLOAT_COLOR"
    store_timing.domain = "FACE"
    store_timing.inputs["Name"].default_value = MTK_ANIM_TIMING
    store_timing.location = (2260, 100)
    links.new(store_texture_id.outputs["Geometry"], store_timing.inputs["Geometry"])
    links.new(call_timing_selector.outputs["Selected"], store_timing.inputs["Value"])

    # --- SUBGROUP: SELECT FACE ANIM FRAME SIZE (COLOR) ---
    call_size_selector = nodes.new("GeometryNodeGroup")
    call_size_selector.node_tree = group_color_selector
    call_size_selector.name = "Select Face Anim Frame Size"
    call_size_selector.location = (760, -1100)
    links.new(read_face_id.outputs["Attribute"], call_size_selector.inputs["Face ID"])

    for index, (socket_name, face) in enumerate((
        ("Top (+Z)", "top"),
        ("Bottom (-Z)", "bottom"),
        ("East (+X)", "east"),
        ("West (-X)", "west"),
        ("North (+Y)", "north"),
        ("South (-Y)", "south"),
    )):
        reader = nodes.new("GeometryNodeInputNamedAttribute")
        reader.data_type = "FLOAT_COLOR"
        reader.inputs["Name"].default_value = face_attribute("anim_frame_size", face)
        reader.location = (560, -1030 - index * 40)
        links.new(reader.outputs["Attribute"], call_size_selector.inputs[socket_name])

    store_size = nodes.new("GeometryNodeStoreNamedAttribute")
    store_size.data_type = "FLOAT_COLOR"
    store_size.domain = "FACE"
    store_size.inputs["Name"].default_value = MTK_ANIM_FRAME_SIZE
    store_size.location = (2440, 100)
    links.new(store_timing.outputs["Geometry"], store_size.inputs["Geometry"])
    links.new(call_size_selector.outputs["Selected"], store_size.inputs["Value"])

    # --- SUBGROUP: HIDDEN FACE CULLING & VERTEX MERGE ---
    call_culling_merge = nodes.new("GeometryNodeGroup")
    call_culling_merge.node_tree = group_culling_merge
    call_culling_merge.name = "Hidden Face Culling & Merge"
    call_culling_merge.location = (2620, 100)
    links.new(store_size.outputs["Geometry"], call_culling_merge.inputs["Geometry"])
    links.new(group_in.outputs["Geometry"], call_culling_merge.inputs["Point Cloud"])

    # --- SUBGROUP: MATERIAL DISPATCHER ---
    call_mat_dispatcher = nodes.new("GeometryNodeGroup")
    call_mat_dispatcher.node_tree = group_mat_dispatcher
    call_mat_dispatcher.name = "Material Dispatcher"
    call_mat_dispatcher.location = (2840, 100)
    links.new(call_culling_merge.outputs["Geometry"], call_mat_dispatcher.inputs["Geometry"])

    # Final Output
    group_out.location = (3060, 100)
    links.new(call_mat_dispatcher.outputs["Geometry"], group_out.inputs["Geometry"])
    prune_unlinked_nodes(gn_tree)
