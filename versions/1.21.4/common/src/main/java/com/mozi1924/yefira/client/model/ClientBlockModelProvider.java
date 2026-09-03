package com.mozi1924.yefira.client.model;

import com.mozi1924.yefira.encoder.BlockDataEncoder;
import com.mozi1924.yefira.encoder.BlockFaceData;
import com.mozi1924.yefira.encoder.BlockModelExtractor;
import com.mozi1924.yefira.encoder.BlockStateModelData;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.block.model.BakedQuad;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.client.resources.model.ModelManager;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;

public class ClientBlockModelProvider implements BlockModelExtractor.IModelProvider {

    private static final Direction[] MC_DIRECTIONS = new Direction[]{
            Direction.EAST,  // Index 0: +X
            Direction.WEST,  // Index 1: -X
            Direction.UP,    // Index 2: +Y
            Direction.DOWN,  // Index 3: -Y
            Direction.SOUTH, // Index 4: +Z
            Direction.NORTH  // Index 5: -Z
    };

    @Override
    public BlockStateModelData getModelData(BlockState state) {
        Minecraft client = Minecraft.getInstance();
        if (client == null) {
            return BlockModelExtractor.FallbackModelProvider.extract(state);
        }

        ModelManager modelManager = client.getModelManager();
        if (modelManager == null || modelManager.getBlockModelShaper() == null) {
            return BlockModelExtractor.FallbackModelProvider.extract(state);
        }

        BakedModel model = modelManager.getBlockModelShaper().getBlockModel(state);
        if (model == null) {
            return BlockModelExtractor.FallbackModelProvider.extract(state);
        }

        String stateStr = BlockDataEncoder.serializeBlockState(state);
        String blockId = BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString();
        String name = blockId.startsWith("minecraft:") ? blockId.substring(10) : blockId;

        int blockType = 0;
        if (name.equals("air") || name.equals("cave_air") || name.equals("void_air") || name.equals("bubble_column") || name.equals("structure_void")) {
            blockType = 7;
        } else if (name.equals("water") || name.equals("flowing_water") || name.equals("lava") || name.equals("flowing_lava")) {
            blockType = 6;
        } else if (name.endsWith("_stairs")) {
            blockType = 3;
        } else if (name.endsWith("_slab")) {
            blockType = 2;
        } else if (name.contains("torch") || name.contains("lantern")) {
            blockType = 4;
        }

        boolean isOpaque = !name.contains("glass") && !name.contains("leaves") && !name.contains("ice") && !name.contains("water") && !name.contains("air") && !name.equals("bubble_column") && !name.equals("structure_void");
        boolean isEmissive = name.contains("glowstone") || name.contains("sea_lantern") || name.contains("shroomlight") || name.contains("magma") || name.contains("lava") || name.contains("fire") || name.contains("lantern");
        float emissiveLevel = isEmissive ? 1.0f : 0.0f;

        RandomSource random = RandomSource.create(42L);
        BlockFaceData[] faces = new BlockFaceData[6];

        for (int i = 0; i < 6; i++) {
            Direction dir = MC_DIRECTIONS[i];
            BakedQuad chosenQuad = null;

            List<BakedQuad> quads = model.getQuads(state, dir, random);
            if (quads != null && !quads.isEmpty()) {
                chosenQuad = quads.get(0);
            }

            if (chosenQuad == null) {
                // Try unculled quads (null direction)
                List<BakedQuad> unculled = model.getQuads(state, null, random);
                if (unculled != null && !unculled.isEmpty()) {
                    for (BakedQuad q : unculled) {
                        if (q.getDirection() == dir) {
                            chosenQuad = q;
                            break;
                        }
                    }
                }
            }

            if (chosenQuad != null) {
                faces[i] = extractFaceFromQuad(chosenQuad, dir);
            } else {
                if (name.contains("banner")) {
                    faces[i] = BlockFaceData.simple("minecraft:entity/banner/banner_base");
                } else {
                    faces[i] = BlockFaceData.simple("minecraft:block/" + name);
                }
            }
        }

        return new BlockStateModelData(stateStr, blockType, isOpaque, isEmissive, emissiveLevel, faces);
    }

    private BlockFaceData extractFaceFromQuad(BakedQuad quad, Direction dir) {
        TextureAtlasSprite sprite = quad.getSprite();
        String spriteName = sprite != null && sprite.contents() != null ? sprite.contents().name().toString() : "";
        int tintIndex = quad.getTintIndex();

        if (sprite == null) {
            return new BlockFaceData(spriteName, 0.0f, new float[]{0.0f, 0.0f, 1.0f, 1.0f}, tintIndex);
        }

        float u0 = sprite.getU0();
        float u1 = sprite.getU1();
        float v0 = sprite.getV0();
        float v1 = sprite.getV1();
        float duRange = (u1 - u0);
        float dvRange = (v1 - v0);
        if (Math.abs(duRange) < 1e-6f) duRange = 1.0f;
        if (Math.abs(dvRange) < 1e-6f) dvRange = 1.0f;

        float[] s = new float[4];
        float[] t = new float[4];
        float[] nu = new float[4];
        float[] nv = new float[4];

        int[] vertices = quad.getVertices();
        for (int v = 0; v < 4; v++) {
            int offset = v * 8;
            float x = Float.intBitsToFloat(vertices[offset]);
            float y = Float.intBitsToFloat(vertices[offset + 1]);
            float z = Float.intBitsToFloat(vertices[offset + 2]);
            float u = Float.intBitsToFloat(vertices[offset + 4]);
            float vCoord = Float.intBitsToFloat(vertices[offset + 5]);

            nu[v] = (u - u0) / duRange;
            nv[v] = (vCoord - v0) / dvRange;

            // Compute local 2D (s, t) on the given face plane
            switch (dir) {
                case UP -> {
                    s[v] = x;
                    t[v] = z;
                }
                case DOWN -> {
                    s[v] = x;
                    t[v] = 1.0f - z;
                }
                case NORTH -> {
                    s[v] = 1.0f - x;
                    t[v] = 1.0f - y;
                }
                case SOUTH -> {
                    s[v] = x;
                    t[v] = 1.0f - y;
                }
                case WEST -> {
                    s[v] = z;
                    t[v] = 1.0f - y;
                }
                case EAST -> {
                    s[v] = 1.0f - z;
                    t[v] = 1.0f - y;
                }
            }
        }

        // Calculate UV bounds in sprite [0, 1] space
        float minU = Math.min(Math.min(nu[0], nu[1]), Math.min(nu[2], nu[3]));
        float maxU = Math.max(Math.max(nu[0], nu[1]), Math.max(nu[2], nu[3]));
        float minV = Math.min(Math.min(nv[0], nv[1]), Math.min(nv[2], nv[3]));
        float maxV = Math.max(Math.max(nv[0], nv[1]), Math.max(nv[2], nv[3]));

        // In canonical FaceInfo order: 0 is TL, 1 is BL, 2 is BR, 3 is TR
        int bestCorner = 0;
        float bestDist = Float.MAX_VALUE;
        for (int v = 0; v < 4; v++) {
            float du = nu[v] - minU;
            float dv = nv[v] - minV;
            float dist = du * du + dv * dv;
            if (dist < bestDist) {
                bestDist = dist;
                bestCorner = v;
            }
        }

        float uvRot = switch (bestCorner) {
            case 0 -> 0.0f;
            case 3 -> 90.0f;
            case 2 -> 180.0f;
            case 1 -> 270.0f;
            default -> 0.0f;
        };

        return new BlockFaceData(spriteName, uvRot, new float[]{minU, minV, maxU, maxV}, tintIndex);
    }
}
