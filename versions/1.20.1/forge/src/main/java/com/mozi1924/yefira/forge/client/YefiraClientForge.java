package com.mozi1924.yefira.forge.client;

import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.client.YefiraClient;
import com.mozi1924.yefira.client.ghost.GhostGizmoRenderer;
import com.mozi1924.yefira.client.ghost.GhostHudOverlay;
import com.mozi1924.yefira.client.render.SelectionBoxRenderer;
import net.minecraft.client.Minecraft;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.client.event.RegisterKeyMappingsEvent;
import net.minecraftforge.client.event.RenderGuiOverlayEvent;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.client.gui.overlay.VanillaGuiOverlay;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;

@Mod.EventBusSubscriber(modid = Yefira.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.MOD)
public class YefiraClientForge {

    @SubscribeEvent
    public static void onClientSetup(FMLClientSetupEvent event) {
        YefiraClient.init();
        YefiraClient.createKeyMappings();
    }

    @SubscribeEvent
    public static void onRegisterKeyMappings(RegisterKeyMappingsEvent event) {
        if (YefiraClient.keyGhostMode == null) {
            YefiraClient.createKeyMappings();
        }
        if (YefiraClient.keyGhostMode != null) event.register(YefiraClient.keyGhostMode);
        if (YefiraClient.keyOpenGui != null) event.register(YefiraClient.keyOpenGui);
        if (YefiraClient.keyFocus != null) event.register(YefiraClient.keyFocus);
        if (YefiraClient.keyClear != null) event.register(YefiraClient.keyClear);
        if (YefiraClient.keyPresetBox != null) event.register(YefiraClient.keyPresetBox);
    }

    @Mod.EventBusSubscriber(modid = Yefira.MOD_ID, value = Dist.CLIENT, bus = Mod.EventBusSubscriber.Bus.FORGE)
    public static class ForgeClientEvents {

        @SubscribeEvent
        public static void onClientTick(TickEvent.ClientTickEvent event) {
            if (event.phase == TickEvent.Phase.END) {
                YefiraClient.onClientTick(Minecraft.getInstance());
            }
        }

        @SubscribeEvent
        public static void onRenderLevelStage(RenderLevelStageEvent event) {
            if (event.getStage() == RenderLevelStageEvent.Stage.AFTER_TRANSLUCENT_BLOCKS) {
                SelectionBoxRenderer.render(event.getPoseStack(), Minecraft.getInstance().renderBuffers().bufferSource(), event.getCamera());
                GhostGizmoRenderer.render(event.getPoseStack(), Minecraft.getInstance().renderBuffers().bufferSource(), event.getCamera());
            }
        }

        @SubscribeEvent
        public static void onRenderGuiOverlay(RenderGuiOverlayEvent.Post event) {
            if (VanillaGuiOverlay.HOTBAR.id().equals(event.getOverlay().id())) {
                GhostHudOverlay.renderOverlay(event.getGuiGraphics());
            }
        }

        @SubscribeEvent
        public static void onPlayerLoggedIn(ClientPlayerNetworkEvent.LoggingIn event) {
            Minecraft client = Minecraft.getInstance();
            client.execute(() -> YefiraClient.onClientJoinServer(client));
        }

        @SubscribeEvent
        public static void onPlayerLoggedOut(ClientPlayerNetworkEvent.LoggingOut event) {
            Minecraft client = Minecraft.getInstance();
            client.execute(() -> YefiraClient.onClientDisconnectServer(client));
        }
    }
}
