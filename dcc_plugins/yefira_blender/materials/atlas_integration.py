"""
MoziToolKit Atlas Material integration and Shader setup for Yefira Blender Plugin.
"""

from __future__ import annotations
import bpy
import logging
from typing import Optional

logger = logging.getLogger("Yefira")

MASTER_MATERIAL_NAME = "Yefira_Atlas_Master"
FALLBACK_MATERIAL_NAME = "Yefira_Fallback_PBR"

def get_or_create_atlas_material() -> bpy.types.Material:
    """
    Get or create the unified Atlas Master Material.
    If MoziToolKit is present, delegates to MoziToolKit's shader builder or atlas chunk materials.
    Otherwise builds a clean, performant fallback PBR shader with vertex attribute color support.
    """
    # 1. Check if MoziToolKit material already exists
    if "MTK_Atlas_Master" in bpy.data.materials:
        return bpy.data.materials["MTK_Atlas_Master"]
    
    if MASTER_MATERIAL_NAME in bpy.data.materials:
        return bpy.data.materials[MASTER_MATERIAL_NAME]

    # 2. Build default shader
    mat = bpy.data.materials.new(name=MASTER_MATERIAL_NAME)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Output Node
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (400, 0)

    # Principled BSDF
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (100, 0)
    links.new(bsdf.outputs['BSDF'], output_node.inputs['Surface'])

    # Roughness
    if 'Roughness' in bsdf.inputs:
        bsdf.inputs['Roughness'].default_value = 0.8

    # Attribute Node: Biome Tint Color
    attr_tint = nodes.new(type='ShaderNodeAttribute')
    attr_tint.attribute_name = "mtk_biome_tint_color"
    attr_tint.location = (-400, 100)

    # Attribute Node: Biome Tint Data
    attr_data = nodes.new(type='ShaderNodeAttribute')
    attr_data.attribute_name = "mtk_biome_tint_data"
    attr_data.location = (-400, -150)

    # Mix Color Node (Multiply Tint with Base)
    mix_node = nodes.new(type='ShaderNodeMix')
    mix_node.data_type = 'RGBA'
    mix_node.blend_type = 'MULTIPLY'
    mix_node.inputs[0].default_value = 1.0  # Factor
    mix_node.location = (-150, 50)

    # Default Base Color
    mix_node.inputs[6].default_value = (0.7, 0.7, 0.7, 1.0) # Base A
    links.new(attr_tint.outputs['Color'], mix_node.inputs[7]) # Base B

    links.new(mix_node.outputs[2], bsdf.inputs['Base Color'])

    return mat


def setup_material_slots_for_object(obj: bpy.types.Object, mat: bpy.types.Material):
    """Ensure object has the specified material assigned to slot 0."""
    if not obj:
        return
    if not obj.data.materials:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat
