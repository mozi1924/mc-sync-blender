import bpy
import time
from .deps_installer import is_websockets_installed, install_websockets
from .websocket_client import SyncClientThread

_client_thread = None

class YEFIRA_OT_install_deps(bpy.types.Operator):
    bl_idname = "yefira.install_deps"
    bl_label = "Install WebSocket Dependency"
    bl_description = "Install 'websockets' module into Blender's Python environment via pip"

    def execute(self, context):
        self.report({'INFO'}, "Installing 'websockets' library...")
        success = install_websockets()
        if success:
            self.report({'INFO'}, "Successfully installed 'websockets'!")
        else:
            self.report({'ERROR'}, "Failed to install 'websockets'. Check console for details.")
        return {'FINISHED'}

class YEFIRA_OT_connect(bpy.types.Operator):
    bl_idname = "yefira.connect"
    bl_label = "Connect"
    bl_description = "Connect to Yefira WebSocket Server"

    def execute(self, context):
        global _client_thread
        props = context.scene.yefira

        if not is_websockets_installed():
            self.report({'WARNING'}, "Please install 'websockets' dependency first!")
            return {'CANCELLED'}

        if _client_thread and _client_thread.is_alive():
            self.report({'INFO'}, "Already connected or connecting.")
            return {'FINISHED'}

        def run_in_main_thread(func):
            def wrapper():
                try:
                    func()
                    # 强制刷新 window_manager 界面重绘
                    for window in bpy.context.window_manager.windows:
                        for area in window.screen.areas:
                            area.tag_redraw()
                except Exception as e:
                    print(f"[Yefira] Timer update error: {e}")
                return None
            bpy.app.timers.register(wrapper)

        def on_status_change(status):
            def update():
                props.connection_status = status
                props.is_connected = (status == "CONNECTED")
            run_in_main_thread(update)

        def on_selection_info(min_x, min_y, min_z, size_x, size_y, size_z):
            def update():
                props.has_selection = True
                props.min_x, props.min_y, props.min_z = min_x, min_y, min_z
                props.max_x = min_x + size_x - 1
                props.max_y = min_y + size_y - 1
                props.max_z = min_z + size_z - 1
                props.size_x, props.size_y, props.size_z = size_x, size_y, size_z
                props.total_blocks = size_x * size_y * size_z
            run_in_main_thread(update)

        def on_full_snapshot(min_x, min_y, min_z, size_x, size_y, size_z, palette, total_blocks):
            def update():
                props.has_selection = True
                props.min_x, props.min_y, props.min_z = min_x, min_y, min_z
                props.max_x = min_x + size_x - 1
                props.max_y = min_y + size_y - 1
                props.max_z = min_z + size_z - 1
                props.size_x, props.size_y, props.size_z = size_x, size_y, size_z
                props.palette_count = len(palette)
                props.total_blocks = total_blocks
                props.update_counter += 1

                # 更新 Palette 列表
                props.palette_list.clear()
                for p_item in palette:
                    item = props.palette_list.add()
                    item.state_str = p_item

                props.last_update_info = f"Full Snapshot: {total_blocks} blocks, {len(palette)} palette states."

                # 记录日志历史
                item = props.delta_history.add()
                item.timestamp = time.strftime("%H:%M:%S")
                item.pos_str = f"Bounds: {size_x}x{size_y}x{size_z}"
                item.block_state = f"Snapshot ({total_blocks} blocks, {len(palette)} states)"
            run_in_main_thread(update)

        def on_delta_update(min_x, min_y, min_z, changes):
            def update():
                props.update_counter += 1
                if changes:
                    curr_time = time.strftime("%H:%M:%S")
                    for abs_x, abs_y, abs_z, state in changes:
                        item = props.delta_history.add()
                        item.timestamp = curr_time
                        item.pos_str = f"({abs_x}, {abs_y}, {abs_z})"
                        item.block_state = state

                    # 保持最多 30 条历史记录
                    while len(props.delta_history) > 30:
                        props.delta_history.remove(0)

                    abs_x, abs_y, abs_z, state = changes[-1]
                    props.last_update_info = f"Delta Update ({len(changes)} blocks):\n({abs_x},{abs_y},{abs_z}) -> {state}"
            run_in_main_thread(update)

        _client_thread = SyncClientThread(
            props.url,
            on_status_change,
            on_selection_info,
            on_full_snapshot,
            on_delta_update
        )
        _client_thread.start()
        self.report({'INFO'}, f"Connecting to {props.url}...")
        return {'FINISHED'}

class YEFIRA_OT_disconnect(bpy.types.Operator):
    bl_idname = "yefira.disconnect"
    bl_label = "Disconnect"
    bl_description = "Disconnect from Yefira WebSocket Server"

    def execute(self, context):
        global _client_thread
        props = context.scene.yefira

        if _client_thread:
            _client_thread.stop()
            _client_thread = None

        props.connection_status = "DISCONNECTED"
        props.is_connected = False
        self.report({'INFO'}, "Disconnected from Yefira server.")
        return {'FINISHED'}

class YEFIRA_OT_refresh(bpy.types.Operator):
    bl_idname = "yefira.refresh"
    bl_label = "Refresh Snapshot"
    bl_description = "Request server to send a fresh full snapshot"

    def execute(self, context):
        global _client_thread
        if _client_thread and _client_thread.is_alive():
            _client_thread.send_text("REFRESH")
            self.report({'INFO'}, "Sent REFRESH request to Yefira Server.")
        else:
            self.report({'WARNING'}, "Not connected to server.")
        return {'FINISHED'}

class YEFIRA_OT_clear_history(bpy.types.Operator):
    bl_idname = "yefira.clear_history"
    bl_label = "Clear History"
    bl_description = "Clear live update history log"

    def execute(self, context):
        context.scene.yefira.delta_history.clear()
        self.report({'INFO'}, "Cleared update history log.")
        return {'FINISHED'}
