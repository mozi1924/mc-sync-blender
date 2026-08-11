package com.mozi1924.mcsbl.mixin;

import com.mozi1924.mcsbl.encoder.BlockDataEncoder;
import com.mozi1924.mcsbl.network.WebSocketServerManager;
import com.mozi1924.mcsbl.selection.SelectionBox;
import com.mozi1924.mcsbl.selection.SelectionManager;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import java.util.Collections;

@Mixin(Level.class)
public abstract class LevelMixin {

    @Inject(
        method = "setBlock(Lnet/minecraft/core/BlockPos;Lnet/minecraft/world/level/block/state/BlockState;II)Z",
        at = @At("RETURN")
    )
    private void mcsync$onSetBlock(BlockPos pos, BlockState state, int flags, int recursionLeft, CallbackInfoReturnable<Boolean> cir) {
        if (Boolean.TRUE.equals(cir.getReturnValue())) {
            Level level = (Level) (Object) this;

            // 仅在服务端逻辑执行广播（避免客户端与服务端重复推流）
            if (!level.isClientSide()) {
                SelectionManager selectionManager = SelectionManager.getInstance();
                if (selectionManager.hasSelection()) {
                    SelectionBox selection = selectionManager.getCurrentSelection();

                    if (level.dimension().equals(selectionManager.getDimension()) && selection.contains(pos)) {
                        BlockDataEncoder.BlockChangeEntry change = new BlockDataEncoder.BlockChangeEntry(pos.immutable(), state);
                        WebSocketServerManager.getInstance().broadcastDeltaUpdate(selection, Collections.singletonList(change));
                    }
                }
            }
        }
    }
}
