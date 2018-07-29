import time
import json
import pprint
import pathlib
import dataclasses
import unittest
from unittest.mock import Mock, patch

from . import testing_utils

from securetalks import crypto
from securetalks import receiver


@patch("securetalks.receiver.LowLevelReceiver")
class TestReceiver(unittest.TestCase):
    def setUp(self):
        self.sender_keys = crypto.KeysProvider(
            pathlib.Path.cwd() / "tests" / "sender_keys"
        )
        self.recver_keys = crypto.KeysProvider(
            pathlib.Path.cwd() / "tests" / "receiver_keys"
        )
        self.sender_mcrypto = crypto.MessageCrypto(self.sender_keys)
        self.recver_mcrypto = crypto.MessageCrypto(self.recver_keys)
        ciphergram = self.sender_mcrypto.get_ciphergram(
            self.recver_keys.pub_key_str, "Message from sender"
        )
        self.message = dict(
            type="ciphergram",
            server_port=8001,
            **dataclasses.asdict(ciphergram)
        )


    def test_handle_ciphergram_store_message(self, llr_mock):
        self.receiver = receiver.Receiver(
            Mock(), Mock(), Mock(), self.recver_mcrypto, Mock(), Mock(), Mock()
        )
        with patch.object(self.receiver, "_store_as_ciphergram") as mock_sc:
            with patch.object(self.receiver, "_store_as_message") as mock_sm:
                self.receiver._handle_ciphergram_message("1.1.1.1", self.message)
                mock_sc.assert_not_called()
                mock_sm.assert_called()

    def test_handle_ciphergram_store_ciphergram(self, llr_mock):
        self.receiver = receiver.Receiver(
            Mock(), Mock(), Mock(), self.sender_mcrypto, Mock(), Mock(), Mock()
        )
        with patch.object(self.receiver, "_store_as_ciphergram") as mock_sc:
            with patch.object(self.receiver, "_store_as_message") as mock_sm:
                self.receiver._handle_ciphergram_message("1.1.1.1", self.message)
                mock_sc.assert_called()
                mock_sm.assert_not_called()

    def test_handle_ciphergram_dont_store_crypto_error(self, llr_mock):
        message = self.message.copy()
        message["proof"] = 1
        self.receiver = receiver.Receiver(
            Mock(), Mock(), Mock(), self.recver_mcrypto, Mock(), Mock(), Mock()
        )
        with patch.object(self.receiver, "_store_as_ciphergram") as mock_sc:
            with patch.object(self.receiver, "_store_as_message") as mock_sm:
                self.receiver._handle_ciphergram_message("1.1.1.1", message)
                mock_sc.assert_not_called()
                mock_sm.assert_not_called()

    def test_handle_ciphergram_dont_store_expired(self, llr_mock):
        curr_time = time.time()
        self.receiver = receiver.Receiver(
            Mock(), Mock(), Mock(), self.recver_mcrypto, Mock(), Mock(), Mock()
        )
        self.receiver.ttl = 0
        with patch.object(self.receiver, "_store_as_ciphergram") as mock_sc:
            with patch.object(self.receiver, "_store_as_message") as mock_sm:
                with patch("time.time") as mock_time:
                    mock_time.return_value = curr_time

                    self.receiver._handle_ciphergram_message(
                        "1.1.1.1", self.message
                    )

                    mock_time.assert_called()
                    mock_sc.assert_not_called()
                    mock_sm.assert_not_called()