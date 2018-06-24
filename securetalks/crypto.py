import time
import json
import logging
import pathlib

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.fernet import Fernet

import proof_of_work


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class RSAKeysNotFoundError(IOError):
    """Error when keys aren't on the disk"""

class KeysProvider:
    def __init__(self, data_dir_name=".securetalks"):
        data_dir = pathlib.Path.home() / data_dir_name
        data_dir.mkdir(exist_ok=True)
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

class MessageParsingError(MessageCryptoError):
    """Error when the message has invalid structure"""

class MessageTimingError(MessageCryptoError):
    """Error when the message is too old to be accepted"""

class MessageDecryptionError(MessageCryptoError):
    """Error when you are not the proper recipient of the message"""

class MessageVerificationError(MessageCryptoError):
    """Error when message's sender and author are not the same"""

class MessageCrypto:
    def __init__(self, keys_provider, timespan_allowed):
        self.keys = keys_provider
        self.timespan_allowed = timespan_allowed

    def get_ciphergram(self, user_key, text):
        try:
            user_public_key = serialization.load_pem_public_key(
                bytes.fromhex(user_key),
                backend=default_backend()
            )
        except Exception:
            raise MessageCryptoInvalidRecipientKey

        inner_ciphergram = self._get_ciphergram(user_public_key, text)
        proof = proof_of_work.compute_pow(inner_ciphergram.encode("utf-8"))
        return json.dumps({
            "type": "ciphergram", "data": inner_ciphergram, "proof": proof
        })

    def _get_ciphergram(self, user_public_key, text):
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
            ciphertext,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )

        return json.dumps([
            int(time.time()), ciphertext.hex(), cipherkey.hex(), signature.hex()
        ])

    def get_plaintext(self, ciphergram):
        try:
            ciphergram_content = json.loads(ciphergram)
            inner_ciphergram = ciphergram_content["data"]
            proof = ciphergram_content["proof"]
        except Exception:
            raise MessageParsingError
        
        if not proof_of_work.check_pow_valid(
            inner_ciphergram.encode("utf-8"), proof
        ):
            raise MessagePOWError

        return self._get_plaintext(inner_ciphergram)

    def _get_plaintext(self, ciphergram):
        try:
            ctime, ciphertext, cipherkey, signature = json.loads(ciphergram)
            ciphertext = bytes.fromhex(ciphertext)
            cipherkey = bytes.fromhex(cipherkey)
            signature = bytes.fromhex(signature)
        except Exception:
            raise MessageParsingError

        self._check_ciphergram_not_old(ctime)

        key = self._decrypt_cipherkey(cipherkey)
        text = self._decrypt_ciphertext(key, ciphertext)

        try:
            node_pub_key_bytes, message = json.loads(text.decode("utf-8"))
            message = bytes.fromhex(message)
            node_pub_key_bytes = bytes.fromhex(node_pub_key_bytes)
            node_pub_key = serialization.load_pem_public_key(
                node_pub_key_bytes, backend=default_backend()
            )
        except Exception:
            raise MessageParsingError

        self._verify_signature(node_pub_key, ciphertext, signature)
        return node_pub_key, message.decode("utf-8")

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
        except (cryptography.fernet.InvalidToken, TypeError):
            raise MessageDecryptionError

        return text

    def _verify_signature(self, node_pub_key, ciphertext, signature):
        try:
            node_pub_key.verify(
                signature,
                ciphertext,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
        except cryptography.exceptions.InvalidSignature:
            raise MessageVerificationError

    def _check_ciphergram_not_old(self, ciphergram_time):
        if time.time() - ciphergram_time > self.timespan_allowed:
            raise MessageTimingError


if __name__ == "__main__":
    keys_provider = KeysProvider()
    crypto = MessageCrypto(keys_provider, 3600)
    message = """Пока вся страна обсуждает победу сборной над соотечественниками Бена Ладена, пенсионную реформу, средний палец Робби Уильямса и нежелание Саши Головина участвовать в псевдопатриотическом шабаше на «Первом канале», в тюрьме строгого режима «Камити» в кенийском городе Найроби для заключенных устроили свой «чемпионат мира по футболу». Мероприятие организовала местная церковь, которая, видимо, до сих пор верит, что футбол способен изменить людей. Но все довольны: маньяки — тем, что им разрешили побегать, а руководство тюрьмы — порядком.Система проста: заключенных разделили на 32 команды, имитирующие реальные сборные мундиаля. В итоге африканские наркоторговцы и рецидивисты были вынуждены косить под Игнашевича и Газинского. В самом прямом смысле этого слова, потому что матч-открытие в кенийской тюрьме между «Россией» и «Саудовской Аравией» завершился со счетом 5:0. В составе «России» даже нашелся свой Денис Черышев по имени Байрон Отиено: он тоже единственный из команды забил два гола. Только местный Черышев гораздо чернее и осужден за убийство. Неизвестно, по какому принципу отбирали игроков в команды и, вообще, старались ли священники соблюсти реальный баланс сил, чтобы рецидивисты из «Германии» играли лучше насильников из «Панамы». Если на такие мелочи внимание не обращалось, то у сборной России впервые появился реальный шанс выиграть мундиаль."""
    ciphergram = crypto.get_ciphergram(crypto.keys.pub_key_str, message)
    print(ciphergram)
    print()
    pub_key, decoded_message = crypto.get_plaintext(ciphergram)
    print(pub_key)
    print()
    print(decoded_message)
