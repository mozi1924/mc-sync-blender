package com.mozi1924.yefira.encoder;

public class BlockStateModelData {
    public final String stateStr;
    public final int blockType; // 0: CUBE, 1: CROSS_PLANT, 2: SLAB, 3: STAIRS, 4: TORCH, 5: PROP, 6: FLUID, 7: AIR
    public final boolean isOpaque;
    public final boolean isEmissive;
    public final float emissiveLevel;
    // 6-face array: 0: East (+X), 1: West (-X), 2: Top (+Y), 3: Bottom (-Y), 4: South (+Z), 5: North (-Z)
    public final BlockFaceData[] faces;

    public BlockStateModelData(
            String stateStr,
            int blockType,
            boolean isOpaque,
            boolean isEmissive,
            float emissiveLevel,
            BlockFaceData[] faces
    ) {
        this.stateStr = stateStr != null ? stateStr : "";
        this.blockType = blockType;
        this.isOpaque = isOpaque;
        this.isEmissive = isEmissive;
        this.emissiveLevel = emissiveLevel;
        if (faces != null && faces.length == 6) {
            this.faces = faces;
        } else {
            this.faces = new BlockFaceData[6];
            for (int i = 0; i < 6; i++) {
                this.faces[i] = BlockFaceData.simple("");
            }
        }
    }

    public String toJson() {
        StringBuilder sb = new StringBuilder();
        sb.append("{\"state\":\"").append(escapeJson(stateStr)).append("\"");
        sb.append(",\"type\":").append(blockType);
        sb.append(",\"opaque\":").append(isOpaque ? 1 : 0);
        sb.append(",\"emissive\":").append(isEmissive ? 1 : 0);
        if (emissiveLevel > 0.0f) {
            sb.append(",\"emissive_level\":").append(emissiveLevel);
        }
        sb.append(",\"faces\":{");
        String[] faceKeys = new String[]{"east", "west", "top", "bottom", "south", "north"};
        for (int i = 0; i < 6; i++) {
            if (i > 0) sb.append(",");
            sb.append("\"").append(faceKeys[i]).append("\":").append(faces[i].toJson());
        }
        sb.append("}}");
        return sb.toString();
    }

    private static String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    @Override
    public String toString() {
        return toJson();
    }
}
