import time
import json
import logging
import pathlib
import dataclasses

import cryptography
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.fernet import Fernet

from . import proof_of_work


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class EncryptedMessage:
    ciphertext: str
    cipherkey: str
    signature: str
    proof: int
    timestamp: int


class RSAKeysNotFoundError(IOError):
    """Error when keys aren't on the disk"""


class KeysProvider:
    def __init__(self, data_dir):
        self._pub_file = data_dir / "pub.pem"
        self._prv_file = data_dir / "prv.pem"
        self._pub_key = self._prv_key = self._pub_key_str = None

    @property
    def pub_key(self):
        if self._pub_key is None:
            self._obtain_keys()
        return self._pub_key

    @property
    def pub_key_str(self):
        if self._pub_key_str is None:
            pub_pem = self.pub_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            self._pub_key_str = pub_pem.hex()
        return self._pub_key_str

    @property
    def prv_key(self):
        if self._prv_key is None:
            self._obtain_keys()
        return self._prv_key

    def _obtain_keys(self):
        try:
            self._pub_key, self._prv_key = self._load_keys()
            logger.info("Keys are loaded")
        except RSAKeysNotFoundError:
            self._pub_key, self._prv_key = self._generate_keys()
            self._store_keys()
            logger.info("Keys are generated and stored on the disk")

    def _generate_keys(self):
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )
        return private_key.public_key(), private_key

    def _store_keys(self):
        pub_pem = self.pub_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        prv_pem = self.prv_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        with open(self._pub_file, "wb") as pub_file:
            with open(self._prv_file, "wb") as prv_file:
                pub_file.write(pub_pem)
                prv_file.write(prv_pem)

    def _load_keys(self):
        if not self._pub_file.exists() or not self._prv_file.exists():
            raise RSAKeysNotFoundError

        private_key = public_key = None
        with open(self._prv_file, "rb") as prv_file:
            with open(self._pub_file, "rb") as pub_file:
                private_key = serialization.load_pem_private_key(
                    prv_file.read(), password=None, backend=default_backend()
                )
                public_key = serialization.load_pem_public_key(
                    pub_file.read(), backend=default_backend()
                )

        return public_key, private_key


class MessageCryptoError(Exception):
    """Base class for all message errors"""


class MessageCryptoInvalidRecipientKey(MessageCryptoError):
    """Error when the recipient's private key is invalid"""


class MessagePOWError(MessageCryptoError):
    """Error when the message has invalid proof of work"""


class MessageDecodingError(MessageCryptoError):
    """Error when the message has invalid structure"""


class MessageDecryptionError(MessageCryptoError):
    """Error when you are not the proper recipient of the message"""


class MessageVerificationError(MessageCryptoError):
    """Error when message's sender and author are not the same"""


class MessageCrypto:
    def __init__(self, keys_provider):
        self.keys = keys_provider

    def get_ciphergram(self, user_key, text):
        try:
            user_public_key = serialization.load_pem_public_key(
                bytes.fromhex(user_key),
                backend=default_backend()
            )
        except Exception:
            raise MessageCryptoInvalidRecipientKey

        ct, ck, s, t = self._get_ciphergram(user_public_key, text)
        proof = proof_of_work.compute_pow(
            (ct+ck+s+str(t)).encode("utf-8")
        )
        return EncryptedMessage(
            ciphertext=ct,
            cipherkey=ck,
            signature=s,
            proof=proof,
            timestamp=t
        )

    def _get_ciphergram(self, user_public_key, text):
        current_time = int(time.time())
        secret_key = Fernet.generate_key()
        fernet = Fernet(secret_key)
        message = [
            self.keys.pub_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).hex(),
            text.encode("utf-8").hex(),
        ]
        ciphertext = fernet.encrypt(json.dumps(message).encode("utf-8"))
        cipherkey = user_public_key.encrypt(
            secret_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        signature = self.keys.prv_key.sign(
            ciphertext + cipherkey,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )

        return (ciphertext.hex(), cipherkey.hex(),
                signature.hex(), current_time, )

    def get_plaintext(self, ciphergram):
        footprint = (
            ciphergram.ciphertext + ciphergram.cipherkey +
            ciphergram.signature + str(ciphergram.timestamp)
        )
        if not proof_of_work.check_pow_valid(
            footprint.encode("utf-8"), ciphergram.proof
        ):
            raise MessagePOWError

        return self._get_plaintext(ciphergram)

    def _get_plaintext(self, ciphergram):
        try:
            ciphertext = bytes.fromhex(ciphergram.ciphertext)
            cipherkey = bytes.fromhex(ciphergram.cipherkey)
            signature = bytes.fromhex(ciphergram.signature)
        except Exception:
            raise MessageDecodingError

        key = self._decrypt_cipherkey(cipherkey)
        text = self._decrypt_ciphertext(key, ciphertext)

        try:
            node_pub_key_str, message = json.loads(text.decode("utf-8"))
            message = bytes.fromhex(message)
            node_pub_key = serialization.load_pem_public_key(
                bytes.fromhex(node_pub_key_str),
                backend=default_backend()
            )
        except Exception:
            raise MessageDecodingError

        self._verify_signature(node_pub_key, ciphertext, cipherkey, signature)
        return node_pub_key_str, message.decode("utf-8")

    def _decrypt_cipherkey(self, cipherkey):
        try:
            key = self.keys.prv_key.decrypt(
                cipherkey,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
        except ValueError:
            raise MessageDecryptionError

        return key

    def _decrypt_ciphertext(self, key, ciphertext):
        try:
            text = Fernet(key).decrypt(ciphertext)
        except Exception as exc:
            raise MessageDecryptionError from exc

        return text

    def _verify_signature(self, node_pub_key, ciphertext, cipherkey, signature):
        try:
            node_pub_key.verify(
                signature,
                ciphertext + cipherkey,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
        except Exception as exc:
            raise MessageVerificationError from exc
