import pprint
import pathlib
import unittest
from unittest.mock import Mock

from . import testing_utils

from securetalks import presentor
from securetalks import storage

class TestPresentor(unittest.TestCase):
    def setUp(self):
        self.db_name = testing_utils.setup_db()
        self.storage = storage.Storage(self.db_name, 60*60*60)
        self.presentor = presentor.Presentor(Mock(), Mock(), self.storage)

    def tearDown(self):
        pathlib.Path(self.db_name).unlink()

    def test_get_dialogs(self):
        dialogs = self.presentor.get_dialogs()
        
        self.assertEqual(len(dialogs), 3)
        self.assertEqual(dialogs[0]["node_id"], "c")
        self.assertEqual(dialogs[0]["last_activity"], 3000)
        self.assertEqual(dialogs[0]["unread_count"], 2)
        self.assertEqual(dialogs[0]["alias"], "Steve Jobs")
        self.assertEqual(len(dialogs[0]["messages"]), 3)
        self.assertEqual(
            dialogs[0]["messages"][0],
            dict(
                node_id="c", to_me=False, sender_timestamp=1000,
                text="message1 c from me", timestamp=1000,
                last_activity=3000, unread_count=2, alias="Steve Jobs"
            )
        )
