"""
Geometry Nodes World Tree Builder for Yefira Blender Plugin.
Generates a complete, high-performance procedural Minecraft world from Point Cloud attributes.
Features procedural 6-face Minecraft cube UV generation and non-square Atlas texture addressing.
"""

from __future__ import annotations
import bpy
import logging
from typing import Any, Optional
from ..materials.atlas_integration import (
    get_or_create_atlas_material,
    extract_atlas_parameters,
    find_bound_atlas_material,
    setup_material_slots_for_object,
)
from ..core.template_catalog import get_or_create_template_collection, TEMPLATE_COLLECTION_NAME
from .world_groups import (
    get_or_create_cube_surface_group,
    get_or_create_instance_attribute_transfer_group,
)

logger = logging.getLogger("Yefira")

WORLD_TREE_NAME = "Yefira_WorldTree"
WORLD_MODIFIER_NAME = "Yefira_WorldModifier"
# Schema version 9: reusable instance-attribute transfer group.
WORLD_TREE_SCHEMA_VERSION = 9
WORLD_TREE_SCHEMA_PROPERTY = "yefira:world_tree_schema"


def _ensure_socket(
    tree: bpy.types.NodeTree,
    name: str,
    in_out: str,
    socket_type: str,
    default_value=None,
    min_value=None,
):
    """Ensure socket exists on node tree interface."""
    for item in tree.interface.items_tree:
        if item.item_type == 'SOCKET' and item.name == name and item.in_out == in_out:
            if default_value is not None and hasattr(item, "default_value"):
                item.default_value = default_value
            return item
    socket = tree.interface.new_socket(name=name, in_out=in_out, socket_type=socket_type)
    if default_value is not None and hasattr(socket, "default_value"):
        socket.default_value = default_value
    if min_value is not None and hasattr(socket, "min_value"):
        socket.min_value = min_value
    return socket


def get_or_create_face_selector_vector_group() -> bpy.types.GeometryNodeTree:
    """Reusable node group: Selects a Vector from 6 face inputs based on Face Normal."""
    name = "Yefira_Face_Selector_Vector"
    tree = bpy.data.node_groups.get(name)
    if tree and tree.get("yefira_built"):
        return tree

    if not tree:
        tree = bpy.data.node_groups.new(name=name, type='GeometryNodeTree')
    tree.nodes.clear()

    _ensure_socket(tree, "Normal", 'INPUT', 'NodeSocketVector')
    _ensure_socket(tree, "South (+Y)", 'INPUT', 'NodeSocketVector')
    _ensure_socket(tree, "North (-Y)", 'INPUT', 'NodeSocketVector')
    _ensure_socket(tree, "East (+X)", 'INPUT', 'NodeSocketVector')
    _ensure_socket(tree, "West (-X)", 'INPUT', 'NodeSocketVector')
    _ensure_socket(tree, "Bottom (-Z)", 'INPUT', 'NodeSocketVector')
    _ensure_socket(tree, "Top (+Z)", 'INPUT', 'NodeSocketVector')
    _ensure_socket(tree, "Selected", 'OUTPUT', 'NodeSocketVector')

    nodes, links = tree.nodes, tree.links
    gin = nodes.new('NodeGroupInput')
    gin.location = (-600, 0)
    gout = nodes.new('NodeGroupOutput')
    gout.location = (800, 0)

    sep_norm = nodes.new('ShaderNodeSeparateXYZ')
    sep_norm.location = (-400, 200)
    links.new(gin.outputs['Normal'], sep_norm.inputs['Vector'])

    cmp_north = nodes.new('FunctionNodeCompare')
    cmp_north.data_type = 'FLOAT'
    cmp_north.operation = 'LESS_THAN'
    cmp_north.inputs['B'].default_value = -0.5
    cmp_north.location = (-200, 300)
    links.new(sep_norm.outputs['Y'], cmp_north.inputs['A'])

    cmp_east = nodes.new('FunctionNodeCompare')
    cmp_east.data_type = 'FLOAT'
    cmp_east.operation = 'GREATER_THAN'
    cmp_east.inputs['B'].default_value = 0.5
    cmp_east.location = (-200, 150)
    links.new(sep_norm.outputs['X'], cmp_east.inputs['A'])

    cmp_west = nodes.new('FunctionNodeCompare')
    cmp_west.data_type = 'FLOAT'
    cmp_west.operation = 'LESS_THAN'
    cmp_west.inputs['B'].default_value = -0.5
    cmp_west.location = (-200, 0)
    links.new(sep_norm.outputs['X'], cmp_west.inputs['A'])

    cmp_bottom = nodes.new('FunctionNodeCompare')
    cmp_bottom.data_type = 'FLOAT'
    cmp_bottom.operation = 'LESS_THAN'
    cmp_bottom.inputs['B'].default_value = -0.5
    cmp_bottom.location = (-200, -150)
    links.new(sep_norm.outputs['Z'], cmp_bottom.inputs['A'])

    cmp_top = nodes.new('FunctionNodeCompare')
    cmp_top.data_type = 'FLOAT'
    cmp_top.operation = 'GREATER_THAN'
    cmp_top.inputs['B'].default_value = 0.5
    cmp_top.location = (-200, -300)
    links.new(sep_norm.outputs['Z'], cmp_top.inputs['A'])

    m1 = nodes.new('ShaderNodeMix')
    m1.data_type = 'VECTOR'
    m1.location = (0, 200)
    links.new(cmp_north.outputs['Result'], m1.inputs[0])
    links.new(gin.outputs['South (+Y)'], m1.inputs[4])
    links.new(gin.outputs['North (-Y)'], m1.inputs[5])

    m2 = nodes.new('ShaderNodeMix')
    m2.data_type = 'VECTOR'
    m2.location = (150, 150)
    links.new(cmp_east.outputs['Result'], m2.inputs[0])
    links.new(m1.outputs[1], m2.inputs[4])
    links.new(gin.outputs['East (+X)'], m2.inputs[5])

    m3 = nodes.new('ShaderNodeMix')
    m3.data_type = 'VECTOR'
    m3.location = (300, 100)
    links.new(cmp_west.outputs['Result'], m3.inputs[0])
    links.new(m2.outputs[1], m3.inputs[4])
    links.new(gin.outputs['West (-X)'], m3.inputs[5])

    m4 = nodes.new('ShaderNodeMix')
    m4.data_type = 'VECTOR'
    m4.location = (450, 50)
    links.new(cmp_bottom.outputs['Result'], m4.inputs[0])
    links.new(m3.outputs[1], m4.inputs[4])
    links.new(gin.outputs['Bottom (-Z)'], m4.inputs[5])

    m5 = nodes.new('ShaderNodeMix')
    m5.data_type = 'VECTOR'
    m5.location = (600, 0)
    links.new(cmp_top.outputs['Result'], m5.inputs[0])
    links.new(m4.outputs[1], m5.inputs[4])
    links.new(gin.outputs['Top (+Z)'], m5.inputs[5])

    links.new(m5.outputs[1], gout.inputs['Selected'])
    tree["yefira_built"] = True
    return tree


