package com.mozi1924.mcsbl.command;

import com.mozi1924.mcsbl.network.WebSocketServerManager;
import com.mozi1924.mcsbl.selection.SelectionBox;
import com.mozi1924.mcsbl.selection.SelectionManager;
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
        dispatcher.register(Commands.literal("mcsync")
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
        );
    }

    private static int setPos1Current(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        BlockPos pos = BlockPos.containing(source.getPosition());
        SelectionManager.getInstance().setPos1(source.getLevel(), pos);
        source.sendSuccess(() -> Component.literal("§a[MC-Sync] Set Pos1 to " + pos.toShortString()), true);
        return 1;
    }

    private static int setPos1Specific(CommandContext<CommandSourceStack> ctx, BlockPos pos) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager.getInstance().setPos1(source.getLevel(), pos);
        source.sendSuccess(() -> Component.literal("§a[MC-Sync] Set Pos1 to " + pos.toShortString()), true);
        return 1;
    }

    private static int setPos2Current(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        BlockPos pos = BlockPos.containing(source.getPosition());
        SelectionManager.getInstance().setPos2(source.getLevel(), pos);
        source.sendSuccess(() -> Component.literal("§a[MC-Sync] Set Pos2 to " + pos.toShortString()), true);
        return 1;
    }

    private static int setPos2Specific(CommandContext<CommandSourceStack> ctx, BlockPos pos) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager.getInstance().setPos2(source.getLevel(), pos);
        source.sendSuccess(() -> Component.literal("§a[MC-Sync] Set Pos2 to " + pos.toShortString()), true);
        return 1;
    }

    private static int clearSelection(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager.getInstance().clearSelection();
        source.sendSuccess(() -> Component.literal("§e[MC-Sync] Selection cleared."), true);
        return 1;
    }

    private static int refreshSnapshot(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager mgr = SelectionManager.getInstance();
        if (mgr.hasSelection() && mgr.getCurrentLevel() != null) {
            WebSocketServerManager.getInstance().broadcastSnapshot(mgr.getCurrentLevel(), mgr.getCurrentSelection());
            source.sendSuccess(() -> Component.literal("§a[MC-Sync] Full snapshot re-broadcasted."), true);
        } else {
            source.sendFailure(Component.literal("§c[MC-Sync] No active selection to refresh."));
        }
        return 1;
    }

    private static int showStatus(CommandContext<CommandSourceStack> ctx) {
        CommandSourceStack source = ctx.getSource();
        SelectionManager mgr = SelectionManager.getInstance();
        if (mgr.hasSelection()) {
            SelectionBox box = mgr.getCurrentSelection();
            source.sendSuccess(() -> Component.literal("§b[MC-Sync] Active Selection:\n" +
                    " - Min: " + box.getMin().toShortString() + "\n" +
                    " - Max: " + box.getMax().toShortString() + "\n" +
                    " - Size: " + box.getSizeX() + "x" + box.getSizeY() + "x" + box.getSizeZ() + " (" + box.getVolume() + " blocks)"), false);
        } else {
            source.sendSuccess(() -> Component.literal("§e[MC-Sync] No active selection."), false);
        }
        return 1;
    }
}
