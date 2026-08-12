package com.mozi1924.yefira.network;

import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.encoder.BlockDataEncoder;
import com.mozi1924.yefira.selection.SelectionBox;
import com.mozi1924.yefira.selection.SelectionManager;
import net.minecraft.world.level.Level;
import org.java_websocket.WebSocket;
import org.java_websocket.handshake.ClientHandshake;
import org.java_websocket.server.WebSocketServer;

import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

public class WebSocketServerManager extends WebSocketServer implements SelectionManager.SelectionChangeListener {

    private static WebSocketServerManager INSTANCE;
    private static int PORT = 8765;

    private final Set<WebSocket> clients = Collections.newSetFromMap(new ConcurrentHashMap<>());

    public static synchronized WebSocketServerManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new WebSocketServerManager(new InetSocketAddress(PORT));
        }
        return INSTANCE;
    }

    public static synchronized void setPort(int port) {
        PORT = port;
    }

    private WebSocketServerManager(InetSocketAddress address) {
        super(address);
        setReuseAddr(true);
    }

    public void startServer() {
        try {
            this.start();
            SelectionManager.getInstance().addListener(this);
            Yefira.LOGGER.info("WebSocket Server started on port: {}", getPort());
        } catch (Exception e) {
            Yefira.LOGGER.error("Failed to start WebSocket Server", e);
        }
    }

    public void stopServer() {
        try {
            SelectionManager.getInstance().removeListener(this);
            this.stop(1000);
            Yefira.LOGGER.info("WebSocket Server stopped.");
        } catch (Exception e) {
            Yefira.LOGGER.error("Error stopping WebSocket Server", e);
        }
    }

    @Override
    public void onOpen(WebSocket conn, ClientHandshake handshake) {
        clients.add(conn);
        Yefira.LOGGER.info("New DCC client connected: {}", conn.getRemoteSocketAddress());

        // 新连接建立时，自动推送当前选区与全量快照
        SelectionManager selectionManager = SelectionManager.getInstance();
        if (selectionManager.hasSelection() && selectionManager.getCurrentLevel() != null) {
            sendSnapshotToClient(conn, selectionManager.getCurrentLevel(), selectionManager.getCurrentSelection());
        }
    }

    @Override
    public void onClose(WebSocket conn, int code, String reason, boolean remote) {
        clients.remove(conn);
        Yefira.LOGGER.info("DCC client disconnected: {}", conn.getRemoteSocketAddress());
    }

    @Override
    public void onMessage(WebSocket conn, String message) {
        // 支持文本指令回复，如 "PING" -> "PONG", "REFRESH" -> 发送全量快照
        if ("PING".equalsIgnoreCase(message.trim())) {
            conn.send("PONG");
        } else if ("REFRESH".equalsIgnoreCase(message.trim())) {
            SelectionManager selectionManager = SelectionManager.getInstance();
            if (selectionManager.hasSelection() && selectionManager.getCurrentLevel() != null) {
                sendSnapshotToClient(conn, selectionManager.getCurrentLevel(), selectionManager.getCurrentSelection());
            }
        }
    }

    @Override
    public void onMessage(WebSocket conn, ByteBuffer message) {
        // 可扩充处理来自客户端的反向数据流
    }

    @Override
    public void onError(WebSocket conn, Exception ex) {
        Yefira.LOGGER.error("WebSocket error on connection: {}", conn != null ? conn.getRemoteSocketAddress() : "global", ex);
    }

    @Override
    public void onStart() {
        Yefira.LOGGER.info("WebSocket Server successfully initialized.");
    }

    // --- SelectionChangeListener 接口实现 ---

    @Override
    public void onSelectionChanged(Level level, SelectionBox selection) {
        if (clients.isEmpty()) return;
        Yefira.LOGGER.info("Broadcasting new selection snapshot to {} clients...", clients.size());
        broadcastSnapshot(level, selection);
    }

    @Override
    public void onSelectionCleared() {
        // 可发送选区清空标志包，目前直接忽略或发送空数据
    }

    // --- 数据发送辅助方法 ---

    private void sendSnapshotToClient(WebSocket conn, Level level, SelectionBox selection) {
        try {
            byte[] infoBytes = BlockDataEncoder.encodeSelectionInfo(selection);
            conn.send(infoBytes);

            byte[] snapshotBytes = BlockDataEncoder.encodeFullSnapshot(level, selection);
            conn.send(snapshotBytes);
        } catch (Exception e) {
            Yefira.LOGGER.error("Failed to send snapshot to client {}", conn.getRemoteSocketAddress(), e);
        }
    }

    public void broadcastSnapshot(Level level, SelectionBox selection) {
        if (clients.isEmpty()) return;
        try {
            byte[] infoBytes = BlockDataEncoder.encodeSelectionInfo(selection);
            byte[] snapshotBytes = BlockDataEncoder.encodeFullSnapshot(level, selection);

            for (WebSocket client : clients) {
                if (client.isOpen()) {
                    client.send(infoBytes);
                    client.send(snapshotBytes);
                }
            }
        } catch (Exception e) {
            Yefira.LOGGER.error("Error broadcasting snapshot", e);
        }
    }

    public void broadcastDeltaUpdate(SelectionBox selection, List<BlockDataEncoder.BlockChangeEntry> changes) {
        if (clients.isEmpty() || changes.isEmpty()) return;
        try {
            byte[] deltaBytes = BlockDataEncoder.encodeDeltaUpdate(selection, changes);
            for (WebSocket client : clients) {
                if (client.isOpen()) {
                    client.send(deltaBytes);
                }
            }
        } catch (Exception e) {
            Yefira.LOGGER.error("Error broadcasting delta update", e);
        }
    }
}
