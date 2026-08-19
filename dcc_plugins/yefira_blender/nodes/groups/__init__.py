"""Atomic Geometry Node groups for procedural Minecraft world construction."""

from .cube_surface import (
    get_or_create_cube_surface_group,
    GROUP_NAME_CUBE_SURFACE,
)
from .instance_attributes import (
    get_or_create_instance_attribute_transfer_group,
    GROUP_NAME_INSTANCE_ATTRIBUTES,
)
from .face_selectors import (
    get_or_create_face_selector_vector_group,
    get_or_create_face_selector_int_group,
    get_or_create_face_selector_color_group,
    GROUP_NAME_FACE_SELECTOR_VECTOR,
    GROUP_NAME_FACE_SELECTOR_INT,
    GROUP_NAME_FACE_SELECTOR_COLOR,
)
from .atlas_uv import (
    get_or_create_atlas_uv_calculator_group,
    GROUP_NAME_ATLAS_UV_CALCULATOR,
)
from .material_dispatcher import (
    get_or_create_material_dispatcher_group,
    GROUP_NAME_MATERIAL_DISPATCHER,
)

__all__ = (
    "get_or_create_cube_surface_group",
    "get_or_create_instance_attribute_transfer_group",
    "get_or_create_face_selector_vector_group",
    "get_or_create_face_selector_int_group",
    "get_or_create_face_selector_color_group",
    "get_or_create_atlas_uv_calculator_group",
    "get_or_create_material_dispatcher_group",
    "GROUP_NAME_CUBE_SURFACE",
    "GROUP_NAME_INSTANCE_ATTRIBUTES",
    "GROUP_NAME_FACE_SELECTOR_VECTOR",
    "GROUP_NAME_FACE_SELECTOR_INT",
    "GROUP_NAME_FACE_SELECTOR_COLOR",
    "GROUP_NAME_ATLAS_UV_CALCULATOR",
    "GROUP_NAME_MATERIAL_DISPATCHER",
)
