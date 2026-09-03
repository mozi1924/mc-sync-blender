package com.mozi1924.yefira.client.mixin;

import com.mozi1924.yefira.client.ghost.GhostModeManager;
import net.minecraft.client.gui.Gui;
import net.minecraft.client.gui.GuiGraphics;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Gui.class)
public class HudMixin {

    @Inject(method = "renderCrosshair", at = @At("HEAD"), cancellable = true, require = 0)
    private void onRenderCrosshair(GuiGraphics graphics, CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            ci.cancel();
        }
    }

    @Inject(method = "renderHotbar", at = @At("HEAD"), cancellable = true, require = 0)
    private void onRenderHotbar(float partialTick, GuiGraphics graphics, CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            ci.cancel();
        }
    }

    @Inject(method = "renderPlayerHealth", at = @At("HEAD"), cancellable = true, require = 0)
    private void onRenderPlayerHealth(GuiGraphics graphics, CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            ci.cancel();
        }
    }
}

