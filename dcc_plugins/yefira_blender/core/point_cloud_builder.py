"""
Ultra-fast Point Cloud Builder for Yefira Blender Plugin.
Emits pure point vertices and attributes for Blender native Geometry Nodes execution.
Zero face generation in Python -> 100% crash-free, sub-millisecond updates.
"""

from __future__ import annotations
import bpy
import logging
from typing import NamedTuple, Optional
from .storage import VoxelStorage, block_key
from .block_classifier import parse_and_classify, BlockTypeEnum, ParsedBlock
from .template_catalog import get_or_create_template_collection, get_template_index_map

logger = logging.getLogger("Yefira")


class PointCloudBuildResult(NamedTuple):
    world_obj: Optional[bpy.types.Object]
    point_count: int
    cubes_count: int
    props_count: int
    fluids_count: int


def _resolve_template_index(template_indices: dict[str, int], name: str) -> int:
    """Resolve a block template name to a Collection index with prefix/suffix fallback."""
    if not name or not template_indices:
        return 0
    if name in template_indices:
        return template_indices[name]
    low = name.lower()
    if low in template_indices:
        return template_indices[low]

    for key, idx in template_indices.items():
        if low.endswith(key) or key.endswith(low):
            return idx
        if "bed_head" in low and "bed_head" in key:
            return idx
        if "bed_foot" in low and "bed_foot" in key:
            return idx
        if "door" in low and "lower" in low and "door_lower" in key:
            return idx
        if "door" in low and "upper" in low and "door_upper" in key:
            return idx
        if "stairs" in low and "stairs" in key:
            return idx
        if "slab" in low and "slab" in key:
            return idx
        if "chest" in low and "chest" in key:
            return idx
        if "torch" in low and "torch" in key:
            return idx
        if "plant" in low and "plant" in key:
            return idx
        if "carpet" in low and "carpet" in key:
            return idx
    return 0


