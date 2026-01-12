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
        self.heartbeat_interval = 15
        self.heartbeat_thread = None

    def _heartbeat_loop(self):
        print("[HEARTBEAT] Thread start.")

        interval = getattr(self, 'heartbeat_interval', 15)
        while self.running:
            try:
                time.sleep(interval)
                if not self.running:
                    break

                packet = build_message(Message_types.PONG.value, "")
                print(f"Odesílám zprávu: {packet}")
                self.sock.sendall(packet)
            
            except Exception as e:
                print(f"[HEATBEAT] Chyba: {e}")
                break
        
        print("[HEARTBEAT] Thread end.")


    def start_heartbeat(self, interval=15):
        self.heartbeat_interval = interval

        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()


    def run(self):
        # self.start_heartbeat()

        while self.running:
            try:
                type_msg, message = receive_full_message(self.sock)
                self.message_queue.put(("message", type_msg, message))
            except Exception as e:
                self.message_queue.put(("error", e))
                print(e)
                break

    def stop(self):
        self.running = False


