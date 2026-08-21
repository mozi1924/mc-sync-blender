import bpy
import time
from ..core.deps_installer import is_websockets_installed, install_websockets
from ..network.websocket_client import SyncClientThread
from ..core.storage import voxel_storage
from ..core.point_cloud_builder import update_world_point_cloud
from ..nodes.geo_nodes import setup_world_geometry_nodes
from ..materials.atlas_integration import extract_atlas_parameters, find_bound_atlas_material

_client_thread = None
_last_seq_id = 0
_rebuild_timer_registered = False

# Deltas received inside this window are applied to VoxelStorage immediately
# on Blender's main thread, but evaluated as one point-cloud update.  This
# prevents a fast edit/fill operation from rebuilding the complete mesh and
# Geometry Nodes graph once per changed block.
REBUILD_DEBOUNCE_SECONDS = 0.075

def trigger_point_cloud_update(context: bpy.types.Context):
    """Update Yefira_World point cloud and configure Geometry Nodes engine."""
    props = context.scene.yefira
    existing_world = bpy.data.objects.get("Yefira_World")
    atlas_params = extract_atlas_parameters(find_bound_atlas_material(existing_world))
    atlas_mapping_dict = atlas_params.get("material_id_map", {})
    block_face_lut = atlas_params.get("block_face_lut", {})

    res = update_world_point_cloud(
        context,
        voxel_storage,
        filter_air=props.filter_air,
        atlas_mapping_dict=atlas_mapping_dict,
        block_face_lut=block_face_lut,
        block_face_chunk_lut=atlas_params.get("block_face_chunk_lut", {}),
        block_face_texture_lut=atlas_params.get("block_face_texture_lut", {}),
        block_face_tint_lut=atlas_params.get("block_face_tint_lut", {}),
        block_face_anim_timing_lut=atlas_params.get("block_face_anim_timing_lut", {}),
        block_face_anim_frame_size_lut=atlas_params.get("block_face_anim_frame_size_lut", {}),
        block_face_uv_rot_lut=atlas_params.get("block_face_uv_rot_lut", {}),
        block_face_uv_bounds_lut=atlas_params.get("block_face_uv_bounds_lut", {}),
        atlas_mapping_textures=atlas_params.get("mapping", {}).get("textures", {}) if isinstance(atlas_params.get("mapping"), dict) else {},
        atlas_width=atlas_params["width"],
        atlas_height=atlas_params["height"],
        tile_size=atlas_params["tile_size"],
        tiles_per_row=atlas_params["tiles_per_row"],
        anim_atlas_width=atlas_params.get("chunk_1_width", 896.0),
        anim_atlas_height=atlas_params.get("chunk_1_height", 1024.0),
        anim_frame_width=atlas_params.get("chunk_1_tile_size", 16.0),
        anim_frame_height=atlas_params.get("chunk_1_tile_size", 16.0),
    )

    if res.world_obj:
        setup_world_geometry_nodes(res.world_obj)

    props.point_count = res.point_count
    props.cubes_count = res.cubes_count
    props.props_count = res.props_count
    props.fluids_count = res.fluids_count


def schedule_point_cloud_update() -> None:
    """Coalesce live updates into a single main-thread point-cloud rebuild."""
    global _rebuild_timer_registered
    if _rebuild_timer_registered:
        return

    _rebuild_timer_registered = True

    def flush():
        global _rebuild_timer_registered
        try:
            # Timers run on Blender's main thread.  Always read the current
            # context here rather than retaining a potentially invalid area
            # context from the websocket callback.
            if voxel_storage.size_x and voxel_storage.size_y and voxel_storage.size_z:
                trigger_point_cloud_update(bpy.context)
        except Exception as e:
            print(f"[Yefira] Deferred point-cloud update error: {e}")
        finally:
            _rebuild_timer_registered = False
        return None

    bpy.app.timers.register(flush, first_interval=REBUILD_DEBOUNCE_SECONDS)


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


