package com.mozi1924.yefira.client.compat;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.LevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.debug.DebugRenderer;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/**
 * Compatibility layer for Minecraft 1.21.x rendering pipeline.
 */
public class RenderCompat {

    /**
     * Draws a line segment using Minecraft 1.21.x VertexConsumer API.
     */
    public static void drawGizmoLine(PoseStack poseStack, VertexConsumer lines,
                                     Vec3 p1, Vec3 p2,
                                     float r, float g, float b, float a,
                                     float dx, float dy, float dz) {
        lines.addVertex(poseStack.last(), (float) p1.x, (float) p1.y, (float) p1.z)
             .setColor(r, g, b, a)
             .setNormal(poseStack.last(), dx, dy, dz);
        lines.addVertex(poseStack.last(), (float) p2.x, (float) p2.y, (float) p2.z)
             .setColor(r, g, b, a)
             .setNormal(poseStack.last(), dx, dy, dz);
    }

    /**
     * Renders a wireframe box.
     */
    public static void renderLineBox(PoseStack poseStack, VertexConsumer lineBuffer, AABB box,
                                     float r, float g, float b, float a) {
        LevelRenderer.renderLineBox(poseStack, lineBuffer, box, r, g, b, a);
    }

    /**
     * Renders a translucent filled box.
     */
    public static void renderFilledBox(PoseStack poseStack, MultiBufferSource bufferSource, AABB box,
                                       float r, float g, float b, float a) {
        DebugRenderer.renderFilledBox(poseStack, bufferSource, box, r, g, b, a);
    }
}
