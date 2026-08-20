"""
Template Asset Collection Manager for Minecraft Props and Non-Cube Models.
Manages the 'MC_Block_Templates' collection in Blender used by Geometry Nodes.
Generates procedural non-cube models and entity blocks with fake-user persistence.
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
    Ensures all default procedural templates exist and are linked.
    """
    if TEMPLATE_COLLECTION_NAME in bpy.data.collections:
        col = bpy.data.collections[TEMPLATE_COLLECTION_NAME]
    else:
        col = bpy.data.collections.new(TEMPLATE_COLLECTION_NAME)
        context.scene.collection.children.link(col)
        col.hide_render = True
        col.hide_viewport = True

    # Always ensure all standard procedural templates exist
    _populate_default_templates(col)
    return col


def get_template_index_map(col: bpy.types.Collection) -> dict[str, int]:
    """
    Return mapping of template object name -> integer index in collection.
    Geometry Nodes 'Collection Info' with 'Pick Instance' uses 0-based indexing matching col.objects.
    Includes comprehensive alias resolution for entity blocks and non-cubes.
    """
    mapping = {}
    obj_names = [obj.name for obj in col.objects]

    for idx, obj in enumerate(col.objects):
        mapping[obj.name] = idx
        mapping[obj.name.lower()] = idx

    # Dynamic alias resolution helper
    def register_alias(alias_key: str, target_name: str):
        if target_name in mapping:
            target_idx = mapping[target_name]
            mapping[alias_key] = target_idx
            mapping[alias_key.lower()] = target_idx

    # Canonical aliases
    for obj_name in obj_names:
        low = obj_name.lower()
        if "stairs" in low:
            register_alias("stairs", obj_name)
            register_alias("stairs_straight", obj_name)
        elif "slab" in low:
            register_alias("slab", obj_name)
            register_alias("slab_bottom", obj_name)
        elif "bed_head" in low:
            register_alias("bed_head", obj_name)
        elif "bed_foot" in low:
            register_alias("bed_foot", obj_name)
        elif "door_lower" in low or "door_bottom" in low:
            register_alias("door_lower", obj_name)
            register_alias("door_bottom", obj_name)
        elif "door_upper" in low or "door_top" in low:
            register_alias("door_upper", obj_name)
            register_alias("door_top", obj_name)
        elif "chest" in low:
            register_alias("chest", obj_name)
        elif "plant" in low or "cross" in low:
            register_alias("cross_plant", obj_name)
            register_alias("flower", obj_name)
        elif "torch" in low:
            register_alias("torch", obj_name)
        elif "trapdoor" in low:
            register_alias("trapdoor", obj_name)
        elif "carpet" in low:
            register_alias("carpet", obj_name)
        elif "fence" in low:
            register_alias("fence", obj_name)
        elif "wall" in low:
            register_alias("wall", obj_name)
        elif "lantern" in low:
            register_alias("lantern", obj_name)

    return mapping


def _attach_template_attributes(mesh: bpy.types.Mesh, is_cross_plant: bool = False) -> None:
    """Attach CubeFaceNorm (FACE domain) and LocalUV (CORNER domain) attributes to a template mesh."""
    norm_attr = mesh.attributes.get("CubeFaceNorm")
    if not norm_attr:
        norm_attr = mesh.attributes.new(name="CubeFaceNorm", type="FLOAT_VECTOR", domain="FACE")

    luv_attr = mesh.attributes.get("LocalUV")
    if not luv_attr:
        luv_attr = mesh.attributes.new(name="LocalUV", type="FLOAT_VECTOR", domain="CORNER")

    mesh.update()

    for poly in mesh.polygons:
        fn = poly.normal
        norm_attr.data[poly.index].vector = (0.0, 1.0, 0.0) if is_cross_plant else (fn.x, fn.y, fn.z)
        for loop_idx in poly.loop_indices:
            vi = mesh.loops[loop_idx].vertex_index
            v_co = mesh.vertices[vi].co
            x, y, z = v_co.x, v_co.y, v_co.z
            if is_cross_plant:
                u = 1.0 if (x > 0.0 or (y > 0.0 and x >= 0.0)) else 0.0
                v = z + 0.5
            else:
                if fn.z > 0.5:     # Top (+Z)
                    u, v = x + 0.5, y + 0.5
                elif fn.z < -0.5:  # Bottom (-Z)
                    u, v = x + 0.5, y + 0.5
                elif fn.y > 0.5:   # North (+Y)
                    u, v = 0.5 - x, z + 0.5
                elif fn.y < -0.5:  # South (-Y)
                    u, v = x + 0.5, z + 0.5
                elif fn.x > 0.5:   # East (+X)
                    u, v = y + 0.5, z + 0.5
                elif fn.x < -0.5:  # West (-X)
                    u, v = 0.5 - y, z + 0.5
                else:
                    u, v = x + 0.5, z + 0.5
            luv_attr.data[loop_idx].vector = (min(max(float(u), 0.0), 1.0), min(max(float(v), 0.0), 1.0), 0.0)

    mesh.update()


