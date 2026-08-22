package com.mozi1924.yefira.client.ghost;

import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.selection.SelectionBox;
import com.mozi1924.yefira.selection.SelectionManager;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElement;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphicsExtractor;

public class GhostHudOverlay implements HudElement {

    public static void register() {
        HudElementRegistry.addLast(Yefira.id("ghost_hud"), new GhostHudOverlay());
    }

    @Override
    public void extractRenderState(GuiGraphicsExtractor graphics, DeltaTracker deltaTracker) {
        GhostModeManager ghost = GhostModeManager.getInstance();
        if (!ghost.isActive()) return;

        Minecraft mc = Minecraft.getInstance();
        Font font = mc.font;
        int screenWidth = mc.getWindow().getGuiScaledWidth();

        // Top Status Bar
        int barHeight = 22;
        graphics.fill(0, 0, screenWidth, barHeight, 0xB0000000); // 70% dark background
        graphics.fill(0, barHeight - 1, screenWidth, barHeight, 0xFF00FFCC); // Accent bottom line

        // Title & Info
        String title = "👻 [Yefira Ghost Mode]";
        graphics.text(font, title, 8, 6, 0xFF00FFFF, true);

        // Control Hints
        String hints = "Hold RMB: Fly (WASD/QE) | LMB: Drag Axis | MMB: Orbit | Shift+MMB: Pan | Scroll: Speed";
        graphics.centeredText(font, hints, screenWidth / 2, 6, 0xFFE0E0E0);

        // Fly Speed
        String speedStr = String.format("Speed: %.1fx", ghost.getFlySpeed());
        int speedWidth = font.width(speedStr);
        graphics.text(font, speedStr, screenWidth - speedWidth - 8, 6, 0xFFFFFF55, true);

        // Selection details in Ghost Mode (bottom left above chat)
        SelectionManager mgr = SelectionManager.getInstance();
        if (mgr.hasSelection()) {
            SelectionBox sel = mgr.getCurrentSelection();
            String selInfo = String.format("Selection: %dx%dx%d (%d blocks)",
                sel.getSizeX(), sel.getSizeY(), sel.getSizeZ(), sel.getVolume());
            int yPos = mc.getWindow().getGuiScaledHeight() - 35;
            graphics.fill(6, yPos - 3, 8 + font.width(selInfo) + 4, yPos + 11, 0x88000000);
            graphics.text(font, selInfo, 8, yPos, 0xFF55FFFF, true);
        }
    }
}
