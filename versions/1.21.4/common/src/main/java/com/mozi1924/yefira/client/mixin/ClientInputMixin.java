package com.mozi1924.yefira.client.mixin;

import com.mozi1924.yefira.client.ghost.GhostModeManager;
import net.minecraft.client.player.ClientInput;
import net.minecraft.world.entity.player.Input;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ClientInput.class)
public class ClientInputMixin {

    @Shadow public Input keyPresses;
    @Shadow public float leftImpulse;
    @Shadow public float forwardImpulse;

    @Inject(method = "tick", at = @At("TAIL"))
    private void onTick(CallbackInfo ci) {
        if (GhostModeManager.getInstance().isActive()) {
            this.keyPresses = Input.EMPTY;
            this.leftImpulse = 0.0f;
            this.forwardImpulse = 0.0f;
        }
    }
}
