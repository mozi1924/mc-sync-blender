import asyncio
import struct
import threading
import logging
import time

logger = logging.getLogger("Yefira")

class SyncClientThread(threading.Thread):
    def __init__(self, url: str, on_status_change, on_selection_info, on_full_snapshot, on_delta_update):
        super().__init__(daemon=True)
        self.url = url
        self.on_status_change = on_status_change
        self.on_selection_info = on_selection_info
        self.on_full_snapshot = on_full_snapshot
        self.on_delta_update = on_delta_update
        self.running = True
        self.is_connected = False
        self.websocket = None
        self.loop = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect_and_listen())

    async def _connect_and_listen(self):
        try:
            import websockets
        except ImportError:
            self.on_status_change("Missing 'websockets' library")
            return

        self.on_status_change("CONNECTING...")
        logger.info(f"Connecting to Yefira WebSocket: {self.url}")

        try:
            async with websockets.connect(self.url) as websocket:
                self.websocket = websocket
                self.is_connected = True
                self.on_status_change("CONNECTED")
                logger.info("Connected to Yefira WebSocket Server successfully!")

                while self.running and self.is_connected:
                    try:
                        message = await websocket.recv()
                        if isinstance(message, bytes):
                            self._parse_binary_packet(message)
                        elif isinstance(message, str):
                            logger.info(f"Received text message: {message}")
                    except websockets.ConnectionClosed:
                        logger.info("WebSocket connection closed by server.")
                        break
                    except Exception as e:
                        logger.error(f"Error receiving message: {e}")
                        break
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.on_status_change(f"ERROR: {e}")
        finally:
            self.is_connected = False
            self.websocket = None
            self.on_status_change("DISCONNECTED")

    def _parse_binary_packet(self, data: bytes):
        if len(data) < 4:
            return

        magic, version, packet_type = struct.unpack('<2sBB', data[:4])
        if magic != b'MC':
            logger.warning(f"Invalid magic header: {magic}")
            return

        offset = 4
        if packet_type == 0x01:  # Selection Info
            min_x, min_y, min_z, size_x, size_y, size_z = struct.unpack('<iiiiii', data[offset:offset+24])
            self.on_selection_info(min_x, min_y, min_z, size_x, size_y, size_z)

        elif packet_type == 0x02:  # Full Snapshot
            min_x, min_y, min_z, size_x, size_y, size_z = struct.unpack('<iiiiii', data[offset:offset+24])
            offset += 24

            palette_count = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2

            palette = []
            for _ in range(palette_count):
                str_len = struct.unpack('<H', data[offset:offset+2])[0]
                offset += 2
                item_str = data[offset:offset+str_len].decode('utf-8')
                offset += str_len
                palette.append(item_str)

            index_bytes_per_block = data[offset]
            offset += 1

            total_blocks = size_x * size_y * size_z
            self.on_full_snapshot(min_x, min_y, min_z, size_x, size_y, size_z, palette, total_blocks)

        elif packet_type == 0x03:  # Delta Update
            min_x, min_y, min_z = struct.unpack('<iii', data[offset:offset+12])
            offset += 12

            change_count = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2

            changes = []
            for _ in range(change_count):
                rel_x, rel_y, rel_z = struct.unpack('<HHH', data[offset:offset+6])
                offset += 6
                str_len = struct.unpack('<H', data[offset:offset+2])[0]
                offset += 2
                state_str = data[offset:offset+str_len].decode('utf-8')
                offset += str_len
                abs_x, abs_y, abs_z = min_x + rel_x, min_y + rel_y, min_z + rel_z
                changes.append((abs_x, abs_y, abs_z, state_str))

            self.on_delta_update(min_x, min_y, min_z, changes)

    def stop(self):
        self.running = False
        self.is_connected = False
        if self.loop and self.websocket:
            try:
                asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)
            except Exception as e:
                logger.error(f"Error stopping websocket: {e}")

    def send_text(self, text: str):
        if self.loop and self.websocket and self.is_connected:
            try:
                asyncio.run_coroutine_threadsafe(self.websocket.send(text), self.loop)
            except Exception as e:
                logger.error(f"Error sending text over websocket: {e}")
