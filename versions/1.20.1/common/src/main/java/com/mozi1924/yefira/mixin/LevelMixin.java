package com.mozi1924.yefira.mixin;

import com.mozi1924.yefira.encoder.BlockDataEncoder;
import com.mozi1924.yefira.network.WebSocketServerManager;
import com.mozi1924.yefira.selection.SelectionBox;
import com.mozi1924.yefira.selection.SelectionManager;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(Level.class)
public abstract class LevelMixin {

    // 拦截 4 参数 setBlock
    @Inject(
        method = "setBlock(Lnet/minecraft/core/BlockPos;Lnet/minecraft/world/level/block/state/BlockState;II)Z",
        at = @At("RETURN"),
        require = 0
    )
    private void mcsync$onSetBlock4(BlockPos pos, BlockState state, int flags, int recursionLeft, CallbackInfoReturnable<Boolean> cir) {
        mcsync$handleBlockChange(pos, state, cir.getReturnValue());
    }

    // 拦截 3 参数 setBlock
    @Inject(
        method = "setBlock(Lnet/minecraft/core/BlockPos;Lnet/minecraft/world/level/block/state/BlockState;I)Z",
        at = @At("RETURN"),
        require = 0
    )
    private void mcsync$onSetBlock3(BlockPos pos, BlockState state, int flags, CallbackInfoReturnable<Boolean> cir) {
        mcsync$handleBlockChange(pos, state, cir.getReturnValue());
    }

    private void mcsync$handleBlockChange(BlockPos pos, BlockState state, Boolean success) {
        if (Boolean.TRUE.equals(success)) {
            Level level = (Level) (Object) this;

            if (!level.isClientSide()) {
                SelectionManager selectionManager = SelectionManager.getInstance();
                if (selectionManager.hasSelection()) {
                    SelectionBox selection = selectionManager.getCurrentSelection();

                    // 校验选区维度与包围盒范围
                    if (selectionManager.getDimension() != null &&
                        level.dimension().equals(selectionManager.getDimension()) &&
                        selection.contains(pos)) {

                        BlockDataEncoder.BlockChangeEntry change = new BlockDataEncoder.BlockChangeEntry(pos.immutable(), state);
                        WebSocketServerManager.getInstance().queueDeltaUpdate(selection, change);
                    }
                }
            }
        }
    }
}
