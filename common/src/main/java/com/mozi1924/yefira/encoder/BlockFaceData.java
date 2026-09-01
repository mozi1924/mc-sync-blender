package com.mozi1924.yefira.encoder;

public class BlockFaceData {
    public final String texture;
    public final float uvRot; // 0.0, 90.0, 180.0, 270.0
    public final float[] uvBounds; // [u_min, v_min, u_max, v_max]
    public final int tintIndex; // -1 for untinted, >= 0 for tinted

    public BlockFaceData(String texture, float uvRot, float[] uvBounds, int tintIndex) {
        this.texture = texture != null ? texture : "";
        this.uvRot = uvRot;
        this.uvBounds = uvBounds != null && uvBounds.length == 4 ? uvBounds : new float[]{0.0f, 0.0f, 1.0f, 1.0f};
        this.tintIndex = tintIndex;
    }

    public static BlockFaceData simple(String texture) {
        return new BlockFaceData(texture, 0.0f, new float[]{0.0f, 0.0f, 1.0f, 1.0f}, -1);
    }

    public static BlockFaceData simple(String texture, float uvRot) {
        return new BlockFaceData(texture, uvRot, new float[]{0.0f, 0.0f, 1.0f, 1.0f}, -1);
    }

    public static BlockFaceData simple(String texture, float uvRot, int tintIndex) {
        return new BlockFaceData(texture, uvRot, new float[]{0.0f, 0.0f, 1.0f, 1.0f}, tintIndex);
    }

    public String toJson() {
        return "{\"tex\":\"" + texture + "\",\"rot\":" + (int) uvRot + ",\"uv\":["
                + uvBounds[0] + "," + uvBounds[1] + "," + uvBounds[2] + "," + uvBounds[3] + "],\"tint\":" + tintIndex + "}";
    }

    @Override
    public String toString() {
        return toJson();
    }
}
