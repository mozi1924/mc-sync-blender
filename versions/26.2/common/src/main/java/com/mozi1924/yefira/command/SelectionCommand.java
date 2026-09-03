package com.mozi1924.yefira.command;

import com.mozi1924.yefira.network.WebSocketServerManager;
import com.mozi1924.yefira.selection.SelectionBox;
import com.mozi1924.yefira.selection.SelectionManager;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.context.CommandContext;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;

public class SelectionCommand {

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(Commands.literal("yefira")
            .then(Commands.literal("pos1")
                .requires(source -> source.permissions().hasPermission(net.minecraft.server.permissions.Permissions.COMMANDS_GAMEMASTER))
                .executes(SelectionCommand::setPos1Current)
                .then(Commands.argument("pos", BlockPosArgument.blockPos())
                    .executes(ctx -> setPos1Specific(ctx, BlockPosArgument.getLoadedBlockPos(ctx, "pos")))))
            .then(Commands.literal("pos2")
                .requires(source -> source.permissions().hasPermission(net.minecraft.server.permissions.Permissions.COMMANDS_GAMEMASTER))
                .executes(SelectionCommand::setPos2Current)
                .then(Commands.argument("pos", BlockPosArgument.blockPos())
                    .executes(ctx -> setPos2Specific(ctx, BlockPosArgument.getLoadedBlockPos(ctx, "pos")))))
            .then(Commands.literal("clear")
                .requires(source -> source.permissions().hasPermission(net.minecraft.server.permissions.Permissions.COMMANDS_GAMEMASTER))
                .executes(SelectionCommand::clearSelection))
            .then(Commands.literal("refresh")
                .requires(source -> source.permissions().hasPermission(net.minecraft.server.permissions.Permissions.COMMANDS_GAMEMASTER))
                .executes(SelectionCommand::refreshSnapshot))
            .then(Commands.literal("status")
                .executes(SelectionCommand::showStatus))
            .then(Commands.literal("server")
                .requires(source -> source.permissions().hasPermission(net.minecraft.server.permissions.Permissions.COMMANDS_GAMEMASTER))
                .then(Commands.literal("start")
                    .executes(SelectionCommand::serverStart))
                .then(Commands.literal("stop")
                    .executes(SelectionCommand::serverStop))
                .then(Commands.literal("restart")
                    .executes(SelectionCommand::serverRestart))
                .then(Commands.literal("status")
                    .executes(SelectionCommand::serverStatus)))
            .then(Commands.literal("dump_directional_models")
                .requires(source -> source.permissions().hasPermission(net.minecraft.server.permissions.Permissions.COMMANDS_GAMEMASTER))
                .executes(SelectionCommand::dumpDirectionalModels))
        );
    }

    private static int serverStart(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        WebSocketServerManager server = WebSocketServerManager.getInstance();
        com.mozi1924.yefira.config.YefiraConfig cfg = com.mozi1924.yefira.config.YefiraConfig.getInstance();
        if (server.isRunning()) {
            source.sendFailure(Component.translatable("yefira.command.server.already_running", server.getHost(), server.getPort()));
        } else {
            server.startServer(cfg.getHost(), cfg.getPort());
            source.sendSuccess(() -> Component.translatable("yefira.command.server.started", cfg.getHost(), cfg.getPort()), true);
        }
        return 1;
    }

    private static int serverStop(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        WebSocketServerManager server = WebSocketServerManager.getInstance();
        if (!server.isRunning()) {
            source.sendFailure(Component.translatable("yefira.command.server.not_running"));
        } else {
            server.stopServer();
            source.sendSuccess(() -> Component.translatable("yefira.command.server.stopped"), true);
        }
        return 1;
    }

    private static int serverRestart(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        WebSocketServerManager server = WebSocketServerManager.getInstance();
        com.mozi1924.yefira.config.YefiraConfig cfg = com.mozi1924.yefira.config.YefiraConfig.getInstance();
        server.restartServer(cfg.getHost(), cfg.getPort());
        source.sendSuccess(() -> Component.translatable("yefira.command.server.restarted", cfg.getHost(), cfg.getPort()), true);
        return 1;
    }

    private static int serverStatus(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        WebSocketServerManager server = WebSocketServerManager.getInstance();
        if (server.isRunning()) {
            source.sendSuccess(() -> Component.translatable("yefira.command.server.status.running",
                    server.getHost(), server.getPort(), server.getConnectedCount()), false);
        } else {
            source.sendSuccess(() -> Component.translatable("yefira.command.server.status.stopped"), false);
        }
        return 1;
    }

    private static int dumpDirectionalModels(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        java.util.Map<String, com.mozi1924.yefira.encoder.BlockStateModelData> models = com.mozi1924.yefira.encoder.BlockModelExtractor.getAllDirectionalModels();
        StringBuilder sb = new StringBuilder("{\n");
        int count = 0;
        for (java.util.Map.Entry<String, com.mozi1924.yefira.encoder.BlockStateModelData> entry : models.entrySet()) {
            if (count > 0) sb.append(",\n");
            sb.append("  \"").append(entry.getKey().replace("\"", "\\\"")).append("\": ").append(entry.getValue().toJson());
            count++;
        }
        sb.append("\n}");
        try {
            java.nio.file.Path outPath = java.nio.file.Paths.get("directional_models_dump.json");
            java.nio.file.Files.writeString(outPath, sb.toString());
            source.sendSuccess(() -> Component.translatable("yefira.command.dump.success", models.size(), outPath.toAbsolutePath().toString()), true);
        } catch (Exception e) {
            source.sendFailure(Component.translatable("yefira.command.dump.failed", e.getMessage()));
        }
        return count;
    }

    private static int setPos1Current(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        BlockPos pos = BlockPos.containing(source.getPosition());
        SelectionManager.getInstance().setPos1(source.getLevel(), pos);
        source.sendSuccess(() -> Component.translatable("yefira.command.pos1.set", pos.toShortString()), true);
        return 1;
    }

    private static int setPos1Specific(CommandContext<CommandSourceStack> ctx, BlockPos pos) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager.getInstance().setPos1(source.getLevel(), pos);
        source.sendSuccess(() -> Component.translatable("yefira.command.pos1.set", pos.toShortString()), true);
        return 1;
    }

    private static int setPos2Current(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        BlockPos pos = BlockPos.containing(source.getPosition());
        SelectionManager.getInstance().setPos2(source.getLevel(), pos);
        source.sendSuccess(() -> Component.translatable("yefira.command.pos2.set", pos.toShortString()), true);
        return 1;
    }

    private static int setPos2Specific(CommandContext<CommandSourceStack> ctx, BlockPos pos) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager.getInstance().setPos2(source.getLevel(), pos);
        source.sendSuccess(() -> Component.translatable("yefira.command.pos2.set", pos.toShortString()), true);
        return 1;
    }

    private static int clearSelection(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager.getInstance().clearSelection();
        source.sendSuccess(() -> Component.translatable("yefira.command.clear.success"), true);
        return 1;
    }

    private static int refreshSnapshot(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager mgr = SelectionManager.getInstance();
        if (mgr.hasSelection() && mgr.getCurrentLevel() != null) {
            WebSocketServerManager.getInstance().broadcastSnapshot(mgr.getCurrentLevel(), mgr.getCurrentSelection());
            source.sendSuccess(() -> Component.translatable("yefira.command.refresh.success"), true);
        } else {
            source.sendFailure(Component.translatable("yefira.command.refresh.no_selection"));
        }
        return 1;
    }

    private static int showStatus(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager mgr = SelectionManager.getInstance();
        if (mgr.hasSelection()) {
            SelectionBox box = mgr.getCurrentSelection();
            source.sendSuccess(() -> Component.translatable("yefira.command.status.info",
                    box.getMin().toShortString(),
                    box.getMax().toShortString(),
                    box.getSizeX(), box.getSizeY(), box.getSizeZ(),
                    box.getVolume()), false);
        } else {
            source.sendSuccess(() -> Component.translatable("yefira.command.status.empty"), false);
        }
        return 1;
    }
}
