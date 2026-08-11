import bpy
from .deps_installer import is_websockets_installed, install_websockets
from .websocket_client import SyncClientThread

_client_thread = None

class MOZISYNC_OT_install_deps(bpy.types.Operator):
    bl_idname = "mozisync.install_deps"
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

class MOZISYNC_OT_connect(bpy.types.Operator):
    bl_idname = "mozisync.connect"
    bl_label = "Connect"
    bl_description = "Connect to MC Sync WebSocket Server"

    def execute(self, context):
        global _client_thread
        props = context.scene.mozisync

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
                except Exception as e:
                    print(f"[Mozisync] Timer update error: {e}")
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
                props.size_x, props.size_y, props.size_z = size_x, size_y, size_z
            run_in_main_thread(update)

        def on_full_snapshot(min_x, min_y, min_z, size_x, size_y, size_z, palette, total_blocks):
            def update():
                props.has_selection = True
                props.min_x, props.min_y, props.min_z = min_x, min_y, min_z
                props.size_x, props.size_y, props.size_z = size_x, size_y, size_z
                props.palette_count = len(palette)
                props.total_blocks = total_blocks
                props.update_counter += 1
                props.last_update_info = f"Full Snapshot: {total_blocks} blocks, {len(palette)} palette states."
            run_in_main_thread(update)

        def on_delta_update(min_x, min_y, min_z, changes):
            def update():
                props.update_counter += 1
                if changes:
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

class MOZISYNC_OT_disconnect(bpy.types.Operator):
    bl_idname = "mozisync.disconnect"
    bl_label = "Disconnect"
    bl_description = "Disconnect from MC Sync WebSocket Server"

    def execute(self, context):
        global _client_thread
        props = context.scene.mozisync

        if _client_thread:
            _client_thread.stop()
            _client_thread = None

        props.connection_status = "DISCONNECTED"
        props.is_connected = False
        self.report({'INFO'}, "Disconnected from MC Sync server.")
        return {'FINISHED'}

class MOZISYNC_OT_refresh(bpy.types.Operator):
    bl_idname = "mozisync.refresh"
    bl_label = "Refresh Snapshot"
    bl_description = "Request server to send a fresh full snapshot"

    def execute(self, context):
        global _client_thread
        if _client_thread and _client_thread.is_alive():
            _client_thread.send_text("REFRESH")
            self.report({'INFO'}, "Sent REFRESH request to MC Sync Server.")
        else:
            self.report({'WARNING'}, "Not connected to server.")
        return {'FINISHED'}
