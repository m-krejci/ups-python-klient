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
        self.heartbeat_thread = None
        self.last_contact = time.time()
        self.timeout_limit = 10

    def _heartbeat_loop(self):
        print("[HEARTBEAT] Thread start.")

        interval = getattr(self, 'heartbeat_interval', PONG_INTERVAL)
        while self.running:
            try:
                time.sleep(interval)
                if not self.running:
                    break
            
            except Exception as e:
                print(f"[HEATBEAT] Chyba: {e}")
                break
        
        print("[HEARTBEAT] Thread end.")


    def start_heartbeat(self, interval=PONG_INTERVAL):
        self.heartbeat_interval = interval

        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()


    def run(self):
        # self.start_heartbeat()
        self.last_contact = time.time()
        while self.running:
            try:
                self.sock.settimeout(5.0)
                type_msg, message = receive_full_message(self.sock)
                
                self.last_contact = time.time()

                if type_msg == Message_types.PING.value:
                    self.last_contact = time.time()
                    # packet = build_message(Message_types.PONG.value, "")
                    # print(f"Odesílám zprávu: {packet}")
                    # self.sock.sendall(packet)
                    continue

                if type_msg == Message_types.RECO.value:
                    self.message_queue.put(("reconnect", type_msg, message))
                    continue
                    
                self.message_queue.put(("message", type_msg, message))

            except socket.timeout:
                continue

            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                if self.running:
                    print(f"[NETWORK] Spojení ztraceno: {e}")
                    self.message_queue.put(("network_lost", str(e)))
                break
            except Exception as e:
                self.message_queue.put(("error", e))
                print(e)
                break

    def stop(self):
        self.running = False

        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except:
            pass

