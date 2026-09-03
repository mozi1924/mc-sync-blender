package com.mozi1924.yefira.fabric;

import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.command.SelectionCommand;
import com.mozi1924.yefira.event.BlockInteractionHandler;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.AttackBlockCallback;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.minecraft.world.InteractionResult;

public class YefiraFabric implements ModInitializer {

    @Override
    public void onInitialize() {
        Yefira.init();

        // Register Commands
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            SelectionCommand.register(dispatcher);
        });

        // Register Block Interaction Callbacks
        AttackBlockCallback.EVENT.register((player, level, hand, pos, direction) -> {
            if (BlockInteractionHandler.handleLeftClick(player, level, hand, pos)) {
                return InteractionResult.SUCCESS;
            }
            return InteractionResult.PASS;
        });

        UseBlockCallback.EVENT.register((player, level, hand, hitResult) -> {
            if (BlockInteractionHandler.handleRightClick(player, level, hand, hitResult.getBlockPos())) {
                return InteractionResult.SUCCESS;
            }
            return InteractionResult.PASS;
        });

        // Server lifecycle & tick events
        ServerTickEvents.END_SERVER_TICK.register(Yefira::onServerTick);
        ServerLifecycleEvents.SERVER_STARTED.register(Yefira::onServerStarted);
        ServerLifecycleEvents.SERVER_STOPPING.register(Yefira::onServerStopping);
    }
}
