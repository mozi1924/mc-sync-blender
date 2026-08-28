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
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

public class WebSocketServerManager implements SelectionManager.SelectionChangeListener {

    private static final WebSocketServerManager INSTANCE = new WebSocketServerManager();
    private static int PORT = 8765;

    private Impl serverImpl;
    private final Set<WebSocket> clients = Collections.newSetFromMap(new ConcurrentHashMap<>());
    private final Map<BlockPos, BlockDataEncoder.BlockChangeEntry> pendingDeltaChanges = new LinkedHashMap<>();
    private SelectionBox pendingDeltaSelection;
    private long lastManifestBroadcastTick = 0;
    private boolean hasEditsSinceLastManifest = false;
    private final AtomicLong globalSeqId = new AtomicLong(1);

    public static class ClientConfig {
        public byte throttleMode = 0; // 0 = NORMAL, 1 = ECO, 2 = PAUSED
        public byte targetFps = 60;
        public boolean isActive = true;
    }

    private final Map<WebSocket, ClientConfig> clientConfigs = new ConcurrentHashMap<>();

    public static WebSocketServerManager getInstance() {
        return INSTANCE;
    }

    public static synchronized void setPort(int port) {
        PORT = port;
    }

    public int getPort() {
        return PORT;
    }

    private WebSocketServerManager() {
    }

    public synchronized void startServer() {
        if (serverImpl != null) {
            Yefira.LOGGER.info("WebSocket Server is already running on port: {}", PORT);
            return;
        }
        try {
            serverImpl = new Impl(new InetSocketAddress(PORT));
            serverImpl.setReuseAddr(true);
            serverImpl.start();
            SelectionManager.getInstance().addListener(this);
            Yefira.LOGGER.info("WebSocket Server started on port: {}", PORT);
        } catch (Exception e) {
            Yefira.LOGGER.error("Failed to start WebSocket Server", e);
            serverImpl = null;
        }
    }

    public synchronized void stopServer() {
        SelectionManager.getInstance().removeListener(this);
        clearPendingDeltaChanges();
        clientConfigs.clear();
        clients.clear();

        if (serverImpl != null) {
            try {
                serverImpl.stop(1000);
                Yefira.LOGGER.info("WebSocket Server stopped.");
            } catch (Exception e) {
                Yefira.LOGGER.error("Error stopping WebSocket Server", e);
            } finally {
                serverImpl = null;
            }
        }
    }

    private class Impl extends WebSocketServer {
        public Impl(InetSocketAddress address) {
            super(address);
        }

        @Override
        public void onOpen(WebSocket conn, ClientHandshake handshake) {
            clients.add(conn);
            clientConfigs.put(conn, new ClientConfig());
            Yefira.LOGGER.info("New DCC client connected: {}", conn.getRemoteSocketAddress());

            SelectionManager selectionManager = SelectionManager.getInstance();
            if (selectionManager.hasSelection() && selectionManager.getCurrentLevel() != null) {
                sendHandshakeManifestToClient(conn, selectionManager.getCurrentLevel(), selectionManager.getCurrentSelection());
            }
        }

        @Override
        public void onClose(WebSocket conn, int code, String reason, boolean remote) {
            clients.remove(conn);
            clientConfigs.remove(conn);
            Yefira.LOGGER.info("DCC client disconnected: {}", conn.getRemoteSocketAddress());
        }

        @Override
        public void onMessage(WebSocket conn, String message) {
            WebSocketServerManager.this.handleTextMessage(conn, message);
        }

        @Override
        public void onMessage(WebSocket conn, ByteBuffer message) {
            WebSocketServerManager.this.handleBinaryMessage(conn, message);
        }

        @Override
        public void onError(WebSocket conn, Exception ex) {
            Yefira.LOGGER.error("WebSocket error on connection: {}", conn != null ? conn.getRemoteSocketAddress() : "global", ex);
        }

        @Override
        public void onStart() {
            Yefira.LOGGER.info("WebSocket Server successfully initialized.");
        }
    }

