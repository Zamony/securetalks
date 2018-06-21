import time
import math
import socket
import struct
import pickle


class TCP:
    def __init__(self, sock=None, reuseaddr=False):
        self.sock = socket.socket() if sock is None else sock
        if reuseaddr:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def bind(self, addr):
        self.sock.bind(addr)

    def listen(self, backlog=None):
        if backlog is None:
            self.sock.listen()
        else:
            self.sock.listen(backlog)

    def accept(self):
        client_sock, addr = self.sock.accept()
        return TCP(sock=client_sock), addr

    def connect(self, addr):
        self.sock.connect(addr)

    def close(self):
        self.sock.close()

    def send(self, msg_obj):
        msg_binary = pickle.dumps(msg_obj)
        self.sock.send(struct.pack("!I", len(msg_binary)))
        self.sock.send(msg_binary)

    def recv(self):
        b1, b2, b3, b4 = (
            self.sock.recv(1),
            self.sock.recv(1),
            self.sock.recv(1),
            self.sock.recv(1),
        )
        data_len = struct.unpack("!I", b1 + b2 + b3 + b4)[0]

        msg_obj = b""
        bytes_read = 0
        while bytes_read < data_len:
            readed_data = self.sock.recv(data_len - bytes_read)
            bytes_read += len(readed_data)
            msg_obj += readed_data

        return pickle.loads(msg_obj)


class UDP:
    def __init__(self, reuseaddr=False):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.msgs = {}
        self.counter = 0
        if reuseaddr:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def bind(self, addr):
        self.sock.bind(addr)

    def close(self):
        self.sock.close()

    def sendto(self, msg_obj, addr, payload_size=250):
        msg_id = self.counter
        msg_binary = pickle.dumps(msg_obj)
        msg_total = math.ceil(len(msg_binary) / payload_size)

        for i, msg_num in zip(
            range(0, len(msg_binary), payload_size), range(msg_total)
        ):
            data = msg_binary[i : i + payload_size]
            message = pickle.dumps((msg_id, msg_num, msg_total, data))
            self._sendtoall(message, addr)

        # нужно для уникальности Id соообщений
        time.sleep(0.01)
        self.counter = (self.counter + 1) % 8000 # 8000 * 0.01 > ttl

    def _sendtoall(self, message, addr):
        bytes_sent = 0
        message_len = len(message)
        while bytes_sent < message_len:
            bytes_sent += self.sock.sendto(message[bytes_sent:], addr)

    def recvfrom(self, ttl=60):
        while True:
            self._del_old_datagrams(ttl)
            self._del_empty_addrs()
            readed_bytes, addr = self.sock.recvfrom(512)
            msg_id, msg_num, msg_total, msg = pickle.loads(readed_bytes)
            
            if addr not in self.msgs:
                self.msgs[addr] = {}

            if msg_id in self.msgs[addr]:
                self.msgs[addr][msg_id]["data"][msg_num] = msg
                if all(self.msgs[addr][msg_id]["data"]):
                    data = b"".join(self.msgs[addr][msg_id]["data"])
                    del self.msgs[addr][msg_id]
                    return pickle.loads(data), addr
            elif msg_total == 1:
                return pickle.loads(msg), addr
            else:
                self.msgs[addr][msg_id] = {
                    "arrived_at": time.time(),
                    "data": [b""] * msg_total,
                }
                self.msgs[addr][msg_id]["data"][msg_num] = msg

    def _del_empty_addrs(self):
        self.msgs = {k: v for (k, v) in self.msgs.items() if v != {}}

    def _del_old_datagrams(self, ttl):
        ids_to_remove = []
        curr_time = time.time()
        for addr in self.msgs:
            for msg_id in self.msgs[addr]:
                if curr_time - self.msgs[addr][msg_id]["arrived_at"] > ttl:
                    ids_to_remove.append((addr, msg_id))

        for addr, msg_id in ids_to_remove:
            del self.msgs[addr][msg_id]
