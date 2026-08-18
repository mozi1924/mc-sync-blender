"""
Ultra-fast Point Cloud Builder for Yefira Blender Plugin.
Emits pure point vertices and attributes for Blender native Geometry Nodes execution.
Zero face generation in Python -> 100% crash-free, sub-millisecond updates.
"""

from __future__ import annotations
import bpy
import logging
from typing import NamedTuple, Optional
from .storage import VoxelStorage
from .block_classifier import parse_and_classify, BlockTypeEnum, ParsedBlock
from .template_catalog import get_or_create_template_collection, get_template_index_map

logger = logging.getLogger("Yefira")


class PointCloudBuildResult(NamedTuple):
    world_obj: Optional[bpy.types.Object]
    point_count: int
    cubes_count: int
    props_count: int
    fluids_count: int


def update_world_point_cloud(
    context: bpy.types.Context,
    storage: VoxelStorage,
    filter_air: bool = True,
    atlas_mapping_dict: dict[str, int] = None,
) -> PointCloudBuildResult:
    """
    Builds or updates the single Point Cloud Mesh object 'Yefira_World'.
    Writes structured attributes consumed directly by the Geometry Nodes tree.
    """
    if storage.size_x == 0 or storage.size_y == 0 or storage.size_z == 0:
        return PointCloudBuildResult(None, 0, 0, 0, 0)

    min_x, min_y, min_z = storage.min_x, storage.min_y, storage.min_z
    size_x, size_y, size_z = storage.size_x, storage.size_y, storage.size_z
    block_map = storage.block_map

    # Ensure template collection exists and fetch instance index map
    template_col = get_or_create_template_collection(context)
    template_indices = get_template_index_map(template_col)

    # Object and Mesh Setup
    obj_name = "Yefira_World"
    mesh_name = "Yefira_World_Mesh"

    if obj_name in bpy.data.objects:
        obj = bpy.data.objects[obj_name]
        mesh = obj.data
    else:
        mesh = bpy.data.meshes.new(mesh_name)
        obj = bpy.data.objects.new(obj_name, mesh)
        obj.location = (0.0, 0.0, 0.0)
        context.collection.objects.link(obj)

    # Attribute Data Lists
    vertices = []
    block_states = []
    block_types = []
    instance_indices = []
    rotations = []
    offsets = []
    material_ids = []
    tint_colors = []
    tint_datas = []
    mc_positions = []

    palette_mat_cache = {}
    cubes_count = 0
    props_count = 0
    fluids_count = 0

    # Fast iteration over voxel map
    for (abs_x, abs_y, abs_z), state_str in block_map.items():
        parsed: ParsedBlock = parse_and_classify(state_str)

        if filter_air and parsed.block_type == BlockTypeEnum.AIR:
            continue

        # Metric 1:1 Scale & Centering
        # Blender X = MC X, Blender Y = MC Z, Blender Z = MC Y
        vx = (abs_x - min_x) - size_x / 2.0 + 0.5
        vy = (abs_z - min_z) - size_z / 2.0 + 0.5
        vz = (abs_y - min_y) + 0.5

        vertices.append((vx, vy, vz))
        block_states.append(parsed.full_state.encode('utf-8'))
        block_types.append(parsed.block_type)

        # Template Index for Collection Info Pick Instance
        tmpl_idx = template_indices.get(parsed.template_name, 0)
        instance_indices.append(tmpl_idx)

        rotations.append(parsed.rot_euler)
        offsets.append(parsed.offset)
        tint_colors.append(parsed.tint_color)
        tint_datas.append(parsed.tint_data)
        mc_positions.append((float(abs_x), float(abs_y), float(abs_z)))

        # Material ID resolution (Atlas mapping or palette hash)
        if atlas_mapping_dict and parsed.name in atlas_mapping_dict:
            mat_id = atlas_mapping_dict[parsed.name]
        else:
            if parsed.name not in palette_mat_cache:
                palette_mat_cache[parsed.name] = len(palette_mat_cache)
            mat_id = palette_mat_cache[parsed.name]
        material_ids.append(mat_id)

        # Statistics
        if parsed.block_type == BlockTypeEnum.CUBE:
            cubes_count += 1
        elif parsed.block_type == BlockTypeEnum.FLUID:
            fluids_count += 1
        else:
            props_count += 1

    # 1. Update pure point geometry in Blender C++
    mesh.clear_geometry()
    mesh.from_pydata(vertices, [], [])
    mesh.update()

    num_pts = len(vertices)
    if num_pts > 0:
        # 2. Fast Attribute Writes
        _write_int_attribute(mesh, "block_type", block_types)
        _write_int_attribute(mesh, "instance_index", instance_indices)
        _write_int_attribute(mesh, "mtk_material_id", material_ids)
        _write_float_vector_attribute(mesh, "instance_rotation", rotations)
        _write_float_vector_attribute(mesh, "instance_offset", offsets)
        _write_float_vector_attribute(mesh, "mc_pos", mc_positions)
        _write_float_color_attribute(mesh, "mtk_biome_tint_color", tint_colors)
        _write_float_color_attribute(mesh, "mtk_biome_tint_data", tint_datas)
        _write_string_attribute(mesh, "block_state", block_states)

    return PointCloudBuildResult(
        world_obj=obj,
        point_count=num_pts,
        cubes_count=cubes_count,
        props_count=props_count,
        fluids_count=fluids_count,
    )


def _write_int_attribute(mesh: bpy.types.Mesh, name: str, values: list[int]):
    attr = mesh.attributes.get(name)
    if not attr or attr.data_type != 'INT' or attr.domain != 'POINT' or len(attr.data) != len(values):
        if attr:
            mesh.attributes.remove(attr)
        attr = mesh.attributes.new(name=name, type='INT', domain='POINT')
    attr.data.foreach_set('value', values)


def _write_float_vector_attribute(mesh: bpy.types.Mesh, name: str, vectors: list[tuple[float, float, float]]):
    attr = mesh.attributes.get(name)
    if not attr or attr.data_type != 'FLOAT_VECTOR' or attr.domain != 'POINT' or len(attr.data) != len(vectors):
        if attr:
            mesh.attributes.remove(attr)
        attr = mesh.attributes.new(name=name, type='FLOAT_VECTOR', domain='POINT')
    
    # Flatten tuples for foreach_set
    flat = [c for v in vectors for c in v]
    attr.data.foreach_set('vector', flat)


def _write_float_color_attribute(mesh: bpy.types.Mesh, name: str, colors: list[tuple[float, float, float, float]]):
    attr = mesh.attributes.get(name)
    if not attr or attr.data_type != 'FLOAT_COLOR' or attr.domain != 'POINT' or len(attr.data) != len(colors):
        if attr:
            mesh.attributes.remove(attr)
        attr = mesh.attributes.new(name=name, type='FLOAT_COLOR', domain='POINT')
    
    flat = [c for col in colors for c in col]
    attr.data.foreach_set('color', flat)


def _write_string_attribute(mesh: bpy.types.Mesh, name: str, strings: list[bytes]):
    attr = mesh.attributes.get(name)
    if not attr or attr.data_type != 'STRING' or attr.domain != 'POINT' or len(attr.data) != len(strings):
        if attr:
            mesh.attributes.remove(attr)
        attr = mesh.attributes.new(name=name, type='STRING', domain='POINT')
    for i, s in enumerate(strings):
        attr.data[i].value = s
