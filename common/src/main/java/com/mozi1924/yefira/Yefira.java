package com.mozi1924.yefira;

import com.mozi1924.yefira.config.YefiraConfig;
import com.mozi1924.yefira.network.WebSocketServerManager;
import com.mozi1924.yefira.selection.SelectionManager;
import com.mozi1924.yefira.selection.SelectionStorageManager;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.storage.LevelResource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.file.Path;

public class Yefira {
    public static final String MOD_ID = "yefira";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    /**
     * Common mod initialization logic.
     */
    public static void init() {
        LOGGER.info("Initializing Yefira Common...");
        YefiraConfig.load();
        LOGGER.info("Yefira Common initialized successfully!");
    }

    /**
     * Common server tick hook.
     */
    public static void onServerTick(MinecraftServer server) {
        WebSocketServerManager.getInstance().flushQueuedDeltaUpdates();
        WebSocketServerManager.getInstance().tickValidationHeartbeat(server.getTickCount());
    }

    /**
     * Common server started lifecycle hook.
     */
    public static void onServerStarted(MinecraftServer server) {
        Path worldDir = server.getWorldPath(LevelResource.ROOT);
        Path storagePath = SelectionStorageManager.getWorldStoragePath(worldDir);
        ServerLevel level = server.overworld();
        boolean loaded = SelectionManager.getInstance().loadSavedSelection(storagePath, level);
        if (loaded) {
            LOGGER.info("Loaded saved selection for world: {}", worldDir.getFileName());
        }

        YefiraConfig cfg = YefiraConfig.getInstance();
        if (cfg.isAutoStartOnWorldLoad()) {
            WebSocketServerManager.getInstance().startServer(cfg.getHost(), cfg.getPort());
        } else {
            LOGGER.info("WebSocket Server auto-start is disabled (on-demand mode).");
        }
    }

    /**
     * Common server stopping lifecycle hook.
     */
    public static void onServerStopping(MinecraftServer server) {
        WebSocketServerManager.getInstance().stopServer();
        SelectionManager.getInstance().resetOnWorldUnload();
    }

    public static ResourceLocation id(String path) {
        return new ResourceLocation(MOD_ID, path);
    }
}
