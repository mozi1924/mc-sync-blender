"""Reusable Face Selector node groups (Vector, Int, Color) that dispatch 6-face attributes based on Normal."""

from __future__ import annotations

import bpy
from ..core import ensure_gn_group, ensure_socket, finalize_group

GROUP_NAME_FACE_SELECTOR_VECTOR = "Yefira_Face_Selector_Vector"
GROUP_NAME_FACE_SELECTOR_INT = "Yefira_Face_Selector_Int"
GROUP_NAME_FACE_SELECTOR_COLOR = "Yefira_Face_Selector_Color"
FACE_SELECTOR_VERSION = 3


def get_or_create_face_selector_vector_group() -> bpy.types.GeometryNodeTree:
    """Reusable node group: Selects a Vector from 6 face inputs based on Face Normal."""
    tree, needs_build = ensure_gn_group(GROUP_NAME_FACE_SELECTOR_VECTOR, FACE_SELECTOR_VERSION)
    if not needs_build:
        return tree

    ensure_socket(tree, "Normal", "INPUT", "NodeSocketVector")
    ensure_socket(tree, "North (+Y)", "INPUT", "NodeSocketVector")
    ensure_socket(tree, "South (-Y)", "INPUT", "NodeSocketVector")
    ensure_socket(tree, "East (+X)", "INPUT", "NodeSocketVector")
    ensure_socket(tree, "West (-X)", "INPUT", "NodeSocketVector")
    ensure_socket(tree, "Bottom (-Z)", "INPUT", "NodeSocketVector")
    ensure_socket(tree, "Top (+Z)", "INPUT", "NodeSocketVector")
    ensure_socket(tree, "Selected", "OUTPUT", "NodeSocketVector")

    nodes, links = tree.nodes, tree.links
    gin = nodes.new("NodeGroupInput")
    gin.location = (-500, 0)
    gout = nodes.new("NodeGroupOutput")
    gout.location = (880, -60)

    sep_norm = nodes.new("ShaderNodeSeparateXYZ")
    sep_norm.location = (-320, 150)
    links.new(gin.outputs["Normal"], sep_norm.inputs["Vector"])

    cmp_south = nodes.new("FunctionNodeCompare")
    cmp_south.data_type, cmp_south.operation = "FLOAT", "LESS_THAN"
    cmp_south.inputs["B"].default_value = -0.5
    cmp_south.location = (-140, 240)
    links.new(sep_norm.outputs["Y"], cmp_south.inputs["A"])

    cmp_east = nodes.new("FunctionNodeCompare")
    cmp_east.data_type, cmp_east.operation = "FLOAT", "GREATER_THAN"
    cmp_east.inputs["B"].default_value = 0.5
    cmp_east.location = (-140, 120)
    links.new(sep_norm.outputs["X"], cmp_east.inputs["A"])

    cmp_west = nodes.new("FunctionNodeCompare")
    cmp_west.data_type, cmp_west.operation = "FLOAT", "LESS_THAN"
    cmp_west.inputs["B"].default_value = -0.5
    cmp_west.location = (-140, 0)
    links.new(sep_norm.outputs["X"], cmp_west.inputs["A"])

    cmp_bottom = nodes.new("FunctionNodeCompare")
    cmp_bottom.data_type, cmp_bottom.operation = "FLOAT", "LESS_THAN"
    cmp_bottom.inputs["B"].default_value = -0.5
    cmp_bottom.location = (-140, -120)
    links.new(sep_norm.outputs["Z"], cmp_bottom.inputs["A"])

    cmp_top = nodes.new("FunctionNodeCompare")
    cmp_top.data_type, cmp_top.operation = "FLOAT", "GREATER_THAN"
    cmp_top.inputs["B"].default_value = 0.5
    cmp_top.location = (-140, -240)
    links.new(sep_norm.outputs["Z"], cmp_top.inputs["A"])

    m1 = nodes.new("ShaderNodeMix")
    m1.data_type, m1.location = "VECTOR", (60, 180)
    links.new(cmp_south.outputs["Result"], m1.inputs[0])
    links.new(gin.outputs["North (+Y)"], m1.inputs[4])
    links.new(gin.outputs["South (-Y)"], m1.inputs[5])

    m2 = nodes.new("ShaderNodeMix")
    m2.data_type, m2.location = "VECTOR", (220, 120)
    links.new(cmp_east.outputs["Result"], m2.inputs[0])
    links.new(m1.outputs[1], m2.inputs[4])
    links.new(gin.outputs["East (+X)"], m2.inputs[5])

    m3 = nodes.new("ShaderNodeMix")
    m3.data_type, m3.location = "VECTOR", (380, 60)
    links.new(cmp_west.outputs["Result"], m3.inputs[0])
    links.new(m2.outputs[1], m3.inputs[4])
    links.new(gin.outputs["West (-X)"], m3.inputs[5])

    m4 = nodes.new("ShaderNodeMix")
    m4.data_type, m4.location = "VECTOR", (540, 0)
    links.new(cmp_bottom.outputs["Result"], m4.inputs[0])
    links.new(m3.outputs[1], m4.inputs[4])
    links.new(gin.outputs["Bottom (-Z)"], m4.inputs[5])

    m5 = nodes.new("ShaderNodeMix")
    m5.data_type, m5.location = "VECTOR", (700, -60)
    links.new(cmp_top.outputs["Result"], m5.inputs[0])
    links.new(m4.outputs[1], m5.inputs[4])
    links.new(gin.outputs["Top (+Z)"], m5.inputs[5])

    links.new(m5.outputs[1], gout.inputs["Selected"])
    return finalize_group(tree)


