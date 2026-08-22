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

    @Inject(method = "extractCrosshair", at = @At("HEAD"), cancellable = true)
    private void onExtractCrosshair(GuiGraphicsExtractor graphics, DeltaTracker deltaTracker, CallbackInfo ci) {
        GhostModeManager ghost = GhostModeManager.getInstance();
        if (ghost.isActive() && !ghost.isFlyLooking()) {
            // Only show crosshair in Fly Navigation mode, hide in normal Ghost Mode
            ci.cancel();
        }
    }

    @Inject(method = "extractHotbarAndDecorations", at = @At("HEAD"), cancellable = true)
    private void onExtractHotbarAndDecorations(GuiGraphicsExtractor graphics, DeltaTracker deltaTracker, CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            // Hide hotbar, health, food, armor, and experience bars in Ghost Mode
            ci.cancel();
        }
    }
}
