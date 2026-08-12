package com.mozi1924.yefira.event;

import com.mozi1924.yefira.selection.SelectionManager;
import net.fabricmc.fabric.api.event.player.AttackBlockCallback;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.BlockHitResult;

public class BlockInteractionHandler {

    public static void register() {
        // 左键攻击/点击方块设置 Pos1 并拦截破坏方块 (手持金镐)
        AttackBlockCallback.EVENT.register((player, level, hand, pos, direction) -> {
            if (isHoldingSelectionTool(player, hand)) {
                if (!level.isClientSide()) {
                    SelectionManager.getInstance().setPos1(level, pos);
                    player.sendSystemMessage(Component.literal("§a[Yefira] First position set to " + pos.toShortString()));
                }
                return InteractionResult.SUCCESS;
            }
            return InteractionResult.PASS;
        });

        // 右键交互方块设置 Pos2 (手持金镐)
        UseBlockCallback.EVENT.register((player, level, hand, hitResult) -> {
            if (hand == InteractionHand.MAIN_HAND && isHoldingSelectionTool(player, hand)) {
                if (!level.isClientSide()) {
                    BlockPos pos = hitResult.getBlockPos();
                    SelectionManager.getInstance().setPos2(level, pos);
                    player.sendSystemMessage(Component.literal("§a[Yefira] Second position set to " + pos.toShortString()));
                }
                return InteractionResult.SUCCESS;
            }
            return InteractionResult.PASS;
        });
    }

    private static boolean isHoldingSelectionTool(Player player, InteractionHand hand) {
        ItemStack held = player.getItemInHand(hand);
        return held.is(Items.GOLDEN_PICKAXE);
    }
}