def get_or_create_face_selector_int_group() -> bpy.types.GeometryNodeTree:
    """Reusable node group: Selects an Integer from 6 face inputs based on Face Normal."""
    tree, needs_build = ensure_gn_group(GROUP_NAME_FACE_SELECTOR_INT, FACE_SELECTOR_VERSION)
    if not needs_build:
        return tree

    ensure_socket(tree, "Normal", "INPUT", "NodeSocketVector")
    ensure_socket(tree, "North (+Y)", "INPUT", "NodeSocketInt", default_value=0)
    ensure_socket(tree, "South (-Y)", "INPUT", "NodeSocketInt", default_value=0)
    ensure_socket(tree, "East (+X)", "INPUT", "NodeSocketInt", default_value=0)
    ensure_socket(tree, "West (-X)", "INPUT", "NodeSocketInt", default_value=0)
    ensure_socket(tree, "Bottom (-Z)", "INPUT", "NodeSocketInt", default_value=0)
    ensure_socket(tree, "Top (+Z)", "INPUT", "NodeSocketInt", default_value=0)
    ensure_socket(tree, "Selected", "OUTPUT", "NodeSocketInt")

    nodes, links = tree.nodes, tree.links
    gin = nodes.new("NodeGroupInput")
    gin.location = (-500, 0)
    gout = nodes.new("NodeGroupOutput")
    gout.location = (880, -60)

    sep_norm = nodes.new("ShaderNodeSeparateXYZ")
    sep_norm.location = (-320, 150)
    links.new(gin.outputs["Normal"], sep_norm.inputs["Vector"])

    cmp_south = nodes.new("FunctionNodeCompare")
    cmp_south.data_type, cmp_south.operation = "FLOAT", "LESS_THAN"
    cmp_south.inputs["B"].default_value = -0.5
    cmp_south.location = (-140, 240)
    links.new(sep_norm.outputs["Y"], cmp_south.inputs["A"])

    cmp_east = nodes.new("FunctionNodeCompare")
    cmp_east.data_type, cmp_east.operation = "FLOAT", "GREATER_THAN"
    cmp_east.inputs["B"].default_value = 0.5
    cmp_east.location = (-140, 120)
    links.new(sep_norm.outputs["X"], cmp_east.inputs["A"])

    cmp_west = nodes.new("FunctionNodeCompare")
    cmp_west.data_type, cmp_west.operation = "FLOAT", "LESS_THAN"
    cmp_west.inputs["B"].default_value = -0.5
    cmp_west.location = (-140, 0)
    links.new(sep_norm.outputs["X"], cmp_west.inputs["A"])

    cmp_bottom = nodes.new("FunctionNodeCompare")
    cmp_bottom.data_type, cmp_bottom.operation = "FLOAT", "LESS_THAN"
    cmp_bottom.inputs["B"].default_value = -0.5
    cmp_bottom.location = (-140, -120)
    links.new(sep_norm.outputs["Z"], cmp_bottom.inputs["A"])

    cmp_top = nodes.new("FunctionNodeCompare")
    cmp_top.data_type, cmp_top.operation = "FLOAT", "GREATER_THAN"
    cmp_top.inputs["B"].default_value = 0.5
    cmp_top.location = (-140, -240)
    links.new(sep_norm.outputs["Z"], cmp_top.inputs["A"])

    def make_switch(compare_node, false_socket, true_socket, x: float, y: float):
        sw = nodes.new("GeometryNodeSwitch")
        sw.input_type = "INT"
        sw.location = (x, y)
        links.new(compare_node.outputs["Result"], sw.inputs["Switch"])
        links.new(false_socket, sw.inputs["False"])
        links.new(true_socket, sw.inputs["True"])
        return sw.outputs["Output"]

    v1 = make_switch(cmp_south, gin.outputs["North (+Y)"], gin.outputs["South (-Y)"], 60, 180)
    v2 = make_switch(cmp_east, v1, gin.outputs["East (+X)"], 220, 120)
    v3 = make_switch(cmp_west, v2, gin.outputs["West (-X)"], 380, 60)
    v4 = make_switch(cmp_bottom, v3, gin.outputs["Bottom (-Z)"], 540, 0)
    v5 = make_switch(cmp_top, v4, gin.outputs["Top (+Z)"], 700, -60)

    links.new(v5, gout.inputs["Selected"])
    return finalize_group(tree)