    private void handleTextMessage(WebSocket conn, String message) {
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

    private void handleBinaryMessage(WebSocket conn, ByteBuffer message) {
        if (message == null || message.remaining() < 4) return;

        message.order(java.nio.ByteOrder.LITTLE_ENDIAN);
        byte b0 = message.get();
        byte b1 = message.get();

        if (b0 != BlockDataEncoder.MAGIC[0] || b1 != BlockDataEncoder.MAGIC[1]) {
            return;
        }

        byte version = message.get();
        byte packetType = message.get();

        if (packetType == BlockDataEncoder.PACKET_C2S_SYNC_CONFIG) {
            byte mode = message.remaining() > 0 ? message.get() : 0;
            byte fps = message.remaining() > 0 ? message.get() : 60;
            byte flags = message.remaining() > 0 ? message.get() : 1;
            ClientConfig cfg = clientConfigs.computeIfAbsent(conn, k -> new ClientConfig());
            cfg.throttleMode = mode;
            cfg.targetFps = fps;
            cfg.isActive = (flags & 1) != 0;
            Yefira.LOGGER.info("Client {} updated sync config: mode={}, targetFps={}, active={}",
                    conn.getRemoteSocketAddress(), mode, fps, cfg.isActive);
            return;
        }

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

    // --- SelectionChangeListener 接口实现 ---

    @Override
    public void onSelectionChanged(Level level, SelectionBox selection) {
        if (clients.isEmpty()) return;
        clearPendingDeltaChanges();
        BlockDataEncoder.clearSectionCRCCache();
        Yefira.LOGGER.info("Broadcasting new selection snapshot to {} clients...", clients.size());
        broadcastSnapshot(level, selection);
    }

    @Override
    public void onSelectionCleared() {
        clearPendingDeltaChanges();
        BlockDataEncoder.clearSectionCRCCache();
        // 可发送选区清空标志包，目前直接忽略或发送空数据
    }

    // --- 数据发送辅助方法 ---

    private void sendHandshakeManifestToClient(WebSocket conn, Level level, SelectionBox selection) {
        try {
            long snapshotSeqId = globalSeqId.incrementAndGet();
            byte[] infoBytes = BlockDataEncoder.encodeSelectionInfo(selection);
            conn.send(infoBytes);

            int totalSections = BlockDataEncoder.getCoveredSections(selection).size();
            int nonEmptySections = BlockDataEncoder.countNonEmptySections(level, selection);
            long totalVolume = selection.getVolume();
            String dimName = level.dimension().identifier().toString();
            byte[] handshakeBytes = BlockDataEncoder.encodeHandshakeInfo(totalSections, nonEmptySections, totalVolume, dimName, 0);
            conn.send(handshakeBytes);

            byte[] manifestBytes = BlockDataEncoder.encodeSectionManifest(level, selection, snapshotSeqId);
            conn.send(manifestBytes);
        } catch (Exception e) {
            Yefira.LOGGER.error("Failed to send handshake manifest to client {}", conn.getRemoteSocketAddress(), e);
        }
    }

    private void sendSnapshotToClient(WebSocket conn, Level level, SelectionBox selection) {
        try {
            long snapshotSeqId = globalSeqId.incrementAndGet();
            long volume = selection.getVolume();

            byte[] infoBytes = BlockDataEncoder.encodeSelectionInfo(selection);
            conn.send(infoBytes);

            byte[] manifestBytes = BlockDataEncoder.encodeSectionManifest(level, selection, snapshotSeqId);
            conn.send(manifestBytes);

            if (volume <= 32768) {
                byte[] snapshotBytes = BlockDataEncoder.encodeFullSnapshot(level, selection);
                conn.send(snapshotBytes);
            } else {
                // 大选区/调试模式世界：流式分块按 Section 发送非空快照，避免单包超过 1MB/20MB 造成内存暴涨或网络超限
                BlockDataEncoder.streamNonEmptySectionSnapshots(level, selection, bytes -> {
                    if (conn.isOpen()) {
                        conn.send(bytes);
                    }
                });
            }
        } catch (Exception e) {
            Yefira.LOGGER.error("Failed to send snapshot to client {}", conn.getRemoteSocketAddress(), e);
        }
    }

    public void broadcastSnapshot(Level level, SelectionBox selection) {
        if (clients.isEmpty()) return;
        try {
            long snapshotSeqId = globalSeqId.incrementAndGet();
            long volume = selection.getVolume();

            byte[] infoBytes = BlockDataEncoder.encodeSelectionInfo(selection);
            byte[] manifestBytes = BlockDataEncoder.encodeSectionManifest(level, selection, snapshotSeqId);

            for (WebSocket client : clients) {
                if (client.isOpen()) {
                    client.send(infoBytes);
                    client.send(manifestBytes);
                }
            }

            if (volume <= 32768) {
                byte[] snapshotBytes = BlockDataEncoder.encodeFullSnapshot(level, selection);
                for (WebSocket client : clients) {
                    if (client.isOpen()) {
                        client.send(snapshotBytes);
                    }
                }
            } else {
                BlockDataEncoder.streamNonEmptySectionSnapshots(level, selection, bytes -> {
                    for (WebSocket client : clients) {
                        if (client.isOpen()) {
                            client.send(bytes);
                        }
                    }
                });
            }
        } catch (Exception e) {
            Yefira.LOGGER.error("Error broadcasting snapshot", e);
        }
    }

    public void broadcastManifest(Level level, SelectionBox selection) {
        if (clients.isEmpty() || level == null || selection == null) return;
        try {
            long seqId = globalSeqId.incrementAndGet();
            byte[] manifestBytes = BlockDataEncoder.encodeSectionManifest(level, selection, seqId);
            for (WebSocket client : clients) {
                if (client.isOpen()) {
                    client.send(manifestBytes);
                }
            }
        } catch (Exception e) {
            Yefira.LOGGER.error("Error broadcasting section manifest", e);
        }
    }

    public void tickValidationHeartbeat(long currentTick) {
        if (clients.isEmpty()) return;
        SelectionManager selectionManager = SelectionManager.getInstance();
        if (!selectionManager.hasSelection() || selectionManager.getCurrentLevel() == null) return;

        // Broadcast manifest if edits occurred and 20 ticks elapsed, or at least every 100 ticks (5s)
        if ((hasEditsSinceLastManifest && currentTick - lastManifestBroadcastTick >= 20)
                || (currentTick - lastManifestBroadcastTick >= 100)) {
            lastManifestBroadcastTick = currentTick;
            hasEditsSinceLastManifest = false;
            broadcastManifest(selectionManager.getCurrentLevel(), selectionManager.getCurrentSelection());
        }
    }

    public void broadcastDeltaUpdate(SelectionBox selection, List<BlockDataEncoder.BlockChangeEntry> changes) {
        if (clients.isEmpty() || changes.isEmpty()) return;
        try {
            hasEditsSinceLastManifest = true;
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
        BlockPos pos = change.pos();
        BlockDataEncoder.invalidateSectionCRC(new BlockDataEncoder.SectionPos(pos.getX() >> 4, pos.getY() >> 4, pos.getZ() >> 4));
        synchronized (pendingDeltaChanges) {
            if (pendingDeltaSelection != null && !sameBounds(pendingDeltaSelection, selection)) {
                pendingDeltaChanges.clear();
            }
            pendingDeltaSelection = selection;
            pendingDeltaChanges.put(change.pos().immutable(), change);
        }
    }

    /** Called from END_SERVER_TICK to make edit traffic bounded, ordered, and optimized for batches. */
    public void flushQueuedDeltaUpdates() {
        synchronized (pendingDeltaChanges) {
            if (pendingDeltaChanges.isEmpty() || pendingDeltaSelection == null) return;
            SelectionBox selection = pendingDeltaSelection;
            List<BlockDataEncoder.BlockChangeEntry> changes = List.copyOf(pendingDeltaChanges.values());
            pendingDeltaChanges.clear();
            pendingDeltaSelection = null;
            hasEditsSinceLastManifest = true;

            SelectionManager selectionManager = SelectionManager.getInstance();
            Level level = selectionManager.getCurrentLevel();

            // When a large burst of edits occurs (e.g. /fill, WorldEdit, large redstone),
            // upgrade densely affected 16x16x16 sections to Section Snapshots (Packet 0x06).
            if (changes.size() > 64 && level != null) {
                Map<BlockDataEncoder.SectionPos, List<BlockDataEncoder.BlockChangeEntry>> sectionGroups = new HashMap<>();
                for (BlockDataEncoder.BlockChangeEntry change : changes) {
                    BlockPos pos = change.pos();
                    BlockDataEncoder.SectionPos secPos = new BlockDataEncoder.SectionPos(pos.getX() >> 4, pos.getY() >> 4, pos.getZ() >> 4);
                    sectionGroups.computeIfAbsent(secPos, k -> new ArrayList<>()).add(change);
                }

                List<BlockDataEncoder.BlockChangeEntry> remainingMicroDeltas = new ArrayList<>();
                for (Map.Entry<BlockDataEncoder.SectionPos, List<BlockDataEncoder.BlockChangeEntry>> entry : sectionGroups.entrySet()) {
                    BlockDataEncoder.SectionPos secPos = entry.getKey();
                    List<BlockDataEncoder.BlockChangeEntry> secChanges = entry.getValue();

                    if (secChanges.size() >= 32 || changes.size() > 256) {
                        // Broadcast optimized Palette Section Snapshot for this whole chunk
                        byte[] secBytes = BlockDataEncoder.encodeSectionSnapshot(level, selection, secPos);
                        for (WebSocket client : clients) {
                            if (client.isOpen()) {
                                client.send(secBytes);
                            }
                        }
                    } else {
                        remainingMicroDeltas.addAll(secChanges);
                    }
                }

                if (!remainingMicroDeltas.isEmpty()) {
                    broadcastDeltaUpdate(selection, remainingMicroDeltas);
                }
            } else {
                broadcastDeltaUpdate(selection, changes);
            }
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
