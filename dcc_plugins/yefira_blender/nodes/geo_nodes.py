import bpy
import logging
from ..core.storage import VoxelStorage

logger = logging.getLogger("Yefira")

AIR_BLOCK_IDS = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}

def update_blender_point_cloud(context, storage: VoxelStorage, filter_air=True, enable_geo_nodes=True):
    if storage.size_x == 0 or storage.size_y == 0 or storage.size_z == 0:
        return None

    min_x, min_y, min_z = storage.min_x, storage.min_y, storage.min_z
    size_x, size_y, size_z = storage.size_x, storage.size_y, storage.size_z

    obj_name = "Yefira_PointCloud"
    mesh_name = "Yefira_PointCloud_Mesh"

    if obj_name in bpy.data.objects:
        obj = bpy.data.objects[obj_name]
        mesh = obj.data
    else:
        mesh = bpy.data.meshes.new(mesh_name)
        obj = bpy.data.objects.new(obj_name, mesh)
        obj.location = (0.0, 0.0, 0.0)
        context.collection.objects.link(obj)

    vertices = []
    block_states = []
    block_ids = []
    mc_positions = []

    palette_map = {}

    for (abs_x, abs_y, abs_z), state_str in storage.block_map.items():
        if filter_air and state_str in AIR_BLOCK_IDS:
            continue

        vx = (abs_x - min_x) - size_x / 2.0 + 0.5
        vy = (abs_z - min_z) - size_z / 2.0 + 0.5  # Blender Y = MC Z
        vz = (abs_y - min_y) + 0.5               # Blender Z = MC Y

        vertices.append((vx, vy, vz))
        block_states.append(state_str.encode('utf-8'))

        if state_str not in palette_map:
            palette_map[state_str] = len(palette_map)
        block_ids.append(palette_map[state_str])
        mc_positions.append((float(abs_x), float(abs_y), float(abs_z)))

    mesh.clear_geometry()
    mesh.from_pydata(vertices, [], [])
    mesh.update()

    if vertices:
        # 1. block_state (STRING)
        attr_state = mesh.attributes.get("block_state")
        if not attr_state or attr_state.domain != 'POINT' or attr_state.data_type != 'STRING':
            if attr_state:
                mesh.attributes.remove(attr_state)
            attr_state = mesh.attributes.new(name="block_state", type='STRING', domain='POINT')

        # 2. block_id (INT)
        attr_id = mesh.attributes.get("block_id")
        if not attr_id or attr_id.domain != 'POINT' or attr_id.data_type != 'INT':
            if attr_id:
                mesh.attributes.remove(attr_id)
            attr_id = mesh.attributes.new(name="block_id", type='INT', domain='POINT')

        # 3. mc_pos (FLOAT_VECTOR)
        attr_pos = mesh.attributes.get("mc_pos")
        if not attr_pos or attr_pos.domain != 'POINT' or attr_pos.data_type != 'FLOAT_VECTOR':
            if attr_pos:
                mesh.attributes.remove(attr_pos)
            attr_pos = mesh.attributes.new(name="mc_pos", type='FLOAT_VECTOR', domain='POINT')

        for i in range(len(vertices)):
            attr_state.data[i].value = block_states[i]
            attr_id.data[i].value = block_ids[i]
            attr_pos.data[i].vector = mc_positions[i]

    if enable_geo_nodes:
        setup_geometry_nodes(obj)

    return obj


def setup_geometry_nodes(obj):
    mod_name = "Yefira_VoxelRenderer"
    tree_name = "Yefira_VoxelTree"

    mod = obj.modifiers.get(mod_name)
    if not mod:
        mod = obj.modifiers.new(name=mod_name, type='NODES')

    if not mod.node_group:
        if tree_name in bpy.data.node_groups:
            gn_tree = bpy.data.node_groups[tree_name]
        else:
            gn_tree = bpy.data.node_groups.new(name=tree_name, type='GeometryNodeTree')
            gn_tree.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
            gn_tree.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

            nodes = gn_tree.nodes
            input_node = nodes.new('NodeGroupInput')
            output_node = nodes.new('NodeGroupOutput')
            input_node.location = (-300, 0)
            output_node.location = (300, 0)

            iop = nodes.new('GeometryNodeInstanceOnPoints')
            iop.location = (0, 0)

            cube = nodes.new('GeometryNodeMeshCube')
            cube.inputs['Size'].default_value = (0.95, 0.95, 0.95)
            cube.location = (-200, -150)

            links = gn_tree.links
            links.new(input_node.outputs['Geometry'], iop.inputs['Points'])
            links.new(cube.outputs['Mesh'], iop.inputs['Instance'])
            links.new(iop.outputs['Instances'], output_node.inputs['Geometry'])

        mod.node_group = gn_tree
