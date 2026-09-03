package com.mozi1924.yefira.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mozi1924.yefira.client.compat.RenderCompat;
import com.mozi1924.yefira.client.ghost.GhostModeManager;
import com.mozi1924.yefira.selection.SelectionBox;
import com.mozi1924.yefira.selection.SelectionManager;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LevelRenderer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.debug.DebugRenderer;
import net.minecraft.core.BlockPos;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

public class SelectionBoxRenderer {

    public static void render(PoseStack poseStack, MultiBufferSource bufferSource, Camera camera) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.level == null) return;

        SelectionManager mgr = SelectionManager.getInstance();
        if (!mgr.hasSelection()) return;

        // Dimension check
        if (mgr.getDimension() != null && !mc.level.dimension().equals(mgr.getDimension())) {
            return;
        }

        SelectionBox selection = mgr.getCurrentSelection();
        if (selection == null) return;

        Vec3 camPos = camera.getPosition();
        BlockPos min = selection.getMin();
        BlockPos max = selection.getMax();

        AABB box = new AABB(
            min.getX() - camPos.x, min.getY() - camPos.y, min.getZ() - camPos.z,
            max.getX() + 1.0 - camPos.x, max.getY() + 1.0 - camPos.y, max.getZ() + 1.0 - camPos.z
        );

        // Bright Cyan Stroke (0.0f, 1.0f, 1.0f, 0.9f)
        VertexConsumer lineBuffer = bufferSource.getBuffer(RenderType.lines());
        RenderCompat.renderLineBox(poseStack, lineBuffer, box, 0.0f, 1.0f, 1.0f, 0.9f);
        // Translucent Cyan Fill (0.0f, 1.0f, 1.0f, 0.2f)
        RenderCompat.renderFilledBox(poseStack, bufferSource, box, 0.0f, 1.0f, 1.0f, 0.2f);

        // Render Green Drag Preview Box if actively dragging in Ghost Mode
        GhostModeManager ghost = GhostModeManager.getInstance();
        if (ghost.isDragging()) {
            SelectionBox previewSel = ghost.getDragPreviewSelection();
            if (previewSel != null) {
                BlockPos pMin = previewSel.getMin();
                BlockPos pMax = previewSel.getMax();
                AABB previewBox = new AABB(
                    pMin.getX() - camPos.x, pMin.getY() - camPos.y, pMin.getZ() - camPos.z,
                    pMax.getX() + 1.0 - camPos.x, pMax.getY() + 1.0 - camPos.y, pMax.getZ() + 1.0 - camPos.z
                );
                // Bright Lime Green Stroke (0.0f, 1.0f, 0.0f, 0.9f)
                RenderCompat.renderLineBox(poseStack, lineBuffer, previewBox, 0.0f, 1.0f, 0.0f, 0.9f);
                // Translucent Green Fill (0.0f, 1.0f, 0.0f, 0.25f)
                RenderCompat.renderFilledBox(poseStack, bufferSource, previewBox, 0.0f, 1.0f, 0.0f, 0.25f);
            }
        }
    }
}
