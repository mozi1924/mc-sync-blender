package com.mozi1924.yefira.forge;

import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.command.SelectionCommand;
import com.mozi1924.yefira.event.BlockInteractionHandler;
import net.minecraft.core.BlockPos;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.fml.common.Mod;

@Mod(Yefira.MOD_ID)
public class YefiraForge {

    public YefiraForge() {
        Yefira.init();

        MinecraftForge.EVENT_BUS.addListener(this::onRegisterCommands);
        MinecraftForge.EVENT_BUS.addListener(this::onServerStarted);
        MinecraftForge.EVENT_BUS.addListener(this::onServerStopping);
        MinecraftForge.EVENT_BUS.addListener(this::onServerTick);
        MinecraftForge.EVENT_BUS.addListener(this::onLeftClickBlock);
        MinecraftForge.EVENT_BUS.addListener(this::onRightClickBlock);
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

    private void onServerTick(TickEvent.ServerTickEvent event) {
        if (event.phase == TickEvent.Phase.END && event.getServer() != null) {
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
