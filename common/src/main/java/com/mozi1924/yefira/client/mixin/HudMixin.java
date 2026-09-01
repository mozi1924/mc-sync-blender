package com.mozi1924.yefira.client.mixin;

import com.mozi1924.yefira.client.ghost.GhostModeManager;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.Hud;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Hud.class)
public class HudMixin {

    @Inject(method = "extractCrosshair", at = @At("HEAD"), cancellable = true, require = 0)
    private void onExtractCrosshair(GuiGraphicsExtractor graphics, DeltaTracker deltaTracker, CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            // Hide crosshair in Ghost Mode (free cursor mode)
            ci.cancel();
        }
    }

    @Inject(method = "extractHotbarAndDecorations", at = @At("HEAD"), cancellable = true, require = 0)
    private void onExtractHotbarAndDecorations(GuiGraphicsExtractor graphics, DeltaTracker deltaTracker, CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            // Hide hotbar, health, food, armor, and experience bars in Ghost Mode (Fabric)
            ci.cancel();
        }
    }

    @Inject(method = "extractHotbar", at = @At("HEAD"), cancellable = true, require = 0)
    private void onExtractHotbar(GuiGraphicsExtractor graphics, DeltaTracker deltaTracker, CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            // Hide hotbar in Ghost Mode (NeoForge)
            ci.cancel();
        }
    }

    @Inject(method = "extractItemHotbar", at = @At("HEAD"), cancellable = true, require = 0)
    private void onExtractItemHotbar(GuiGraphicsExtractor graphics, DeltaTracker deltaTracker, CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            // Hide item hotbar in Ghost Mode
            ci.cancel();
        }
    }

    @Inject(method = "extractPlayerHealth", at = @At("HEAD"), cancellable = true, require = 0)
    private void onExtractPlayerHealth(GuiGraphicsExtractor graphics, CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            // Hide player health in Ghost Mode
            ci.cancel();
        }
    }
}

