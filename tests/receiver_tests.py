import json
import pprint
import pathlib
import dataclasses
import unittest
from unittest.mock import Mock, patch

from . import testing_utils

from securetalks import crypto
from securetalks import receiver


class TestReceiver(unittest.TestCase):
    def setUp(self):
        self.sender_keys = crypto.KeysProvider(
            pathlib.Path.cwd() / "tests" / "sender_keys"
        )
        self.recver_keys = crypto.KeysProvider(
            pathlib.Path.cwd() / "tests" / "receiver_keys"
        )
        self.sender_mcrypto = crypto.MessageCrypto(
            self.sender_keys, 60*60
        )
        self.recver_mcrypto = crypto.MessageCrypto(
            self.recver_keys, 60*60
        )
        ciphergram = self.sender_mcrypto.get_ciphergram(
            self.recver_keys.pub_key_str, "Message from sender"
        )
        self.message = dict(
            type="ciphergram",**dataclasses.asdict(ciphergram)
        )


    def test_handle_ciphergram_store_message(self):
        self.receiver = receiver.Receiver(
            Mock(), Mock(), Mock(), self.recver_mcrypto, Mock()
        )
        with patch.object(self.receiver, "_store_as_ciphergram") as mock_sc:
            with patch.object(self.receiver, "_store_as_message") as mock_sm:
                self.receiver._handle_ciphergram_message("1.1.1.1", self.message)
                mock_sc.assert_not_called()
                mock_sm.assert_called()

    def test_handle_ciphergram_store_ciphergram(self):
        self.receiver = receiver.Receiver(
            Mock(), Mock(), Mock(), self.sender_mcrypto, Mock()
        )
        with patch.object(self.receiver, "_store_as_ciphergram") as mock_sc:
            with patch.object(self.receiver, "_store_as_message") as mock_sm:
                self.receiver._handle_ciphergram_message("1.1.1.1", self.message)
                mock_sc.assert_called()
                mock_sm.assert_not_called()

    def test_handle_ciphergram_dont_store_crypto_error(self):
        message = self.message.copy()
        message["proof"] = 1
        self.receiver = receiver.Receiver(
            Mock(), Mock(), Mock(), self.recver_mcrypto, Mock()
        )
        with patch.object(self.receiver, "_store_as_ciphergram") as mock_sc:
            with patch.object(self.receiver, "_store_as_message") as mock_sm:
                self.receiver._handle_ciphergram_message("1.1.1.1", message)
                mock_sc.assert_not_called()
                mock_sm.assert_not_called()

    def test_handle_ciphergram_dont_store_expired(self):
        self.receiver = receiver.Receiver(
            Mock(), Mock(), Mock(), self.recver_mcrypto, Mock()
        )
        self.receiver.ttl = 0
        with patch.object(self.receiver, "_store_as_ciphergram") as mock_sc:
            with patch.object(self.receiver, "_store_as_message") as mock_sm:
                self.receiver._handle_ciphergram_message("1.1.1.1", self.message)
                mock_sc.assert_not_called()
                mock_sm.assert_not_called()