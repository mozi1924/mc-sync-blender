package com.mozi1924.yefira;

import net.fabricmc.api.ModInitializer;

import net.minecraft.resources.Identifier;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Yefira implements ModInitializer {
	public static final String MOD_ID = "yefira";

	// This logger is used to write text to the console and the log file.
	// It is considered best practice to use your mod id as the logger's name.
	// That way, it's clear which mod wrote info, warnings, and errors.
	public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	@Override
	public void onInitialize() {
		LOGGER.info("Initializing Yefira Mod...");

		// 加载配置文件
		com.mozi1924.yefira.config.YefiraConfig.load();

		// 注册游戏内选区指令 /yefira
		com.mozi1924.yefira.command.SelectionCommand.register();

		// 注册快捷选区交互工具 (手持金镐)
		com.mozi1924.yefira.event.BlockInteractionHandler.register();

		// Bound delta traffic to one packet per server tick.  Blender performs a
		// second, short coalescing pass before evaluating its point cloud.
		net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents.END_SERVER_TICK.register(server -> {
			com.mozi1924.yefira.network.WebSocketServerManager.getInstance().flushQueuedDeltaUpdates();
			com.mozi1924.yefira.network.WebSocketServerManager.getInstance().tickValidationHeartbeat(server.getTickCount());
		});

		// 监听服务器生命周期
		net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents.SERVER_STARTED.register(server -> {
			java.nio.file.Path worldDir = server.getWorldPath(net.minecraft.world.level.storage.LevelResource.ROOT);
			java.nio.file.Path storagePath = com.mozi1924.yefira.selection.SelectionStorageManager.getWorldStoragePath(worldDir);
			net.minecraft.server.level.ServerLevel level = server.overworld();
			boolean loaded = com.mozi1924.yefira.selection.SelectionManager.getInstance().loadSavedSelection(storagePath, level);
			if (loaded) {
				LOGGER.info("Loaded saved selection for world: {}", worldDir.getFileName());
			}
			com.mozi1924.yefira.config.YefiraConfig cfg = com.mozi1924.yefira.config.YefiraConfig.getInstance();
			if (cfg.isAutoStartOnWorldLoad()) {
				com.mozi1924.yefira.network.WebSocketServerManager.getInstance().startServer(cfg.getHost(), cfg.getPort());
			} else {
				LOGGER.info("WebSocket Server auto-start is disabled (on-demand mode).");
			}
		});

		net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
			com.mozi1924.yefira.network.WebSocketServerManager.getInstance().stopServer();
			com.mozi1924.yefira.selection.SelectionManager.getInstance().resetOnWorldUnload();
		});

		LOGGER.info("Yefira initialized successfully!");
	}

	public static Identifier id(String path) {
		return Identifier.fromNamespaceAndPath(MOD_ID, path);
	}
}
