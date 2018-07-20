import pprint
import pathlib
import unittest

from . import testing_utils

from securetalks import presentor
from securetalks import storage

class TestPresentor(unittest.TestCase):
    def setUp(self):
        self.db_name = testing_utils.setup_db()
        self.storage = storage.Storage(self.db_name, 60*60*60)
        self.presentor = presentor.Presentor(self.storage)

    def tearDown(self):
        self.storage.close()
        pathlib.Path(self.db_name).unlink()

    def test_get_dialogs(self):
        dialogs = self.presentor.get_dialogs()
        
        self.assertEqual(len(dialogs), 3)
        self.assertEqual(dialogs[0]["talking_to"], "c")
        self.assertEqual(dialogs[0]["last_updated"], 3000)
        self.assertEqual(dialogs[0]["unread_count"], 2)
        self.assertEqual(dialogs[0]["alias"], "Steve Jobs")
        self.assertEqual(len(dialogs[0]["messages"]), 3)
        self.assertEqual(
            dialogs[0]["messages"][0],
            dict(
                talking_to="c", to_me=True,
                text="message3 c to me", timestamp=6000
            )
        )