def get_or_create_face_selector_int_group() -> bpy.types.GeometryNodeTree:
    """Reusable node group: Selects an Integer from 6 face inputs based on Face Normal."""
    name = "Yefira_Face_Selector_Int"
    tree = bpy.data.node_groups.get(name)
    if tree and tree.get("yefira_built"):
        return tree

    if not tree:
        tree = bpy.data.node_groups.new(name=name, type='GeometryNodeTree')
    tree.nodes.clear()

    _ensure_socket(tree, "Normal", 'INPUT', 'NodeSocketVector')
    _ensure_socket(tree, "South (+Y)", 'INPUT', 'NodeSocketInt', default_value=0)
    _ensure_socket(tree, "North (-Y)", 'INPUT', 'NodeSocketInt', default_value=0)
    _ensure_socket(tree, "East (+X)", 'INPUT', 'NodeSocketInt', default_value=0)
    _ensure_socket(tree, "West (-X)", 'INPUT', 'NodeSocketInt', default_value=0)
    _ensure_socket(tree, "Bottom (-Z)", 'INPUT', 'NodeSocketInt', default_value=0)
    _ensure_socket(tree, "Top (+Z)", 'INPUT', 'NodeSocketInt', default_value=0)
    _ensure_socket(tree, "Selected", 'OUTPUT', 'NodeSocketInt')

    nodes, links = tree.nodes, tree.links
    gin = nodes.new('NodeGroupInput')
    gin.location = (-600, 0)
    gout = nodes.new('NodeGroupOutput')
    gout.location = (800, 0)

    sep_norm = nodes.new('ShaderNodeSeparateXYZ')
    sep_norm.location = (-400, 200)
    links.new(gin.outputs['Normal'], sep_norm.inputs['Vector'])

    cmp_north = nodes.new('FunctionNodeCompare')
    cmp_north.data_type = 'FLOAT'
    cmp_north.operation = 'LESS_THAN'
    cmp_north.inputs['B'].default_value = -0.5
    cmp_north.location = (-200, 300)
    links.new(sep_norm.outputs['Y'], cmp_north.inputs['A'])

    cmp_east = nodes.new('FunctionNodeCompare')
    cmp_east.data_type = 'FLOAT'
    cmp_east.operation = 'GREATER_THAN'
    cmp_east.inputs['B'].default_value = 0.5
    cmp_east.location = (-200, 150)
    links.new(sep_norm.outputs['X'], cmp_east.inputs['A'])

    cmp_west = nodes.new('FunctionNodeCompare')
    cmp_west.data_type = 'FLOAT'
    cmp_west.operation = 'LESS_THAN'
    cmp_west.inputs['B'].default_value = -0.5
    cmp_west.location = (-200, 0)
    links.new(sep_norm.outputs['X'], cmp_west.inputs['A'])

    cmp_bottom = nodes.new('FunctionNodeCompare')
    cmp_bottom.data_type = 'FLOAT'
    cmp_bottom.operation = 'LESS_THAN'
    cmp_bottom.inputs['B'].default_value = -0.5
    cmp_bottom.location = (-200, -150)
    links.new(sep_norm.outputs['Z'], cmp_bottom.inputs['A'])

    cmp_top = nodes.new('FunctionNodeCompare')
    cmp_top.data_type = 'FLOAT'
    cmp_top.operation = 'GREATER_THAN'
    cmp_top.inputs['B'].default_value = 0.5
    cmp_top.location = (-200, -300)
    links.new(sep_norm.outputs['Z'], cmp_top.inputs['A'])

    def make_switch(compare_node, false_socket, true_socket, x, y):
        sw = nodes.new('GeometryNodeSwitch')
        sw.input_type = 'INT'
        sw.location = (x, y)
        links.new(compare_node.outputs['Result'], sw.inputs['Switch'])
        links.new(false_socket, sw.inputs['False'])
        links.new(true_socket, sw.inputs['True'])
        return sw.outputs['Output']

    v1 = make_switch(cmp_north, gin.outputs['South (+Y)'], gin.outputs['North (-Y)'], 0, 200)
    v2 = make_switch(cmp_east, v1, gin.outputs['East (+X)'], 150, 150)
    v3 = make_switch(cmp_west, v2, gin.outputs['West (-X)'], 300, 100)
    v4 = make_switch(cmp_bottom, v3, gin.outputs['Bottom (-Z)'], 450, 50)
    v5 = make_switch(cmp_top, v4, gin.outputs['Top (+Z)'], 600, 0)

    links.new(v5, gout.inputs['Selected'])
    tree["yefira_built"] = True
    return tree


