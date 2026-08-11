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
    "name": "Mozisync B3D (MC Sync Blender)",
    "author": "Mozi Team",
    "description": "Minecraft to Blender Selection & Incremental Binary WebSocket Receiver Plugin",
    "blender": (4, 2, 0),
    "version": (1, 0, 0),
    "location": "View3D > Sidebar > MC Sync",
    "category": "Import-Export",
}

import bpy
from . import auto_load
from .properties import MozisyncSceneProperties

auto_load.init()

def register():
    auto_load.register()
    bpy.types.Scene.mozisync = bpy.props.PointerProperty(type=MozisyncSceneProperties)

def unregister():
    if hasattr(bpy.types.Scene, "mozisync"):
        del bpy.types.Scene.mozisync
    auto_load.unregister()
