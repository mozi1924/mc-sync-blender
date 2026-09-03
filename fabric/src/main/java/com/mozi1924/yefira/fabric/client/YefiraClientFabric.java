package com.mozi1924.yefira.fabric.client;

import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.client.YefiraClient;
import com.mozi1924.yefira.client.ghost.GhostGizmoRenderer;
import com.mozi1924.yefira.client.ghost.GhostHudOverlay;
import com.mozi1924.yefira.client.render.SelectionBoxRenderer;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;

public class YefiraClientFabric implements ClientModInitializer {

    @Override
    public void onInitializeClient() {
        YefiraClient.init();
        YefiraClient.createKeyMappings();

        // Register keymappings
        KeyBindingHelper.registerKeyBinding(YefiraClient.keyPos1);
        KeyBindingHelper.registerKeyBinding(YefiraClient.keyPos2);
        KeyBindingHelper.registerKeyBinding(YefiraClient.keyGhostMode);
        KeyBindingHelper.registerKeyBinding(YefiraClient.keyOpenGui);
        KeyBindingHelper.registerKeyBinding(YefiraClient.keyFocus);
        KeyBindingHelper.registerKeyBinding(YefiraClient.keyClear);
        KeyBindingHelper.registerKeyBinding(YefiraClient.keyPresetBox);

        // Register 3D Level Renderers (Selection box & Ghost gizmos)
        net.fabricmc.fabric.api.client.rendering.v1.WorldRenderEvents.AFTER_TRANSLUCENT.register(context -> {
            SelectionBoxRenderer.render(context.matrixStack(), context.consumers(), context.camera());
            GhostGizmoRenderer.render(context.matrixStack(), context.consumers(), context.camera());
        });

        // Register Ghost Mode HUD Overlay
        net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback.EVENT.register((graphics, deltaTracker) -> {
            GhostHudOverlay.renderOverlay(graphics);
        });

        // Register Connection Lifecycle
        ClientPlayConnectionEvents.JOIN.register((handler, sender, client) -> {
            client.execute(() -> YefiraClient.onClientJoinServer(client));
        });

        ClientPlayConnectionEvents.DISCONNECT.register((handler, client) -> {
            client.execute(() -> YefiraClient.onClientDisconnectServer(client));
        });

        // Register Client Tick
        ClientTickEvents.END_CLIENT_TICK.register(YefiraClient::onClientTick);
    }
}
