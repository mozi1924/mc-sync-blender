"""Procedural 1x1x1 Minecraft Cube geometry generator with Face Normal and Local UV attributes."""

from __future__ import annotations

import bpy
from ..core import ensure_gn_group, ensure_socket, finalize_group

GROUP_NAME_CUBE_SURFACE = "Yefira_Cube_Surface"
CUBE_SURFACE_VERSION = 2


def get_or_create_cube_surface_group() -> bpy.types.GeometryNodeTree:
    """
    Build a standard 1x1x1 Minecraft cube and attach stable face normal/local UV fields.
    Outputs:
        - Geometry: Mesh with 'CubeFaceNorm' on FACE domain and 'LocalUV' on CORNER domain.
    """
    tree, needs_build = ensure_gn_group(GROUP_NAME_CUBE_SURFACE, CUBE_SURFACE_VERSION)
    if not needs_build:
        return tree

    ensure_socket(tree, "Geometry", "OUTPUT", "NodeSocketGeometry")
    nodes, links = tree.nodes, tree.links

    # 1. Base Mesh Cube
    cube = nodes.new("GeometryNodeMeshCube")
    cube.inputs["Size"].default_value = (1.0, 1.0, 1.0)
    cube.location = (-650, 0)

    # 2. Store Face Normal on FACE domain
    normal = nodes.new("GeometryNodeInputNormal")
    normal.location = (-650, 250)

    store_normal = nodes.new("GeometryNodeStoreNamedAttribute")
    store_normal.data_type = "FLOAT_VECTOR"
    store_normal.domain = "FACE"
    store_normal.inputs["Name"].default_value = "CubeFaceNorm"
    store_normal.location = (-460, 0)
    links.new(cube.outputs["Mesh"], store_normal.inputs["Geometry"])
    links.new(normal.outputs["Normal"], store_normal.inputs["Value"])

    # 3. Position and Normal Deconstruction for 6-Face Local UV calculation
    position = nodes.new("GeometryNodeInputPosition")
    position.location = (-650, 480)
    separate_pos = nodes.new("ShaderNodeSeparateXYZ")
    separate_pos.location = (-460, 480)
    links.new(position.outputs["Position"], separate_pos.inputs["Vector"])

    separate_normal = nodes.new("ShaderNodeSeparateXYZ")
    separate_normal.location = (-460, 250)
    links.new(normal.outputs["Normal"], separate_normal.inputs["Vector"])

    def compare(axis: str, operation: str, y: float) -> bpy.types.Node:
        node = nodes.new("FunctionNodeCompare")
        node.data_type, node.operation = "FLOAT", operation
        node.inputs["B"].default_value = 0.5 if operation == "GREATER_THAN" else -0.5
        node.location = (-260, y)
        links.new(separate_normal.outputs[axis], node.inputs["A"])
        return node

    top = compare("Z", "GREATER_THAN", 400)
    bottom = compare("Z", "LESS_THAN", 300)
    east = compare("X", "GREATER_THAN", 200)
    west = compare("X", "LESS_THAN", 100)
    north = compare("Y", "LESS_THAN", 0)

    def offset(axis: str, operation: str, y: float):
        node = nodes.new("ShaderNodeMath")
        node.operation = operation
        node.location = (-260, y)
        if operation == "ADD":
            node.inputs[1].default_value = 0.5
            links.new(separate_pos.outputs[axis], node.inputs[0])
        else:
            node.inputs[0].default_value = 0.5
            links.new(separate_pos.outputs[axis], node.inputs[1])
        return node.outputs["Value"]

    plus_x, minus_x = offset("X", "ADD", -120), offset("X", "SUBTRACT", -200)
    plus_y, minus_y = offset("Y", "ADD", -280), offset("Y", "SUBTRACT", -360)
    plus_z = offset("Z", "ADD", -440)

    def mix(selector: bpy.types.Node, false_value, true_value, x: float, y: float):
        node = nodes.new("ShaderNodeMix")
        node.data_type, node.location = "FLOAT", (x, y)
        links.new(selector.outputs["Result"], node.inputs[0])
        links.new(false_value, node.inputs[2])
        links.new(true_value, node.inputs[3])
        return node.outputs[0]

    local_v = mix(top, mix(bottom, plus_y, plus_z, -60, 320), minus_y, 120, 320)
    local_u = mix(east, mix(west, mix(north, plus_x, minus_x, -60, 100), plus_y, 120, 100), minus_y, 300, 100)

    combine = nodes.new("ShaderNodeCombineXYZ")
    combine.location = (480, 200)
    links.new(local_u, combine.inputs["X"])
    links.new(local_v, combine.inputs["Y"])

    # 4. Store LocalUV on CORNER domain
    store_uv = nodes.new("GeometryNodeStoreNamedAttribute")
    store_uv.data_type, store_uv.domain = "FLOAT_VECTOR", "CORNER"
    store_uv.inputs["Name"].default_value = "LocalUV"
    store_uv.location = (660, 0)
    links.new(store_normal.outputs["Geometry"], store_uv.inputs["Geometry"])
    links.new(combine.outputs["Vector"], store_uv.inputs["Value"])

    # 5. Output
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (840, 0)
    links.new(store_uv.outputs["Geometry"], group_out.inputs["Geometry"])

    tree["yefira_role"] = "cube_surface"
    return finalize_group(tree)
