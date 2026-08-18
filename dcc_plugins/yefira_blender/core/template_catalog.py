"""
Template Asset Collection Manager for Minecraft Props and Non-Cube Models.
Manages the 'MC_Block_Templates' collection in Blender used by Geometry Nodes.
"""

from __future__ import annotations
import bpy
import logging
from typing import Optional

logger = logging.getLogger("Yefira")

TEMPLATE_COLLECTION_NAME = "MC_Block_Templates"

def get_or_create_template_collection(context: bpy.types.Context) -> bpy.types.Collection:
    """
    Find or create the 'MC_Block_Templates' collection in the active scene.
    Ensures default procedural templates exist if the collection is newly created.
    """
    if TEMPLATE_COLLECTION_NAME in bpy.data.collections:
        col = bpy.data.collections[TEMPLATE_COLLECTION_NAME]
    else:
        col = bpy.data.collections.new(TEMPLATE_COLLECTION_NAME)
        context.scene.collection.children.link(col)
        # Exclude from view layer rendering by default so template instances don't clutter the origin
        col.hide_render = True
        col.hide_viewport = True

    # Populate basic procedural shapes if collection is empty
    if not col.objects:
        _populate_default_templates(col)

    return col


def get_template_index_map(col: bpy.types.Collection) -> dict[str, int]:
    """
    Return mapping of template object name -> integer index in collection.
    Geometry Nodes 'Collection Info' with 'Pick Instance' uses 0-based indexing matching col.objects.
    """
    mapping = {}
    for idx, obj in enumerate(col.objects):
        # Match both exact name and base name (e.g. 'oak_stairs' matches 'oak_stairs' or 'oak_stairs_straight')
        mapping[obj.name] = idx
        clean_name = obj.name.lower()
        mapping[clean_name] = idx
    return mapping


def _populate_default_templates(col: bpy.types.Collection):
    """
    Create basic fallback procedural template meshes in the collection.
    Users can replace or add custom OBJ/glTF models to this collection anytime.
    """
    # 1. Stairs Template (Standard step shape: L-shaped box)
    if "stairs_straight" not in bpy.data.objects:
        stair_mesh = bpy.data.meshes.new("Template_Stairs_Mesh")
        # 8 vertices for bottom half, 8 vertices for back step
        # Bottom half: [-0.5, 0.5] x [-0.5, 0.5] x [-0.5, 0.0]
        # Top-back half: [-0.5, 0.5] x [0.0, 0.5] x [0.0, 0.5]
        v = [
            (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5), # 0-3: bottom
            (-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (0.5, 0.0, 0.0), (-0.5, 0.0, 0.0),     # 4-7: step ledge
            (-0.5, 0.0, 0.5), (0.5, 0.0, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5),       # 8-11: top ledge
        ]
        f = [
            (0, 1, 2, 3), # Bottom
            (0, 4, 5, 1), # Front lower
            (4, 7, 6, 5), # Step horizontal
            (7, 8, 9, 6), # Step vertical
            (8, 11, 10, 9), # Top horizontal
            (3, 2, 10, 11), # Back vertical
            (0, 3, 11, 8, 7, 4), # Left side
            (1, 5, 6, 9, 10, 2), # Right side
        ]
        stair_mesh.from_pydata(v, [], f)
        stair_mesh.update()
        stair_obj = bpy.data.objects.new("stairs_straight", stair_mesh)
        col.objects.link(stair_obj)

    # 2. Slab Template (Bottom half cube: 1x1x0.5)
    if "slab_bottom" not in bpy.data.objects:
        slab_mesh = bpy.data.meshes.new("Template_Slab_Mesh")
        v = [
            (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
            (-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (0.5, 0.5, 0.0), (-0.5, 0.5, 0.0),
        ]
        f = [
            (0, 1, 2, 3), (4, 7, 6, 5),
            (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)
        ]
        slab_mesh.from_pydata(v, [], f)
        slab_mesh.update()
        slab_obj = bpy.data.objects.new("slab_bottom", slab_mesh)
        col.objects.link(slab_obj)

    # 3. Cross Plant Template (Intersecting X quads)
    if "cross_plant" not in bpy.data.objects:
        plant_mesh = bpy.data.meshes.new("Template_CrossPlant_Mesh")
        d = 0.4
        v = [
            (-d, -d, -0.5), (d, d, -0.5), (d, d, 0.5), (-d, -d, 0.5),
            (-d, d, -0.5), (d, -d, -0.5), (d, -d, 0.5), (-d, d, 0.5),
        ]
        f = [
            (0, 1, 2, 3), (1, 0, 3, 2), # Quad 1 (double sided)
            (4, 5, 6, 7), (5, 4, 7, 6), # Quad 2 (double sided)
        ]
        plant_mesh.from_pydata(v, [], f)
        plant_mesh.update()
        plant_obj = bpy.data.objects.new("cross_plant", plant_mesh)
        col.objects.link(plant_obj)

    # 4. Torch Template (Small vertical pillar)
    if "torch" not in bpy.data.objects:
        torch_mesh = bpy.data.meshes.new("Template_Torch_Mesh")
        w = 0.0625 # 2 pixels wide
        v = [
            (-w, -w, -0.5), (w, -w, -0.5), (w, w, -0.5), (-w, w, -0.5),
            (-w, -w, 0.125), (w, -w, 0.125), (w, w, 0.125), (-w, w, 0.125),
        ]
        f = [
            (0, 1, 2, 3), (4, 7, 6, 5),
            (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)
        ]
        torch_mesh.from_pydata(v, [], f)
        torch_mesh.update()
        torch_obj = bpy.data.objects.new("torch", torch_mesh)
        col.objects.link(torch_obj)
