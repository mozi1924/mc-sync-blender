package com.mozi1924.yefira.client.mixin;

import com.mozi1924.yefira.client.ghost.GhostModeManager;
import net.minecraft.client.renderer.ItemInHandRenderer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ItemInHandRenderer.class)
public class ItemInHandRendererMixin {

    @Inject(method = "submitHandsWithItems", at = @At("HEAD"), cancellable = true, require = 0)
    private void onSubmitHandsWithItems(CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            ci.cancel();
        }
    }
}
