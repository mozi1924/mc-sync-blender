package com.mozi1924.yefira.fabric.client;

import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.client.YefiraClient;
import com.mozi1924.yefira.client.ghost.GhostGizmoRenderer;
import com.mozi1924.yefira.client.ghost.GhostHudOverlay;
import com.mozi1924.yefira.client.render.SelectionBoxRenderer;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keymapping.v1.KeyMappingHelper;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;
import net.fabricmc.fabric.api.client.rendering.v1.level.LevelRenderEvents;

public class YefiraClientFabric implements ClientModInitializer {

    @Override
    public void onInitializeClient() {
        YefiraClient.init();
        YefiraClient.createKeyMappings();

        // Register keymappings
        KeyMappingHelper.registerKeyMapping(YefiraClient.keyPos1);
        KeyMappingHelper.registerKeyMapping(YefiraClient.keyPos2);
        KeyMappingHelper.registerKeyMapping(YefiraClient.keyGhostMode);
        KeyMappingHelper.registerKeyMapping(YefiraClient.keyOpenGui);
        KeyMappingHelper.registerKeyMapping(YefiraClient.keyFocus);
        KeyMappingHelper.registerKeyMapping(YefiraClient.keyClear);
        KeyMappingHelper.registerKeyMapping(YefiraClient.keyPresetBox);

        // Register 3D Level Renderers (Selection box & Ghost gizmos)
        LevelRenderEvents.BEFORE_GIZMOS.register(context -> {
            SelectionBoxRenderer.render();
            GhostGizmoRenderer.render();
        });

        // Register Ghost Mode HUD Overlay
        HudElementRegistry.addLast(Yefira.id("ghost_hud"), (graphics, deltaTracker) -> {
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