def _ensure_template_box(
    col: bpy.types.Collection,
    name: str,
    min_pt: tuple[float, float, float],
    max_pt: tuple[float, float, float],
) -> bpy.types.Object:
    """Helper to create and link an axis-aligned cuboid mesh template with fake-user."""
    obj = bpy.data.objects.get(name)
    if not obj:
        mesh = bpy.data.meshes.new(f"Template_{name}_Mesh")
        mesh.use_fake_user = True
        x0, y0, z0 = min_pt
        x1, y1, z1 = max_pt
        v = [
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
        ]
        f = [
            (0, 1, 2, 3), (4, 7, 6, 5),
            (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)
        ]
        mesh.from_pydata(v, [], f)
        mesh.update()
        _attach_template_attributes(mesh)
        obj = bpy.data.objects.new(name, mesh)
    else:
        if obj.data and ("LocalUV" not in obj.data.attributes or "CubeFaceNorm" not in obj.data.attributes):
            _attach_template_attributes(obj.data)

    obj.use_fake_user = True
    if obj.data:
        obj.data.use_fake_user = True
    if obj.name not in col.objects:
        col.objects.link(obj)
    return obj


def _populate_default_templates(col: bpy.types.Collection):
    """
    Create basic fallback procedural template meshes in the collection.
    Covers common Minecraft entity blocks (Beds, Doors, Chests, Trapdoors, Slabs, Stairs, Plants).
    """
    # 1. Stairs Template (Standard step shape: L-shaped box)
    if "stairs_straight" not in bpy.data.objects:
        stair_mesh = bpy.data.meshes.new("Template_Stairs_Mesh")
        stair_mesh.use_fake_user = True
        v = [
            (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
            (-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (0.5, 0.0, 0.0), (-0.5, 0.0, 0.0),
            (-0.5, 0.0, 0.5), (0.5, 0.0, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5),
        ]
        f = [
            (0, 1, 2, 3), (0, 4, 5, 1), (4, 7, 6, 5), (7, 8, 9, 6),
            (8, 11, 10, 9), (3, 2, 10, 11), (0, 3, 11, 8, 7, 4), (1, 5, 6, 9, 10, 2),
        ]
        stair_mesh.from_pydata(v, [], f)
        stair_mesh.update()
        _attach_template_attributes(stair_mesh)
        stair_obj = bpy.data.objects.new("stairs_straight", stair_mesh)
        stair_obj.use_fake_user = True
    else:
        stair_obj = bpy.data.objects["stairs_straight"]
        stair_obj.use_fake_user = True
        if stair_obj.data:
            stair_obj.data.use_fake_user = True
            if "LocalUV" not in stair_obj.data.attributes or "CubeFaceNorm" not in stair_obj.data.attributes:
                _attach_template_attributes(stair_obj.data)

    if stair_obj.name not in col.objects:
        col.objects.link(stair_obj)

    # 2. Slab Template (Bottom half cube: 1x1x0.5)
    _ensure_template_box(col, "slab_bottom", (-0.5, -0.5, -0.5), (0.5, 0.5, 0.0))

    # 3. Cross Plant Template (Intersecting X quads)
    if "cross_plant" not in bpy.data.objects:
        plant_mesh = bpy.data.meshes.new("Template_CrossPlant_Mesh")
        plant_mesh.use_fake_user = True
        d = 0.4
        v = [
            (-d, -d, -0.5), (d, d, -0.5), (d, d, 0.5), (-d, -d, 0.5),
            (-d, d, -0.5), (d, -d, -0.5), (d, -d, 0.5), (-d, d, 0.5),
        ]
        f = [
            (0, 1, 2, 3), (1, 0, 3, 2),
            (4, 5, 6, 7), (5, 4, 7, 6),
        ]
        plant_mesh.from_pydata(v, [], f)
        plant_mesh.update()
        _attach_template_attributes(plant_mesh, is_cross_plant=True)
        plant_obj = bpy.data.objects.new("cross_plant", plant_mesh)
        plant_obj.use_fake_user = True
    else:
        plant_obj = bpy.data.objects["cross_plant"]
        plant_obj.use_fake_user = True
        if plant_obj.data:
            plant_obj.data.use_fake_user = True
            if "LocalUV" not in plant_obj.data.attributes or "CubeFaceNorm" not in plant_obj.data.attributes:
                _attach_template_attributes(plant_obj.data, is_cross_plant=True)

    if plant_obj.name not in col.objects:
        col.objects.link(plant_obj)

    # 4. Torch Template (Small vertical pillar)
    w = 0.0625
    _ensure_template_box(col, "torch", (-w, -w, -0.5), (w, w, 0.125))

    # 5. Bed Head Template (Entity Block: Mattress height 9/16, Headboard)
    _ensure_template_box(col, "bed_head", (-0.5, -0.5, -0.5), (0.5, 0.5, 0.0625))

    # 6. Bed Foot Template (Entity Block: Mattress height 9/16)
    _ensure_template_box(col, "bed_foot", (-0.5, -0.5, -0.5), (0.5, 0.5, 0.0625))

    # 7. Door Lower Template (Vertical 3/16 panel bottom)
    _ensure_template_box(col, "door_lower", (-0.5, -0.5, -0.5), (0.5, -0.3125, 0.5))

    # 8. Door Upper Template (Vertical 3/16 panel top)
    _ensure_template_box(col, "door_upper", (-0.5, -0.5, -0.5), (0.5, -0.3125, 0.5))

    # 9. Chest Template (Entity Block: 14x14x14 box centered)
    c = 0.4375
    _ensure_template_box(col, "chest", (-c, -c, -0.5), (c, c, 0.375))

    # 10. Trapdoor Template (Horizontal flat flap 3/16 thick)
    _ensure_template_box(col, "trapdoor", (-0.5, -0.5, -0.5), (0.5, 0.5, -0.3125))

    # 11. Carpet Template (Flat layer 1/16 thick)
    _ensure_template_box(col, "carpet", (-0.5, -0.5, -0.5), (0.5, 0.5, -0.4375))
