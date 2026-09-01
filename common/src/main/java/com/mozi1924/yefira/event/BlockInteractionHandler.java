package com.mozi1924.yefira.event;

import com.mozi1924.yefira.selection.SelectionManager;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;

public class BlockInteractionHandler {

    public static boolean handleLeftClick(Player player, Level level, InteractionHand hand, BlockPos pos) {
        if (com.mozi1924.yefira.config.YefiraConfig.getInstance().isEnableLegacyPickaxeTool() && isHoldingSelectionTool(player, hand)) {
            if (!level.isClientSide()) {
                SelectionManager.getInstance().setPos1(level, pos);
                player.sendSystemMessage(Component.translatable("yefira.command.pos1.set", pos.toShortString()));
            }
            return true;
        }
        return false;
    }

    public static boolean handleRightClick(Player player, Level level, InteractionHand hand, BlockPos pos) {
        if (com.mozi1924.yefira.config.YefiraConfig.getInstance().isEnableLegacyPickaxeTool()
                && hand == InteractionHand.MAIN_HAND && isHoldingSelectionTool(player, hand)) {
            if (!level.isClientSide()) {
                SelectionManager.getInstance().setPos2(level, pos);
                player.sendSystemMessage(Component.translatable("yefira.command.pos2.set", pos.toShortString()));
            }
            return true;
        }
        return false;
    }

    private static boolean isHoldingSelectionTool(Player player, InteractionHand hand) {
        ItemStack held = player.getItemInHand(hand);
        return held.is(Items.GOLDEN_PICKAXE);
    }
}
