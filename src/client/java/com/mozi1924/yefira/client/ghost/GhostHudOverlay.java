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

        boolean isFly = ghost.isFlyLooking();

        // Top Status Bar
        int barHeight = 22;
        graphics.fill(0, 0, screenWidth, barHeight, 0xB0000000); // 70% dark background
        int accentColor = isFly ? 0xFFFF9900 : 0xFF00FFCC; // Orange in Fly mode, Cyan in Free mode
        graphics.fill(0, barHeight - 1, screenWidth, barHeight, accentColor);

        // Title
        String title = isFly ? "🚀 [Fly Navigation Active]" : "👻 [Yefira Ghost Mode]";
        int titleColor = isFly ? 0xFFFFAA33 : 0xFF00FFFF;
        graphics.text(font, title, 8, 6, titleColor, true);

        // Control Hints
        String hints = isFly
            ? "WASD: Fly | Space/E: Up | Shift/Q: Down | Scroll: Speed | Shift+~ / ESC: Exit"
            : "Shift+~: Fly Nav | MMB: Orbit | Shift+MMB: Pan | Ctrl+MMB / Scroll: Zoom | LMB: Drag Axis";
        graphics.centeredText(font, hints, screenWidth / 2, 6, 0xFFE0E0E0);

        // Fly Speed / Status
        String speedStr = String.format("Speed: %.1fx", ghost.getFlySpeed());
        int speedWidth = font.width(speedStr);
        graphics.text(font, speedStr, screenWidth - speedWidth - 8, 6, 0xFFFFFF55, true);

        // Selection details (bottom left)
        SelectionManager mgr = SelectionManager.getInstance();
        if (mgr.hasSelection()) {
            SelectionBox sel = mgr.getCurrentSelection();
            String selInfo = String.format("Selection: %dx%dx%d (%d blocks)",
                sel.getSizeX(), sel.getSizeY(), sel.getSizeZ(), sel.getVolume());
            int yPos = mc.getWindow().getGuiScaledHeight() - 25;
            graphics.fill(6, yPos - 3, 8 + font.width(selInfo) + 4, yPos + 11, 0x88000000);
            graphics.text(font, selInfo, 8, yPos, 0xFF55FFFF, true);
        }
    }
}
