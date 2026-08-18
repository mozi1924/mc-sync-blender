"""
Geometry Nodes World Tree Builder for Yefira Blender Plugin.
Generates a complete, high-performance procedural Minecraft world from Point Cloud attributes.
"""

from __future__ import annotations
import bpy
import logging
from ..materials.atlas_integration import get_or_create_atlas_material, setup_material_slots_for_object
from ..core.template_catalog import get_or_create_template_collection, TEMPLATE_COLLECTION_NAME

logger = logging.getLogger("Yefira")

WORLD_TREE_NAME = "Yefira_WorldTree"
WORLD_MODIFIER_NAME = "Yefira_WorldModifier"

def setup_world_geometry_nodes(world_obj: bpy.types.Object, template_col: bpy.types.Collection = None) -> bpy.types.Modifier:
    """
    Attach and configure the unified Geometry Nodes tree on the Yefira_World point cloud.
    Handles Cube instancing, Collection Info prop instancing, rotation, and Atlas Material binding.
    """
    if not world_obj:
        return None

    if not template_col:
        template_col = get_or_create_template_collection(bpy.context)

    mat = get_or_create_atlas_material()
    setup_material_slots_for_object(world_obj, mat)

    mod = world_obj.modifiers.get(WORLD_MODIFIER_NAME)
    if not mod:
        mod = world_obj.modifiers.new(name=WORLD_MODIFIER_NAME, type='NODES')

    # Recreate or update node group
    if WORLD_TREE_NAME in bpy.data.node_groups:
        gn_tree = bpy.data.node_groups[WORLD_TREE_NAME]
        gn_tree.nodes.clear()
        _build_tree_nodes_and_links(gn_tree, template_col, mat)
    else:
        gn_tree = _create_world_geometry_node_tree(WORLD_TREE_NAME, template_col, mat)

    mod.node_group = gn_tree
    return mod


def _create_world_geometry_node_tree(
    tree_name: str,
    template_col: bpy.types.Collection,
    mat: bpy.types.Material,
) -> bpy.types.GeometryNodeTree:
    gn_tree = bpy.data.node_groups.new(name=tree_name, type='GeometryNodeTree')
    gn_tree.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    gn_tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    _build_tree_nodes_and_links(gn_tree, template_col, mat)
    return gn_tree


def _build_tree_nodes_and_links(
    gn_tree: bpy.types.GeometryNodeTree,
    template_col: bpy.types.Collection,
    mat: bpy.types.Material,
):
    nodes = gn_tree.nodes
    links = gn_tree.links

    # 1. Inputs & Outputs
    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-1000, 0)

    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (1300, 0)

    # 2. Named Attribute Readers
    # A. block_type (INT)
    attr_type = nodes.new('GeometryNodeInputNamedAttribute')
    attr_type.data_type = 'INT'
    attr_type.inputs['Name'].default_value = "block_type"
    attr_type.location = (-1000, -250)

    # B. instance_index (INT)
    attr_idx = nodes.new('GeometryNodeInputNamedAttribute')
    attr_idx.data_type = 'INT'
    attr_idx.inputs['Name'].default_value = "instance_index"
    attr_idx.location = (-600, -350)

    # C. instance_rotation (FLOAT_VECTOR)
    attr_rot = nodes.new('GeometryNodeInputNamedAttribute')
    attr_rot.data_type = 'FLOAT_VECTOR'
    attr_rot.inputs['Name'].default_value = "instance_rotation"
    attr_rot.location = (-200, -400)

    # 3. Compare block_type == 0 (Cubes)
    cmp_cube = nodes.new('FunctionNodeCompare')
    cmp_cube.data_type = 'INT'
    cmp_cube.operation = 'EQUAL'
    cmp_cube.inputs['B'].default_value = 0 # Compare with 0 (Cube)
    cmp_cube.location = (-750, 100)
    links.new(attr_type.outputs['Attribute'], cmp_cube.inputs['A'])

    # 4. Separate Geometry (Cubes vs Props)
    sep_geo = nodes.new('GeometryNodeSeparateGeometry')
    sep_geo.location = (-550, 100)
    links.new(group_in.outputs['Geometry'], sep_geo.inputs['Geometry'])
    links.new(cmp_cube.outputs['Result'], sep_geo.inputs['Selection'])

    # --- BRANCH A: Standard Cubes with UVMap ---
    mesh_cube = nodes.new('GeometryNodeMeshCube')
    mesh_cube.inputs['Size'].default_value = (1.0, 1.0, 1.0)
    mesh_cube.location = (-400, 350)

    # Store UVMap attribute on the Cube mesh
    store_uv = nodes.new('GeometryNodeStoreNamedAttribute')
    store_uv.data_type = 'FLOAT_VECTOR'
    store_uv.domain = 'CORNER'
    store_uv.inputs['Name'].default_value = "UVMap"
    store_uv.location = (-200, 350)
    links.new(mesh_cube.outputs['Mesh'], store_uv.inputs['Geometry'])
    links.new(mesh_cube.outputs['UV Map'], store_uv.inputs['Value'])

    iop_cube = nodes.new('GeometryNodeInstanceOnPoints')
    iop_cube.location = (50, 200)
    links.new(sep_geo.outputs['Selection'], iop_cube.inputs['Points'])
    links.new(store_uv.outputs['Geometry'], iop_cube.inputs['Instance'])

    # --- BRANCH B: Collection Props ---
    iop_prop = nodes.new('GeometryNodeInstanceOnPoints')
    iop_prop.inputs['Pick Instance'].default_value = True
    iop_prop.location = (50, -150)

    col_info = nodes.new('GeometryNodeCollectionInfo')
    col_info.inputs['Collection'].default_value = template_col
    col_info.inputs['Separate Children'].default_value = True
    col_info.inputs['Reset Children'].default_value = True
    col_info.location = (-300, -150)

    links.new(sep_geo.outputs['Inverted'], iop_prop.inputs['Points'])
    links.new(col_info.outputs['Instances'], iop_prop.inputs['Instance'])
    links.new(attr_idx.outputs['Attribute'], iop_prop.inputs['Instance Index'])
    links.new(attr_rot.outputs['Attribute'], iop_prop.inputs['Rotation'])

    # --- JOIN BRANCHES ---
    join_node = nodes.new('GeometryNodeJoinGeometry')
    join_node.location = (350, 0)
    links.new(iop_cube.outputs['Instances'], join_node.inputs['Geometry'])
    links.new(iop_prop.outputs['Instances'], join_node.inputs['Geometry'])

    # --- REALIZE INSTANCES ---
    realize_node = nodes.new('GeometryNodeRealizeInstances')
    realize_node.location = (600, 0)
    links.new(join_node.outputs['Geometry'], realize_node.inputs['Geometry'])

    # --- SET MATERIAL ---
    set_mat = nodes.new('GeometryNodeSetMaterial')
    set_mat.inputs['Material'].default_value = mat
    set_mat.location = (900, 0)
    links.new(realize_node.outputs['Geometry'], set_mat.inputs['Geometry'])
    links.new(set_mat.outputs['Geometry'], group_out.inputs['Geometry'])
