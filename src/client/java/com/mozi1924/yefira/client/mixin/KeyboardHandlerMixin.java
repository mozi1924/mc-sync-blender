package com.mozi1924.yefira.client.mixin;

import com.mozi1924.yefira.client.YefiraClient;
import com.mozi1924.yefira.client.ghost.GhostModeManager;
import net.minecraft.client.KeyboardHandler;
import net.minecraft.client.Minecraft;
import net.minecraft.client.input.KeyEvent;
import org.lwjgl.glfw.GLFW;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(KeyboardHandler.class)
public class KeyboardHandlerMixin {

    @Shadow @Final private Minecraft minecraft;

    @Inject(method = "keyPress", at = @At("HEAD"), cancellable = true)
    private void onKeyPress(long window, int action, KeyEvent keyEvent, CallbackInfo ci) {
        GhostModeManager ghost = GhostModeManager.getInstance();
        if (!ghost.isActive()) {
            return;
        }

        // If a GUI screen (like PauseScreen, Chat, Inventory) is open, let vanilla handle it
        if (this.minecraft.gui != null && this.minecraft.gui.screen() != null) {
            return;
        }

        int key = keyEvent.key();

        // 1. ESC key handling
        if (key == GLFW.GLFW_KEY_ESCAPE) {
            if (ghost.isFlyLooking()) {
                if (action == GLFW.GLFW_PRESS) {
                    ghost.exitFlyNavigation();
                }
                ci.cancel();
                return;
            }
            // Allow ESC to open pause screen in normal ghost mode
            return;
        }

        // 2. Ghost Mode toggle key (e.g. G)
        if (YefiraClient.keyGhostMode != null && YefiraClient.keyGhostMode.matches(keyEvent)) {
            if (action == GLFW.GLFW_PRESS) {
                ghost.toggle();
            }
            ci.cancel();
            return;
        }

        // 3. Blender Fly Navigation toggle: Shift + ~ (GLFW_KEY_GRAVE_ACCENT)
        if (key == GLFW.GLFW_KEY_GRAVE_ACCENT || key == GLFW.GLFW_KEY_WORLD_1) {
            if (action == GLFW.GLFW_PRESS) {
                ghost.toggleFlyNavigation();
            }
            ci.cancel();
            return;
        }

        // In Ghost Mode, block all vanilla gameplay key events (hotbar, drop item, chat, attack, use item)
        // Movement keys (WASD, Space, Shift, Ctrl, Q, E) are polled directly by GhostModeManager in tickMovement()
        ci.cancel();
    }
}
