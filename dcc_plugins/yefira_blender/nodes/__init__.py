"""Geometry Nodes subpackage for Yefira Blender Plugin."""

from .core import (
    ensure_gn_group,
    ensure_socket,
    finalize_group,
    prune_unlinked_nodes,
)
from .groups import (
    get_or_create_atlas_uv_calculator_group,
    get_or_create_cube_surface_group,
    get_or_create_face_selector_color_group,
    get_or_create_face_selector_int_group,
    get_or_create_face_selector_vector_group,
    get_or_create_instance_attribute_transfer_group,
)
from .world_tree import (
    setup_world_geometry_nodes,
    WORLD_TREE_NAME,
    WORLD_MODIFIER_NAME,
    WORLD_TREE_SCHEMA_VERSION,
    WORLD_TREE_SCHEMA_PROPERTY,
)

__all__ = (
    "ensure_gn_group",
    "ensure_socket",
    "finalize_group",
    "prune_unlinked_nodes",
    "get_or_create_atlas_uv_calculator_group",
    "get_or_create_cube_surface_group",
    "get_or_create_face_selector_color_group",
    "get_or_create_face_selector_int_group",
    "get_or_create_face_selector_vector_group",
    "get_or_create_instance_attribute_transfer_group",
    "setup_world_geometry_nodes",
    "WORLD_TREE_NAME",
    "WORLD_MODIFIER_NAME",
    "WORLD_TREE_SCHEMA_VERSION",
    "WORLD_TREE_SCHEMA_PROPERTY",
)
