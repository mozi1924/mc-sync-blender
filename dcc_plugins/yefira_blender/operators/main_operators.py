import bpy
import time
from ..core.deps_installer import is_websockets_installed, install_websockets
from ..network.websocket_client import SyncClientThread
from ..core.storage import voxel_storage
from ..nodes.geo_nodes import update_blender_point_cloud

_client_thread = None
_last_seq_id = 0

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
        global _client_thread, _last_seq_id
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

        def on_full_snapshot(min_x, min_y, min_z, size_x, size_y, size_z, palette, grid_indices):
            def update():
                props.has_selection = True
                props.min_x, props.min_y, props.min_z = min_x, min_y, min_z
                props.max_x = min_x + size_x - 1
                props.max_y = min_y + size_y - 1
                props.max_z = min_z + size_z - 1
                props.size_x, props.size_y, props.size_z = size_x, size_y, size_z
                props.palette_count = len(palette)
                total_blocks = size_x * size_y * size_z
                props.total_blocks = total_blocks
                props.update_counter += 1

                # 1. 更新 VoxelStorage 内存存储
                voxel_storage.set_full_snapshot(min_x, min_y, min_z, size_x, size_y, size_z, palette, grid_indices)

                # 2. 构建/更新 Blender 中的点云 Mesh 及其自定义属性
                obj = update_blender_point_cloud(bpy.context, voxel_storage, props.filter_air, props.enable_geo_nodes)
                props.point_count = len(obj.data.vertices) if obj else 0

                # 更新 Palette UI 列表
                props.palette_list.clear()
                for p_item in palette:
                    item = props.palette_list.add()
                    item.state_str = p_item

                props.last_update_info = f"Full Snapshot: {total_blocks} blocks ({props.point_count} points)."

                # 记录日志历史
                item = props.delta_history.add()
                item.timestamp = time.strftime("%H:%M:%S")
                item.pos_str = f"Bounds: {size_x}x{size_y}x{size_z}"
                item.block_state = f"Snapshot ({total_blocks} blocks, {props.point_count} pts)"
            run_in_main_thread(update)

        def on_delta_update(min_x, min_y, min_z, changes, seq_id):
            def update():
                global _last_seq_id
                props.update_counter += 1

                if _last_seq_id > 0 and seq_id > _last_seq_id + 1:
                    print(f"[Yefira] SeqID gap detected! Expected {_last_seq_id + 1}, got {seq_id}. Requesting full sync...")
                    if _client_thread:
                        _client_thread.send_req_full_sync()

                _last_seq_id = seq_id

                if changes:
                    # 更新 VoxelStorage 增量数据
                    voxel_storage.apply_delta_update(changes)
                    obj = update_blender_point_cloud(bpy.context, voxel_storage, props.filter_air, props.enable_geo_nodes)
                    props.point_count = len(obj.data.vertices) if obj else 0

                    curr_time = time.strftime("%H:%M:%S")
                    for abs_x, abs_y, abs_z, state in changes:
                        item = props.delta_history.add()
                        item.timestamp = curr_time
                        item.pos_str = f"({abs_x}, {abs_y}, {abs_z})"
                        item.block_state = f"[Seq #{seq_id}] {state}"

                    while len(props.delta_history) > 30:
                        props.delta_history.remove(0)

                    abs_x, abs_y, abs_z, state = changes[-1]
                    props.last_update_info = f"Delta [Seq #{seq_id}] ({len(changes)} blocks):\n({abs_x},{abs_y},{abs_z}) -> {state}"
            run_in_main_thread(update)

        def on_section_manifest(current_seq_id, sections):
            def update():
                global _last_seq_id
                _last_seq_id = current_seq_id

                mismatched = voxel_storage.validate_manifest(sections)
                props.sync_verified = (len(mismatched) == 0)
                props.mismatch_count = len(mismatched)

                item = props.delta_history.add()
                item.timestamp = time.strftime("%H:%M:%S")
                item.pos_str = f"Manifest: {len(sections)} Sections"

                if mismatched:
                    props.validation_info = f"Mismatch: {len(mismatched)} / {len(sections)} sections"
                    item.block_state = f"Validation mismatch for {len(mismatched)} sections, requesting section sync..."
                    if _client_thread:
                        _client_thread.send_req_section_sync(mismatched)
                else:
                    props.validation_info = f"100% Synced ({len(sections)} sections verified)"
                    item.block_state = f"All {len(sections)} sections validated (CRC32 OK)."

            run_in_main_thread(update)

        def on_section_snapshot(sec_x, sec_y, sec_z, start_x, start_y, start_z, size_x, size_y, size_z, palette, grid_indices):
            def update():
                props.update_counter += 1
                voxel_storage.set_section_snapshot(sec_x, sec_y, sec_z, start_x, start_y, start_z, size_x, size_y, size_z, palette, grid_indices)
                obj = update_blender_point_cloud(bpy.context, voxel_storage, props.filter_air, props.enable_geo_nodes)
                props.point_count = len(obj.data.vertices) if obj else 0

                item = props.delta_history.add()
                item.timestamp = time.strftime("%H:%M:%S")
                item.pos_str = f"Section ({sec_x},{sec_y},{sec_z})"
                item.block_state = f"Section Sync ({props.point_count} pts)"
            run_in_main_thread(update)

        _client_thread = SyncClientThread(
            props.url,
            on_status_change,
            on_selection_info,
            on_full_snapshot,
            on_delta_update,
            on_section_manifest,
            on_section_snapshot
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

class YEFIRA_OT_rebuild_point_cloud(bpy.types.Operator):
    bl_idname = "yefira.rebuild_point_cloud"
    bl_label = "Rebuild Point Cloud"
    bl_description = "Force rebuild Blender Point Cloud mesh and custom attributes from local voxel storage"

    def execute(self, context):
        props = context.scene.yefira
        obj = update_blender_point_cloud(context, voxel_storage, props.filter_air, props.enable_geo_nodes)
        if obj:
            props.point_count = len(obj.data.vertices)
            self.report({'INFO'}, f"Successfully rebuilt Point Cloud: {props.point_count} points.")
        else:
            self.report({'WARNING'}, "No voxel data available to rebuild point cloud.")
        return {'FINISHED'}

class YEFIRA_OT_clear_history(bpy.types.Operator):
    bl_idname = "yefira.clear_history"
    bl_label = "Clear History"
    bl_description = "Clear live update history log"

    def execute(self, context):
        context.scene.yefira.delta_history.clear()
        self.report({'INFO'}, "Cleared update history log.")
        return {'FINISHED'}
