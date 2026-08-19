"""Reusable Geometry Nodes building blocks for the Yefira world tree.

The public world tree intentionally contains only orchestration nodes.  The
implementation details that would otherwise make that tree difficult to read
live in these named node groups instead.
"""

from __future__ import annotations

import bpy


FACE_NAMES = ("top", "bottom", "east", "west", "south", "north")
FACE_TILE_ATTRIBUTES = tuple(f"mtk_tile_{face}" for face in FACE_NAMES)
FACE_INT_ATTRIBUTES = tuple(
    f"mtk_{kind}_{face}"
    for kind in ("chunk", "texture")
    for face in FACE_NAMES
)
ATLAS_FLOAT_ATTRIBUTES = (
    "mtk_atlas_width", "mtk_atlas_height", "mtk_tile_size", "mtk_tiles_per_row",
)
FACE_TINT_ATTRIBUTES = tuple(f"mtk_tint_data_{face}" for face in FACE_NAMES)


def ensure_socket(tree, name, in_out, socket_type, default_value=None):
    """Create an interface socket once and return it."""
    for item in tree.interface.items_tree:
        if item.item_type == 'SOCKET' and item.name == name and item.in_out == in_out:
            if default_value is not None and hasattr(item, "default_value"):
                item.default_value = default_value
            return item
    socket = tree.interface.new_socket(name=name, in_out=in_out, socket_type=socket_type)
    if default_value is not None and hasattr(socket, "default_value"):
        socket.default_value = default_value
    return socket


def _new_group(name: str):
    tree = bpy.data.node_groups.get(name)
    if tree and tree.get("yefira_group_version") == 1:
        return tree, False
    if not tree:
        tree = bpy.data.node_groups.new(name=name, type='GeometryNodeTree')
    tree.nodes.clear()
    return tree, True


def get_or_create_instance_attribute_transfer_group():
    """Copy all point-cloud rendering fields to the instance domain once.

    Both cube and collection-instance branches use the same contract, so the
    root graph no longer duplicates more than thirty reader/store node pairs.
    """
    tree, build = _new_group("Yefira_Transfer_Instance_Attributes")
    if not build:
        return tree
    ensure_socket(tree, "Geometry", 'INPUT', 'NodeSocketGeometry')
    ensure_socket(tree, "Geometry", 'OUTPUT', 'NodeSocketGeometry')
    nodes, links = tree.nodes, tree.links
    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-700, 0)
    last_geometry = group_in.outputs['Geometry']

    specs = (
        *((name, 'FLOAT_VECTOR') for name in FACE_TILE_ATTRIBUTES),
        *((name, 'INT') for name in FACE_INT_ATTRIBUTES),
        *((name, 'FLOAT') for name in ATLAS_FLOAT_ATTRIBUTES),
        *((name, 'FLOAT_COLOR') for name in FACE_TINT_ATTRIBUTES),
    )
    for index, (attribute, data_type) in enumerate(specs):
        reader = nodes.new('GeometryNodeInputNamedAttribute')
        reader.data_type = data_type
        reader.inputs['Name'].default_value = attribute
        reader.location = (-500, 300 - index * 45)
        store = nodes.new('GeometryNodeStoreNamedAttribute')
        store.data_type = data_type
        store.domain = 'INSTANCE'
        store.inputs['Name'].default_value = attribute
        store.location = (-100 + index * 150, 0)
        links.new(last_geometry, store.inputs['Geometry'])
        links.new(reader.outputs['Attribute'], store.inputs['Value'])
        last_geometry = store.outputs['Geometry']

    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (len(specs) * 150 + 80, 0)
    links.new(last_geometry, group_out.inputs['Geometry'])
    tree["yefira_group_version"] = 1
    tree["yefira_role"] = "instance_attribute_transfer"
    return tree


