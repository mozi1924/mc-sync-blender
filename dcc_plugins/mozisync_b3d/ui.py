import bpy
from .deps_installer import is_websockets_installed

class MOZISYNC_PT_main_panel(bpy.types.Panel):
    bl_label = "MC Sync Blender (Mozisync B3D)"
    bl_idname = "MOZISYNC_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MC Sync"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.mozisync

        # 1. 依赖库检查与安装区
        box_dep = layout.box()
        box_dep.label(text="Dependency Status:", icon='PREFERENCES')
        if not is_websockets_installed():
            box_dep.alert = True
            box_dep.label(text="Missing 'websockets' library!", icon='ERROR')
            box_dep.operator("mozisync.install_deps", icon='CONSOLE')
        else:
            box_dep.label(text="websockets library: Installed", icon='CHECKMARK')

        layout.separator()

        # 2. 通信设置与连接区
        box_conn = layout.box()
        box_conn.label(text="WebSocket Connection", icon='URL')
        box_conn.prop(props, "url", text="Address")

        row = box_conn.row(align=True)
        if not props.is_connected:
            row.operator("mozisync.connect", icon='PLAY', text="Connect")
        else:
            row.operator("mozisync.disconnect", icon='PAUSE', text="Disconnect")
            row.operator("mozisync.refresh", icon='FILE_REFRESH', text="Refresh")

        # 状态指示
        status_row = box_conn.row()
        status_row.label(text=f"Status: {props.connection_status}")

        layout.separator()

        # 3. 接收端可行性验证数据面板
        box_data = layout.box()
        box_data.label(text="Receiver Feasibility Monitor", icon='INFO')

        if props.has_selection:
            box_data.label(text=f"Origin: ({props.min_x}, {props.min_y}, {props.min_z})")
            box_data.label(text=f"Bounds: {props.size_x} x {props.size_y} x {props.size_z}")
            box_data.label(text=f"Total Volume: {props.total_blocks} blocks")
            box_data.label(text=f"Palette States: {props.palette_count}")
        else:
            box_data.label(text="No active selection in MC world", icon='ERROR')

        layout.separator()

        # 4. 实时增量更新日志
        box_log = layout.box()
        box_log.label(text="Live Update Log", icon='SORTTIME')
        box_log.label(text=f"Updates Received: {props.update_counter}")
        
        # 换行显示更新摘要
        col = box_log.column()
        col.scale_y = 0.8
        for line in props.last_update_info.split("\n"):
            col.label(text=line)
