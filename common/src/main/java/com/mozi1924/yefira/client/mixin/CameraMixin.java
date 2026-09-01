package com.mozi1924.yefira.client.mixin;

import com.mozi1924.yefira.client.ghost.GhostModeManager;
import net.minecraft.client.Camera;
import net.minecraft.client.DeltaTracker;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix4f;
import org.joml.Matrix4fc;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Camera.class)
public abstract class CameraMixin {

    @Shadow @Final private Minecraft minecraft;
    @Shadow private boolean initialized;
    @Shadow private Level level;
    @Shadow private Entity entity;
    @Shadow private Vec3 position;
    @Shadow private boolean detached;
    @Shadow private float depthFar;
    @Shadow private float fov;
    @Shadow private float hudFov;
    @Shadow @Final private Matrix4f cachedViewRotMatrix;

    @Shadow protected abstract void setRotation(float yRot, float xRot);
    @Shadow protected abstract void setPosition(Vec3 pos);
    @Shadow protected abstract float calculateFov(float partialTicks);
    @Shadow protected abstract float calculateHudFov(float partialTicks);
    @Shadow public abstract float getCameraEntityPartialTicks(DeltaTracker deltaTracker);
    @Shadow public abstract Matrix4f getViewRotationMatrix(Matrix4f dest);
    @Shadow protected abstract Matrix4f createProjectionMatrixForCulling();
    @Shadow protected abstract void prepareCullFrustum(Matrix4fc viewRot, Matrix4f proj, Vec3 pos);
    @Shadow protected abstract void setupPerspective(float near, float far, float fov, float width, float height);

    @Inject(method = "update", at = @At("HEAD"), cancellable = true)
    private void onUpdate(DeltaTracker deltaTracker, CallbackInfo ci) {
        GhostModeManager ghost = GhostModeManager.getInstance();
        if (ghost.isActive()) {
            float maxCloudDist = (Integer) this.minecraft.options.cloudRange().get() * 16.0f;
            float renderDist = this.minecraft.options.getEffectiveRenderDistance() * 16.0f;
            this.depthFar = Math.max(renderDist * 4.0f, maxCloudDist);

            if (this.minecraft.player == null || this.level == null) {
                return;
            }
            if (this.entity == null) {
                this.entity = this.minecraft.player;
            }

            float partialTicks = this.getCameraEntityPartialTicks(deltaTracker);
            this.fov = this.calculateFov(partialTicks);
            this.hudFov = this.calculateHudFov(partialTicks);

            Vec3 ghostPos = ghost.getCameraPos();
            this.setPosition(ghostPos);
            this.setRotation(ghost.getYaw(), ghost.getPitch());
            this.detached = true;

            this.prepareCullFrustum(this.getViewRotationMatrix(this.cachedViewRotMatrix), this.createProjectionMatrixForCulling(), this.position);

            float width = (float) this.minecraft.getWindow().getWidth();
            float height = (float) this.minecraft.getWindow().getHeight();
            this.setupPerspective(0.05f, this.depthFar, this.fov, width, height);

            this.initialized = true;
            ci.cancel();
        }
    }
}
