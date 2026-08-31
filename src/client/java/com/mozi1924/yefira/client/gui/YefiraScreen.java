package com.mozi1924.yefira.client.gui;

import com.mozi1924.yefira.config.YefiraConfig;
import com.mozi1924.yefira.network.WebSocketServerManager;
import com.mozi1924.yefira.selection.SelectionBox;
import com.mozi1924.yefira.selection.SelectionManager;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.Checkbox;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

public class YefiraScreen extends Screen {

    private EditBox hostEdit;
    private EditBox portEdit;
    private Checkbox autoStartCheckbox;
    private Checkbox legacyPickaxeCheckbox;
    private Button startStopButton;
    private Button restartButton;
    private Button clearSelectionButton;

    public YefiraScreen() {
        super(Component.translatable("yefira.gui.title"));
    }

    @Override
    protected void init() {
        super.init();

        int centerX = this.width / 2;
        int startY = 40;

        YefiraConfig cfg = YefiraConfig.getInstance();

        // Host EditBox
        this.hostEdit = new EditBox(this.font, centerX - 100, startY + 20, 200, 20, Component.translatable("yefira.gui.host"));
        this.hostEdit.setValue(cfg.getHost());
        this.addRenderableWidget(this.hostEdit);

        // Port EditBox
        this.portEdit = new EditBox(this.font, centerX - 100, startY + 60, 200, 20, Component.translatable("yefira.gui.port"));
        this.portEdit.setValue(String.valueOf(cfg.getPort()));
        this.addRenderableWidget(this.portEdit);

        // AutoStart Checkbox
        this.autoStartCheckbox = Checkbox.builder(Component.translatable("yefira.gui.autostart"), this.font)
                .pos(centerX - 100, startY + 90)
                .selected(cfg.isAutoStartOnWorldLoad())
                .onValueChange((cb, val) -> {
                    cfg.setAutoStartOnWorldLoad(val);
                    YefiraConfig.save();
                })
                .build();
        this.addRenderableWidget(this.autoStartCheckbox);

        // Legacy Pickaxe Checkbox
        this.legacyPickaxeCheckbox = Checkbox.builder(Component.translatable("yefira.gui.legacy_pickaxe"), this.font)
                .pos(centerX - 100, startY + 115)
                .selected(cfg.isEnableLegacyPickaxeTool())
                .onValueChange((cb, val) -> {
                    cfg.setEnableLegacyPickaxeTool(val);
                    YefiraConfig.save();
                })
                .build();
        this.addRenderableWidget(this.legacyPickaxeCheckbox);

        // Server Start / Stop Button
        WebSocketServerManager server = WebSocketServerManager.getInstance();
        Component startStopText = server.isRunning()
                ? Component.translatable("yefira.gui.server.stop")
                : Component.translatable("yefira.gui.server.start");

        this.startStopButton = Button.builder(startStopText, btn -> {
            applyConfigFromFields();
            if (server.isRunning()) {
                server.stopServer();
            } else {
                server.startServer(cfg.getHost(), cfg.getPort());
            }
            updateButtonLabels();
        }).bounds(centerX - 100, startY + 145, 95, 20).build();
        this.addRenderableWidget(this.startStopButton);

        // Server Restart Button
        this.restartButton = Button.builder(Component.translatable("yefira.gui.server.restart"), btn -> {
            applyConfigFromFields();
            server.restartServer(cfg.getHost(), cfg.getPort());
            updateButtonLabels();
        }).bounds(centerX + 5, startY + 145, 95, 20).build();
        this.addRenderableWidget(this.restartButton);

        // Clear Selection Button
        this.clearSelectionButton = Button.builder(Component.translatable("yefira.gui.selection.clear"), btn -> {
            SelectionManager.getInstance().clearSelection();
        }).bounds(centerX - 100, startY + 175, 200, 20).build();
        this.addRenderableWidget(this.clearSelectionButton);

        // Done / Close Button
        Button doneButton = Button.builder(Component.translatable("gui.done"), btn -> {
            applyConfigFromFields();
            this.onClose();
        }).bounds(centerX - 100, this.height - 30, 200, 20).build();
        this.addRenderableWidget(doneButton);
    }

    private void applyConfigFromFields() {
        YefiraConfig cfg = YefiraConfig.getInstance();
        if (hostEdit != null) {
            String host = hostEdit.getValue().trim();
            if (!host.isEmpty()) {
                cfg.setHost(host);
            }
        }
        if (portEdit != null) {
            try {
                int port = Integer.parseInt(portEdit.getValue().trim());
                if (port >= 1024 && port <= 65535) {
                    cfg.setPort(port);
                }
            } catch (NumberFormatException ignored) {}
        }
        YefiraConfig.save();
    }

    private void updateButtonLabels() {
        WebSocketServerManager server = WebSocketServerManager.getInstance();
        if (startStopButton != null) {
            startStopButton.setMessage(server.isRunning()
                    ? Component.translatable("yefira.gui.server.stop")
                    : Component.translatable("yefira.gui.server.start"));
        }
    }

    @Override
    public void onClose() {
        applyConfigFromFields();
        super.onClose();
    }

    @Override
    public void extractRenderState(GuiGraphicsExtractor graphics, int mouseX, int mouseY, float partialTick) {
        super.extractRenderState(graphics, mouseX, mouseY, partialTick);

        int centerX = this.width / 2;
        int startY = 40;

        // Title
        graphics.centeredText(this.font, this.title, centerX, 15, 0xFFFFFF);

        // Labels
        graphics.text(this.font, Component.translatable("yefira.gui.host.label"), centerX - 100, startY + 8, 0xAAAAAA);
        graphics.text(this.font, Component.translatable("yefira.gui.port.label"), centerX - 100, startY + 48, 0xAAAAAA);

        // Server Status display
        WebSocketServerManager server = WebSocketServerManager.getInstance();
        boolean running = server.isRunning();
        Component statusComponent = running
                ? Component.translatable("yefira.gui.status.running", server.getHost(), server.getPort(), server.getConnectedCount())
                : Component.translatable("yefira.gui.status.stopped");
        int statusColor = running ? 0x55FF55 : 0xFF5555;
        graphics.centeredText(this.font, statusComponent, centerX, startY + 205, statusColor);

        // Selection info display
        SelectionManager mgr = SelectionManager.getInstance();
        if (mgr.hasSelection()) {
            SelectionBox sel = mgr.getCurrentSelection();
            Component selText = Component.translatable("yefira.gui.selection.info",
                    sel.getMin().toShortString(), sel.getMax().toShortString(),
                    sel.getSizeX(), sel.getSizeY(), sel.getSizeZ(), sel.getVolume());
            graphics.centeredText(this.font, selText, centerX, startY + 220, 0x55FFFF);
        } else {
            graphics.centeredText(this.font, Component.translatable("yefira.gui.selection.none"), centerX, startY + 220, 0xAAAAAA);
        }
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }
}
