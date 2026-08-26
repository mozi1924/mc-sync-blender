package com.mozi1924.yefira.client.model;

import com.mozi1924.yefira.encoder.BlockDataEncoder;
import com.mozi1924.yefira.encoder.BlockFaceData;
import com.mozi1924.yefira.encoder.BlockModelExtractor;
import com.mozi1924.yefira.encoder.BlockStateModelData;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.geom.builders.UVPair;
import net.minecraft.client.renderer.block.BlockStateModelSet;
import net.minecraft.client.renderer.block.dispatch.BlockStateModel;
import net.minecraft.client.renderer.block.dispatch.BlockStateModelPart;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.client.resources.model.ModelManager;
import net.minecraft.client.resources.model.geometry.BakedQuad;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.block.state.BlockState;
import org.joml.Vector3fc;

import java.util.ArrayList;
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
        if (modelManager == null) {
            return BlockModelExtractor.FallbackModelProvider.extract(state);
        }

        BlockStateModelSet modelSet = modelManager.getBlockStateModelSet();
        if (modelSet == null) {
            return BlockModelExtractor.FallbackModelProvider.extract(state);
        }

        BlockStateModel model = modelSet.get(state);
        if (model == null) {
            return BlockModelExtractor.FallbackModelProvider.extract(state);
        }

        String stateStr = BlockDataEncoder.serializeBlockState(state);
        String blockId = BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString();
        String name = blockId.startsWith("minecraft:") ? blockId.substring(10) : blockId;

        int blockType = 0;
        if (name.equals("air") || name.equals("cave_air") || name.equals("void_air")) {
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

        boolean isOpaque = !name.contains("glass") && !name.contains("leaves") && !name.contains("ice") && !name.contains("water") && !name.contains("air");
        boolean isEmissive = name.contains("glowstone") || name.contains("sea_lantern") || name.contains("shroomlight") || name.contains("magma") || name.contains("lava") || name.contains("fire") || name.contains("lantern");
        float emissiveLevel = isEmissive ? 1.0f : 0.0f;

        RandomSource random = RandomSource.create(42L);
        List<BlockStateModelPart> parts = new ArrayList<>();
        try {
            model.collectParts(random, parts);
        } catch (Throwable ignored) {}

        BlockFaceData[] faces = new BlockFaceData[6];

        for (int i = 0; i < 6; i++) {
            Direction dir = MC_DIRECTIONS[i];
            BakedQuad chosenQuad = null;

            if (parts != null) {
                for (BlockStateModelPart part : parts) {
                    List<BakedQuad> quads = part.getQuads(dir);
                    if (quads != null && !quads.isEmpty()) {
                        chosenQuad = quads.get(0);
                        break;
                    }
                }
                if (chosenQuad == null) {
                    // Try unculled quads (null direction)
                    for (BlockStateModelPart part : parts) {
                        List<BakedQuad> quads = part.getQuads(null);
                        if (quads != null && !quads.isEmpty()) {
                            for (BakedQuad q : quads) {
                                if (q.direction() == dir) {
                                    chosenQuad = q;
                                    break;
                                }
                            }
                            if (chosenQuad != null) break;
                        }
                    }
                }
            }

            if (chosenQuad != null) {
                faces[i] = extractFaceFromQuad(chosenQuad, dir);
            } else {
                if (name.equals("chest") || name.equals("trapped_chest") || name.equals("ender_chest")) {
                    String cStem = name.equals("chest") ? "normal" : (name.equals("trapped_chest") ? "trapped" : "ender");
                    faces[i] = BlockFaceData.simple("minecraft:entity/chest/" + cStem);
                } else if (name.contains("banner")) {
                    faces[i] = BlockFaceData.simple("minecraft:entity/banner/banner_base");
                } else {
                    faces[i] = BlockFaceData.simple("minecraft:block/" + name);
                }
            }
        }

        return new BlockStateModelData(stateStr, blockType, isOpaque, isEmissive, emissiveLevel, faces);
    }

    private BlockFaceData extractFaceFromQuad(BakedQuad quad, Direction dir) {
        TextureAtlasSprite sprite = quad.materialInfo() != null ? quad.materialInfo().sprite() : null;
        String spriteName = sprite != null && sprite.contents() != null ? sprite.contents().name().toString() : "";
        int tintIndex = quad.materialInfo() != null ? quad.materialInfo().tintIndex() : -1;

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

        for (int v = 0; v < 4; v++) {
            Vector3fc pos = quad.position(v);
            long packedUV = quad.packedUV(v);
            float u = UVPair.unpackU(packedUV);
            float vCoord = UVPair.unpackV(packedUV);

            nu[v] = (u - u0) / duRange;
            nv[v] = (vCoord - v0) / dvRange;

            float x = pos.x();
            float y = pos.y();
            float z = pos.z();

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
