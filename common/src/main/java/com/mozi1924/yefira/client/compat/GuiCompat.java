package com.mozi1924.yefira.client.compat;

import net.minecraft.client.gui.components.Checkbox;
import net.minecraft.network.chat.Component;
import java.util.function.Consumer;

/**
 * Compatibility layer for Minecraft GUI components.
 */
public class GuiCompat {

    /**
     * Creates a Checkbox compatible with Minecraft 1.20.x.
     */
    public static Checkbox createCheckbox(int x, int y, int width, int height,
                                          Component message, boolean initialValue,
                                          Consumer<Boolean> onValueChange) {
        return new ConfigCheckbox(x, y, width, height, message, initialValue, onValueChange);
    }

    private static class ConfigCheckbox extends Checkbox {
        private final Consumer<Boolean> onToggle;

        public ConfigCheckbox(int x, int y, int width, int height, Component message, boolean selected, Consumer<Boolean> onToggle) {
            super(x, y, width, height, message, selected);
            this.onToggle = onToggle;
        }

        @Override
        public void onPress() {
            super.onPress();
            if (this.onToggle != null) {
                this.onToggle.accept(this.selected());
            }
        }
    }
}
