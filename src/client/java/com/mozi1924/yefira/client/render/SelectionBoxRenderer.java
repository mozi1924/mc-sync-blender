package com.mozi1924.yefira.client.render;

import com.mozi1924.yefira.selection.SelectionBox;
import com.mozi1924.yefira.selection.SelectionManager;
import net.fabricmc.fabric.api.client.rendering.v1.level.LevelRenderEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.gizmos.GizmoStyle;
import net.minecraft.gizmos.Gizmos;
import net.minecraft.world.phys.AABB;

public class SelectionBoxRenderer {

    public static void register() {
        LevelRenderEvents.BEFORE_GIZMOS.register(context -> {
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

            BlockPos min = selection.getMin();
            BlockPos max = selection.getMax();

            AABB box = new AABB(
                min.getX(), min.getY(), min.getZ(),
                max.getX() + 1.0, max.getY() + 1.0, max.getZ() + 1.0
            );

            // Bright Cyan Stroke (90% opacity), Translucent Cyan Fill (20% opacity)
            GizmoStyle style = GizmoStyle.strokeAndFill(0xE600FFFF, 2.0f, 0x3300FFFF);
            Gizmos.cuboid(box, style);
        });
    }
}
