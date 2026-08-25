package com.mozi1924.yefira.network;

import com.mozi1924.yefira.Yefira;
import com.mozi1924.yefira.encoder.BlockDataEncoder;
import com.mozi1924.yefira.selection.SelectionBox;
import com.mozi1924.yefira.selection.SelectionManager;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import org.java_websocket.WebSocket;
import org.java_websocket.handshake.ClientHandshake;
import org.java_websocket.server.WebSocketServer;

import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

public class WebSocketServerManager extends WebSocketServer implements SelectionManager.SelectionChangeListener {

    private static WebSocketServerManager INSTANCE;
    private static int PORT = 8765;

    private final Set<WebSocket> clients = Collections.newSetFromMap(new ConcurrentHashMap<>());
    // Block edits frequently arrive as a burst (fill, paste, WorldEdit-like
    // operations).  Accumulate the last state for each coordinate and emit
    // at most one delta packet per server tick.
    private final Map<BlockPos, BlockDataEncoder.BlockChangeEntry> pendingDeltaChanges = new LinkedHashMap<>();
    private SelectionBox pendingDeltaSelection;

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

    private final AtomicLong globalSeqId = new AtomicLong(1);

    @Override
    public void onOpen(WebSocket conn, ClientHandshake handshake) {
        clients.add(conn);
        Yefira.LOGGER.info("New DCC client connected: {}", conn.getRemoteSocketAddress());

        // New clients receive one authoritative full snapshot plus its
        // manifest.  Section snapshots are repair payloads only and are sent
        // on an explicit client request after a manifest mismatch.
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
        } else if ("DUMP_MODELS".equalsIgnoreCase(message.trim())) {
            java.util.Map<String, com.mozi1924.yefira.encoder.BlockStateModelData> models = com.mozi1924.yefira.encoder.BlockModelExtractor.getAllDirectionalModels();
            StringBuilder sb = new StringBuilder("DUMP_MODELS:{\n");
            int count = 0;
            for (java.util.Map.Entry<String, com.mozi1924.yefira.encoder.BlockStateModelData> entry : models.entrySet()) {
                if (count > 0) sb.append(",\n");
                sb.append("  \"").append(entry.getKey().replace("\"", "\\\"")).append("\": ").append(entry.getValue().toJson());
                count++;
            }
            sb.append("\n}");
            conn.send(sb.toString());
        }
    }

    @Override
    public void onMessage(WebSocket conn, ByteBuffer message) {
        if (message == null || message.remaining() < 4) return;

        message.order(java.nio.ByteOrder.LITTLE_ENDIAN);
        byte b0 = message.get();
        byte b1 = message.get();

        if (b0 != BlockDataEncoder.MAGIC[0] || b1 != BlockDataEncoder.MAGIC[1]) {
            return;
        }

        byte version = message.get();
        byte packetType = message.get();

        SelectionManager selectionManager = SelectionManager.getInstance();
        if (!selectionManager.hasSelection() || selectionManager.getCurrentLevel() == null) {
            return;
        }

        Level level = selectionManager.getCurrentLevel();
        SelectionBox selection = selectionManager.getCurrentSelection();

        if (packetType == BlockDataEncoder.PACKET_C2S_REQ_FULL_SYNC) {
            Yefira.LOGGER.info("Client {} requested FULL SYNC.", conn.getRemoteSocketAddress());
            sendSnapshotToClient(conn, level, selection);
        } else if (packetType == BlockDataEncoder.PACKET_C2S_REQ_SECTION_SYNC) {
            if (message.remaining() < 2) return;
            int count = message.getShort() & 0xFFFF;
            Yefira.LOGGER.info("Client {} requested section sync for {} sections.", conn.getRemoteSocketAddress(), count);

            for (int i = 0; i < count; i++) {
                if (message.remaining() < 12) break;
                int secX = message.getInt();
                int secY = message.getInt();
                int secZ = message.getInt();
                BlockDataEncoder.SectionPos secPos = new BlockDataEncoder.SectionPos(secX, secY, secZ);
                byte[] sectionSnapshot = BlockDataEncoder.encodeSectionSnapshot(level, selection, secPos);
                conn.send(sectionSnapshot);
            }
        }
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
        clearPendingDeltaChanges();
        Yefira.LOGGER.info("Broadcasting new selection snapshot to {} clients...", clients.size());
        broadcastSnapshot(level, selection);
    }

    @Override
    public void onSelectionCleared() {
        clearPendingDeltaChanges();
        // 可发送选区清空标志包，目前直接忽略或发送空数据
    }

    // --- 数据发送辅助方法 ---

    private void sendSnapshotToClient(WebSocket conn, Level level, SelectionBox selection) {
        try {
            long snapshotSeqId = globalSeqId.incrementAndGet();
            byte[] infoBytes = BlockDataEncoder.encodeSelectionInfo(selection);
            conn.send(infoBytes);

            byte[] manifestBytes = BlockDataEncoder.encodeSectionManifest(level, selection, snapshotSeqId);
            conn.send(manifestBytes);

            byte[] snapshotBytes = BlockDataEncoder.encodeFullSnapshot(level, selection);
            conn.send(snapshotBytes);
        } catch (Exception e) {
            Yefira.LOGGER.error("Failed to send snapshot to client {}", conn.getRemoteSocketAddress(), e);
        }
    }

    public void broadcastSnapshot(Level level, SelectionBox selection) {
        if (clients.isEmpty()) return;
        try {
            long snapshotSeqId = globalSeqId.incrementAndGet();
            byte[] infoBytes = BlockDataEncoder.encodeSelectionInfo(selection);
            byte[] manifestBytes = BlockDataEncoder.encodeSectionManifest(level, selection, snapshotSeqId);
            byte[] snapshotBytes = BlockDataEncoder.encodeFullSnapshot(level, selection);

            for (WebSocket client : clients) {
                if (client.isOpen()) {
                    client.send(infoBytes);
                    client.send(manifestBytes);
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
            long seqId = globalSeqId.incrementAndGet();
            byte[] deltaBytes = BlockDataEncoder.encodeDeltaUpdate(selection, changes, seqId);
            for (WebSocket client : clients) {
                if (client.isOpen()) {
                    client.send(deltaBytes);
                }
            }
        } catch (Exception e) {
            Yefira.LOGGER.error("Error broadcasting delta update", e);
        }
    }

    /** Queue an edit for the next server tick, coalescing repeated writes. */
    public void queueDeltaUpdate(SelectionBox selection, BlockDataEncoder.BlockChangeEntry change) {
        if (clients.isEmpty()) return;
        synchronized (pendingDeltaChanges) {
            if (pendingDeltaSelection != null && !sameBounds(pendingDeltaSelection, selection)) {
                pendingDeltaChanges.clear();
            }
            pendingDeltaSelection = selection;
            pendingDeltaChanges.put(change.pos().immutable(), change);
        }
    }

    /** Called from END_SERVER_TICK to make edit traffic bounded and ordered. */
    public void flushQueuedDeltaUpdates() {
        synchronized (pendingDeltaChanges) {
            if (pendingDeltaChanges.isEmpty() || pendingDeltaSelection == null) return;
            SelectionBox selection = pendingDeltaSelection;
            List<BlockDataEncoder.BlockChangeEntry> changes = List.copyOf(pendingDeltaChanges.values());
            pendingDeltaChanges.clear();
            pendingDeltaSelection = null;
            // Keep this send ordered with selection changes: if a selection
            // changes concurrently, it either clears this batch before the
            // send, or waits and sends its replacement snapshot afterwards.
            // A client can therefore never receive an old-selection delta
            // after the replacement full snapshot.
            broadcastDeltaUpdate(selection, changes);
        }
    }

    private void clearPendingDeltaChanges() {
        synchronized (pendingDeltaChanges) {
            pendingDeltaChanges.clear();
            pendingDeltaSelection = null;
        }
    }

    private static boolean sameBounds(SelectionBox a, SelectionBox b) {
        return a.getMin().equals(b.getMin()) && a.getMax().equals(b.getMax());
    }
}
