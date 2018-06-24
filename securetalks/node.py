import crypto
import storage
import snakesockets

class MessageParsingError(Exception):
    """Error when received bytes aren't being a message"""

class Node:
    def __init__(self, storage, mcrypto, port):
        self.storage = storage
        self.mcrypto = mcrypto
        self.port = port
        self._waiting_for_offline = set()

    def send_message_to(self, user_key, message):
        try:
            ciphergram = mcrypto.get_ciphergram(message)
        except Exception:
            pass
        else:
            self._broadcast(message)

    def receive(self, address, message_bytes):
        try:
            message_json = message_bytes.decode("utf-8")
            message = json.loads(message_json)
            message["type"]
        except Exception:
            raise MessageParsingError

        self._process_message(address, message)

    def request_offline_data(self, ip_address):
        self._waiting_for_offline.add(ip_address)
        sock = snakesockets.TCP()
        sock.connect( (ip_address, self.port) )
        sock.send('{"type": "request_offline_data"}')
        sock.close()

    def _broadcast_from(self, ip_address, message):
        for address in self.storage.known_addresses:
            if address != ip_address:
                self._send_to(address, message)

    def _broadcast(self, message):
        for address in self.storage.known_addresses:
            self._send_to(address, message)

    def _sendto(self, ip_address, message):
        client_socket = snakesockets.TCP()
        client_socket.connect( (ip_address, self.port) )
        client_socket.send(message)
        client_socket.close()

    def _process_ciphergram(self, cipherfram):
        try:
            user_pub_key, msg = self.mcrypto.get_plaintext()
        except crypto.MessageDecryptionError:
            self.storage.add_ciphergram(message)
        except crypto.MessageCryptoError:
            pass
        else:
            self.storage.add_message_from(user_pub_key, msg)

    def _process_message(self, address, message):
        if message["type"] == "ciphergram":
            self._process_ciphergram(message)
            self._broadcast_from(address, message)
        elif message["type"] == "request_offline_data":
            for ciphergram, timestamp in self.storage.ciphergrams:
                self._sendto(
                    address,
                    json.dumps({
                        "type": "response_offline_data",
                        "ciphergram": ciphergram,
                        "ttl": timestamp,
                    })
                )
        elif message["type"] == "response_offline_data":
            if address in self._waiting_for_offline:
                self._process_ciphergram(message)
        else:
            raise MessageParsingError
