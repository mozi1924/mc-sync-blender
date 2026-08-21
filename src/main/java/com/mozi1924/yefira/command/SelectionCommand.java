package com.mozi1924.yefira.command;

import com.mozi1924.yefira.network.WebSocketServerManager;
import com.mozi1924.yefira.selection.SelectionBox;
import com.mozi1924.yefira.selection.SelectionManager;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.context.CommandContext;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;

public class SelectionCommand {

    public static void register() {
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            registerCommands(dispatcher);
        });
    }

    private static void registerCommands(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(Commands.literal("yefira")
            .then(Commands.literal("pos1")
                .executes(SelectionCommand::setPos1Current)
                .then(Commands.argument("pos", BlockPosArgument.blockPos())
                    .executes(ctx -> setPos1Specific(ctx, BlockPosArgument.getLoadedBlockPos(ctx, "pos")))))
            .then(Commands.literal("pos2")
                .executes(SelectionCommand::setPos2Current)
                .then(Commands.argument("pos", BlockPosArgument.blockPos())
                    .executes(ctx -> setPos2Specific(ctx, BlockPosArgument.getLoadedBlockPos(ctx, "pos")))))
            .then(Commands.literal("clear")
                .executes(SelectionCommand::clearSelection))
            .then(Commands.literal("refresh")
                .executes(SelectionCommand::refreshSnapshot))
            .then(Commands.literal("status")
                .executes(SelectionCommand::showStatus))
            .then(Commands.literal("dump_directional_models")
                .executes(SelectionCommand::dumpDirectionalModels))
        );
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
            source.sendSuccess(() -> Component.literal("§a[Yefira] Dumped " + models.size() + " directional models to " + outPath.toAbsolutePath()), true);
        } catch (Exception e) {
            source.sendFailure(Component.literal("§c[Yefira] Failed to dump models: " + e.getMessage()));
        }
        return count;
    }

    private static int setPos1Current(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        BlockPos pos = BlockPos.containing(source.getPosition());
        SelectionManager.getInstance().setPos1(source.getLevel(), pos);
        source.sendSuccess(() -> Component.literal("§a[Yefira] Set Pos1 to " + pos.toShortString()), true);
        return 1;
    }

    private static int setPos1Specific(CommandContext<CommandSourceStack> ctx, BlockPos pos) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager.getInstance().setPos1(source.getLevel(), pos);
        source.sendSuccess(() -> Component.literal("§a[Yefira] Set Pos1 to " + pos.toShortString()), true);
        return 1;
    }

    private static int setPos2Current(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        BlockPos pos = BlockPos.containing(source.getPosition());
        SelectionManager.getInstance().setPos2(source.getLevel(), pos);
        source.sendSuccess(() -> Component.literal("§a[Yefira] Set Pos2 to " + pos.toShortString()), true);
        return 1;
    }

    private static int setPos2Specific(CommandContext<CommandSourceStack> ctx, BlockPos pos) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager.getInstance().setPos2(source.getLevel(), pos);
        source.sendSuccess(() -> Component.literal("§a[Yefira] Set Pos2 to " + pos.toShortString()), true);
        return 1;
    }

    private static int clearSelection(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager.getInstance().clearSelection();
        source.sendSuccess(() -> Component.literal("§e[Yefira] Selection cleared."), true);
        return 1;
    }

    private static int refreshSnapshot(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager mgr = SelectionManager.getInstance();
        if (mgr.hasSelection() && mgr.getCurrentLevel() != null) {
            WebSocketServerManager.getInstance().broadcastSnapshot(mgr.getCurrentLevel(), mgr.getCurrentSelection());
            source.sendSuccess(() -> Component.literal("§a[Yefira] Full snapshot re-broadcasted."), true);
        } else {
            source.sendFailure(Component.literal("§c[Yefira] No active selection to refresh."));
        }
        return 1;
    }

    private static int showStatus(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager mgr = SelectionManager.getInstance();
        if (mgr.hasSelection()) {
            SelectionBox box = mgr.getCurrentSelection();
            source.sendSuccess(() -> Component.literal("§b[Yefira] Active Selection:\n" +
                    " - Min: " + box.getMin().toShortString() + "\n" +
                    " - Max: " + box.getMax().toShortString() + "\n" +
                    " - Size: " + box.getSizeX() + "x" + box.getSizeY() + "x" + box.getSizeZ() + " (" + box.getVolume() + " blocks)"), false);
        } else {
            source.sendSuccess(() -> Component.literal("§e[Yefira] No active selection."), false);
        }
        return 1;
    }
}
