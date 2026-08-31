package com.mozi1924.yefira.client.ghost;

import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.network.WebSocketServerManager;
import com.mozi1924.yefira.selection.SelectionBox;
import com.mozi1924.yefira.selection.SelectionManager;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElement;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.network.chat.Component;

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
        Component titleComp = isFly
            ? Component.translatable("yefira.hud.title.fly")
            : Component.translatable("yefira.hud.title.ghost");
        int titleColor = isFly ? 0xFFFFAA33 : 0xFF00FFFF;
        graphics.text(font, titleComp, 8, 6, titleColor, true);

        // Control Hints
        Component hintsComp = isFly
            ? Component.translatable("yefira.hud.hints.fly")
            : Component.translatable("yefira.hud.hints.ghost");
        graphics.centeredText(font, hintsComp, screenWidth / 2, 6, 0xFFE0E0E0);

        // Server Status & Fly Speed (top right)
        WebSocketServerManager ws = WebSocketServerManager.getInstance();
        Component serverStatusComp = ws.isRunning()
            ? Component.translatable("yefira.hud.server.running", ws.getConnectedCount())
            : Component.translatable("yefira.hud.server.stopped");
        int statusColor = ws.isRunning() ? 0x55FF55 : 0xFF7777;
        int statusWidth = font.width(serverStatusComp);
        graphics.text(font, serverStatusComp, screenWidth - statusWidth - 8, 6, statusColor, true);

        // Selection details (bottom left)
        SelectionManager mgr = SelectionManager.getInstance();
        int bottomY = mc.getWindow().getGuiScaledHeight() - 25;
        if (mgr.hasSelection()) {
            SelectionBox sel = mgr.getCurrentSelection();
            Component selInfo = Component.translatable("yefira.hud.selection.info",
                sel.getSizeX(), sel.getSizeY(), sel.getSizeZ(), sel.getVolume());
            graphics.fill(6, bottomY - 3, 8 + font.width(selInfo) + 4, bottomY + 11, 0x88000000);
            graphics.text(font, selInfo, 8, bottomY, 0xFF55FFFF, true);
        } else if (ghost.getHoveredBlockPos() != null) {
            Component hoverInfo = Component.translatable("yefira.hud.hovered.block", ghost.getHoveredBlockPos().toShortString());
            graphics.fill(6, bottomY - 3, 8 + font.width(hoverInfo) + 4, bottomY + 11, 0x88000000);
            graphics.text(font, hoverInfo, 8, bottomY, 0xFFFFFF55, true);
        }
    }
}
