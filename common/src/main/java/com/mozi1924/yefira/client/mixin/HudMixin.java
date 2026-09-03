package com.mozi1924.yefira.client.mixin;

import com.mozi1924.yefira.client.ghost.GhostModeManager;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.gui.Gui;
import net.minecraft.client.gui.GuiGraphics;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Gui.class)
public class HudMixin {

    @Inject(method = "renderCrosshair", at = @At("HEAD"), cancellable = true, require = 0)
    private void onRenderCrosshair(GuiGraphics graphics, DeltaTracker deltaTracker, CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            // Hide crosshair in Ghost Mode (free cursor mode)
            ci.cancel();
        }
    }

    @Inject(method = "renderHotbarAndDecorations", at = @At("HEAD"), cancellable = true, require = 0)
    private void onRenderHotbarAndDecorations(GuiGraphics graphics, DeltaTracker deltaTracker, CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            // Hide hotbar, health, food, armor, and experience bars in Ghost Mode
            ci.cancel();
        }
    }

    @Inject(method = "renderItemHotbar", at = @At("HEAD"), cancellable = true, require = 0)
    private void onRenderItemHotbar(GuiGraphics graphics, DeltaTracker deltaTracker, CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            // Hide item hotbar in Ghost Mode
            ci.cancel();
        }
    }

    @Inject(method = "renderPlayerHealth", at = @At("HEAD"), cancellable = true, require = 0)
    private void onRenderPlayerHealth(GuiGraphics graphics, CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            // Hide player health in Ghost Mode
            ci.cancel();
        }
    }
}

