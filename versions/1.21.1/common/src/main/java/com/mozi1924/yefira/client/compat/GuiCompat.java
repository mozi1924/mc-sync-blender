package com.mozi1924.yefira.client.compat;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Checkbox;
import net.minecraft.network.chat.Component;
import java.util.function.Consumer;

/**
 * Compatibility layer for Minecraft 1.21.x GUI components.
 */
public class GuiCompat {

    /**
     * Creates a Checkbox compatible with Minecraft 1.21.x.
     */
    public static Checkbox createCheckbox(int x, int y, int width, int height,
                                          Component message, boolean initialValue,
                                          Consumer<Boolean> onValueChange) {
        return Checkbox.builder(message, Minecraft.getInstance().font)
                .pos(x, y)
                .selected(initialValue)
                .onValueChange((cb, val) -> {
                    if (onValueChange != null) {
                        onValueChange.accept(val);
                    }
                })
                .build();
    }
}
