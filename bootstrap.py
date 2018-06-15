import logging
import multiprocessing
import pathlib

import secrets

import rsa
import pyaes

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class RSAKeysNotFoundError(IOError):
    pass


class KeysProvider:
    def __init__(self, data_dir_name=".securetalks"):
        data_dir = pathlib.Path.home() / data_dir_name
        data_dir.mkdir(exist_ok=True)
        self.key_files = (
            data_dir / "pub.pem",
            data_dir / "prv.pem",
            data_dir / "pub_sign.pem",
            data_dir / "prv_sign.pem",
        )

    def _generate_keys(self):
        nprocs = multiprocessing.cpu_count()
        pub_key, prv_key = rsa.newkeys(4096, poolsize=nprocs)
        pub_sign_key, prv_sign_key = rsa.newkeys(4096, poolsize=nprocs)

        return pub_key, prv_key, pub_sign_key, prv_sign_key

    def _save_keys(self, keys):
        for key, key_file in zip(keys, self.key_files):
            with open(key_file, "wb") as file:
                out_data = key.save_pkcs1()
                file.write(out_data)

    def _load_keys(self):
        if not all(key.exists() for key in self.key_files):
            logger.info("RSA keys not found")
            raise RSAKeysNotFoundError

        keys = []
        public_flag = True
        for key_file in self.key_files:
            with open(key_file, "rb") as file:
                key_data = file.read()
                if public_flag:
                    keys.append(rsa.PublicKey.load_pkcs1(key_data))
                else:
                    keys.append(rsa.PrivateKey.load_pkcs1(key_data))

                public_flag = not public_flag

        return keys

    def get_keys(self):
        keys = None
        try:
            keys = self._load_keys()
            logger.info("Keys are loaded")
        except (RSAKeysNotFoundError, ValueError):
            logger.exception("An error occurred on reading keys")
            keys = self._generate_keys()
            self._save_keys(keys)
            logger.info("Keys are generated and saved")

        return keys


class DecryptionError(rsa.DecryptionError):
    pass

class MessageCrypto:

    def __init__(self, pub_key, prv_key, pub_sign_key, prv_sign_key):
        self.pub_key = pub_key
        self.prv_key = prv_key
        self.pub_sign_key = pub_sign_key
        self.prv_sign_key = prv_sign_key


    def encrypt_text(self, text, recv_pub_key):
        text_bytes = text.encode("utf-8")
        key = secrets.token_bytes(32)
        aes = pyaes.AESModeOfOperationCTR(key)
        ciphertext: bytes = aes.encrypt(text_bytes)
        cipherkey: bytes = rsa.encrypt(key, recv_pub_key)

        return ciphertext, cipherkey

    def decrypt_text(self, ciphertext, cipherkey):
        try:
            key = rsa.decrypt(cipherkey, self.prv_key)
        except rsa.DecryptionError:
            raise DecryptionError
        aes = pyaes.AESModeOfOperationCTR(key)
        decrypted = aes.decrypt(ciphertext)

        return decrypted.decode("utf-8")


        

if __name__ == "__main__":
    kp = KeysProvider()
    keys = kp.get_keys()

    mc = MessageCrypto(*keys)
    ciphertext, cipherkey = mc.encrypt_text(
    """Электричка — это электропоезд. Ласточка и Сапсан, по идее, электрички, но при этом они поезда дальнего следования (а Ласточка бывает ещё и пригородного). Поэтому когда мы говорим про электричку, то обычно имеем в виду поезд пригородного сообщения с билетом без фиксации мест. То есть где можно стоять. Но не всё из этого множества электропоезда, потому что бывают рельсовые автобусы, автомотрисы и дизельные поезда — например, между станциями Кривандино и Рязановка как раз ходит РА-1.Есть электрички с местами, но это среднее между обычным поездом и электричкой. Там обычно все льготы на пригородные поезда. Но при этом продаётся билет на места через кассу, как на дальний.Бывают электрички с вагонами повышенной комфортности: вы садитесь в электричку и можете зайти в специальный вагон, заплатить сбор прямо внутри электрички. Там можно поспать на свежем белье или сесть в более мягкое и большое кресло. Так, например, в некоторых поездах на Горьковской железной дороге. """    
    , mc.pub_key)
    print( mc.decrypt_text(ciphertext, cipherkey) )


    # start_server(port)
    # known_nodes = load_known_nodes()
    # request_my_messages(known_nodes)
