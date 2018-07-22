import json
import dataclasses
import multiprocessing

from . import crypto
from . import snakesockets


class Sender:
    def __init__(self, storage, mcrypto, queue):
        self.queue = queue
        self.storage = storage
        self.offline_requested = None
        self.llsender = LowLevelSender(self.queue, mcrypto)
        self.llsender_proc = multiprocessing.Process(
            target=self.llsender.run
        )
        self.llsender_proc.start()

    def send_message_to(self, user_key, message):
        self.broadcast(message, user_key)

    def request_offline_data(self):
        self.offline_requested = {
            address for address in self.storage.ipaddresses.listall()
        }
        self.broadcast(
            json.dumps(dict(type="request_offline_data"))
        )

    def send_to(self, message, ip_address):
        self.queue.put(
            ([ip_address, ], message, None)
        )

    def broadcast(self, message, user_key=None):
        addresses = self.storage.ipaddresses.listall()
        self.queue.put((addresses, message, user_key))

    def broadcast_from(self, message, ip_address):
        ip_addresses = self.storage.ipaddresses.listall()
        ip_addresses.remove(ip_address)
        self.queue.put((ip_addresses, message, None))

    def terminate(self):
        self.llsender_proc.terminate()
        self.llsender_proc.join()


class LowLevelSender:
    def __init__(self, queue, mcrypto):
        self.queue = queue
        self.mcrypto = mcrypto

    def _send_message(self, ip_addresses, message):
        for ip_address in ip_addresses:
            client_socket = snakesockets.TCP()
            client_socket.connect((ip_address.address, 8080))
            client_socket.send(message)

    def run(self):
        while True:
            addresses, message, node_id = self.queue.get()
            if node_id is not None:
                ciphergram = self.mcrypto.get_ciphergram(node_id, message)
                self._send_message(
                    addresses,
                    json.dumps(
                        dict(
                            type="ciphergram",
                            **dataclasses.asdict(ciphergram)
                        )
                    )
                )
            else:
                self._send_message(addresses, message)
