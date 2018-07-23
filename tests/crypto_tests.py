import pprint
import pathlib
import dataclasses
import unittest
from unittest.mock import Mock, patch

from . import testing_utils

from securetalks import crypto


class TestMessageCrypto(unittest.TestCase):
    def setUp(self):
        self.sender_keys = crypto.KeysProvider(
            pathlib.Path.cwd() / "tests" / "sender_keys"
        )
        self.recver_keys = crypto.KeysProvider(
            pathlib.Path.cwd() / "tests" / "receiver_keys"
        )
        self.sender_mcrypto = crypto.MessageCrypto(
            self.sender_keys
        )
        self.recver_mcrypto = crypto.MessageCrypto(
            self.recver_keys
        )

    def test_can_decrypt_message(self):
        text = "This is an encrypted message from sender."
        ciphergram = self.sender_mcrypto.get_ciphergram(
            self.recver_keys.pub_key_str, text
        )
        user_pub_key, plaintext = self.recver_mcrypto.get_plaintext(
            ciphergram
        )

        self.assertEqual(plaintext, text)
        self.assertEqual(user_pub_key, self.sender_keys.pub_key_str)

    def test_invalid_receiver_pub_key(self):
        user_pub_key = self.recver_keys.pub_key_str + "invalid"

        with self.assertRaises(crypto.MessageCryptoInvalidRecipientKey):
            self.sender_mcrypto.get_ciphergram(user_pub_key, "Text")

    def test_invalid_pow(self):
        text = "This is an encrypted message from sender."
        ciphergram = self.sender_mcrypto.get_ciphergram(
            self.recver_keys.pub_key_str, text
        )
        ciphergram = dataclasses.replace(ciphergram, proof=1)
        with self.assertRaises(crypto.MessagePOWError):
            self.recver_mcrypto.get_plaintext(ciphergram)

    def test_message_decoding_error_bytes(self):
        text = "This is an encrypted message from sender."
        ciphergram = self.sender_mcrypto.get_ciphergram(
            self.recver_keys.pub_key_str, text
        )
        ciphergram = dataclasses.replace(ciphergram, cipherkey="invalid_type")
        with self.assertRaises(crypto.MessagePOWError):
            self.recver_mcrypto.get_plaintext(ciphergram)

    def test_decryption_error_wrong_private_key(self):
        text = "This is an encrypted message from sender."
        ciphergram = self.sender_mcrypto.get_ciphergram(
            self.recver_keys.pub_key_str, text
        )
        with self.assertRaises(crypto.MessageDecryptionError):
            self.sender_mcrypto.get_plaintext(ciphergram)

    @patch("securetalks.crypto.MessageCrypto._decrypt_cipherkey")
    def test_decryption_error_wrong_fernet_key(self, mock_decrypt):
        mock_decrypt.return_value = b"ff"
        text = "This is an encrypted message from sender."
        ciphergram = self.sender_mcrypto.get_ciphergram(
            self.recver_keys.pub_key_str, text
        )

        with self.assertRaises(crypto.MessageDecryptionError):
            self.recver_mcrypto.get_plaintext(ciphergram)

    @patch("securetalks.crypto.proof_of_work.check_pow_valid")
    def test_verification_error(self, mock_check_pow):
        mock_check_pow.return_value = True
        origin_text = "From Paul"
        origin_ciphergram = self.sender_mcrypto.get_ciphergram(
            self.recver_keys.pub_key_str, origin_text
        )
        modified_text = "From Mike"
        modified_ciphergram = self.sender_mcrypto.get_ciphergram(
            self.recver_keys.pub_key_str, modified_text
        )

        ciphergram = dataclasses.replace(
            origin_ciphergram,
            ciphertext=modified_ciphergram.ciphertext,
            cipherkey=modified_ciphergram.cipherkey,
            proof=modified_ciphergram.proof,
            timestamp=modified_ciphergram.timestamp
        )

        with self.assertRaises(crypto.MessageVerificationError):
            self.recver_mcrypto.get_plaintext(ciphergram)
