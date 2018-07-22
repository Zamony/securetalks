import time
import json

from . import orm
from . import crypto


class MessageParsingError(ValueError):
    """Error occurring when message structure is invalid"""


class Receiver:
    def __init__(self, presentor, sender, storage, mcrypto, queue):
        self.queue = queue
        self.sender = sender
        self.storage = storage
        self.mcrypto = mcrypto
        self.presentor = presentor
        self.ttl = 60*60*24*2  # two days

    def run(self):
        while True:
            address, message_bytes = self.queue.get()
            try:
                message_json = message_bytes.decode("utf-8")
                message = json.loads(message_json)
                message["type"]
            except Exception:
                pass  # message parsing error
            else:
                self._receive(address, message)

    def _receive(self, address, message):
        if message["type"] == "ciphergram":
            self._handle_ciphergram_message(address, message)

        elif message["type"] == "request_offline_data":
            self._handle_request_offline_message(address, message)

        elif message["type"] == "response_offline_data":
            self._handle_response_offline_message(address, message)

        else:
            pass  # message parsing error

    def _handle_request_offline_message(self, address, message):
        response = dict(
            type="response_offline_data",
            ciphergrams=[]
        )
        for ciphergram in self.storage.ciphergrams.list_all():
            response["ciphergrams"].append(
                dict(
                    content=ciphergram.content,
                    timestamp=ciphergram.timestamp
                )
            )
        self.sender.send_to(json.dumps(response), address)

    def _handle_response_offline_message(self, address, message):
        try:
            self.sender.offline_requested.remove(address)
            message["ciphergrams"]
        except KeyError:
            return  # flooding

        for cph in message["ciphergrams"]:
            self._handle_ciphergram_message(
                address, cph, offline=True
            )

    def _handle_ciphergram_message(self, address, message, offline=False):
        try:
            message = json.dumps(message)
            ciphergram = self._parse_ciphergram(message)
        except MessageParsingError:
            return

        try:
            node_id, msg_text = self.mcrypto.get_plaintext(ciphergram)
        except crypto.MessageDecryptionError:
            self._store_as_ciphergram(message, ciphergram.timestamp)
        except crypto.MessageCryptoError:
            return
        else:
            if abs(ciphergram.timestamp - time.time()) > self.ttl:
                return  # message is too old
            self._store_as_message(node_id, msg_text, ciphergram.timestamp)
            if not offline:
                self.sender.broadcast_from(message, address)

    def _parse_ciphergram(self, flat_ciphergram):
        try:
            crypto_message = json.loads(flat_ciphergram)
            del crypto_message["type"]
            crypto_message = crypto.EncryptedMessage(**crypto_message)
        except Exception as exc:
            raise MessageParsingError from exc
        return crypto_message

    def _store_as_ciphergram(self, message, timestamp):
        ciphergram = orm.Ciphergram(message, timestamp)
        try:
            self.storage.add_ciphergram(ciphergram)
        except orm.CiphergramAlreadyExistsError:
            pass

    def _store_as_message(self, node_id, msg_text, timestamp):
        message = orm.Message(
            node_id, msg_text,
            to_me=True, sender_timestamp=timestamp
        )
        if not self.storage.messages.check_message_exists(message):
            self.storage.messages.add_message(message)