def get_or_create_cube_surface_group():
    """Build one Minecraft cube and attach stable face normal/local UV fields."""
    tree, build = _new_group("Yefira_Cube_Surface")
    if not build:
        return tree
    ensure_socket(tree, "Geometry", 'OUTPUT', 'NodeSocketGeometry')
    nodes, links = tree.nodes, tree.links
    cube = nodes.new('GeometryNodeMeshCube')
    cube.inputs['Size'].default_value = (1.0, 1.0, 1.0)
    cube.location = (-900, 0)
    normal = nodes.new('GeometryNodeInputNormal')
    normal.location = (-900, 250)
    store_normal = nodes.new('GeometryNodeStoreNamedAttribute')
    store_normal.data_type = 'FLOAT_VECTOR'
    store_normal.domain = 'FACE'
    store_normal.inputs['Name'].default_value = "CubeFaceNorm"
    store_normal.location = (-700, 0)
    links.new(cube.outputs['Mesh'], store_normal.inputs['Geometry'])
    links.new(normal.outputs['Normal'], store_normal.inputs['Value'])

    position = nodes.new('GeometryNodeInputPosition')
    position.location = (-900, 500)
    separate_pos = nodes.new('ShaderNodeSeparateXYZ')
    separate_pos.location = (-720, 500)
    links.new(position.outputs['Position'], separate_pos.inputs['Vector'])
    separate_normal = nodes.new('ShaderNodeSeparateXYZ')
    separate_normal.location = (-700, 250)
    links.new(normal.outputs['Normal'], separate_normal.inputs['Vector'])

    def compare(axis, operation, y):
        node = nodes.new('FunctionNodeCompare')
        node.data_type, node.operation = 'FLOAT', operation
        node.inputs['B'].default_value = 0.5 if operation == 'GREATER_THAN' else -0.5
        node.location = (-500, y)
        links.new(separate_normal.outputs[axis], node.inputs['A'])
        return node
    top = compare('Z', 'GREATER_THAN', 450)
    bottom = compare('Z', 'LESS_THAN', 350)
    east = compare('X', 'GREATER_THAN', 250)
    west = compare('X', 'LESS_THAN', 150)
    north = compare('Y', 'LESS_THAN', 50)

    def offset(axis, operation, y):
        node = nodes.new('ShaderNodeMath')
        node.operation = operation
        node.location = (-500, y)
        if operation == 'ADD':
            node.inputs[1].default_value = 0.5
            links.new(separate_pos.outputs[axis], node.inputs[0])
        else:
            node.inputs[0].default_value = 0.5
            links.new(separate_pos.outputs[axis], node.inputs[1])
        return node.outputs['Value']
    plus_x, minus_x = offset('X', 'ADD', -100), offset('X', 'SUBTRACT', -200)
    plus_y, minus_y = offset('Y', 'ADD', -300), offset('Y', 'SUBTRACT', -400)
    plus_z = offset('Z', 'ADD', -500)

    def mix(selector, false_value, true_value, x, y):
        node = nodes.new('ShaderNodeMix')
        node.data_type, node.location = 'FLOAT', (x, y)
        links.new(selector.outputs['Result'], node.inputs[0])
        links.new(false_value, node.inputs[2])
        links.new(true_value, node.inputs[3])
        return node.outputs[0]
    local_v = mix(top, mix(bottom, plus_y, plus_z, -250, 350), minus_y, -50, 350)
    local_u = mix(east, mix(west, mix(north, plus_x, minus_x, -250, 100), plus_y, -50, 100), minus_y, 150, 100)
    combine = nodes.new('ShaderNodeCombineXYZ')
    combine.location = (350, 250)
    links.new(local_u, combine.inputs['X'])
    links.new(local_v, combine.inputs['Y'])
    store_uv = nodes.new('GeometryNodeStoreNamedAttribute')
    store_uv.data_type, store_uv.domain = 'FLOAT_VECTOR', 'CORNER'
    store_uv.inputs['Name'].default_value = "LocalUV"
    store_uv.location = (550, 0)
    links.new(store_normal.outputs['Geometry'], store_uv.inputs['Geometry'])
    links.new(combine.outputs['Vector'], store_uv.inputs['Value'])
    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (750, 0)
    links.new(store_uv.outputs['Geometry'], group_out.inputs['Geometry'])
    tree["yefira_group_version"] = 1
    tree["yefira_role"] = "cube_surface"
    return tree