class YEFIRA_OT_rebuild_world(bpy.types.Operator):
    bl_idname = "yefira.rebuild_world"
    bl_label = "Rebuild Point Cloud"
    bl_description = "Rebuild Point Cloud and re-evaluate Geometry Nodes tree"

    def execute(self, context):
        if voxel_storage.size_x == 0 or voxel_storage.size_y == 0:
            self.report({'WARNING'}, "No voxel data in storage.")
            return {'CANCELLED'}

        trigger_point_cloud_update(context)
        self.report({'INFO'}, "Rebuilt Point Cloud and Geometry Nodes successfully.")
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
                global _last_seq_id
                # The manifest immediately following this full replacement
                # establishes its sequence baseline.
                _last_seq_id = 0
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

                # 1. Update VoxelStorage
                voxel_storage.set_full_snapshot(min_x, min_y, min_z, size_x, size_y, size_z, palette, grid_indices)

                # Point-cloud evaluation is debounced so an immediately
                # following manifest or repair packet cannot cause a second
                # full rebuild.
                schedule_point_cloud_update()

                # Update Palette UI list
                props.palette_list.clear()
                for p_item in palette:
                    item = props.palette_list.add()
                    item.state_str = p_item

                props.last_update_info = f"Full Snapshot queued: {total_blocks} blocks (generation {voxel_storage.generation})"

                # Log delta history
                item = props.delta_history.add()
                item.timestamp = time.strftime("%H:%M:%S")
                item.pos_str = f"Bounds: {size_x}x{size_y}x{size_z}"
                item.block_state = f"Snapshot ({total_blocks} blks; render queued)"
            run_in_main_thread(update)

        def on_delta_update(min_x, min_y, min_z, changes, seq_id):
            def update():
                global _last_seq_id
                props.update_counter += 1

                if _last_seq_id > 0 and seq_id > _last_seq_id + 1:
                    print(f"[Yefira] SeqID gap detected! Expected {_last_seq_id + 1}, got {seq_id}. Requesting full sync...")
                    if _client_thread:
                        _client_thread.send_req_full_sync()
                    # Do not render a known-incomplete state while the
                    # authoritative replacement snapshot is in flight.
                    return

                if _last_seq_id > 0 and seq_id <= _last_seq_id:
                    print(f"[Yefira] Ignoring stale Delta SeqID {seq_id} (current {_last_seq_id}).")
                    return

                _last_seq_id = seq_id

                if changes:
                    # Storage verifies the packet's absolute selection origin
                    # before mutation, so a delayed previous-selection delta
                    # cannot be addressed by a transient point index.
                    if not voxel_storage.apply_delta_update(min_x, min_y, min_z, changes):
                        if _client_thread:
                            _client_thread.send_req_full_sync()
                        return
                    schedule_point_cloud_update()

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
                props.validation_info = "Verified" if props.sync_verified else f"Repairing {len(mismatched)} section(s)"

                item = props.delta_history.add()
                item.timestamp = time.strftime("%H:%M:%S")
                item.pos_str = f"Manifest: {len(sections)} Sections"
                item.block_state = "Verified OK" if props.sync_verified else f"{len(mismatched)} Mismatches"

                if mismatched and _client_thread:
                    print(f"[Yefira] CRC mismatch in {len(mismatched)} sections. Requesting section sync...")
                    _client_thread.send_req_section_sync(mismatched)
            run_in_main_thread(update)

        def on_section_snapshot(sec_x, sec_y, sec_z, start_x, start_y, start_z, size_x, size_y, size_z, palette, grid_indices):
            def update():
                if voxel_storage.set_section_snapshot(sec_x, sec_y, sec_z, start_x, start_y, start_z, size_x, size_y, size_z, palette, grid_indices):
                    schedule_point_cloud_update()
                    props.last_update_info = f"Section ({sec_x}, {sec_y}, {sec_z}) repaired (render queued)."
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
        return {'FINISHED'}


class YEFIRA_OT_disconnect(bpy.types.Operator):
    bl_idname = "yefira.disconnect"
    bl_label = "Disconnect"
    bl_description = "Disconnect from Yefira WebSocket Server"

    def execute(self, context):
        global _client_thread
        if _client_thread:
            _client_thread.stop()
            _client_thread = None
        props = context.scene.yefira
        props.is_connected = False
        props.connection_status = "DISCONNECTED"
        return {'FINISHED'}


class YEFIRA_OT_refresh(bpy.types.Operator):
    bl_idname = "yefira.refresh"
    bl_label = "Refresh"
    bl_description = "Request full snapshot refresh from Minecraft server"

    def execute(self, context):
        global _client_thread
        if _client_thread and _client_thread.is_connected:
            _client_thread.send_req_full_sync()
            self.report({'INFO'}, "Requested full snapshot from server.")
        else:
            self.report({'WARNING'}, "Not connected to server.")
        return {'FINISHED'}


class YEFIRA_OT_clear_history(bpy.types.Operator):
    bl_idname = "yefira.clear_history"
    bl_label = "Clear History"
    bl_description = "Clear delta change history log"

    def execute(self, context):
        props = context.scene.yefira
        props.delta_history.clear()
        return {'FINISHED'}
