import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty

class MozisyncSceneProperties(bpy.types.PropertyGroup):
    url: StringProperty(
        name="Server URL",
        description="WebSocket address of MC-Sync mod server",
        default="ws://localhost:8765"
    )

    connection_status: StringProperty(
        name="Status",
        default="DISCONNECTED"
    )

    is_connected: BoolProperty(
        name="Is Connected",
        default=False
    )

    # 选区数据
    has_selection: BoolProperty(default=False)
    min_x: IntProperty(default=0)
    min_y: IntProperty(default=0)
    min_z: IntProperty(default=0)
    size_x: IntProperty(default=0)
    size_y: IntProperty(default=0)
    size_z: IntProperty(default=0)
    total_blocks: IntProperty(default=0)
    palette_count: IntProperty(default=0)

    # 最新变动日志
    last_update_info: StringProperty(
        name="Last Update",
        default="No updates received yet."
    )
    update_counter: IntProperty(default=0)
