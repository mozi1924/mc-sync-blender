"""Calculates UVMap coordinate in non-square Atlas texture space from Local UV and Tile coordinate."""

from __future__ import annotations

import bpy
from ..core import ensure_gn_group, ensure_socket, finalize_group

GROUP_NAME_ATLAS_UV_CALCULATOR = "Yefira_Atlas_UV_Calculator"
ATLAS_UV_CALCULATOR_VERSION = 2


def get_or_create_atlas_uv_calculator_group() -> bpy.types.GeometryNodeTree:
    """
    Reusable node group: Calculates UVMap coordinate in Atlas space from LocalUV and Tile Col/Row.
    Inputs:
        - Target Tile (Vector): (col, row, _)
        - Local UV (Vector): (u, v, _)
        - Tiles Per Row (Float): e.g. 64.0
        - Tile Size (Float): e.g. 16.0
        - Atlas Height (Float): e.g. 1024.0
    Outputs:
        - Atlas UV (Vector): (atlas_u, atlas_v, 0.0)
    """
    tree, needs_build = ensure_gn_group(GROUP_NAME_ATLAS_UV_CALCULATOR, ATLAS_UV_CALCULATOR_VERSION)
    if not needs_build:
        return tree

    ensure_socket(tree, "Target Tile", "INPUT", "NodeSocketVector")
    ensure_socket(tree, "Local UV", "INPUT", "NodeSocketVector")
    ensure_socket(tree, "Tiles Per Row", "INPUT", "NodeSocketFloat", default_value=64.0)
    ensure_socket(tree, "Tile Size", "INPUT", "NodeSocketFloat", default_value=16.0)
    ensure_socket(tree, "Atlas Height", "INPUT", "NodeSocketFloat", default_value=1024.0)
    ensure_socket(tree, "Atlas UV", "OUTPUT", "NodeSocketVector")

    nodes, links = tree.nodes, tree.links
    gin = nodes.new("NodeGroupInput")
    gin.location = (-450, 0)
    gout = nodes.new("NodeGroupOutput")
    gout.location = (720, 20)

    sep_target = nodes.new("ShaderNodeSeparateXYZ")
    sep_target.location = (-280, 120)
    links.new(gin.outputs["Target Tile"], sep_target.inputs["Vector"])

    sep_local = nodes.new("ShaderNodeSeparateXYZ")
    sep_local.location = (-280, -120)
    links.new(gin.outputs["Local UV"], sep_local.inputs["Vector"])

    step_u = nodes.new("ShaderNodeMath")
    step_u.operation = "DIVIDE"
    step_u.inputs[0].default_value = 1.0
    step_u.location = (-100, 200)
    links.new(gin.outputs["Tiles Per Row"], step_u.inputs[1])

    step_v = nodes.new("ShaderNodeMath")
    step_v.operation = "DIVIDE"
    step_v.location = (-100, -180)
    links.new(gin.outputs["Tile Size"], step_v.inputs[0])
    links.new(gin.outputs["Atlas Height"], step_v.inputs[1])

    col_plus_u = nodes.new("ShaderNodeMath")
    col_plus_u.operation = "ADD"
    col_plus_u.location = (-100, 80)
    links.new(sep_target.outputs["X"], col_plus_u.inputs[0])
    links.new(sep_local.outputs["X"], col_plus_u.inputs[1])

    atlas_u = nodes.new("ShaderNodeMath")
    atlas_u.operation = "MULTIPLY"
    atlas_u.location = (80, 100)
    links.new(col_plus_u.outputs["Value"], atlas_u.inputs[0])
    links.new(step_u.outputs["Value"], atlas_u.inputs[1])

    inv_v = nodes.new("ShaderNodeMath")
    inv_v.operation = "SUBTRACT"
    inv_v.inputs[0].default_value = 1.0
    inv_v.location = (-100, -60)
    links.new(sep_local.outputs["Y"], inv_v.inputs[1])

    row_plus_inv_v = nodes.new("ShaderNodeMath")
    row_plus_inv_v.operation = "ADD"
    row_plus_inv_v.location = (80, -60)
    links.new(sep_target.outputs["Y"], row_plus_inv_v.inputs[0])
    links.new(inv_v.outputs["Value"], row_plus_inv_v.inputs[1])

    v_scaled = nodes.new("ShaderNodeMath")
    v_scaled.operation = "MULTIPLY"
    v_scaled.location = (240, -60)
    links.new(row_plus_inv_v.outputs["Value"], v_scaled.inputs[0])
    links.new(step_v.outputs["Value"], v_scaled.inputs[1])

    atlas_v = nodes.new("ShaderNodeMath")
    atlas_v.operation = "SUBTRACT"
    atlas_v.inputs[0].default_value = 1.0
    atlas_v.location = (400, -60)
    links.new(v_scaled.outputs["Value"], atlas_v.inputs[1])

    comb = nodes.new("ShaderNodeCombineXYZ")
    comb.location = (560, 20)
    links.new(atlas_u.outputs["Value"], comb.inputs["X"])
    links.new(atlas_v.outputs["Value"], comb.inputs["Y"])
    links.new(comb.outputs["Vector"], gout.inputs["Atlas UV"])

    return finalize_group(tree)
