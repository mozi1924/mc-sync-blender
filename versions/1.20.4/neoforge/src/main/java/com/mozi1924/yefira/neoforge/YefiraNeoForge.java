package com.mozi1924.yefira.neoforge;

import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.command.SelectionCommand;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.TickEvent;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import net.neoforged.neoforge.event.server.ServerStoppingEvent;

@Mod(Yefira.MOD_ID)
public class YefiraNeoForge {

    public YefiraNeoForge(IEventBus modEventBus) {
        Yefira.init();

        NeoForge.EVENT_BUS.addListener(this::onRegisterCommands);
        NeoForge.EVENT_BUS.addListener(this::onServerStarted);
        NeoForge.EVENT_BUS.addListener(this::onServerStopping);
        NeoForge.EVENT_BUS.addListener(this::onServerTick);
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
}
