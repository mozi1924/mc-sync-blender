import bpy
from .deps_installer import is_websockets_installed

class YEFIRA_UL_palette_list(bpy.types.UIList):
    """Palette 调色板 UI 列表"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.state_str, icon='CUBE')

class YEFIRA_UL_delta_list(bpy.types.UIList):
    """Delta 变动历史 UI 列表"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.label(text=item.timestamp, icon='TIME')
            row.label(text=item.pos_str, icon='EMPTY_AXIS')
            row.label(text=item.block_state, icon='FILE_REFRESH')

class YEFIRA_PT_main_panel(bpy.types.Panel):
    bl_label = "Yefira B3D"
    bl_idname = "YEFIRA_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Yefira"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        props = scene.yefira

        # 1. 依赖库检查与安装区
        if not is_websockets_installed():
            box_dep = layout.box()
            box_dep.alert = True
            box_dep.label(text="Missing 'websockets' library!", icon='ERROR')
            box_dep.operator("yefira.install_deps", icon='CONSOLE')
            layout.separator()

        # 2. 通信设置与连接区
        box_conn = layout.box()
        box_conn.label(text="WebSocket Connection", icon='URL')
        box_conn.prop(props, "url", text="Address")

        row = box_conn.row(align=True)
        if not props.is_connected:
            row.operator("yefira.connect", icon='PLAY', text="Connect")
        else:
            row.operator("yefira.disconnect", icon='PAUSE', text="Disconnect")
            row.operator("yefira.refresh", icon='FILE_REFRESH', text="Refresh")

        # 状态指示
        status_row = box_conn.row()
        status_icon = 'CHECKMARK' if props.is_connected else 'CANCEL'
        status_row.label(text=f"Status: {props.connection_status}", icon=status_icon)

        layout.separator()

        # 3. 详细选区数据 Inspector 面板
        box_data = layout.box()
        box_data.label(text="Selection Details", icon='SCENE_DATA')

        if props.has_selection:
            col = box_data.column(align=True)
            col.label(text=f"Min Pos: ({props.min_x}, {props.min_y}, {props.min_z})", icon='NONE')
            col.label(text=f"Max Pos: ({props.max_x}, {props.max_y}, {props.max_z})", icon='NONE')
            col.label(text=f"Size: {props.size_x} x {props.size_y} x {props.size_z}", icon='NONE')
            col.label(text=f"Volume: {props.total_blocks} blocks", icon='OUTLINER_OB_MESH')
            col.label(text=f"Palette States: {props.palette_count} types", icon='OUTLINER_COLLECTION')

            # 4. Palette 方块调色板表
            box_pal = layout.box()
            box_pal.label(text="Palette Block States", icon='CUBE')
            box_pal.template_list(
                "YEFIRA_UL_palette_list", "",
                props, "palette_list",
                props, "palette_active_index",
                rows=4
            )
        else:
            box_data.label(text="No active selection in MC world", icon='ERROR')

        layout.separator()

        # 5. 实时变动历史日志 UIList
        box_log = layout.box()
        header_row = box_log.row(align=True)
        header_row.label(text=f"Live Updates ({props.update_counter})", icon='TIME')
        header_row.operator("yefira.clear_history", icon='TRASH', text="")

        box_log.template_list(
            "YEFIRA_UL_delta_list", "",
            props, "delta_history",
            props, "delta_active_index",
            rows=6
        )

        if props.last_update_info:
            box_log.label(text=f"Latest: {props.last_update_info}")
