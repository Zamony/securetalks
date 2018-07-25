import json
import dataclasses
import multiprocessing

from . import storage
from . import crypto
from . import snakesockets


class Sender:
    def __init__(self, mcrypto, db_path, ttl, queue):
        self.queue = queue
        self.db_path = db_path
        self.ttl = ttl
        self.offline_requested = None
        self.llsender = LowLevelSender(self.queue, mcrypto)
        self.llsender_proc = multiprocessing.Process(
            target=self.llsender.run
        )
        self.llsender_proc.start()

    def send_message_to(self, user_key, message):
        self.broadcast(message, user_key)

    def request_offline_data(self):
        with storage.Storage(self.db_path, self.ttl) as storage_obj:
            self.offline_requested = {
                address for address in storage_obj.ipaddresses.list_all()
            }
        
        self.broadcast(
            json.dumps(dict(type="request_offline_data"))
        )

    def send_to(self, message, ip_address):
        self.queue.put(
            ([ip_address, ], message, None)
        )

    def broadcast(self, message, user_key=None):
        with storage.Storage(self.db_path, self.ttl) as storage_obj:
            addresses = storage_obj.ipaddresses.list_all()
        self.queue.put((addresses, message, user_key))

    def broadcast_from(self, message, ip_address):
        with storage.Storage(self.db_path, self.ttl) as storage_obj:
            ip_addresses = storage_obj.ipaddresses.list_all()
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
                try:
                    ciphergram = self.mcrypto.get_ciphergram(node_id, message)
                except crypto.MessageCryptoInvalidRecipientKey:
                    pass
                else:
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