def get_or_create_face_selector_color_group() -> bpy.types.GeometryNodeTree:
    """Reusable node group: Selects a Color (RGBA) from 6 face inputs based on Face Normal."""
    tree, needs_build = ensure_gn_group(GROUP_NAME_FACE_SELECTOR_COLOR, FACE_SELECTOR_VERSION)
    if not needs_build:
        return tree

    ensure_socket(tree, "Normal", "INPUT", "NodeSocketVector")
    ensure_socket(tree, "North (+Y)", "INPUT", "NodeSocketColor")
    ensure_socket(tree, "South (-Y)", "INPUT", "NodeSocketColor")
    ensure_socket(tree, "East (+X)", "INPUT", "NodeSocketColor")
    ensure_socket(tree, "West (-X)", "INPUT", "NodeSocketColor")
    ensure_socket(tree, "Bottom (-Z)", "INPUT", "NodeSocketColor")
    ensure_socket(tree, "Top (+Z)", "INPUT", "NodeSocketColor")
    ensure_socket(tree, "Selected", "OUTPUT", "NodeSocketColor")

    nodes, links = tree.nodes, tree.links
    gin = nodes.new("NodeGroupInput")
    gin.location = (-500, 0)
    gout = nodes.new("NodeGroupOutput")
    gout.location = (880, -60)

    sep_norm = nodes.new("ShaderNodeSeparateXYZ")
    sep_norm.location = (-320, 150)
    links.new(gin.outputs["Normal"], sep_norm.inputs["Vector"])

    cmp_south = nodes.new("FunctionNodeCompare")
    cmp_south.data_type, cmp_south.operation = "FLOAT", "LESS_THAN"
    cmp_south.inputs["B"].default_value = -0.5
    cmp_south.location = (-140, 240)
    links.new(sep_norm.outputs["Y"], cmp_south.inputs["A"])

    cmp_east = nodes.new("FunctionNodeCompare")
    cmp_east.data_type, cmp_east.operation = "FLOAT", "GREATER_THAN"
    cmp_east.inputs["B"].default_value = 0.5
    cmp_east.location = (-140, 120)
    links.new(sep_norm.outputs["X"], cmp_east.inputs["A"])

    cmp_west = nodes.new("FunctionNodeCompare")
    cmp_west.data_type, cmp_west.operation = "FLOAT", "LESS_THAN"
    cmp_west.inputs["B"].default_value = -0.5
    cmp_west.location = (-140, 0)
    links.new(sep_norm.outputs["X"], cmp_west.inputs["A"])

    cmp_bottom = nodes.new("FunctionNodeCompare")
    cmp_bottom.data_type, cmp_bottom.operation = "FLOAT", "LESS_THAN"
    cmp_bottom.inputs["B"].default_value = -0.5
    cmp_bottom.location = (-140, -120)
    links.new(sep_norm.outputs["Z"], cmp_bottom.inputs["A"])

    cmp_top = nodes.new("FunctionNodeCompare")
    cmp_top.data_type, cmp_top.operation = "FLOAT", "GREATER_THAN"
    cmp_top.inputs["B"].default_value = 0.5
    cmp_top.location = (-140, -240)
    links.new(sep_norm.outputs["Z"], cmp_top.inputs["A"])

    m1 = nodes.new("ShaderNodeMix")
    m1.data_type, m1.location = "RGBA", (60, 180)
    links.new(cmp_south.outputs["Result"], m1.inputs[0])
    links.new(gin.outputs["North (+Y)"], m1.inputs[6])
    links.new(gin.outputs["South (-Y)"], m1.inputs[7])

    m2 = nodes.new("ShaderNodeMix")
    m2.data_type, m2.location = "RGBA", (220, 120)
    links.new(cmp_east.outputs["Result"], m2.inputs[0])
    links.new(m1.outputs[2], m2.inputs[6])
    links.new(gin.outputs["East (+X)"], m2.inputs[7])

    m3 = nodes.new("ShaderNodeMix")
    m3.data_type, m3.location = "RGBA", (380, 60)
    links.new(cmp_west.outputs["Result"], m3.inputs[0])
    links.new(m2.outputs[2], m3.inputs[6])
    links.new(gin.outputs["West (-X)"], m3.inputs[7])

    m4 = nodes.new("ShaderNodeMix")
    m4.data_type, m4.location = "RGBA", (540, 0)
    links.new(cmp_bottom.outputs["Result"], m4.inputs[0])
    links.new(m3.outputs[2], m4.inputs[6])
    links.new(gin.outputs["Bottom (-Z)"], m4.inputs[7])

    m5 = nodes.new("ShaderNodeMix")
    m5.data_type, m5.location = "RGBA", (700, -60)
    links.new(cmp_top.outputs["Result"], m5.inputs[0])
    links.new(m4.outputs[2], m5.inputs[6])
    links.new(gin.outputs["Top (+Z)"], m5.inputs[7])

    links.new(m5.outputs[2], gout.inputs["Selected"])
    return finalize_group(tree)
