"""Reusable Geometry Nodes building blocks for the Yefira world tree.

This module now re-exports modular groups from `yefira_blender.nodes.groups`
for backward compatibility.
"""

from __future__ import annotations

from .core import ensure_socket
from .groups import (
    get_or_create_cube_surface_group,
    get_or_create_instance_attribute_transfer_group,
    GROUP_NAME_CUBE_SURFACE,
    GROUP_NAME_INSTANCE_ATTRIBUTES,
)
from .groups.instance_attributes import (
    FACE_NAMES,
    FACE_TILE_ATTRIBUTES,
    FACE_INT_ATTRIBUTES,
    ATLAS_FLOAT_ATTRIBUTES,
    FACE_TINT_ATTRIBUTES,
)

__all__ = (
    "ensure_socket",
    "get_or_create_cube_surface_group",
    "get_or_create_instance_attribute_transfer_group",
    "GROUP_NAME_CUBE_SURFACE",
    "GROUP_NAME_INSTANCE_ATTRIBUTES",
    "FACE_NAMES",
    "FACE_TILE_ATTRIBUTES",
    "FACE_INT_ATTRIBUTES",
    "ATLAS_FLOAT_ATTRIBUTES",
    "FACE_TINT_ATTRIBUTES",
)
