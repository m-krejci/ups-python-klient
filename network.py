import socket
import threading
import queue
from message_handler import *
import time
from message_types import *


class Network(threading.Thread):
    def __init__(self, sock: socket.socket, message_queue: queue.Queue):
        super().__init__(daemon=True)
        self.sock = sock
        self.message_queue = message_queue
        self.running = True

        self.heartbeat_interval = PONG_INTERVAL
        self.timeout_limit = 3 * PONG_INTERVAL  # 3x výpadek
        self.heartbeat_thread = None

        self.last_contact = time.time()

    def _heartbeat_loop(self):
        print("[HEARTBEAT] Thread start.")
        while self.running:
            time.sleep(self.heartbeat_interval)

            elapsed = time.time() - self.last_contact
            if elapsed > self.timeout_limit:
                print("[HEARTBEAT] Timeout – spojení mrtvé")
                self.message_queue.put(
                    ("network_lost", "heartbeat timeout")
                )
                self.running = False
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                    self.sock.close()
                except:
                    pass
                break

        print("[HEARTBEAT] Thread end.")

    def start_heartbeat(self, interval=PONG_INTERVAL):
        self.heartbeat_interval = interval
        self.timeout_limit = 3 * interval
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self.heartbeat_thread.start()

    def run(self):
        self.last_contact = time.time()
        self.start_heartbeat()   # ← teď se opravdu spustí

        while self.running:
            try:
                self.sock.settimeout(1.0)
                type_msg, message = receive_full_message(self.sock)

                # jakákoliv komunikace = kontakt
                self.last_contact = time.time()

                if type_msg == Message_types.PING.value:
                    packet = build_message(Message_types.PONG.value, "")
                    self.sock.sendall(packet)
                    continue

                if type_msg == Message_types.RECO.value:
                    self.message_queue.put(("reconnect", type_msg, message))
                    continue

                self.message_queue.put(("message", type_msg, message))

            except socket.timeout:
                continue

            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                if self.running:
                    self.message_queue.put(("network_lost", str(e)))
                break

            except Exception as e:
                self.message_queue.put(("error", e))
                break

    def stop(self):
        self.running = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except:
            pass
