import json
import logging
import dataclasses
import multiprocessing

from . import crypto
from . import snakesockets

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Sender:
    def __init__(self, mcrypto, storage, my_port, queue):
        self.queue = queue
        self.storage = storage
        self.my_port = my_port
        self.offline_requested = None
        self.llsender = LowLevelSender(self.queue, mcrypto)
        self.llsender_proc = multiprocessing.Process(
            target=self.llsender.run
        )
        self.llsender_proc.start()

    def send_message_to(self, user_key, message):
        self.broadcast(message, user_key)

    def request_offline_data(self):
        self.offline_requested = [
            address for address in self.storage.ipaddresses.list_all()
        ]
        
        self.broadcast(
            json.dumps(
                dict(
                    type="request_offline_data",
                    server_port=self.my_port
                )
            )
        )

    def send_to(self, message, ip_address):
        self.queue.put(
            ([ip_address, ], message, None)
        )

    def broadcast(self, message, user_key=None):
        addresses = self.storage.ipaddresses.list_all()
        self.queue.put((addresses, message, user_key))

    def broadcast_from(self, message, ip_address):
        ip_addresses = self.storage.ipaddresses.list_all()
        try:
            ip_addresses.remove(ip_address)
        except ValueError:
            pass
        else:
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
            try:
                client_socket = snakesockets.TCP()
                client_socket.connect((ip_address.address, ip_address.port))
                client_socket.send(message.encode("utf-8"))
            except Exception:
                pass
            logger.info(
                f"Sending message to {ip_address} with content {message}"
            )

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
