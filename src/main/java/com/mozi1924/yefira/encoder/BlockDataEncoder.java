package com.mozi1924.yefira.encoder;

import com.mozi1924.yefira.selection.SelectionBox;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.*;

public class BlockDataEncoder {

    public static final byte[] MAGIC = new byte[]{(byte) 0x4D, (byte) 0x43}; // 'M', 'C'
    public static final byte PROTOCOL_VERSION = 0x01;

    public static final byte PACKET_SELECTION_INFO = 0x01;
    public static final byte PACKET_FULL_SNAPSHOT = 0x02;
    public static final byte PACKET_DELTA_UPDATE = 0x03;

    /**
     * 将 BlockState 序列化为规范字符串标识，例如 "minecraft:oak_log[axis=y,facing=north]"
     */
    public static String serializeBlockState(BlockState state) {
        String blockId = BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString();
        Collection<Property<?>> properties = state.getProperties();
        if (properties.isEmpty()) {
            return blockId;
        }

        StringBuilder sb = new StringBuilder(blockId).append("[");
        boolean first = true;
        for (Property<?> property : properties) {
            if (!first) {
                sb.append(",");
            }
            sb.append(property.getName()).append("=").append(getPropertyValueName(state, property));
            first = false;
        }
        sb.append("]");
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    private static <T extends Comparable<T>> String getPropertyValueName(BlockState state, Property<T> property) {
        T val = state.getValue(property);
        return property.getName(val);
    }

    /**
     * 编码 0x01 Selection Info 字节数据包
     */
    public static byte[] encodeSelectionInfo(SelectionBox selection) {
        ByteBuffer buf = ByteBuffer.allocate(4 + 6 * 4);
        buf.order(ByteOrder.LITTLE_ENDIAN);

        // Header
        buf.put(MAGIC);
        buf.put(PROTOCOL_VERSION);
        buf.put(PACKET_SELECTION_INFO);

        // Min Pos
        buf.putInt(selection.getMin().getX());
        buf.putInt(selection.getMin().getY());
        buf.putInt(selection.getMin().getZ());

        // Size
        buf.putInt(selection.getSizeX());
        buf.putInt(selection.getSizeY());
        buf.putInt(selection.getSizeZ());

        return buf.array();
    }

    /**
     * 编码 0x02 Full Snapshot 全量快照字节数据包
     */
    public static byte[] encodeFullSnapshot(Level level, SelectionBox selection) {
        BlockPos min = selection.getMin();
        int sizeX = selection.getSizeX();
        int sizeY = selection.getSizeY();
        int sizeZ = selection.getSizeZ();

        // 收集所有 BlockState 建立 Palette
        List<String> palette = new ArrayList<>();
        Map<String, Integer> paletteMap = new HashMap<>();

        // 预处理建立 Palette 和 三维 State 数组
        int totalBlocks = sizeX * sizeY * sizeZ;
        int[] gridIndices = new int[totalBlocks];

        int index = 0;
        BlockPos.MutableBlockPos mutablePos = new BlockPos.MutableBlockPos();

        for (int x = 0; x < sizeX; x++) {
            for (int y = 0; y < sizeY; y++) {
                for (int z = 0; z < sizeZ; z++) {
                    mutablePos.set(min.getX() + x, min.getY() + y, min.getZ() + z);
                    BlockState state = level.getBlockState(mutablePos);
                    String stateStr = serializeBlockState(state);

                    int paletteIdx = paletteMap.computeIfAbsent(stateStr, k -> {
                        int newIdx = palette.size();
                        palette.add(k);
                        return newIdx;
                    });

                    gridIndices[index++] = paletteIdx;
                }
            }
        }

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (DataOutputStream out = new DataOutputStream(baos)) {
            // Little Endian 流辅助写入
            writeHeader(out, PACKET_FULL_SNAPSHOT);

            // Bounds
            writeIntLE(out, min.getX());
            writeIntLE(out, min.getY());
            writeIntLE(out, min.getZ());

            writeIntLE(out, sizeX);
            writeIntLE(out, sizeY);
            writeIntLE(out, sizeZ);

            // Palette Count
            writeShortLE(out, palette.size());
            for (String item : palette) {
                byte[] bytes = item.getBytes(StandardCharsets.UTF_8);
                writeShortLE(out, bytes.length);
                out.write(bytes);
            }

            // Grid Indices (use uint8 if palette.size() <= 256, else uint16)
            boolean isBytePalette = palette.size() <= 256;
            out.writeByte(isBytePalette ? 1 : 2); // 1 = byte index, 2 = short index

            for (int idx : gridIndices) {
                if (isBytePalette) {
                    out.writeByte(idx & 0xFF);
                } else {
                    writeShortLE(out, idx);
                }
            }
            out.flush();
        } catch (IOException e) {
            e.printStackTrace();
        }

        return baos.toByteArray();
    }

    /**
     * 编码 0x03 Delta Update 增量更新字节数据包
     */
    public static byte[] encodeDeltaUpdate(SelectionBox selection, List<BlockChangeEntry> changes) {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (DataOutputStream out = new DataOutputStream(baos)) {
            writeHeader(out, PACKET_DELTA_UPDATE);

            // Bounds min pos (for reference)
            writeIntLE(out, selection.getMin().getX());
            writeIntLE(out, selection.getMin().getY());
            writeIntLE(out, selection.getMin().getZ());

            // Count
            writeShortLE(out, changes.size());

            BlockPos min = selection.getMin();
            for (BlockChangeEntry change : changes) {
                int relX = change.pos().getX() - min.getX();
                int relY = change.pos().getY() - min.getY();
                int relZ = change.pos().getZ() - min.getZ();

                writeShortLE(out, relX);
                writeShortLE(out, relY);
                writeShortLE(out, relZ);

                String stateStr = serializeBlockState(change.state());
                byte[] bytes = stateStr.getBytes(StandardCharsets.UTF_8);
                writeShortLE(out, bytes.length);
                out.write(bytes);
            }
            out.flush();
        } catch (IOException e) {
            e.printStackTrace();
        }

        return baos.toByteArray();
    }

    public record BlockChangeEntry(BlockPos pos, BlockState state) {}

    private static void writeHeader(DataOutputStream out, byte packetType) throws IOException {
        out.write(MAGIC);
        out.writeByte(PROTOCOL_VERSION);
        out.writeByte(packetType);
    }

    private static void writeIntLE(DataOutputStream out, int value) throws IOException {
        out.writeByte(value & 0xFF);
        out.writeByte((value >> 8) & 0xFF);
        out.writeByte((value >> 16) & 0xFF);
        out.writeByte((value >> 24) & 0xFF);
    }

    private static void writeShortLE(DataOutputStream out, int value) throws IOException {
        out.writeByte(value & 0xFF);
        out.writeByte((value >> 8) & 0xFF);
    }
}