def get_or_create_face_selector_color_group() -> bpy.types.GeometryNodeTree:
    """Reusable node group: Selects a Color (RGBA) from 6 face inputs based on Face Normal."""
    name = "Yefira_Face_Selector_Color"
    tree = bpy.data.node_groups.get(name)
    if tree and tree.get("yefira_built"):
        return tree

    if not tree:
        tree = bpy.data.node_groups.new(name=name, type='GeometryNodeTree')
    tree.nodes.clear()

    _ensure_socket(tree, "Normal", 'INPUT', 'NodeSocketVector')
    _ensure_socket(tree, "South (+Y)", 'INPUT', 'NodeSocketColor')
    _ensure_socket(tree, "North (-Y)", 'INPUT', 'NodeSocketColor')
    _ensure_socket(tree, "East (+X)", 'INPUT', 'NodeSocketColor')
    _ensure_socket(tree, "West (-X)", 'INPUT', 'NodeSocketColor')
    _ensure_socket(tree, "Bottom (-Z)", 'INPUT', 'NodeSocketColor')
    _ensure_socket(tree, "Top (+Z)", 'INPUT', 'NodeSocketColor')
    _ensure_socket(tree, "Selected", 'OUTPUT', 'NodeSocketColor')

    nodes, links = tree.nodes, tree.links
    gin = nodes.new('NodeGroupInput')
    gin.location = (-600, 0)
    gout = nodes.new('NodeGroupOutput')
    gout.location = (800, 0)

    sep_norm = nodes.new('ShaderNodeSeparateXYZ')
    sep_norm.location = (-400, 200)
    links.new(gin.outputs['Normal'], sep_norm.inputs['Vector'])

    cmp_north = nodes.new('FunctionNodeCompare')
    cmp_north.data_type = 'FLOAT'
    cmp_north.operation = 'LESS_THAN'
    cmp_north.inputs['B'].default_value = -0.5
    cmp_north.location = (-200, 300)
    links.new(sep_norm.outputs['Y'], cmp_north.inputs['A'])

    cmp_east = nodes.new('FunctionNodeCompare')
    cmp_east.data_type = 'FLOAT'
    cmp_east.operation = 'GREATER_THAN'
    cmp_east.inputs['B'].default_value = 0.5
    cmp_east.location = (-200, 150)
    links.new(sep_norm.outputs['X'], cmp_east.inputs['A'])

    cmp_west = nodes.new('FunctionNodeCompare')
    cmp_west.data_type = 'FLOAT'
    cmp_west.operation = 'LESS_THAN'
    cmp_west.inputs['B'].default_value = -0.5
    cmp_west.location = (-200, 0)
    links.new(sep_norm.outputs['X'], cmp_west.inputs['A'])

    cmp_bottom = nodes.new('FunctionNodeCompare')
    cmp_bottom.data_type = 'FLOAT'
    cmp_bottom.operation = 'LESS_THAN'
    cmp_bottom.inputs['B'].default_value = -0.5
    cmp_bottom.location = (-200, -150)
    links.new(sep_norm.outputs['Z'], cmp_bottom.inputs['A'])

    cmp_top = nodes.new('FunctionNodeCompare')
    cmp_top.data_type = 'FLOAT'
    cmp_top.operation = 'GREATER_THAN'
    cmp_top.inputs['B'].default_value = 0.5
    cmp_top.location = (-200, -300)
    links.new(sep_norm.outputs['Z'], cmp_top.inputs['A'])

    m1 = nodes.new('ShaderNodeMix')
    m1.data_type = 'RGBA'
    m1.location = (0, 200)
    links.new(cmp_north.outputs['Result'], m1.inputs[0])
    links.new(gin.outputs['South (+Y)'], m1.inputs[6])
    links.new(gin.outputs['North (-Y)'], m1.inputs[7])

    m2 = nodes.new('ShaderNodeMix')
    m2.data_type = 'RGBA'
    m2.location = (150, 150)
    links.new(cmp_east.outputs['Result'], m2.inputs[0])
    links.new(m1.outputs[2], m2.inputs[6])
    links.new(gin.outputs['East (+X)'], m2.inputs[7])

    m3 = nodes.new('ShaderNodeMix')
    m3.data_type = 'RGBA'
    m3.location = (300, 100)
    links.new(cmp_west.outputs['Result'], m3.inputs[0])
    links.new(m2.outputs[2], m3.inputs[6])
    links.new(gin.outputs['West (-X)'], m3.inputs[7])

    m4 = nodes.new('ShaderNodeMix')
    m4.data_type = 'RGBA'
    m4.location = (450, 50)
    links.new(cmp_bottom.outputs['Result'], m4.inputs[0])
    links.new(m3.outputs[2], m4.inputs[6])
    links.new(gin.outputs['Bottom (-Z)'], m4.inputs[7])

    m5 = nodes.new('ShaderNodeMix')
    m5.data_type = 'RGBA'
    m5.location = (600, 0)
    links.new(cmp_top.outputs['Result'], m5.inputs[0])
    links.new(m4.outputs[2], m5.inputs[6])
    links.new(gin.outputs['Top (+Z)'], m5.inputs[7])

    links.new(m5.outputs[2], gout.inputs['Selected'])
    tree["yefira_built"] = True
    return tree


