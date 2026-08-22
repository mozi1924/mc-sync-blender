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

    @Inject(method = "onMove", at = @At("HEAD"))
    private void onMouseMove(long window, double xpos, double ypos, CallbackInfo ci) {
        GhostModeManager ghost = GhostModeManager.getInstance();
        if (ghost.isActive() && !ghost.isFlyLooking()) {
            ghost.onMouseMove(xpos, ypos);
        }
    }

    @Inject(method = "turnPlayer", at = @At("HEAD"), cancellable = true)
    private void onTurnPlayer(double delta, CallbackInfo ci) {
        GhostModeManager ghost = GhostModeManager.getInstance();
        if (ghost.isActive()) {
            if (ghost.isFlyLooking()) {
                double sens = this.minecraft.options.sensitivity().get() * 0.6 + 0.2;
                double mult = sens * sens * sens * 8.0;
                double dx = this.accumulatedDX * mult;
                double dy = this.accumulatedDY * mult;
                ghost.onMouseTurn(dx, dy);
            }
            this.accumulatedDX = 0.0;
            this.accumulatedDY = 0.0;
            ci.cancel();
        }
    }

    @Inject(method = "onButton", at = @At("HEAD"), cancellable = true)
    private void onMouseButton(long window, MouseButtonInfo buttonInfo, int action, CallbackInfo ci) {
        GhostModeManager ghost = GhostModeManager.getInstance();
        if (ghost.isActive()) {
            ghost.onMouseButton(buttonInfo, action);
            ci.cancel();
        }
    }

    @Inject(method = "onScroll", at = @At("HEAD"), cancellable = true)
    private void onMouseScroll(long window, double xoffset, double yoffset, CallbackInfo ci) {
        GhostModeManager ghost = GhostModeManager.getInstance();
        if (ghost.isActive()) {
            ghost.onMouseScroll(yoffset);
            ci.cancel();
        }
    }
}
