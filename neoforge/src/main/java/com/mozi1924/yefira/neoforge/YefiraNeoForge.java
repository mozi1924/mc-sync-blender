package com.mozi1924.yefira.neoforge;

import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.command.SelectionCommand;
import com.mozi1924.yefira.event.BlockInteractionHandler;
import net.minecraft.core.BlockPos;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import net.neoforged.neoforge.event.server.ServerStoppingEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;

@Mod(Yefira.MOD_ID)
public class YefiraNeoForge {

    public YefiraNeoForge(IEventBus modEventBus) {
        Yefira.init();

        // Register gameplay event listeners on NeoForge EventBus
        NeoForge.EVENT_BUS.addListener(this::onRegisterCommands);
        NeoForge.EVENT_BUS.addListener(this::onServerStarted);
        NeoForge.EVENT_BUS.addListener(this::onServerStopping);
        NeoForge.EVENT_BUS.addListener(this::onServerTick);
        NeoForge.EVENT_BUS.addListener(this::onLeftClickBlock);
        NeoForge.EVENT_BUS.addListener(this::onRightClickBlock);

    }

    private void onRegisterCommands(RegisterCommandsEvent event) {
        SelectionCommand.register(event.getDispatcher());
    }

    private void onServerStarted(ServerStartedEvent event) {
        Yefira.onServerStarted(event.getServer());
    }

    private void onServerStopping(ServerStoppingEvent event) {
        Yefira.onServerStopping(event.getServer());
    }

    private void onServerTick(ServerTickEvent.Post event) {
        if (event.getServer() != null) {
            Yefira.onServerTick(event.getServer());
        }
    }

    private void onLeftClickBlock(PlayerInteractEvent.LeftClickBlock event) {
        Player player = event.getEntity();
        Level level = event.getLevel();
        InteractionHand hand = event.getHand();
        BlockPos pos = event.getPos();

        if (BlockInteractionHandler.handleLeftClick(player, level, hand, pos)) {
            event.setCanceled(true);
        }
    }

    private void onRightClickBlock(PlayerInteractEvent.RightClickBlock event) {
        Player player = event.getEntity();
        Level level = event.getLevel();
        InteractionHand hand = event.getHand();
        BlockPos pos = event.getPos();

        if (BlockInteractionHandler.handleRightClick(player, level, hand, pos)) {
            event.setCanceled(true);
        }
    }
}