def get_or_create_atlas_uv_calculator_group() -> bpy.types.GeometryNodeTree:
    """Reusable node group: Calculates UVMap coordinate in Atlas space from LocalUV and Tile Col/Row."""
    name = "Yefira_Atlas_UV_Calculator"
    tree = bpy.data.node_groups.get(name)
    if tree and tree.get("yefira_built"):
        return tree

    if not tree:
        tree = bpy.data.node_groups.new(name=name, type='GeometryNodeTree')
    tree.nodes.clear()

    _ensure_socket(tree, "Target Tile", 'INPUT', 'NodeSocketVector')
    _ensure_socket(tree, "Local UV", 'INPUT', 'NodeSocketVector')
    _ensure_socket(tree, "Tiles Per Row", 'INPUT', 'NodeSocketFloat', default_value=64.0)
    _ensure_socket(tree, "Tile Size", 'INPUT', 'NodeSocketFloat', default_value=16.0)
    _ensure_socket(tree, "Atlas Height", 'INPUT', 'NodeSocketFloat', default_value=1024.0)
    _ensure_socket(tree, "Atlas UV", 'OUTPUT', 'NodeSocketVector')

    nodes, links = tree.nodes, tree.links
    gin = nodes.new('NodeGroupInput')
    gin.location = (-600, 0)
    gout = nodes.new('NodeGroupOutput')
    gout.location = (600, 0)

    sep_target = nodes.new('ShaderNodeSeparateXYZ')
    sep_target.location = (-400, 150)
    links.new(gin.outputs['Target Tile'], sep_target.inputs['Vector'])

    sep_local = nodes.new('ShaderNodeSeparateXYZ')
    sep_local.location = (-400, -150)
    links.new(gin.outputs['Local UV'], sep_local.inputs['Vector'])

    step_u = nodes.new('ShaderNodeMath')
    step_u.operation = 'DIVIDE'
    step_u.inputs[0].default_value = 1.0
    step_u.location = (-200, 250)
    links.new(gin.outputs['Tiles Per Row'], step_u.inputs[1])

    step_v = nodes.new('ShaderNodeMath')
    step_v.operation = 'DIVIDE'
    step_v.location = (-200, -250)
    links.new(gin.outputs['Tile Size'], step_v.inputs[0])
    links.new(gin.outputs['Atlas Height'], step_v.inputs[1])

    col_plus_u = nodes.new('ShaderNodeMath')
    col_plus_u.operation = 'ADD'
    col_plus_u.location = (-200, 100)
    links.new(sep_target.outputs['X'], col_plus_u.inputs[0])
    links.new(sep_local.outputs['X'], col_plus_u.inputs[1])

    atlas_u = nodes.new('ShaderNodeMath')
    atlas_u.operation = 'MULTIPLY'
    atlas_u.location = (0, 100)
    links.new(col_plus_u.outputs['Value'], atlas_u.inputs[0])
    links.new(step_u.outputs['Value'], atlas_u.inputs[1])

    inv_v = nodes.new('ShaderNodeMath')
    inv_v.operation = 'SUBTRACT'
    inv_v.inputs[0].default_value = 1.0
    inv_v.location = (-200, -50)
    links.new(sep_local.outputs['Y'], inv_v.inputs[1])

    row_plus_inv_v = nodes.new('ShaderNodeMath')
    row_plus_inv_v.operation = 'ADD'
    row_plus_inv_v.location = (0, -50)
    links.new(sep_target.outputs['Y'], row_plus_inv_v.inputs[0])
    links.new(inv_v.outputs['Value'], row_plus_inv_v.inputs[1])

    v_scaled = nodes.new('ShaderNodeMath')
    v_scaled.operation = 'MULTIPLY'
    v_scaled.location = (180, -50)
    links.new(row_plus_inv_v.outputs['Value'], v_scaled.inputs[0])
    links.new(step_v.outputs['Value'], v_scaled.inputs[1])

    atlas_v = nodes.new('ShaderNodeMath')
    atlas_v.operation = 'SUBTRACT'
    atlas_v.inputs[0].default_value = 1.0
    atlas_v.location = (340, -50)
    links.new(v_scaled.outputs['Value'], atlas_v.inputs[1])

    comb = nodes.new('ShaderNodeCombineXYZ')
    comb.location = (450, 50)
    links.new(atlas_u.outputs['Value'], comb.inputs['X'])
    links.new(atlas_v.outputs['Value'], comb.inputs['Y'])
    links.new(comb.outputs['Vector'], gout.inputs['Atlas UV'])

    tree["yefira_built"] = True
    return tree


