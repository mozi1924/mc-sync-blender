# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Yefira B3D",
    "author": "Mozi Team",
    "description": "Minecraft to Blender Selection & Incremental Binary WebSocket Receiver Plugin",
    "blender": (4, 2, 0),
    "version": (1, 0, 0),
    "location": "View3D > Sidebar > Yefira",
    "category": "Import-Export",
}

import bpy
from . import auto_load
from .properties import YefiraSceneProperties

auto_load.init()

def register():
    auto_load.register()
    bpy.types.Scene.yefira = bpy.props.PointerProperty(type=YefiraSceneProperties)

def unregister():
    if hasattr(bpy.types.Scene, "yefira"):
        try:
            del bpy.types.Scene.yefira
        except Exception:
            pass
    try:
        auto_load.unregister()
    except Exception:
        pass
