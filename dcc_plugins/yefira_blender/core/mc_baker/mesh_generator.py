"""
Blender Mesh Generator for BakedModel instances.
Constructs exact polygon meshes and loop UV layers for arbitrary non-full and complex blocks.
"""

from __future__ import annotations
from typing import Optional, Union, Tuple
import bpy
import bmesh
from mathutils import Vector

from .types import BakedModel, BakedFace, BakedElement


def mc_pos_to_blender(mc_pos: Tuple[float, float, float], origin_centered: bool = True) -> Tuple[float, float, float]:
    x, y, z = mc_pos
    if origin_centered:
        bx = x - 0.5
        by = -(z - 0.5)
        bz = y - 0.5
    else:
        bx = x
        by = 1.0 - z
        bz = y
    return (bx, by, bz)


def build_blender_mesh_from_baked_model(
    baked_model: BakedModel,
    mesh_name: str = "MC_Baked_Block",
    origin_centered: bool = True,
    material_map: Optional[dict[str, bpy.types.Material]] = None
) -> bpy.types.Mesh:
    mesh = bpy.data.meshes.new(mesh_name)
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    mat_slot_indices: dict[str, int] = {}
    if material_map:
        for tex_name, mat in material_map.items():
            if mat.name not in mesh.materials:
                mat_slot_indices[tex_name] = len(mesh.materials)
                mesh.materials.append(mat)

    for element in baked_model.elements:
        for face_dir, baked_face in element.faces.items():
            if not baked_face.vertices or len(baked_face.vertices) < 4:
                continue

            bl_verts_coords = [
                mc_pos_to_blender(v, origin_centered)
                for v in baked_face.vertices
            ]

            bm_verts = [bm.verts.new(v) for v in bl_verts_coords]
            try:
                bm_face = bm.faces.new(bm_verts)
            except ValueError:
                continue

            if baked_face.uvs and len(baked_face.uvs) == 4:
                for i, loop in enumerate(bm_face.loops):
                    u, v = baked_face.uvs[i]
                    loop[uv_layer].uv = Vector((u, 1.0 - v))

            if baked_face.texture in mat_slot_indices:
                bm_face.material_index = mat_slot_indices[baked_face.texture]

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh


def create_block_object(
    baked_model: BakedModel,
    object_name: str = "MC_Block",
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    collection: Optional[bpy.types.Collection] = None,
    material_map: Optional[dict[str, bpy.types.Material]] = None
) -> bpy.types.Object:
    mesh = build_blender_mesh_from_baked_model(
        baked_model=baked_model,
        mesh_name=f"Mesh_{object_name}",
        origin_centered=True,
        material_map=material_map
    )
    obj = bpy.data.objects.new(object_name, mesh)
    obj.location = location

    target_coll = collection or bpy.context.collection
    target_coll.objects.link(obj)
    return obj
