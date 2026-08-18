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

logger = logging.getLogger("Yefira")

WORLD_TREE_NAME = "Yefira_WorldTree"
WORLD_MODIFIER_NAME = "Yefira_WorldModifier"
# Changing this is an explicit migration.  Point-cloud updates must never
# rebuild the node graph: doing so invalidates evaluation work and makes live
# sync depend on Blender's transient node/point ordering.
WORLD_TREE_SCHEMA_VERSION = 6
WORLD_TREE_SCHEMA_PROPERTY = "yefira:world_tree_schema"


def setup_world_geometry_nodes(world_obj: bpy.types.Object, template_col: bpy.types.Collection = None) -> Optional[bpy.types.Modifier]:
    """
    Attach and configure the unified Geometry Nodes tree on the Yefira_World point cloud.
    Handles Cube instancing, Collection Info prop instancing, rotation, and Atlas Material binding.
    """
    if not world_obj:
        return None

    if not template_col:
        template_col = get_or_create_template_collection(bpy.context)

    # Prefer the material slots already applied to this world.  Falling back
    # to a global data-block search here used to overwrite a valid replacement
    # with the first unrelated atlas chunk Blender happened to enumerate.
    mat = find_bound_atlas_material(world_obj) or get_or_create_atlas_material()
    setup_material_slots_for_object(world_obj, mat)

    atlas_params = extract_atlas_parameters(mat)

    mod = world_obj.modifiers.get(WORLD_MODIFIER_NAME)
    if not mod:
        mod = world_obj.modifiers.new(name=WORLD_MODIFIER_NAME, type='NODES')

    # Create the graph once, then retain it for all live point updates.  The
    # schema marker provides a controlled one-time migration for files made by
    # older versions of the add-on.
    gn_tree = bpy.data.node_groups.get(WORLD_TREE_NAME)
    if gn_tree and gn_tree.get(WORLD_TREE_SCHEMA_PROPERTY) == WORLD_TREE_SCHEMA_VERSION:
        _update_tree_bindings(gn_tree, template_col, mat)
    elif gn_tree:
        gn_tree.nodes.clear()
        _remove_legacy_atlas_inputs(gn_tree)
        _ensure_socket(gn_tree, "Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        _ensure_socket(gn_tree, "Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
        _build_tree_nodes_and_links(gn_tree, template_col, mat, atlas_params)
        gn_tree[WORLD_TREE_SCHEMA_PROPERTY] = WORLD_TREE_SCHEMA_VERSION
    else:
        gn_tree = _create_world_geometry_node_tree(WORLD_TREE_NAME, template_col, mat, atlas_params)
        gn_tree[WORLD_TREE_SCHEMA_PROPERTY] = WORLD_TREE_SCHEMA_VERSION

    mod.node_group = gn_tree

    return mod


def _update_tree_bindings(
    tree: bpy.types.GeometryNodeTree,
    template_col: bpy.types.Collection,
    mat: bpy.types.Material,
) -> None:
    """Refresh external data-block references without rebuilding nodes."""
    for node in tree.nodes:
        if node.bl_idname == 'GeometryNodeSetMaterial' and 'Material' in node.inputs:
            node.inputs['Material'].default_value = mat
        elif node.bl_idname == 'GeometryNodeCollectionInfo' and 'Collection' in node.inputs:
            node.inputs['Collection'].default_value = template_col


def _remove_legacy_atlas_inputs(tree: bpy.types.GeometryNodeTree) -> None:
    """Remove former user-facing atlas controls during the v5 migration."""
    for item in list(tree.interface.items_tree):
        if (
            item.item_type == 'SOCKET'
            and item.in_out == 'INPUT'
            and item.name in {"Atlas Width", "Atlas Height", "Tile Size", "Tiles Per Row"}
        ):
            tree.interface.remove(item)


def _create_world_geometry_node_tree(
    tree_name: str,
    template_col: bpy.types.Collection,
    mat: bpy.types.Material,
    atlas_params: dict[str, Any],
) -> bpy.types.GeometryNodeTree:
    gn_tree = bpy.data.node_groups.new(name=tree_name, type='GeometryNodeTree')
    _ensure_socket(gn_tree, "Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    _ensure_socket(gn_tree, "Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    _build_tree_nodes_and_links(gn_tree, template_col, mat, atlas_params)
    return gn_tree


def _ensure_socket(tree: bpy.types.GeometryNodeTree, name: str, in_out: str, socket_type: str, default_value=None, min_value=None):
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


def _build_tree_nodes_and_links(
    gn_tree: bpy.types.GeometryNodeTree,
    template_col: bpy.types.Collection,
    mat: bpy.types.Material,
    atlas_params: dict[str, Any],
):
    nodes = gn_tree.nodes
    links = gn_tree.links

    # 1. Inputs & Outputs
    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-1400, 0)

    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (2800, 0)

    # 2. Named Attribute Readers from Point Cloud
    # A. block_type (INT)
    attr_type = nodes.new('GeometryNodeInputNamedAttribute')
    attr_type.data_type = 'INT'
    attr_type.inputs['Name'].default_value = "block_type"
    attr_type.location = (-1400, -250)

    # B. instance_index (INT)
    attr_idx = nodes.new('GeometryNodeInputNamedAttribute')
    attr_idx.data_type = 'INT'
    attr_idx.inputs['Name'].default_value = "instance_index"
    attr_idx.location = (-1000, -350)

    # C. instance_rotation (FLOAT_VECTOR)
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

    # Direction comparisons for base cube
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

    # Coordinate arithmetic (X+0.5, 0.5-X, Y+0.5, 0.5-Y, Z+0.5)
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
    links.new(add_z_05.outputs['Value'], mix_v1.inputs[2]) # False: Z+0.5
    links.new(add_y_05.outputs['Value'], mix_v1.inputs[3]) # True: Y+0.5

    mix_v2 = nodes.new('ShaderNodeMix')
    mix_v2.data_type = 'FLOAT'
    mix_v2.location = (-60, 1100)
    links.new(cmp_top.outputs['Result'], mix_v2.inputs[0])
    links.new(mix_v1.outputs[0], mix_v2.inputs[2])         # False: mix_v1
    links.new(sub_05_y.outputs['Value'], mix_v2.inputs[3]) # True: 0.5-Y (Top)

    # Select local U
    mix_u1 = nodes.new('ShaderNodeMix')
    mix_u1.data_type = 'FLOAT'
    mix_u1.location = (-220, 900)
    links.new(cmp_north.outputs['Result'], mix_u1.inputs[0])
    links.new(add_x_05.outputs['Value'], mix_u1.inputs[2]) # False: X+0.5
    links.new(sub_05_x.outputs['Value'], mix_u1.inputs[3]) # True: 0.5-X (North)

    mix_u2 = nodes.new('ShaderNodeMix')
    mix_u2.data_type = 'FLOAT'
    mix_u2.location = (-60, 900)
    links.new(cmp_west.outputs['Result'], mix_u2.inputs[0])
    links.new(mix_u1.outputs[0], mix_u2.inputs[2])         # False: mix_u1
    links.new(add_y_05.outputs['Value'], mix_u2.inputs[3]) # True: Y+0.5 (West)

    mix_u3 = nodes.new('ShaderNodeMix')
    mix_u3.data_type = 'FLOAT'
    mix_u3.location = (100, 900)
    links.new(cmp_east.outputs['Result'], mix_u3.inputs[0])
    links.new(mix_u2.outputs[0], mix_u3.inputs[2])         # False: mix_u2
    links.new(sub_05_y.outputs['Value'], mix_u3.inputs[3]) # True: 0.5-Y (East)

    # Combine local UV
    comb_local_uv = nodes.new('ShaderNodeCombineXYZ')
    comb_local_uv.location = (280, 1000)
    links.new(mix_u3.outputs[0], comb_local_uv.inputs['X'])
    links.new(mix_v2.outputs[0], comb_local_uv.inputs['Y'])

    # Store LocalUV on Base Cube Mesh
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
    links.new(store_local_uv.outputs['Geometry'], iop_cube.inputs['Instance'])

    # Store 6-face tile coordinate attributes on INSTANCE domain for Cubes
    last_cube_geo = iop_cube.outputs['Instances']
    inst_store_x = 700
    for face_name in ("mtk_tile_top", "mtk_tile_bottom", "mtk_tile_east", "mtk_tile_west", "mtk_tile_south", "mtk_tile_north"):
        r_face = nodes.new('GeometryNodeInputNamedAttribute')
        r_face.data_type = 'FLOAT_VECTOR'
        r_face.inputs['Name'].default_value = face_name
        r_face.location = (inst_store_x, 600)

        st_face = nodes.new('GeometryNodeStoreNamedAttribute')
        st_face.data_type = 'FLOAT_VECTOR'
        st_face.domain = 'INSTANCE'
        st_face.inputs['Name'].default_value = face_name
        st_face.location = (inst_store_x, 400)

        links.new(last_cube_geo, st_face.inputs['Geometry'])
        links.new(r_face.outputs['Attribute'], st_face.inputs['Value'])
        last_cube_geo = st_face.outputs['Geometry']
        inst_store_x += 180

    # Preserve MoziToolKit's per-face atlas identity through instancing.
    # Tile coordinates alone are ambiguous when an atlas spans chunks.
    for attr_name in (
        "mtk_chunk_top", "mtk_chunk_bottom", "mtk_chunk_east", "mtk_chunk_west", "mtk_chunk_south", "mtk_chunk_north",
        "mtk_texture_top", "mtk_texture_bottom", "mtk_texture_east", "mtk_texture_west", "mtk_texture_south", "mtk_texture_north",
    ):
        reader = nodes.new('GeometryNodeInputNamedAttribute')
        reader.data_type = 'INT'
        reader.inputs['Name'].default_value = attr_name
        store = nodes.new('GeometryNodeStoreNamedAttribute')
        store.data_type = 'INT'
        store.domain = 'INSTANCE'
        store.inputs['Name'].default_value = attr_name
        links.new(last_cube_geo, store.inputs['Geometry'])
        links.new(reader.outputs['Attribute'], store.inputs['Value'])
        last_cube_geo = store.outputs['Geometry']

    for attr_name in ("mtk_atlas_width", "mtk_atlas_height", "mtk_tile_size", "mtk_tiles_per_row"):
        reader = nodes.new('GeometryNodeInputNamedAttribute')
        reader.data_type = 'FLOAT'
        reader.inputs['Name'].default_value = attr_name
        store = nodes.new('GeometryNodeStoreNamedAttribute')
        store.data_type = 'FLOAT'
        store.domain = 'INSTANCE'
        store.inputs['Name'].default_value = attr_name
        links.new(last_cube_geo, store.inputs['Geometry'])
        links.new(reader.outputs['Attribute'], store.inputs['Value'])
        last_cube_geo = store.outputs['Geometry']

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

    # Store 6-face tile coordinate attributes on INSTANCE domain for Props
    last_prop_geo = iop_prop.outputs['Instances']
    prop_store_x = 700
    for face_name in ("mtk_tile_top", "mtk_tile_bottom", "mtk_tile_east", "mtk_tile_west", "mtk_tile_south", "mtk_tile_north"):
        r_face_p = nodes.new('GeometryNodeInputNamedAttribute')
        r_face_p.data_type = 'FLOAT_VECTOR'
        r_face_p.inputs['Name'].default_value = face_name
        r_face_p.location = (prop_store_x, -50)

        st_face_p = nodes.new('GeometryNodeStoreNamedAttribute')
        st_face_p.data_type = 'FLOAT_VECTOR'
        st_face_p.domain = 'INSTANCE'
        st_face_p.inputs['Name'].default_value = face_name
        st_face_p.location = (prop_store_x, -250)

        links.new(last_prop_geo, st_face_p.inputs['Geometry'])
        links.new(r_face_p.outputs['Attribute'], st_face_p.inputs['Value'])
        last_prop_geo = st_face_p.outputs['Geometry']
        prop_store_x += 180

    for attr_name in (
        "mtk_chunk_top", "mtk_chunk_bottom", "mtk_chunk_east", "mtk_chunk_west", "mtk_chunk_south", "mtk_chunk_north",
        "mtk_texture_top", "mtk_texture_bottom", "mtk_texture_east", "mtk_texture_west", "mtk_texture_south", "mtk_texture_north",
    ):
        reader = nodes.new('GeometryNodeInputNamedAttribute')
        reader.data_type = 'INT'
        reader.inputs['Name'].default_value = attr_name
        store = nodes.new('GeometryNodeStoreNamedAttribute')
        store.data_type = 'INT'
        store.domain = 'INSTANCE'
        store.inputs['Name'].default_value = attr_name
        links.new(last_prop_geo, store.inputs['Geometry'])
        links.new(reader.outputs['Attribute'], store.inputs['Value'])
        last_prop_geo = store.outputs['Geometry']

    for attr_name in ("mtk_atlas_width", "mtk_atlas_height", "mtk_tile_size", "mtk_tiles_per_row"):
        reader = nodes.new('GeometryNodeInputNamedAttribute')
        reader.data_type = 'FLOAT'
        reader.inputs['Name'].default_value = attr_name
        store = nodes.new('GeometryNodeStoreNamedAttribute')
        store.data_type = 'FLOAT'
        store.domain = 'INSTANCE'
        store.inputs['Name'].default_value = attr_name
        links.new(last_prop_geo, store.inputs['Geometry'])
        links.new(reader.outputs['Attribute'], store.inputs['Value'])
        last_prop_geo = store.outputs['Geometry']

    # --- JOIN BRANCHES ---
    join_node = nodes.new('GeometryNodeJoinGeometry')
    join_node.location = (1800, 100)
    links.new(last_cube_geo, join_node.inputs['Geometry'])
    links.new(last_prop_geo, join_node.inputs['Geometry'])

    # --- REALIZE INSTANCES ---
    realize_node = nodes.new('GeometryNodeRealizeInstances')
    realize_node.location = (2000, 100)
    links.new(join_node.outputs['Geometry'], realize_node.inputs['Geometry'])

    # Read Face Normal from Realized Mesh for 6-Face Tile Selection
    read_face_norm = nodes.new('GeometryNodeInputNamedAttribute')
    read_face_norm.data_type = 'FLOAT_VECTOR'
    read_face_norm.inputs['Name'].default_value = "CubeFaceNorm"
    read_face_norm.location = (1100, -100)

    sep_norm_real = nodes.new('ShaderNodeSeparateXYZ')
    sep_norm_real.location = (1280, -100)
    links.new(read_face_norm.outputs['Attribute'], sep_norm_real.inputs['Vector'])

    cmp_top_r = nodes.new('FunctionNodeCompare')
    cmp_top_r.data_type = 'FLOAT'
    cmp_top_r.operation = 'GREATER_THAN'
    cmp_top_r.inputs['B'].default_value = 0.5
    cmp_top_r.location = (1460, 50)
    links.new(sep_norm_real.outputs['Z'], cmp_top_r.inputs['A'])

    cmp_bottom_r = nodes.new('FunctionNodeCompare')
    cmp_bottom_r.data_type = 'FLOAT'
    cmp_bottom_r.operation = 'LESS_THAN'
    cmp_bottom_r.inputs['B'].default_value = -0.5
    cmp_bottom_r.location = (1460, -50)
    links.new(sep_norm_real.outputs['Z'], cmp_bottom_r.inputs['A'])

    cmp_east_r = nodes.new('FunctionNodeCompare')
    cmp_east_r.data_type = 'FLOAT'
    cmp_east_r.operation = 'GREATER_THAN'
    cmp_east_r.inputs['B'].default_value = 0.5
    cmp_east_r.location = (1460, -150)
    links.new(sep_norm_real.outputs['X'], cmp_east_r.inputs['A'])

    cmp_west_r = nodes.new('FunctionNodeCompare')
    cmp_west_r.data_type = 'FLOAT'
    cmp_west_r.operation = 'LESS_THAN'
    cmp_west_r.inputs['B'].default_value = -0.5
    cmp_west_r.location = (1460, -250)
    links.new(sep_norm_real.outputs['X'], cmp_west_r.inputs['A'])

    cmp_north_r = nodes.new('FunctionNodeCompare')
    cmp_north_r.data_type = 'FLOAT'
    cmp_north_r.operation = 'LESS_THAN'
    cmp_north_r.inputs['B'].default_value = -0.5
    cmp_north_r.location = (1460, -350)
    links.new(sep_norm_real.outputs['Y'], cmp_north_r.inputs['A'])

    # Read 6 Face Tile Coordinate Attributes from Realized Mesh
    read_tile_top = nodes.new('GeometryNodeInputNamedAttribute')
    read_tile_top.data_type = 'FLOAT_VECTOR'
    read_tile_top.inputs['Name'].default_value = "mtk_tile_top"
    read_tile_top.location = (1280, -450)

    read_tile_bottom = nodes.new('GeometryNodeInputNamedAttribute')
    read_tile_bottom.data_type = 'FLOAT_VECTOR'
    read_tile_bottom.inputs['Name'].default_value = "mtk_tile_bottom"
    read_tile_bottom.location = (1280, -550)

    read_tile_east = nodes.new('GeometryNodeInputNamedAttribute')
    read_tile_east.data_type = 'FLOAT_VECTOR'
    read_tile_east.inputs['Name'].default_value = "mtk_tile_east"
    read_tile_east.location = (1280, -650)

    read_tile_west = nodes.new('GeometryNodeInputNamedAttribute')
    read_tile_west.data_type = 'FLOAT_VECTOR'
    read_tile_west.inputs['Name'].default_value = "mtk_tile_west"
    read_tile_west.location = (1280, -750)

    read_tile_south = nodes.new('GeometryNodeInputNamedAttribute')
    read_tile_south.data_type = 'FLOAT_VECTOR'
    read_tile_south.inputs['Name'].default_value = "mtk_tile_south"
    read_tile_south.location = (1280, -850)

    read_tile_north = nodes.new('GeometryNodeInputNamedAttribute')
    read_tile_north.data_type = 'FLOAT_VECTOR'
    read_tile_north.inputs['Name'].default_value = "mtk_tile_north"
    read_tile_north.location = (1280, -950)

    # Select Face Tile Coordinate:
    mix_tile1 = nodes.new('ShaderNodeMix')
    mix_tile1.data_type = 'VECTOR'
    mix_tile1.location = (1660, -350)
    links.new(cmp_north_r.outputs['Result'], mix_tile1.inputs[0])
    links.new(read_tile_south.outputs['Attribute'], mix_tile1.inputs[4])
    links.new(read_tile_north.outputs['Attribute'], mix_tile1.inputs[5])

    mix_tile2 = nodes.new('ShaderNodeMix')
    mix_tile2.data_type = 'VECTOR'
    mix_tile2.location = (1820, -350)
    links.new(cmp_east_r.outputs['Result'], mix_tile2.inputs[0])
    links.new(mix_tile1.outputs[1], mix_tile2.inputs[4])
    links.new(read_tile_east.outputs['Attribute'], mix_tile2.inputs[5])

    mix_tile3 = nodes.new('ShaderNodeMix')
    mix_tile3.data_type = 'VECTOR'
    mix_tile3.location = (1980, -350)
    links.new(cmp_west_r.outputs['Result'], mix_tile3.inputs[0])
    links.new(mix_tile2.outputs[1], mix_tile3.inputs[4])
    links.new(read_tile_west.outputs['Attribute'], mix_tile3.inputs[5])

    mix_tile4 = nodes.new('ShaderNodeMix')
    mix_tile4.data_type = 'VECTOR'
    mix_tile4.location = (2140, -350)
    links.new(cmp_bottom_r.outputs['Result'], mix_tile4.inputs[0])
    links.new(mix_tile3.outputs[1], mix_tile4.inputs[4])
    links.new(read_tile_bottom.outputs['Attribute'], mix_tile4.inputs[5])

    mix_tile5 = nodes.new('ShaderNodeMix')
    mix_tile5.data_type = 'VECTOR'
    mix_tile5.location = (2300, -350)
    links.new(cmp_top_r.outputs['Result'], mix_tile5.inputs[0])
    links.new(mix_tile4.outputs[1], mix_tile5.inputs[4])
    links.new(read_tile_top.outputs['Attribute'], mix_tile5.inputs[5])

    sep_target_tile = nodes.new('ShaderNodeSeparateXYZ')
    sep_target_tile.location = (1460, 200)
    links.new(mix_tile5.outputs[1], sep_target_tile.inputs['Vector'])

    # --- ATLAS UV TRANSFORMATION ---
    # Atlas dimensions are data, not artist controls.  MoziToolKit/Yefira
    # writes these named geometry attributes for every point before evaluation.
    attr_tile_size = nodes.new('GeometryNodeInputNamedAttribute')
    attr_tile_size.data_type = 'FLOAT'
    attr_tile_size.inputs['Name'].default_value = "mtk_tile_size"
    attr_tile_size.location = (1240, 560)

    attr_atlas_height = nodes.new('GeometryNodeInputNamedAttribute')
    attr_atlas_height.data_type = 'FLOAT'
    attr_atlas_height.inputs['Name'].default_value = "mtk_atlas_height"
    attr_atlas_height.location = (1240, 440)

    attr_tiles_per_row = nodes.new('GeometryNodeInputNamedAttribute')
    attr_tiles_per_row.data_type = 'FLOAT'
    attr_tiles_per_row.inputs['Name'].default_value = "mtk_tiles_per_row"
    attr_tiles_per_row.location = (1240, 680)

    step_u = nodes.new('ShaderNodeMath')
    step_u.operation = 'DIVIDE'
    step_u.location = (1460, 500)
    step_u.inputs[0].default_value = 1.0
    links.new(attr_tiles_per_row.outputs['Attribute'], step_u.inputs[1])

    step_v = nodes.new('ShaderNodeMath')
    step_v.operation = 'DIVIDE'
    step_v.location = (1460, 380)
    links.new(attr_tile_size.outputs['Attribute'], step_v.inputs[0])
    links.new(attr_atlas_height.outputs['Attribute'], step_v.inputs[1])

    read_local_uv = nodes.new('GeometryNodeInputNamedAttribute')
    read_local_uv.data_type = 'FLOAT_VECTOR'
    read_local_uv.inputs['Name'].default_value = "LocalUV"
    read_local_uv.location = (1460, -200)

    sep_local_uv = nodes.new('ShaderNodeSeparateXYZ')
    sep_local_uv.location = (1640, -200)
    links.new(read_local_uv.outputs['Attribute'], sep_local_uv.inputs['Vector'])

    # Atlas U = (col + local_u) * step_u
    col_plus_u = nodes.new('ShaderNodeMath')
    col_plus_u.operation = 'ADD'
    col_plus_u.location = (1680, 300)
    links.new(sep_target_tile.outputs['X'], col_plus_u.inputs[0])
    links.new(sep_local_uv.outputs['X'], col_plus_u.inputs[1])

    atlas_u = nodes.new('ShaderNodeMath')
    atlas_u.operation = 'MULTIPLY'
    atlas_u.location = (1840, 300)
    links.new(col_plus_u.outputs['Value'], atlas_u.inputs[0])
    links.new(step_u.outputs['Value'], atlas_u.inputs[1])

    # Atlas V = 1.0 - (row + (1.0 - local_v)) * step_v
    inv_v = nodes.new('ShaderNodeMath')
    inv_v.operation = 'SUBTRACT'
    inv_v.inputs[0].default_value = 1.0
    inv_v.location = (1680, 180)
    links.new(sep_local_uv.outputs['Y'], inv_v.inputs[1])

    row_plus_inv_v = nodes.new('ShaderNodeMath')
    row_plus_inv_v.operation = 'ADD'
    row_plus_inv_v.location = (1840, 180)
    links.new(sep_target_tile.outputs['Y'], row_plus_inv_v.inputs[0])
    links.new(inv_v.outputs['Value'], row_plus_inv_v.inputs[1])

    v_scaled = nodes.new('ShaderNodeMath')
    v_scaled.operation = 'MULTIPLY'
    v_scaled.location = (2000, 180)
    links.new(row_plus_inv_v.outputs['Value'], v_scaled.inputs[0])
    links.new(step_v.outputs['Value'], v_scaled.inputs[1])

    atlas_v = nodes.new('ShaderNodeMath')
    atlas_v.operation = 'SUBTRACT'
    atlas_v.inputs[0].default_value = 1.0
    atlas_v.location = (2160, 180)
    links.new(v_scaled.outputs['Value'], atlas_v.inputs[1])

    # Combine Atlas UV
    comb_atlas_uv = nodes.new('ShaderNodeCombineXYZ')
    comb_atlas_uv.location = (2320, 250)
    links.new(atlas_u.outputs['Value'], comb_atlas_uv.inputs['X'])
    links.new(atlas_v.outputs['Value'], comb_atlas_uv.inputs['Y'])

    # Store Final UVMap attribute on Realized Mesh
    store_uv_final = nodes.new('GeometryNodeStoreNamedAttribute')
    store_uv_final.data_type = 'FLOAT_VECTOR'
    store_uv_final.domain = 'CORNER'
    store_uv_final.inputs['Name'].default_value = "UVMap"
    store_uv_final.location = (2400, 50)
    links.new(realize_node.outputs['Geometry'], store_uv_final.inputs['Geometry'])
    links.new(comb_atlas_uv.outputs['Vector'], store_uv_final.inputs['Value'])

    # Store UV Tiling Transform attribute for downstream shaders (MC Atlas UV Tiling)
    store_tiling = nodes.new('GeometryNodeStoreNamedAttribute')
    store_tiling.data_type = 'FLOAT_COLOR'
    store_tiling.domain = 'CORNER'
    store_tiling.inputs['Name'].default_value = "mtk_uv_tiling_transform"
    store_tiling.inputs['Value'].default_value = (1.0, 1.0, 0.0, 0.0)
    store_tiling.location = (2550, 50)
    links.new(store_uv_final.outputs['Geometry'], store_tiling.inputs['Geometry'])

    # Store UV Rotation attribute for downstream shaders
    store_rot = nodes.new('GeometryNodeStoreNamedAttribute')
    store_rot.data_type = 'FLOAT'
    store_rot.domain = 'CORNER'
    store_rot.inputs['Name'].default_value = "mtk_uv_rotation"
    store_rot.inputs['Value'].default_value = 0.0
    store_rot.location = (2700, 50)
    links.new(store_tiling.outputs['Geometry'], store_rot.inputs['Geometry'])

    def selected_face_int_attribute(prefix: str, label: str):
        """Resolve one of six point attributes to a realized FACE attribute."""
        readers = {}
        for face in ("top", "bottom", "east", "west", "south", "north"):
            reader = nodes.new('GeometryNodeInputNamedAttribute')
            reader.data_type = 'INT'
            reader.inputs['Name'].default_value = f"{prefix}_{face}"
            readers[face] = reader

        def mix(compare, false_socket, true_socket):
            node = nodes.new('ShaderNodeMix')
            node.data_type = 'FLOAT'
            links.new(compare.outputs['Result'], node.inputs[0])
            links.new(false_socket, node.inputs[2])
            links.new(true_socket, node.inputs[3])
            return node.outputs[0]

        value = mix(cmp_north_r, readers['south'].outputs['Attribute'], readers['north'].outputs['Attribute'])
        value = mix(cmp_east_r, value, readers['east'].outputs['Attribute'])
        value = mix(cmp_west_r, value, readers['west'].outputs['Attribute'])
        value = mix(cmp_bottom_r, value, readers['bottom'].outputs['Attribute'])
        value = mix(cmp_top_r, value, readers['top'].outputs['Attribute'])
        store = nodes.new('GeometryNodeStoreNamedAttribute')
        store.data_type = 'INT'
        store.domain = 'FACE'
        store.inputs['Name'].default_value = label
        links.new(value, store.inputs['Value'])
        return store

    store_chunk_id = selected_face_int_attribute("mtk_chunk", "mtk_atlas_chunk_id")
    store_texture_id = selected_face_int_attribute("mtk_texture", "mtk_atlas_texture_id")
    links.new(store_rot.outputs['Geometry'], store_chunk_id.inputs['Geometry'])
    links.new(store_chunk_id.outputs['Geometry'], store_texture_id.inputs['Geometry'])

    # MoziToolKit emits one material per atlas chunk.  Resolve the material
    # number first, then apply the bound atlas material as the final geometry
    # operation.  In Blender's evaluator the reverse order can leave the
    # realized mesh with an unresolved material field (white viewport mesh).
    chunk_attr = nodes.new('GeometryNodeInputNamedAttribute')
    chunk_attr.data_type = 'INT'
    chunk_attr.inputs['Name'].default_value = "mtk_atlas_chunk_id"
    chunk_attr.location = (2850, -120)
    set_mat_index = nodes.new('GeometryNodeSetMaterialIndex')
    set_mat_index.location = (2900, 50)
    links.new(store_texture_id.outputs['Geometry'], set_mat_index.inputs['Geometry'])
    links.new(chunk_attr.outputs['Attribute'], set_mat_index.inputs['Material Index'])

    # --- SET MATERIAL ---
    set_mat = nodes.new('GeometryNodeSetMaterial')
    set_mat.inputs['Material'].default_value = mat
    set_mat.location = (3050, 50)
    links.new(set_mat_index.outputs['Geometry'], set_mat.inputs['Geometry'])
    links.new(set_mat.outputs['Geometry'], group_out.inputs['Geometry'])
