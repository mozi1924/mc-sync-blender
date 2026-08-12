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

		// 注册游戏内选区指令 /mcsync
		com.mozi1924.yefira.command.SelectionCommand.register();

		// 注册快捷选区交互工具 (手持木斧)
		com.mozi1924.yefira.event.BlockInteractionHandler.register();

		// 监听服务器生命周期
		net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents.SERVER_STARTED.register(server -> {
			com.mozi1924.yefira.network.WebSocketServerManager.getInstance().startServer();
		});

		net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
			com.mozi1924.yefira.network.WebSocketServerManager.getInstance().stopServer();
		});

		LOGGER.info("Yefira initialized successfully!");
	}

	public static Identifier id(String path) {
		return Identifier.fromNamespaceAndPath(MOD_ID, path);
	}
}