def update_world_point_cloud(
    context: bpy.types.Context,
    storage: VoxelStorage,
    filter_air: bool = True,
    atlas_mapping_dict: Optional[dict[str, Any]] = None,
    block_face_lut: Optional[dict[str, list[tuple[int, int]]]] = None,
    block_face_chunk_lut: Optional[dict[str, list[int]]] = None,
    block_face_texture_lut: Optional[dict[str, list[int]]] = None,
    block_face_tint_lut: Optional[dict[str, list[tuple[float, float, float, float]]]] = None,
    block_face_anim_timing_lut: Optional[dict[str, list[tuple[float, float, float, float]]]] = None,
    block_face_anim_frame_size_lut: Optional[dict[str, list[tuple[float, float, float, float]]]] = None,
    atlas_width: float = 1024.0,
    atlas_height: float = 1024.0,
    tile_size: float = 16.0,
    tiles_per_row: int = 64,
    anim_atlas_width: float = 896.0,
    anim_atlas_height: float = 1024.0,
    anim_frame_width: float = 16.0,
    anim_frame_height: float = 16.0,
) -> PointCloudBuildResult:
    """
    Constructs or updates the Yefira_World mesh object from storage voxels in Blender C++.
    Writes structured attributes including 6-face Atlas tile coordinates and animation metadata.
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
    block_keys = []
    block_types = []
    instance_indices = []
    rotations = []
    offsets = []
    material_ids = []
    tint_colors = []
    tint_datas = []
    mc_positions = []

    # 6-face Atlas tile coordinates (col, row, 0.0)
    tile_east = []
    tile_west = []
    tile_top = []
    tile_bottom = []
    tile_south = []
    tile_north = []
    face_chunks = [[] for _ in range(6)]
    face_textures = [[] for _ in range(6)]
    face_tint_data = [[] for _ in range(6)]
    face_anim_timing = [[] for _ in range(6)]
    face_anim_frame_size = [[] for _ in range(6)]

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
        block_states.append(parsed.full_state)
        # Do not use a point index as a block address.  This value survives
        # point-cloud rebuilds and is the canonical DCC-facing identity.
        block_keys.append(block_key(abs_x, abs_y, abs_z))
        block_types.append(parsed.block_type)

        # Template Index for Collection Info Pick Instance
        tmpl_idx = _resolve_template_index(template_indices, parsed.template_name)
        instance_indices.append(tmpl_idx)

        rotations.append(parsed.rot_euler)
        offsets.append(parsed.offset)
        tint_colors.append(parsed.tint_color)
        tint_datas.append(parsed.tint_data)
        mc_positions.append((float(abs_x), float(abs_y), float(abs_z)))

        atlas_keys = _atlas_lookup_keys(parsed)

        # Material ID resolution (Atlas mapping or palette hash)
        mat_id = None
        if atlas_mapping_dict:
            mat_id = next((atlas_mapping_dict[key] for key in atlas_keys if key in atlas_mapping_dict), None)
        if mat_id is None:
            if parsed.name not in palette_mat_cache:
                palette_mat_cache[parsed.name] = len(palette_mat_cache)
            mat_id = palette_mat_cache[parsed.name]
        material_ids.append(mat_id)

        # 6-Face Tile Coordinates Lookup from Face LUT
        coords = None
        if block_face_lut:
            coords = next((block_face_lut[key] for key in atlas_keys if key in block_face_lut), None)

        if coords and len(coords) >= 6:
            # Face Order: +X (East), -X (West), +Y (Top), -Y (Bottom), +Z (South), -Z (North)
            e_col, e_row = coords[0]
            w_col, w_row = coords[1]
            t_col, t_row = coords[2]
            b_col, b_row = coords[3]
            s_col, s_row = coords[4]
            n_col, n_row = coords[5]
        else:
            # Fallback based on mat_id if no face_lut
            e_col = w_col = t_col = b_col = s_col = n_col = (mat_id % 256)
            e_row = w_row = t_row = b_row = s_row = n_row = (mat_id // 256)

        tile_east.append((float(e_col), float(e_row), 0.0))
        tile_west.append((float(w_col), float(w_row), 0.0))
        tile_top.append((float(t_col), float(t_row), 0.0))
        tile_bottom.append((float(b_col), float(b_row), 0.0))
        tile_south.append((float(s_col), float(s_row), 0.0))
        tile_north.append((float(n_col), float(n_row), 0.0))

        chunk_ids = _lookup_face_values(block_face_chunk_lut, parsed, 0)
        texture_ids = _lookup_face_values(block_face_texture_lut, parsed, mat_id)
        for face_index in range(6):
            face_chunks[face_index].append(chunk_ids[face_index])
            face_textures[face_index].append(texture_ids[face_index])
        tint_values = _lookup_face_values(block_face_tint_lut, parsed, (0.0, 0.0, 0.0, 0.0))
        for face_index in range(6):
            face_tint_data[face_index].append(tint_values[face_index])

        anim_timing_values = _lookup_face_values(block_face_anim_timing_lut, parsed, (1.0, 1.0, 0.0, 0.0))
        anim_frame_size_values = _lookup_face_values(block_face_anim_frame_size_lut, parsed, (float(tile_size), float(tile_size), 0.0, 0.0))
        for face_index in range(6):
            face_anim_timing[face_index].append(anim_timing_values[face_index])
            face_anim_frame_size[face_index].append(anim_frame_size_values[face_index])

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
        # Atlas metadata is emitted as geometry attributes rather than
        # Geometry Nodes modifier inputs.  This makes a material replacement
        # deterministic and removes user-adjustable sync state.
        _write_float_attribute(mesh, "mtk_atlas_width", [float(atlas_width)] * num_pts)
        _write_float_attribute(mesh, "mtk_atlas_height", [float(atlas_height)] * num_pts)
        _write_float_attribute(mesh, "mtk_tile_size", [float(tile_size)] * num_pts)
        _write_float_attribute(mesh, "mtk_tiles_per_row", [float(tiles_per_row)] * num_pts)
        _write_float_attribute(mesh, "mtk_anim_atlas_width", [float(anim_atlas_width)] * num_pts)
        _write_float_attribute(mesh, "mtk_anim_atlas_height", [float(anim_atlas_height)] * num_pts)
        _write_float_attribute(mesh, "mtk_anim_frame_width", [float(anim_frame_width)] * num_pts)
        _write_float_attribute(mesh, "mtk_anim_frame_height", [float(anim_frame_height)] * num_pts)
        _write_float_vector_attribute(mesh, "instance_rotation", rotations)
        _write_float_vector_attribute(mesh, "instance_offset", offsets)
        _write_float_vector_attribute(mesh, "mc_pos", mc_positions)
        _write_float_vector_attribute(mesh, "mtk_tile_east", tile_east)
        _write_float_vector_attribute(mesh, "mtk_tile_west", tile_west)
        _write_float_vector_attribute(mesh, "mtk_tile_top", tile_top)
        _write_float_vector_attribute(mesh, "mtk_tile_bottom", tile_bottom)
        _write_float_vector_attribute(mesh, "mtk_tile_south", tile_south)
        _write_float_vector_attribute(mesh, "mtk_tile_north", tile_north)
        for name, values in zip(("east", "west", "top", "bottom", "south", "north"), face_chunks):
            _write_int_attribute(mesh, f"mtk_chunk_{name}", values)
        for name, values in zip(("east", "west", "top", "bottom", "south", "north"), face_textures):
            _write_int_attribute(mesh, f"mtk_texture_{name}", values)
        for name, values in zip(("east", "west", "top", "bottom", "south", "north"), face_tint_data):
            _write_float_color_attribute(mesh, f"mtk_tint_data_{name}", values)
        for name, values in zip(("east", "west", "top", "bottom", "south", "north"), face_anim_timing):
            _write_float_color_attribute(mesh, f"mtk_anim_timing_{name}", values)
        for name, values in zip(("east", "west", "top", "bottom", "south", "north"), face_anim_frame_size):
            _write_float_color_attribute(mesh, f"mtk_anim_frame_size_{name}", values)
        _write_float_color_attribute(mesh, "mtk_biome_tint_color", tint_colors)
        _write_float_color_attribute(mesh, "mtk_biome_tint_data", tint_datas)
        _write_float_color_attribute(mesh, "mtk_uv_tiling_transform", [(1.0, 1.0, 0.0, 0.0)] * num_pts)
        _write_float_attribute(mesh, "mtk_uv_rotation", [0.0] * num_pts)
        _write_string_attribute(mesh, "block_state", block_states)
        _write_string_attribute(mesh, "mc_block_key", block_keys)

    return PointCloudBuildResult(
        world_obj=obj,
        point_count=num_pts,
        cubes_count=cubes_count,
        props_count=props_count,
        fluids_count=fluids_count,
    )


def _lookup_face_values(lut, parsed: ParsedBlock, default) -> list:
    values = None
    if lut:
        values = next((lut[key] for key in _atlas_lookup_keys(parsed) if key in lut), None)
    if not values or len(values) < 6:
        return [default] * 6
    return [type(default)(value) if isinstance(default, int) else tuple(value) for value in values[:6]]


def _atlas_lookup_keys(parsed: ParsedBlock) -> tuple[str, ...]:
    """Return the mapping keys which can represent this exact block state.

    Vanilla door blockstates select ``*_door_bottom`` or ``*_door_top``
    models; resource packs usually expose those textures rather than a single
    ``*_door`` texture.  The point cloud retains the full state, so preserve
    that distinction before falling back to the ordinary block-name aliases.
    """
    keys: list[str] = []
    if parsed.name.endswith("_door"):
        half = parsed.props.get("half", "lower")
        keys.append(f"{parsed.name}_{'top' if half == 'upper' else 'bottom'}")
    keys.extend((parsed.name, parsed.block_id, f"minecraft:{parsed.name}"))
    return tuple(dict.fromkeys(keys))


def _write_float_attribute(mesh: bpy.types.Mesh, name: str, values: list[float]):
    attr = mesh.attributes.get(name)
    if not attr or attr.data_type != 'FLOAT' or attr.domain != 'POINT' or len(attr.data) != len(values):
        if attr:
            mesh.attributes.remove(attr)
        attr = mesh.attributes.new(name=name, type='FLOAT', domain='POINT')
    attr.data.foreach_set('value', values)


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


def _write_string_attribute(mesh: bpy.types.Mesh, name: str, strings: list[str | bytes]):
    attr = mesh.attributes.get(name)
    if not attr or attr.data_type != 'STRING' or attr.domain != 'POINT' or len(attr.data) != len(strings):
        if attr:
            mesh.attributes.remove(attr)
        attr = mesh.attributes.new(name=name, type='STRING', domain='POINT')
    for i, s in enumerate(strings):
        # Blender's RNA string-attribute API uses UTF-8 bytes even though the
        # logical value is text.  Normalise here so block states and stable
        # ``mc_block_key`` values have one safe writer.
        attr.data[i].value = s if isinstance(s, bytes) else s.encode('utf-8')