def setup_world_geometry_nodes(
    world_obj: bpy.types.Object,
    template_col: bpy.types.Collection = None,
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

    mod = world_obj.modifiers.get(WORLD_MODIFIER_NAME)
    if not mod:
        mod = world_obj.modifiers.new(name=WORLD_MODIFIER_NAME, type='NODES')

    gn_tree = bpy.data.node_groups.get(WORLD_TREE_NAME)
    if gn_tree and gn_tree.get(WORLD_TREE_SCHEMA_PROPERTY) == WORLD_TREE_SCHEMA_VERSION:
        _update_tree_bindings(gn_tree, template_col)
    elif gn_tree:
        gn_tree.nodes.clear()
        _remove_legacy_atlas_inputs(gn_tree)
        _ensure_socket(gn_tree, "Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        _ensure_socket(gn_tree, "Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
        _build_tree_nodes_and_links(gn_tree, template_col, atlas_params)
        gn_tree[WORLD_TREE_SCHEMA_PROPERTY] = WORLD_TREE_SCHEMA_VERSION
    else:
        gn_tree = _create_world_geometry_node_tree(WORLD_TREE_NAME, template_col, atlas_params)
        gn_tree[WORLD_TREE_SCHEMA_PROPERTY] = WORLD_TREE_SCHEMA_VERSION

    mod.node_group = gn_tree
    return mod


def _update_tree_bindings(
    tree: bpy.types.GeometryNodeTree,
    template_col: bpy.types.Collection,
) -> None:
    """Refresh external data-block references without rebuilding nodes."""
    for node in tree.nodes:
        if node.bl_idname == 'GeometryNodeCollectionInfo' and 'Collection' in node.inputs:
            node.inputs['Collection'].default_value = template_col


def _remove_legacy_atlas_inputs(tree: bpy.types.GeometryNodeTree) -> None:
    """Remove former user-facing atlas controls during migration."""
    for item in list(tree.interface.items_tree):
        if (
            item.item_type == 'SOCKET'
            and item.in_out == 'INPUT'
            and item.name in {"Atlas Width", "Atlas Height", "Tile Size", "Tiles Per Row"}
        ):
            tree.interface.remove(item)


def _prune_unlinked_nodes(tree: bpy.types.GeometryNodeTree) -> None:
    """Remove construction leftovers that do not contribute to group output.

    The builder uses named fields as well as geometry wires.  Walking upstream
    from every Group Output input preserves both kinds of dependency while
    allowing a migration to replace a subgraph with a node group cleanly.
    """
    required = {node for node in tree.nodes if node.bl_idname == 'NodeGroupOutput'}
    stack = list(required)
    while stack:
        node = stack.pop()
        for input_socket in node.inputs:
            for link in input_socket.links:
                if link.from_node not in required:
                    required.add(link.from_node)
                    stack.append(link.from_node)
    for node in list(tree.nodes):
        if node not in required:
            tree.nodes.remove(node)


def _create_world_geometry_node_tree(
    tree_name: str,
    template_col: bpy.types.Collection,
    atlas_params: dict[str, Any],
) -> bpy.types.GeometryNodeTree:
    gn_tree = bpy.data.node_groups.new(name=tree_name, type='GeometryNodeTree')
    _ensure_socket(gn_tree, "Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    _ensure_socket(gn_tree, "Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    _build_tree_nodes_and_links(gn_tree, template_col, atlas_params)
    return gn_tree


def _build_tree_nodes_and_links(
    gn_tree: bpy.types.GeometryNodeTree,
    template_col: bpy.types.Collection,
    atlas_params: dict[str, Any],
):
    nodes = gn_tree.nodes
    links = gn_tree.links

    # Ensure reusable node groups
    group_vec_selector = get_or_create_face_selector_vector_group()
    group_int_selector = get_or_create_face_selector_int_group()
    group_color_selector = get_or_create_face_selector_color_group()
    group_uv_calc = get_or_create_atlas_uv_calculator_group()
    group_cube_surface = get_or_create_cube_surface_group()
    group_attribute_transfer = get_or_create_instance_attribute_transfer_group()

    # 1. Inputs & Outputs
    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-1400, 0)

    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (3200, 0)

    # 2. Named Attribute Readers from Point Cloud
    attr_type = nodes.new('GeometryNodeInputNamedAttribute')
    attr_type.data_type = 'INT'
    attr_type.inputs['Name'].default_value = "block_type"
    attr_type.location = (-1400, -250)

    attr_idx = nodes.new('GeometryNodeInputNamedAttribute')
    attr_idx.data_type = 'INT'
    attr_idx.inputs['Name'].default_value = "instance_index"
    attr_idx.location = (-1000, -350)

    attr_rot = nodes.new('GeometryNodeInputNamedAttribute')
    attr_rot.data_type = 'FLOAT_VECTOR'
    attr_rot.inputs['Name'].default_value = "instance_rotation"
    attr_rot.location = (-600, -400)

    # 3. Compare block_type == 0 (Cubes)
    cmp_cube = nodes.new('FunctionNodeCompare')
    cmp_cube.data_type = 'INT'
    cmp_cube.operation = 'EQUAL'
    cmp_cube.inputs['B'].default_value = 0
    cmp_cube.location = (-1150, 100)
    links.new(attr_type.outputs['Attribute'], cmp_cube.inputs['A'])

    # 4. Separate Geometry (Cubes vs Props)
    sep_geo = nodes.new('GeometryNodeSeparateGeometry')
    sep_geo.location = (-950, 100)
    links.new(group_in.outputs['Geometry'], sep_geo.inputs['Geometry'])
    links.new(cmp_cube.outputs['Result'], sep_geo.inputs['Selection'])

    # --- BRANCH A: Standard Cubes with 6-Face Local UV ---
    mesh_cube = nodes.new('GeometryNodeMeshCube')
    mesh_cube.inputs['Size'].default_value = (1.0, 1.0, 1.0)
    mesh_cube.location = (-950, 500)

    # Store Face Normal directly on FACE domain of Base Cube
    norm_cube = nodes.new('GeometryNodeInputNormal')
    norm_cube.location = (-950, 650)

    store_face_norm = nodes.new('GeometryNodeStoreNamedAttribute')
    store_face_norm.data_type = 'FLOAT_VECTOR'
    store_face_norm.domain = 'FACE'
    store_face_norm.inputs['Name'].default_value = "CubeFaceNorm"
    store_face_norm.location = (-750, 500)
    links.new(mesh_cube.outputs['Mesh'], store_face_norm.inputs['Geometry'])
    links.new(norm_cube.outputs['Normal'], store_face_norm.inputs['Value'])

    # Position and Normal for Local UV
    pos_in = nodes.new('GeometryNodeInputPosition')
    pos_in.location = (-950, 850)
    sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    sep_pos.location = (-780, 850)
    links.new(pos_in.outputs['Position'], sep_pos.inputs['Vector'])

    sep_norm_cube = nodes.new('ShaderNodeSeparateXYZ')
    sep_norm_cube.location = (-580, 650)
    links.new(norm_cube.outputs['Normal'], sep_norm_cube.inputs['Vector'])

    # Direction comparisons for base cube local UV
    cmp_top = nodes.new('FunctionNodeCompare')
    cmp_top.data_type = 'FLOAT'
    cmp_top.operation = 'GREATER_THAN'
    cmp_top.inputs['B'].default_value = 0.5
    cmp_top.location = (-400, 1200)
    links.new(sep_norm_cube.outputs['Z'], cmp_top.inputs['A'])

    cmp_bottom = nodes.new('FunctionNodeCompare')
    cmp_bottom.data_type = 'FLOAT'
    cmp_bottom.operation = 'LESS_THAN'
    cmp_bottom.inputs['B'].default_value = -0.5
    cmp_bottom.location = (-400, 1100)
    links.new(sep_norm_cube.outputs['Z'], cmp_bottom.inputs['A'])

    cmp_east = nodes.new('FunctionNodeCompare')
    cmp_east.data_type = 'FLOAT'
    cmp_east.operation = 'GREATER_THAN'
    cmp_east.inputs['B'].default_value = 0.5
    cmp_east.location = (-400, 1000)
    links.new(sep_norm_cube.outputs['X'], cmp_east.inputs['A'])

    cmp_west = nodes.new('FunctionNodeCompare')
    cmp_west.data_type = 'FLOAT'
    cmp_west.operation = 'LESS_THAN'
    cmp_west.inputs['B'].default_value = -0.5
    cmp_west.location = (-400, 900)
    links.new(sep_norm_cube.outputs['X'], cmp_west.inputs['A'])

    cmp_north = nodes.new('FunctionNodeCompare')
    cmp_north.data_type = 'FLOAT'
    cmp_north.operation = 'LESS_THAN'
    cmp_north.inputs['B'].default_value = -0.5
    cmp_north.location = (-400, 800)
    links.new(sep_norm_cube.outputs['Y'], cmp_north.inputs['A'])

    add_x_05 = nodes.new('ShaderNodeMath')
    add_x_05.operation = 'ADD'
    add_x_05.inputs[1].default_value = 0.5
    add_x_05.location = (-600, 680)
    links.new(sep_pos.outputs['X'], add_x_05.inputs[0])

    sub_05_x = nodes.new('ShaderNodeMath')
    sub_05_x.operation = 'SUBTRACT'
    sub_05_x.inputs[0].default_value = 0.5
    sub_05_x.location = (-600, 580)
    links.new(sep_pos.outputs['X'], sub_05_x.inputs[1])

    add_y_05 = nodes.new('ShaderNodeMath')
    add_y_05.operation = 'ADD'
    add_y_05.inputs[1].default_value = 0.5
    add_y_05.location = (-600, 480)
    links.new(sep_pos.outputs['Y'], add_y_05.inputs[0])

    sub_05_y = nodes.new('ShaderNodeMath')
    sub_05_y.operation = 'SUBTRACT'
    sub_05_y.inputs[0].default_value = 0.5
    sub_05_y.location = (-600, 380)
    links.new(sep_pos.outputs['Y'], sub_05_y.inputs[1])

    add_z_05 = nodes.new('ShaderNodeMath')
    add_z_05.operation = 'ADD'
    add_z_05.inputs[1].default_value = 0.5
    add_z_05.location = (-600, 280)
    links.new(sep_pos.outputs['Z'], add_z_05.inputs[0])

    # Select local V
    mix_v1 = nodes.new('ShaderNodeMix')
    mix_v1.data_type = 'FLOAT'
    mix_v1.location = (-220, 1100)
    links.new(cmp_bottom.outputs['Result'], mix_v1.inputs[0])
    links.new(add_z_05.outputs['Value'], mix_v1.inputs[2])
    links.new(add_y_05.outputs['Value'], mix_v1.inputs[3])

    mix_v2 = nodes.new('ShaderNodeMix')
    mix_v2.data_type = 'FLOAT'
    mix_v2.location = (-60, 1100)
    links.new(cmp_top.outputs['Result'], mix_v2.inputs[0])
    links.new(mix_v1.outputs[0], mix_v2.inputs[2])
    links.new(sub_05_y.outputs['Value'], mix_v2.inputs[3])

    # Select local U
    mix_u1 = nodes.new('ShaderNodeMix')
    mix_u1.data_type = 'FLOAT'
    mix_u1.location = (-220, 900)
    links.new(cmp_north.outputs['Result'], mix_u1.inputs[0])
    links.new(add_x_05.outputs['Value'], mix_u1.inputs[2])
    links.new(sub_05_x.outputs['Value'], mix_u1.inputs[3])

    mix_u2 = nodes.new('ShaderNodeMix')
    mix_u2.data_type = 'FLOAT'
    mix_u2.location = (-60, 900)
    links.new(cmp_west.outputs['Result'], mix_u2.inputs[0])
    links.new(mix_u1.outputs[0], mix_u2.inputs[2])
    links.new(add_y_05.outputs['Value'], mix_u2.inputs[3])

    mix_u3 = nodes.new('ShaderNodeMix')
    mix_u3.data_type = 'FLOAT'
    mix_u3.location = (100, 900)
    links.new(cmp_east.outputs['Result'], mix_u3.inputs[0])
    links.new(mix_u2.outputs[0], mix_u3.inputs[2])
    links.new(sub_05_y.outputs['Value'], mix_u3.inputs[3])

    comb_local_uv = nodes.new('ShaderNodeCombineXYZ')
    comb_local_uv.location = (280, 1000)
    links.new(mix_u3.outputs[0], comb_local_uv.inputs['X'])
    links.new(mix_v2.outputs[0], comb_local_uv.inputs['Y'])

    store_local_uv = nodes.new('GeometryNodeStoreNamedAttribute')
    store_local_uv.data_type = 'FLOAT_VECTOR'
    store_local_uv.domain = 'CORNER'
    store_local_uv.inputs['Name'].default_value = "LocalUV"
    store_local_uv.location = (280, 500)
    links.new(store_face_norm.outputs['Geometry'], store_local_uv.inputs['Geometry'])
    links.new(comb_local_uv.outputs['Vector'], store_local_uv.inputs['Value'])

    # Instance Cubes on Selection Points
    iop_cube = nodes.new('GeometryNodeInstanceOnPoints')
    iop_cube.location = (480, 400)
    links.new(sep_geo.outputs['Selection'], iop_cube.inputs['Points'])
    cube_surface = nodes.new('GeometryNodeGroup')
    cube_surface.node_tree = group_cube_surface
    cube_surface.name = "Minecraft Cube Surface"
    cube_surface.label = "Cube Surface + Local UV"
    cube_surface.location = (280, 550)
    links.new(cube_surface.outputs['Geometry'], iop_cube.inputs['Instance'])

    last_cube_geo = iop_cube.outputs['Instances']

    # Pass the shared point-cloud render contract to INSTANCE domain.
    # Keep this in a group so the cube and prop branches cannot drift apart.
    transfer_cube_attributes = nodes.new('GeometryNodeGroup')
    transfer_cube_attributes.node_tree = group_attribute_transfer
    transfer_cube_attributes.name = "Transfer Cube Instance Attributes"
    transfer_cube_attributes.label = "Transfer Instance Attributes"
    transfer_cube_attributes.location = (700, 400)
    links.new(last_cube_geo, transfer_cube_attributes.inputs['Geometry'])
    last_cube_geo = transfer_cube_attributes.outputs['Geometry']

    # --- BRANCH B: Collection Props ---
    iop_prop = nodes.new('GeometryNodeInstanceOnPoints')
    iop_prop.inputs['Pick Instance'].default_value = True
    iop_prop.location = (480, -150)

    col_info = nodes.new('GeometryNodeCollectionInfo')
    col_info.inputs['Collection'].default_value = template_col
    col_info.inputs['Separate Children'].default_value = True
    col_info.inputs['Reset Children'].default_value = True
    col_info.location = (200, -150)

    links.new(sep_geo.outputs['Inverted'], iop_prop.inputs['Points'])
    links.new(col_info.outputs['Instances'], iop_prop.inputs['Instance'])
    links.new(attr_idx.outputs['Attribute'], iop_prop.inputs['Instance Index'])
    links.new(attr_rot.outputs['Attribute'], iop_prop.inputs['Rotation'])

    last_prop_geo = iop_prop.outputs['Instances']

    transfer_prop_attributes = nodes.new('GeometryNodeGroup')
    transfer_prop_attributes.node_tree = group_attribute_transfer
    transfer_prop_attributes.name = "Transfer Prop Instance Attributes"
    transfer_prop_attributes.label = "Transfer Instance Attributes"
    transfer_prop_attributes.location = (700, -150)
    links.new(last_prop_geo, transfer_prop_attributes.inputs['Geometry'])
    last_prop_geo = transfer_prop_attributes.outputs['Geometry']

    # --- JOIN BRANCHES & REALIZE ---
    join_node = nodes.new('GeometryNodeJoinGeometry')
    join_node.location = (1800, 100)
    links.new(last_cube_geo, join_node.inputs['Geometry'])
    links.new(last_prop_geo, join_node.inputs['Geometry'])

    realize_node = nodes.new('GeometryNodeRealizeInstances')
    realize_node.location = (2000, 100)
    links.new(join_node.outputs['Geometry'], realize_node.inputs['Geometry'])

    # Read Face Normal from Realized Mesh
    read_face_norm = nodes.new('GeometryNodeInputNamedAttribute')
    read_face_norm.data_type = 'FLOAT_VECTOR'
    read_face_norm.inputs['Name'].default_value = "CubeFaceNorm"
    read_face_norm.location = (2000, -100)

    # --- NODE GROUP: SELECT FACE TILE (VECTOR) ---
    call_tile_selector = nodes.new('GeometryNodeGroup')
    call_tile_selector.node_tree = group_vec_selector
    call_tile_selector.name = "Select Face Tile"
    call_tile_selector.location = (2250, 300)
    links.new(read_face_norm.outputs['Attribute'], call_tile_selector.inputs['Normal'])

    for socket_name, attr_name in (
        ('Top (+Z)', 'mtk_tile_top'),
        ('Bottom (-Z)', 'mtk_tile_bottom'),
        ('East (+X)', 'mtk_tile_east'),
        ('West (-X)', 'mtk_tile_west'),
        ('South (+Y)', 'mtk_tile_south'),
        ('North (-Y)', 'mtk_tile_north'),
    ):
        reader = nodes.new('GeometryNodeInputNamedAttribute')
        reader.data_type = 'FLOAT_VECTOR'
        reader.inputs['Name'].default_value = attr_name
        reader.location = (2050, 500)
        links.new(reader.outputs['Attribute'], call_tile_selector.inputs[socket_name])

    # --- NODE GROUP: ATLAS UV CALCULATOR ---
    call_uv_calc = nodes.new('GeometryNodeGroup')
    call_uv_calc.node_tree = group_uv_calc
    call_uv_calc.name = "Calculate Atlas UV"
    call_uv_calc.location = (2450, 300)
    links.new(call_tile_selector.outputs['Selected'], call_uv_calc.inputs['Target Tile'])

    read_local_uv = nodes.new('GeometryNodeInputNamedAttribute')
    read_local_uv.data_type = 'FLOAT_VECTOR'
    read_local_uv.inputs['Name'].default_value = "LocalUV"
    read_local_uv.location = (2250, 100)
    links.new(read_local_uv.outputs['Attribute'], call_uv_calc.inputs['Local UV'])

    for socket_name, attr_name in (
        ('Tiles Per Row', 'mtk_tiles_per_row'),
        ('Tile Size', 'mtk_tile_size'),
        ('Atlas Height', 'mtk_atlas_height'),
    ):
        reader = nodes.new('GeometryNodeInputNamedAttribute')
        reader.data_type = 'FLOAT'
        reader.inputs['Name'].default_value = attr_name
        reader.location = (2250, -50)
        links.new(reader.outputs['Attribute'], call_uv_calc.inputs[socket_name])

    # Store UVMap (CORNER)
    store_uv_final = nodes.new('GeometryNodeStoreNamedAttribute')
    store_uv_final.data_type = 'FLOAT_VECTOR'
    store_uv_final.domain = 'CORNER'
    store_uv_final.inputs['Name'].default_value = "UVMap"
    store_uv_final.location = (2650, 100)
    links.new(realize_node.outputs['Geometry'], store_uv_final.inputs['Geometry'])
    links.new(call_uv_calc.outputs['Atlas UV'], store_uv_final.inputs['Value'])

    # Store UV Tiling Transform
    store_tiling = nodes.new('GeometryNodeStoreNamedAttribute')
    store_tiling.data_type = 'FLOAT_COLOR'
    store_tiling.domain = 'CORNER'
    store_tiling.inputs['Name'].default_value = "mtk_uv_tiling_transform"
    store_tiling.inputs['Value'].default_value = (1.0, 1.0, 0.0, 0.0)
    store_tiling.location = (2800, 100)
    links.new(store_uv_final.outputs['Geometry'], store_tiling.inputs['Geometry'])

    # Store UV Rotation
    store_rot = nodes.new('GeometryNodeStoreNamedAttribute')
    store_rot.data_type = 'FLOAT'
    store_rot.domain = 'CORNER'
    store_rot.inputs['Name'].default_value = "mtk_uv_rotation"
    store_rot.inputs['Value'].default_value = 0.0
    store_rot.location = (2950, 100)
    links.new(store_tiling.outputs['Geometry'], store_rot.inputs['Geometry'])

    # --- NODE GROUP: SELECT FACE TINT DATA (COLOR) ---
    call_tint_selector = nodes.new('GeometryNodeGroup')
    call_tint_selector.node_tree = group_color_selector
    call_tint_selector.name = "Select Biome Tint Data"
    call_tint_selector.location = (2450, -200)
    links.new(read_face_norm.outputs['Attribute'], call_tint_selector.inputs['Normal'])

    for socket_name, face in (
        ('Top (+Z)', 'top'),
        ('Bottom (-Z)', 'bottom'),
        ('East (+X)', 'east'),
        ('West (-X)', 'west'),
        ('South (+Y)', 'south'),
        ('North (-Y)', 'north'),
    ):
        reader = nodes.new('GeometryNodeInputNamedAttribute')
        reader.data_type = 'FLOAT_COLOR'
        reader.inputs['Name'].default_value = f"mtk_tint_data_{face}"
        reader.location = (2250, -200)
        links.new(reader.outputs['Attribute'], call_tint_selector.inputs[socket_name])

    store_tint_data = nodes.new('GeometryNodeStoreNamedAttribute')
    store_tint_data.data_type = 'FLOAT_COLOR'
    store_tint_data.domain = 'FACE'
    store_tint_data.inputs['Name'].default_value = "mtk_biome_tint_data"
    store_tint_data.location = (2650, -100)
    links.new(store_rot.outputs['Geometry'], store_tint_data.inputs['Geometry'])
    links.new(call_tint_selector.outputs['Selected'], store_tint_data.inputs['Value'])

    # --- NODE GROUP: SELECT FACE CHUNK ID (INT) ---
    call_chunk_selector = nodes.new('GeometryNodeGroup')
    call_chunk_selector.node_tree = group_int_selector
    call_chunk_selector.name = "Select Face Chunk ID"
    call_chunk_selector.location = (2450, -400)
    links.new(read_face_norm.outputs['Attribute'], call_chunk_selector.inputs['Normal'])

    for socket_name, face in (
        ('Top (+Z)', 'top'),
        ('Bottom (-Z)', 'bottom'),
        ('East (+X)', 'east'),
        ('West (-X)', 'west'),
        ('South (+Y)', 'south'),
        ('North (-Y)', 'north'),
    ):
        reader = nodes.new('GeometryNodeInputNamedAttribute')
        reader.data_type = 'INT'
        reader.inputs['Name'].default_value = f"mtk_chunk_{face}"
        reader.location = (2250, -400)
        links.new(reader.outputs['Attribute'], call_chunk_selector.inputs[socket_name])

    store_chunk_id = nodes.new('GeometryNodeStoreNamedAttribute')
    store_chunk_id.data_type = 'INT'
    store_chunk_id.domain = 'FACE'
    store_chunk_id.inputs['Name'].default_value = "mtk_atlas_chunk_id"
    store_chunk_id.location = (2650, -300)
    links.new(store_tint_data.outputs['Geometry'], store_chunk_id.inputs['Geometry'])
    links.new(call_chunk_selector.outputs['Selected'], store_chunk_id.inputs['Value'])

    # --- NODE GROUP: SELECT FACE TEXTURE ID (INT) ---
    call_texture_selector = nodes.new('GeometryNodeGroup')
    call_texture_selector.node_tree = group_int_selector
    call_texture_selector.name = "Select Face Texture ID"
    call_texture_selector.location = (2450, -600)
    links.new(read_face_norm.outputs['Attribute'], call_texture_selector.inputs['Normal'])

    for socket_name, face in (
        ('Top (+Z)', 'top'),
        ('Bottom (-Z)', 'bottom'),
        ('East (+X)', 'east'),
        ('West (-X)', 'west'),
        ('South (+Y)', 'south'),
        ('North (-Y)', 'north'),
    ):
        reader = nodes.new('GeometryNodeInputNamedAttribute')
        reader.data_type = 'INT'
        reader.inputs['Name'].default_value = f"mtk_texture_{face}"
        reader.location = (2250, -600)
        links.new(reader.outputs['Attribute'], call_texture_selector.inputs[socket_name])

    store_texture_id = nodes.new('GeometryNodeStoreNamedAttribute')
    store_texture_id.data_type = 'INT'
    store_texture_id.domain = 'FACE'
    store_texture_id.inputs['Name'].default_value = "mtk_atlas_texture_id"
    store_texture_id.location = (2650, -500)
    links.new(store_chunk_id.outputs['Geometry'], store_texture_id.inputs['Geometry'])
    links.new(call_texture_selector.outputs['Selected'], store_texture_id.inputs['Value'])

    # --- SET MATERIAL INDEX ---
    # Directly set Material Index from chunk ID, enabling multi-chunk slot dispatching!
    set_mat_index = nodes.new('GeometryNodeSetMaterialIndex')
    set_mat_index.location = (2900, -300)
    links.new(store_texture_id.outputs['Geometry'], set_mat_index.inputs['Geometry'])
    links.new(call_chunk_selector.outputs['Selected'], set_mat_index.inputs['Material Index'])

    # Connect final geometry directly to Group Output (no single Set Material override!)
    links.new(set_mat_index.outputs['Geometry'], group_out.inputs['Geometry'])
    _prune_unlinked_nodes(gn_tree)
