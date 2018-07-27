import ssl
import time
import json
import logging
import dataclasses
import threading
import multiprocessing

from . import orm
from . import crypto
from . import snakesockets

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MessageParsingError(ValueError):
    """Error occurring when message structure is invalid"""


class Receiver:
    def __init__(self, gui, sender, storage,
                 mcrypto, certs, queue, listening_address):
        self.gui = gui
        self.sender = sender
        self.storage = storage
        self.mcrypto = mcrypto
        self.queue = queue
        self.ttl = 60*60*24*2  # two days
        
        self.llreceiver = LowLevelReceiver(certs, queue, listening_address)
        self.llreceiver_proc = multiprocessing.Process(
            target=self.llreceiver.run
        )
        self.llreceiver_proc.start()

    def run(self):
        while True:
            address, message_bytes = self.queue.get()
            if address is None and message_bytes is None:
                break
            try:
                message_json = message_bytes.decode("utf-8")
                message = json.loads(message_json)
                message["type"]
            except Exception:
                pass  # message parsing error
            else:
                self._receive(address, message)

    def terminate(self):
        self.llreceiver_proc.terminate()
        self.llreceiver_proc.join()
        self.queue.put([None, None]) # stop yourself

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
        try:
            address.port = int(message["server_port"])
        except Exception:
            return

        if not self.storage.ipaddresses.check_address_exists(address):
            self.storage.ipaddresses.add_address(address)

        logger.info(
            f"Got request for offline data from {address} with {message}"
        )
        
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
        except (ValueError, KeyError):
            return  # flooding
        else:
            for cph in message["ciphergrams"]:
                self._handle_ciphergram_message(
                    address, cph, offline=True
                )

    def _handle_ciphergram_message(self, address, message, offline=False):
        try:
            message = json.dumps(message)
            ciphergram = self._parse_ciphergram(message)
        except MessageParsingError:
            logger.info("Got ciphergram message, parsing error")
            return

        try:
            node_id, msg_text = self.mcrypto.get_plaintext(ciphergram)
        except crypto.MessageDecryptionError:
            logger.info("Got ciphergram message, decryption error")
            self._store_as_ciphergram(message, ciphergram.timestamp)
        except crypto.MessageCryptoError:
            logger.info("Got ciphergram message, crypto error")
            return
        else:
            if abs(ciphergram.timestamp - time.time()) > self.ttl:
                logger.info("Got ciphergram message, message is too old")
                return  # message is too old

            logger.info("Got ciphergram message, stored as message")
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
            self.storage.ciphergrams.add_ciphergram(ciphergram)
        except orm.CiphergramAlreadyExistsError:
            pass

    def _store_as_message(self, node_id, msg_text, timestamp):
        node = orm.Node(node_id)
        message = orm.Message(
            node_id, msg_text,
            to_me=True, sender_timestamp=timestamp
        )
        if not self.storage.nodes.check_node_exists(node):
            self.storage.nodes.add_node(node)
        if not self.storage.messages.check_message_exists(message):
            self.storage.messages.add_message(message)
            self.gui.push_message({**node, **message})


class LowLevelReceiver:
    def __init__(self, certs, queue, listening_address):
        self.certs = certs
        self.queue = queue
        self.listening_address = listening_address

    def _worker(self, client_socket, client_addr):
        message = client_socket.recv()
        logger.info(f"Received message {message}")
        self.queue.put((orm.IPAddress(*client_addr), message))
        client_socket.close()

    def run(self):
        context = ssl.SSLContext()
        context.load_cert_chain(self.certs.cert_file, self.certs.key_file)
        server_socket = snakesockets.TCP(reuseaddr=True)
        server_socket.sock = context.wrap_socket(
            server_socket.sock, server_side=True
        )
        server_socket.bind(self.listening_address)
        server_socket.listen()

        while True:
            client_socket, client_addr = server_socket.accept()
            client_thread = threading.Thread(
                target=self._worker, args=(client_socket, client_addr)
            )
            client_thread.start()
