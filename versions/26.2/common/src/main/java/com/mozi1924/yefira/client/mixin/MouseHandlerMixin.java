package com.mozi1924.yefira.client.mixin;

import com.mozi1924.yefira.client.ghost.GhostModeManager;
import net.minecraft.client.Minecraft;
import net.minecraft.client.MouseHandler;
import net.minecraft.client.input.MouseButtonInfo;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(MouseHandler.class)
public class MouseHandlerMixin {

    @Shadow @Final private Minecraft minecraft;
    @Shadow private double accumulatedDX;
    @Shadow private double accumulatedDY;

    @Inject(method = "onMove", at = @At("HEAD"), require = 0)
    private void onMouseMove(long window, double xpos, double ypos, CallbackInfo ci) {
        if (this.minecraft.gui != null && this.minecraft.gui.screen() != null) {
            return;
        }
        GhostModeManager ghost = GhostModeManager.getInstance();
        if (ghost.isActive()) {
            ghost.onMouseMove(xpos, ypos);
        }
    }

    @Inject(method = "turnPlayer", at = @At("HEAD"), cancellable = true, require = 0)
    private void onTurnPlayer(double delta, CallbackInfo ci) {
        GhostModeManager ghost = GhostModeManager.getInstance();
        if (ghost.isActive()) {
            this.accumulatedDX = 0.0;
            this.accumulatedDY = 0.0;
            ci.cancel();
        }
    }

    @Inject(method = "onButton", at = @At("HEAD"), cancellable = true, require = 0)
    private void onMouseButton(long window, MouseButtonInfo buttonInfo, int action, CallbackInfo ci) {
        if (this.minecraft.gui != null && this.minecraft.gui.screen() != null) {
            return;
        }
        GhostModeManager ghost = GhostModeManager.getInstance();
        if (ghost.isActive()) {
            ghost.onMouseButton(buttonInfo, action);
            ci.cancel();
        }
    }

    @Inject(method = "onScroll", at = @At("HEAD"), cancellable = true, require = 0)
    private void onMouseScroll(long window, double xoffset, double yoffset, CallbackInfo ci) {
        if (this.minecraft.gui != null && this.minecraft.gui.screen() != null) {
            return;
        }
        GhostModeManager ghost = GhostModeManager.getInstance();
        if (ghost.isActive()) {
            ghost.onMouseScroll(yoffset);
            ci.cancel();
        }
    }
}
