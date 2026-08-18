import zlib
import logging

logger = logging.getLogger("Yefira")


def block_key(x: int, y: int, z: int) -> str:
    """Return the canonical, topology-independent identity of one MC block.

    Point indices are an implementation detail of Blender's mesh and are
    expected to change after an update.  Every sync consumer must therefore
    use this absolute-coordinate key (or the equivalent ``mc_pos`` attribute)
    when it needs to address a block.
    """
    return f"{int(x)},{int(y)},{int(z)}"


class VoxelStorage:
    def __init__(self):
        self.min_x = 0
        self.min_y = 0
        self.min_z = 0
        self.size_x = 0
        self.size_y = 0
        self.size_z = 0
        self.block_map = {}  # (abs_x, abs_y, abs_z) -> state_str
        self.section_crc_map = {}  # (sec_x, sec_y, sec_z) -> uint32 crc
        # Incremented for every authoritative full snapshot.  It is useful to
        # UI/render consumers and, importantly, documents that a snapshot is
        # a replacement of the complete selection rather than an append.
        self.generation = 0

    def clear(self):
        self.block_map.clear()
        self.section_crc_map.clear()
        self.size_x = self.size_y = self.size_z = 0
        self.generation += 1

    def matches_bounds(self, min_x, min_y, min_z) -> bool:
        """Whether an incremental packet belongs to the active selection."""
        return (
            self.size_x > 0 and self.size_y > 0 and self.size_z > 0
            and (self.min_x, self.min_y, self.min_z) == (min_x, min_y, min_z)
        )

    def contains(self, x, y, z) -> bool:
        return (
            self.min_x <= x < self.min_x + self.size_x
            and self.min_y <= y < self.min_y + self.size_y
            and self.min_z <= z < self.min_z + self.size_z
        )

    def set_full_snapshot(self, min_x, min_y, min_z, size_x, size_y, size_z, palette, grid_indices):
        self.min_x, self.min_y, self.min_z = min_x, min_y, min_z
        self.size_x, self.size_y, self.size_z = size_x, size_y, size_z
        self.block_map.clear()
        self.section_crc_map.clear()
        self.generation += 1

        total_blocks = size_x * size_y * size_z
        for idx in range(total_blocks):
            if idx < len(grid_indices):
                palette_idx = grid_indices[idx]
                if palette_idx < len(palette):
                    state_str = palette[palette_idx]
                    
                    # Unpack index: i = (x * sizeY + y) * sizeZ + z
                    rem = idx % (size_y * size_z)
                    x = idx // (size_y * size_z)
                    y = rem // size_z
                    z = rem % size_z

                    abs_x = min_x + x
                    abs_y = min_y + y
                    abs_z = min_z + z
                    self.block_map[(abs_x, abs_y, abs_z)] = state_str

        self.recalculate_all_section_crcs()
        return self.generation

    def set_section_snapshot(self, sec_x, sec_y, sec_z, start_x, start_y, start_z, size_x, size_y, size_z, palette, grid_indices):
        # Section data is only a repair payload for the current full snapshot.
        # Rejecting mismatched bounds prevents a late packet from an old
        # selection silently corrupting the active one.
        if not self.matches_bounds(self.min_x, self.min_y, self.min_z):
            return False
        if size_x < 0 or size_y < 0 or size_z < 0:
            return False

        total_blocks = size_x * size_y * size_z
        max_x = self.min_x + self.size_x - 1
        max_y = self.min_y + self.size_y - 1
        max_z = self.min_z + self.size_z - 1
        expected_start = (
            max(self.min_x, sec_x << 4),
            max(self.min_y, sec_y << 4),
            max(self.min_z, sec_z << 4),
        )
        expected_end = (
            min(max_x, (sec_x << 4) + 15),
            min(max_y, (sec_y << 4) + 15),
            min(max_z, (sec_z << 4) + 15),
        )
        expected_size = tuple(max(0, end - start + 1) for start, end in zip(expected_start, expected_end))
        if (start_x, start_y, start_z) != expected_start or (size_x, size_y, size_z) != expected_size:
            logger.warning("Discarded section snapshot with unexpected bounds for (%s, %s, %s)", sec_x, sec_y, sec_z)
            return False
        if len(grid_indices) < total_blocks or any(index < 0 or index >= len(palette) for index in grid_indices[:total_blocks]):
            logger.warning("Discarded malformed section snapshot for (%s, %s, %s)", sec_x, sec_y, sec_z)
            return False

        for idx in range(total_blocks):
            palette_idx = grid_indices[idx]
            state_str = palette[palette_idx]
            rem = idx % (size_y * size_z)
            x = idx // (size_y * size_z)
            y = rem // size_z
            z = rem % size_z

            abs_x = start_x + x
            abs_y = start_y + y
            abs_z = start_z + z
            self.block_map[(abs_x, abs_y, abs_z)] = state_str

        self.calculate_and_store_section_crc(sec_x, sec_y, sec_z)
        return True

    def apply_delta_update(self, min_x, min_y, min_z, changes) -> bool:
        """Apply one delta only when it belongs to the active snapshot.

        A delayed websocket callback can otherwise write valid coordinates
        from the preceding selection into a newly selected region.  Validate
        the entire batch first so delta application is atomic from the
        renderer's perspective.
        """
        if not self.matches_bounds(min_x, min_y, min_z):
            logger.warning("Discarded delta for stale selection bounds (%s, %s, %s)", min_x, min_y, min_z)
            return False
        if any(not self.contains(x, y, z) for x, y, z, _state in changes):
            logger.warning("Discarded delta containing coordinates outside the active selection")
            return False

        affected_sections = set()
        for abs_x, abs_y, abs_z, state_str in changes:
            self.block_map[(abs_x, abs_y, abs_z)] = state_str
            sec_key = (abs_x >> 4, abs_y >> 4, abs_z >> 4)
            affected_sections.add(sec_key)

        for sec_x, sec_y, sec_z in affected_sections:
            self.calculate_and_store_section_crc(sec_x, sec_y, sec_z)
        return True

    def calculate_and_store_section_crc(self, sec_x, sec_y, sec_z):
        max_x = self.min_x + self.size_x - 1
        max_y = self.min_y + self.size_y - 1
        max_z = self.min_z + self.size_z - 1

        start_x = max(self.min_x, sec_x << 4)
        end_x = min(max_x, (sec_x << 4) + 15)
        start_y = max(self.min_y, sec_y << 4)
        end_y = min(max_y, (sec_y << 4) + 15)
        start_z = max(self.min_z, sec_z << 4)
        end_z = min(max_z, (sec_z << 4) + 15)

        crc_val = 0
        for x in range(start_x, end_x + 1):
            for y in range(start_y, end_y + 1):
                for z in range(start_z, end_z + 1):
                    state_str = self.block_map.get((x, y, z), "minecraft:air")
                    crc_val = zlib.crc32(state_str.encode('utf-8'), crc_val)

        unsigned_crc = crc_val & 0xFFFFFFFF
        self.section_crc_map[(sec_x, sec_y, sec_z)] = unsigned_crc
        return unsigned_crc

    def recalculate_all_section_crcs(self):
        self.section_crc_map.clear()
        if self.size_x == 0 or self.size_y == 0 or self.size_z == 0:
            return

        max_x = self.min_x + self.size_x - 1
        max_y = self.min_y + self.size_y - 1
        max_z = self.min_z + self.size_z - 1

        min_sec_x, max_sec_x = self.min_x >> 4, max_x >> 4
        min_sec_y, max_sec_y = self.min_y >> 4, max_y >> 4
        min_sec_z, max_sec_z = self.min_z >> 4, max_z >> 4

        for sx in range(min_sec_x, max_sec_x + 1):
            for sy in range(min_sec_y, max_sec_y + 1):
                for sz in range(min_sec_z, max_sec_z + 1):
                    self.calculate_and_store_section_crc(sx, sy, sz)

    def validate_manifest(self, server_sections):
        mismatched = []
        for sec_x, sec_y, sec_z, server_crc32 in server_sections:
            key = (sec_x, sec_y, sec_z)
            local_crc = self.section_crc_map.get(key, None)
            if local_crc != server_crc32:
                mismatched.append(key)
        return mismatched


# Global VoxelStorage instance
voxel_storage = VoxelStorage()
