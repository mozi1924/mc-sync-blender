package com.mozi1924.yefira.client.ghost;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
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

public class GhostGizmoRenderer {

    public static final int COLOR_X = 0xFFFF3333; // Red
    public static final int COLOR_Y = 0xFF33FF33; // Green
    public static final int COLOR_Z = 0xFF3388FF; // Blue
    public static final int COLOR_CENTER = 0xFFFFCC00; // Gold
    public static final int COLOR_HIGHLIGHT = 0xFFFFFF55; // Bright Yellow

    public static void render(PoseStack poseStack, MultiBufferSource bufferSource, Camera camera) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.level == null) return;

        GhostModeManager ghost = GhostModeManager.getInstance();
        if (!ghost.isActive()) return;

        SelectionManager mgr = SelectionManager.getInstance();
        Vec3 camPos = camera.getPosition();
        VertexConsumer lineBuffer = bufferSource.getBuffer(RenderType.lines());

        // 1. Render Hovered Block Outline in Free Cursor Mode
        if (!ghost.isDragging() && !ghost.isBoxCreating() && !mgr.hasSelection() && ghost.getHoveredBlockPos() != null) {
            BlockPos hPos = ghost.getHoveredBlockPos();
            AABB blockBox = new AABB(
                hPos.getX() - camPos.x, hPos.getY() - camPos.y, hPos.getZ() - camPos.z,
                hPos.getX() + 1.0 - camPos.x, hPos.getY() + 1.0 - camPos.y, hPos.getZ() + 1.0 - camPos.z
            );
            LevelRenderer.renderLineBox(poseStack, lineBuffer, blockBox, 0.0f, 1.0f, 0.93f, 1.0f);
            DebugRenderer.renderFilledBox(poseStack, bufferSource, blockBox, 0.0f, 1.0f, 0.93f, 0.2f);
        }

        // 2. Render Box Creation Preview when dragging to create
        if (ghost.isBoxCreating()) {
            SelectionBox boxCreate = ghost.getBoxCreateSelection();
            if (boxCreate != null) {
                BlockPos bMin = boxCreate.getMin();
                BlockPos bMax = boxCreate.getMax();
                AABB createBox = new AABB(
                    bMin.getX() - camPos.x, bMin.getY() - camPos.y, bMin.getZ() - camPos.z,
                    bMax.getX() + 1.0 - camPos.x, bMax.getY() + 1.0 - camPos.y, bMax.getZ() + 1.0 - camPos.z
                );
                LevelRenderer.renderLineBox(poseStack, lineBuffer, createBox, 0.0f, 1.0f, 0.33f, 1.0f);
                DebugRenderer.renderFilledBox(poseStack, bufferSource, createBox, 0.0f, 1.0f, 0.33f, 0.25f);
            }
            return;
        }

        // Dimension check for committed selection gizmos
        if (mgr.hasSelection() && mgr.getDimension() != null && !mc.level.dimension().equals(mgr.getDimension())) {
            return;
        }

        BlockPos pos1 = ghost.getEffectivePos1();
        BlockPos pos2 = ghost.getEffectivePos2();

        // Render Pos1 Gizmo
        if (pos1 != null) {
            Vec3 origin1 = new Vec3(pos1.getX() + 0.5, pos1.getY() + 0.5, pos1.getZ() + 0.5);
            renderCornerGizmo(poseStack, bufferSource, lineBuffer, camPos, origin1, GhostModeManager.CORNER_POS1, "Pos 1", 0xFF00FFCC);
        }

        // Render Pos2 Gizmo
        if (pos2 != null) {
            Vec3 origin2 = new Vec3(pos2.getX() + 0.5, pos2.getY() + 0.5, pos2.getZ() + 0.5);
            renderCornerGizmo(poseStack, bufferSource, lineBuffer, camPos, origin2, GhostModeManager.CORNER_POS2, "Pos 2", 0xFFFF00CC);
        }

        // Render Center Move Gizmo if both pos1 and pos2 are set
        if (pos1 != null && pos2 != null) {
            BlockPos min = new BlockPos(
                Math.min(pos1.getX(), pos2.getX()),
                Math.min(pos1.getY(), pos2.getY()),
                Math.min(pos1.getZ(), pos2.getZ())
            );
            BlockPos max = new BlockPos(
                Math.max(pos1.getX(), pos2.getX()),
                Math.max(pos1.getY(), pos2.getY()),
                Math.max(pos1.getZ(), pos2.getZ())
            );
            Vec3 center = new Vec3(
                (min.getX() + max.getX() + 1) / 2.0,
                (min.getY() + max.getY() + 1) / 2.0,
                (min.getZ() + max.getZ() + 1) / 2.0
            );
            renderCenterGizmo(poseStack, bufferSource, lineBuffer, camPos, center);
        }
    }

    private static void renderCornerGizmo(PoseStack poseStack, MultiBufferSource bufferSource, VertexConsumer lineBuffer, Vec3 camPos, Vec3 origin, int cornerId, String label, int labelColor) {
        GhostModeManager ghost = GhostModeManager.getInstance();
        Vec3 cameraPos = ghost.getCameraPos();
        double dist = Math.max(0.5, origin.distanceTo(cameraPos));
        float axisLength = (float) (dist * 0.15);
        float centerHalf = (float) (dist * 0.018);

        int hoveredCorner = ghost.getHoveredCorner();
        int hoveredAxis = ghost.getHoveredAxis();
        int draggingCorner = ghost.getDraggingCorner();
        int draggingAxis = ghost.getDraggingAxis();

        boolean isCurrentCorner = (draggingCorner == cornerId) || (draggingCorner == GhostModeManager.CORNER_NONE && hoveredCorner == cornerId);

        Vec3 relOrigin = origin.subtract(camPos);

        // Center handle cube
        boolean centerHighlighted = isCurrentCorner && ((draggingCorner != GhostModeManager.CORNER_NONE ? draggingAxis : hoveredAxis) == GhostModeManager.AXIS_CENTER);
        int centerColor = centerHighlighted ? COLOR_HIGHLIGHT : COLOR_CENTER;
        AABB centerBox = new AABB(
            relOrigin.x - centerHalf, relOrigin.y - centerHalf, relOrigin.z - centerHalf,
            relOrigin.x + centerHalf, relOrigin.y + centerHalf, relOrigin.z + centerHalf
        );
        float cr = ((centerColor >> 16) & 0xFF) / 255.0f;
        float cg = ((centerColor >> 8) & 0xFF) / 255.0f;
        float cb = (centerColor & 0xFF) / 255.0f;
        LevelRenderer.renderLineBox(poseStack, lineBuffer, centerBox, cr, cg, cb, 1.0f);
        DebugRenderer.renderFilledBox(poseStack, bufferSource, centerBox, cr, cg, cb, 0.5f);

        // X Axis (Red)
        boolean xHighlighted = isCurrentCorner && ((draggingCorner != GhostModeManager.CORNER_NONE ? draggingAxis : hoveredAxis) == GhostModeManager.AXIS_X);
        int colorX = xHighlighted ? COLOR_HIGHLIGHT : COLOR_X;
        drawLine(poseStack, lineBuffer, relOrigin, relOrigin.add(axisLength, 0, 0), colorX);

        // Y Axis (Green)
        boolean yHighlighted = isCurrentCorner && ((draggingCorner != GhostModeManager.CORNER_NONE ? draggingAxis : hoveredAxis) == GhostModeManager.AXIS_Y);
        int colorY = yHighlighted ? COLOR_HIGHLIGHT : COLOR_Y;
        drawLine(poseStack, lineBuffer, relOrigin, relOrigin.add(0, axisLength, 0), colorY);

        // Z Axis (Blue)
        boolean zHighlighted = isCurrentCorner && ((draggingCorner != GhostModeManager.CORNER_NONE ? draggingAxis : hoveredAxis) == GhostModeManager.AXIS_Z);
        int colorZ = zHighlighted ? COLOR_HIGHLIGHT : COLOR_Z;
        drawLine(poseStack, lineBuffer, relOrigin, relOrigin.add(0, 0, axisLength), colorZ);
    }

    private static void renderCenterGizmo(PoseStack poseStack, MultiBufferSource bufferSource, VertexConsumer lineBuffer, Vec3 camPos, Vec3 center) {
        GhostModeManager ghost = GhostModeManager.getInstance();
        Vec3 cameraPos = ghost.getCameraPos();
        double dist = Math.max(0.5, center.distanceTo(cameraPos));
        float axisLength = (float) (dist * 0.15);
        float centerHalf = (float) (dist * 0.015);

        int hoveredCorner = ghost.getHoveredCorner();
        int hoveredAxis = ghost.getHoveredAxis();
        int draggingCorner = ghost.getDraggingCorner();
        int draggingAxis = ghost.getDraggingAxis();

        boolean isCenterGizmo = (draggingCorner == GhostModeManager.CORNER_CENTER) ||
                                (draggingCorner == GhostModeManager.CORNER_NONE && hoveredCorner == GhostModeManager.CORNER_CENTER);

        Vec3 relCenter = center.subtract(camPos);

        // Center cube
        AABB centerBox = new AABB(
            relCenter.x - centerHalf, relCenter.y - centerHalf, relCenter.z - centerHalf,
            relCenter.x + centerHalf, relCenter.y + centerHalf, relCenter.z + centerHalf
        );
        float cr = ((COLOR_CENTER >> 16) & 0xFF) / 255.0f;
        float cg = ((COLOR_CENTER >> 8) & 0xFF) / 255.0f;
        float cb = (COLOR_CENTER & 0xFF) / 255.0f;
        LevelRenderer.renderLineBox(poseStack, lineBuffer, centerBox, cr, cg, cb, 1.0f);
        DebugRenderer.renderFilledBox(poseStack, bufferSource, centerBox, cr, cg, cb, 0.6f);

        // X Axis
        boolean xHighlighted = isCenterGizmo && ((draggingCorner != GhostModeManager.CORNER_NONE ? draggingAxis : hoveredAxis) == GhostModeManager.AXIS_X);
        int colorX = xHighlighted ? COLOR_HIGHLIGHT : COLOR_X;
        drawLine(poseStack, lineBuffer, relCenter, relCenter.add(axisLength, 0, 0), colorX);

        // Y Axis
        boolean yHighlighted = isCenterGizmo && ((draggingCorner != GhostModeManager.CORNER_NONE ? draggingAxis : hoveredAxis) == GhostModeManager.AXIS_Y);
        int colorY = yHighlighted ? COLOR_HIGHLIGHT : COLOR_Y;
        drawLine(poseStack, lineBuffer, relCenter, relCenter.add(0, axisLength, 0), colorY);

        // Z Axis
        boolean zHighlighted = isCenterGizmo && ((draggingCorner != GhostModeManager.CORNER_NONE ? draggingAxis : hoveredAxis) == GhostModeManager.AXIS_Z);
        int colorZ = zHighlighted ? COLOR_HIGHLIGHT : COLOR_Z;
        drawLine(poseStack, lineBuffer, relCenter, relCenter.add(0, 0, axisLength), colorZ);
    }

    private static void drawLine(PoseStack poseStack, VertexConsumer lines, Vec3 p1, Vec3 p2, int argb) {
        float a = ((argb >> 24) & 0xFF) / 255.0f;
        float r = ((argb >> 16) & 0xFF) / 255.0f;
        float g = ((argb >> 8) & 0xFF) / 255.0f;
        float b = (argb & 0xFF) / 255.0f;

        float dx = (float) (p2.x - p1.x);
        float dy = (float) (p2.y - p1.y);
        float dz = (float) (p2.z - p1.z);
        float len = (float) Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (len > 1e-5f) {
            dx /= len;
            dy /= len;
            dz /= len;
        } else {
            dy = 1.0f;
        }

        lines.vertex(poseStack.last().pose(), (float) p1.x, (float) p1.y, (float) p1.z).color(r, g, b, a).normal(poseStack.last().normal(), dx, dy, dz).endVertex();
        lines.vertex(poseStack.last().pose(), (float) p2.x, (float) p2.y, (float) p2.z).color(r, g, b, a).normal(poseStack.last().normal(), dx, dy, dz).endVertex();
    }
}
