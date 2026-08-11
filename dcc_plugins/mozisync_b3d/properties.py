import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty, CollectionProperty, PointerProperty

class MozisyncPaletteItem(bpy.types.PropertyGroup):
    state_str: StringProperty(name="BlockState")

class MozisyncDeltaItem(bpy.types.PropertyGroup):
    timestamp: StringProperty(name="Time")
    pos_str: StringProperty(name="Position")
    block_state: StringProperty(name="BlockState")

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

    # 3D 视图选区辅助线开关
    show_3d_bbox: BoolProperty(
        name="Show 3D BBox",
        description="Visualize selection bounding box in 3D Viewport",
        default=True
    )

    # 选区数据
    has_selection: BoolProperty(default=False)
    min_x: IntProperty(default=0)
    min_y: IntProperty(default=0)
    min_z: IntProperty(default=0)
    max_x: IntProperty(default=0)
    max_y: IntProperty(default=0)
    max_z: IntProperty(default=0)
    size_x: IntProperty(default=0)
    size_y: IntProperty(default=0)
    size_z: IntProperty(default=0)
    total_blocks: IntProperty(default=0)
    palette_count: IntProperty(default=0)

    # Palette 调色板项列表
    palette_list: CollectionProperty(type=MozisyncPaletteItem)
    palette_active_index: IntProperty(default=0)

    # 实时变动历史列表
    delta_history: CollectionProperty(type=MozisyncDeltaItem)
    delta_active_index: IntProperty(default=0)

    # 最新变动摘要
    last_update_info: StringProperty(
        name="Last Update",
        default="No updates received yet."
    )
    update_counter: IntProperty(default=0)
