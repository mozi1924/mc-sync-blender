package com.mozi1924.yefira.client;

import com.mojang.blaze3d.platform.InputConstants;
import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.client.render.SelectionBoxRenderer;
import com.mozi1924.yefira.network.WebSocketServerManager;
import com.mozi1924.yefira.selection.SelectionManager;
import com.mozi1924.yefira.selection.SelectionStorageManager;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keymapping.v1.KeyMappingHelper;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.core.BlockPos;
import net.minecraft.world.item.Items;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import org.lwjgl.glfw.GLFW;

import java.nio.file.Path;

public class YefiraClient implements ClientModInitializer {

	public static final KeyMapping.Category YEFIRA_CATEGORY = KeyMapping.Category.register(Yefira.id("selection"));

	public static KeyMapping keyPos1;
	public static KeyMapping keyPos2;

	@Override
	public void onInitializeClient() {
		// Register key bindings
		keyPos1 = KeyMappingHelper.registerKeyMapping(new KeyMapping(
			"key.yefira.pos1",
			InputConstants.Type.MOUSE,
			GLFW.GLFW_MOUSE_BUTTON_LEFT,
			YEFIRA_CATEGORY
		));

		keyPos2 = KeyMappingHelper.registerKeyMapping(new KeyMapping(
			"key.yefira.pos2",
			InputConstants.Type.MOUSE,
			GLFW.GLFW_MOUSE_BUTTON_RIGHT,
			YEFIRA_CATEGORY
		));

		// Register 3D Bounding Box Renderer
		SelectionBoxRenderer.register();

		// Register Client play connection events for multiplayer server selections
		ClientPlayConnectionEvents.JOIN.register((handler, sender, client) -> {
			if (!client.hasSingleplayerServer()) {
				ServerData serverData = client.getCurrentServer();
				if (serverData != null && serverData.ip != null) {
					Path serverPath = SelectionStorageManager.getServerStoragePath(serverData.ip);
					boolean loaded = SelectionManager.getInstance().loadSavedSelection(serverPath, client.level);
					if (loaded) {
						Yefira.LOGGER.info("Loaded server selection for IP: {}", serverData.ip);
						WebSocketServerManager.getInstance().startServer();
					}
				}
			}
		});

		ClientPlayConnectionEvents.DISCONNECT.register((handler, client) -> {
			if (!client.hasSingleplayerServer()) {
				SelectionManager.getInstance().setActiveStoragePath(null);
			}
		});

		// Register client tick listener for key presses
		ClientTickEvents.END_CLIENT_TICK.register(client -> {
			if (client.player == null || client.level == null) {
				return;
			}

			// Check if player is holding Golden Pickaxe in main hand or off hand
			boolean holdingTool = client.player.getMainHandItem().is(Items.GOLDEN_PICKAXE) ||
								  client.player.getOffhandItem().is(Items.GOLDEN_PICKAXE);

			while (keyPos1.consumeClick()) {
				if (holdingTool && client.hitResult != null && client.hitResult.getType() == HitResult.Type.BLOCK) {
					BlockHitResult blockHit = (BlockHitResult) client.hitResult;
					BlockPos pos = blockHit.getBlockPos();
					if (client.player.connection != null) {
						client.player.connection.sendCommand("yefira pos1 " + pos.getX() + " " + pos.getY() + " " + pos.getZ());
					}
				}
			}

			while (keyPos2.consumeClick()) {
				if (holdingTool && client.hitResult != null && client.hitResult.getType() == HitResult.Type.BLOCK) {
					BlockHitResult blockHit = (BlockHitResult) client.hitResult;
					BlockPos pos = blockHit.getBlockPos();
					if (client.player.connection != null) {
						client.player.connection.sendCommand("yefira pos2 " + pos.getX() + " " + pos.getY() + " " + pos.getZ());
					}
				}
			}
		});
	}
}