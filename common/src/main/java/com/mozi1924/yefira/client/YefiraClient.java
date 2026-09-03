package com.mozi1924.yefira.client;

import com.mojang.blaze3d.platform.InputConstants;
import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.client.compat.KeyMappingCompat;
import com.mozi1924.yefira.client.ghost.GhostModeManager;
import com.mozi1924.yefira.client.gui.YefiraScreen;
import com.mozi1924.yefira.client.model.ClientBlockModelProvider;
import com.mozi1924.yefira.config.YefiraConfig;
import com.mozi1924.yefira.encoder.BlockModelExtractor;
import com.mozi1924.yefira.network.WebSocketServerManager;
import com.mozi1924.yefira.selection.SelectionManager;
import com.mozi1924.yefira.selection.SelectionStorageManager;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ServerData;
import net.minecraft.core.BlockPos;
import net.minecraft.world.item.Items;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import org.lwjgl.glfw.GLFW;

import java.nio.file.Path;

public class YefiraClient {

    public static final String YEFIRA_CATEGORY = "key.categories.yefira";

    public static KeyMapping keyPos1;
    public static KeyMapping keyPos2;
    public static KeyMapping keyGhostMode;
    public static KeyMapping keyOpenGui;
    public static KeyMapping keyFocus;
    public static KeyMapping keyClear;
    public static KeyMapping keyPresetBox;

    public static void init() {
        // Register Client Block Model Provider
        BlockModelExtractor.setProvider(new ClientBlockModelProvider());
    }

    public static void createKeyMappings() {
        keyPos1 = KeyMappingCompat.createKeyMapping(
            "key.yefira.pos1",
            InputConstants.Type.MOUSE,
            GLFW.GLFW_MOUSE_BUTTON_LEFT,
            YEFIRA_CATEGORY
        );

        keyPos2 = KeyMappingCompat.createKeyMapping(
            "key.yefira.pos2",
            InputConstants.Type.MOUSE,
            GLFW.GLFW_MOUSE_BUTTON_RIGHT,
            YEFIRA_CATEGORY
        );

        keyGhostMode = KeyMappingCompat.createKeyMapping(
            "key.yefira.ghost_mode",
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_G,
            YEFIRA_CATEGORY
        );

        keyOpenGui = KeyMappingCompat.createKeyMapping(
            "key.yefira.open_gui",
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_O,
            YEFIRA_CATEGORY
        );

        keyFocus = KeyMappingCompat.createKeyMapping(
            "key.yefira.focus",
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_F,
            YEFIRA_CATEGORY
        );

        keyClear = KeyMappingCompat.createKeyMapping(
            "key.yefira.clear",
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_X,
            YEFIRA_CATEGORY
        );

        keyPresetBox = KeyMappingCompat.createKeyMapping(
            "key.yefira.preset_box",
            InputConstants.Type.KEYSYM,
            GLFW.GLFW_KEY_C,
            YEFIRA_CATEGORY
        );
    }

    public static void onClientJoinServer(Minecraft client) {
        if (!client.hasSingleplayerServer()) {
            ServerData serverData = client.getCurrentServer();
            if (serverData != null && serverData.ip != null) {
                Path serverPath = SelectionStorageManager.getServerStoragePath(serverData.ip);
                boolean loaded = SelectionManager.getInstance().loadSavedSelection(serverPath, client.level);
                if (loaded) {
                    Yefira.LOGGER.info("Loaded server selection for IP: {}", serverData.ip);
                }
            }
            YefiraConfig cfg = YefiraConfig.getInstance();
            if (cfg.isAutoStartOnWorldLoad()) {
                WebSocketServerManager.getInstance().startServer(cfg.getHost(), cfg.getPort());
            }
        }
    }

    public static void onClientDisconnectServer(Minecraft client) {
        if (GhostModeManager.getInstance().isActive()) {
            GhostModeManager.getInstance().disable();
        }
        if (!client.hasSingleplayerServer()) {
            SelectionManager.getInstance().setActiveStoragePath(null);
            WebSocketServerManager.getInstance().stopServer();
        }
    }

    public static void onClientTick(Minecraft client) {
        if (client.player == null || client.level == null) {
            return;
        }

        if (keyGhostMode != null) {
            while (keyGhostMode.consumeClick()) {
                GhostModeManager.getInstance().toggle();
            }
        }

        if (keyOpenGui != null) {
            while (keyOpenGui.consumeClick()) {
                client.setScreen(new YefiraScreen());
            }
        }

        if (GhostModeManager.getInstance().isActive()) {
            GhostModeManager.getInstance().tickMovement();
        }

        // Check if legacy pickaxe tool is enabled in config
        boolean legacyEnabled = YefiraConfig.getInstance().isEnableLegacyPickaxeTool();
        if (legacyEnabled) {
            boolean holdingTool = client.player.getMainHandItem().is(Items.GOLDEN_PICKAXE) ||
                                  client.player.getOffhandItem().is(Items.GOLDEN_PICKAXE);

            if (keyPos1 != null) {
                while (keyPos1.consumeClick()) {
                    if (holdingTool && client.hitResult != null && client.hitResult.getType() == HitResult.Type.BLOCK) {
                        BlockHitResult blockHit = (BlockHitResult) client.hitResult;
                        BlockPos pos = blockHit.getBlockPos();
                        if (client.player.connection != null) {
                            client.player.connection.sendCommand("yefira pos1 " + pos.getX() + " " + pos.getY() + " " + pos.getZ());
                        }
                    }
                }
            }

            if (keyPos2 != null) {
                while (keyPos2.consumeClick()) {
                    if (holdingTool && client.hitResult != null && client.hitResult.getType() == HitResult.Type.BLOCK) {
                        BlockHitResult blockHit = (BlockHitResult) client.hitResult;
                        BlockPos pos = blockHit.getBlockPos();
                        if (client.player.connection != null) {
                            client.player.connection.sendCommand("yefira pos2 " + pos.getX() + " " + pos.getY() + " " + pos.getZ());
                        }
                    }
                }
            }
        }
    }
}
