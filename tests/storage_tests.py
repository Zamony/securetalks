import time
import shutil
import pathlib
import sqlite3
import unittest

from securetalks import storage
from securetalks import orm


def setup_db():
    db_path = pathlib.Path(__file__).parent / "test.db"
    if not db_path.exists():
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.executescript(storage.Storage.storage_init_script)
        conn.close()

    db_name = str(db_path.parent / "test_active.db")
    shutil.copyfile(db_path, db_name)
    return db_name
    

class TestNodes(unittest.TestCase):
    def setUp(self):
        self._db_name = setup_db()
        self._conn = sqlite3.connect(self._db_name)
        self._cursor = self._conn.cursor()
        self.nodes = storage.Nodes(self._conn, self._cursor)

    def tearDown(self):
        self._conn.close()
        pathlib.Path(self._db_name).unlink()

    def test_update_node_activity(self):
        delta = 2
        node = orm.Node("a")
        self.nodes.update_node_activity(node)
        self._cursor.execute(
            "SELECT last_activity FROM Nodes WHERE node_id=?",
            (node.node_id, )
        )

        last_activity_db, = self._cursor.fetchone()
        curr_time = time.time()

        self.assertLessEqual(curr_time - last_activity_db, delta)
        self.assertLessEqual(curr_time - node.last_activity, delta)

    def test_update_node_activity_failed(self):
        node = orm.Node("not_found_node")
        with self.assertRaises(orm.NodeNotFoundError):
            self.nodes.update_node_activity(node)

    def test_increment_unread_count(self):
        node = orm.Node("a")
        self.nodes.increment_node_unread(node)
        self._cursor.execute(
            "SELECT unread_count FROM Nodes WHERE node_id=?",
            (node.node_id, )
        )

        unread_count, = self._cursor.fetchone()
        self.assertEqual(node.unread_count, 1)
        self.assertEqual(unread_count, 1)

    def test_set_node_unread_to_zero(self):
        node = orm.Node("b")
        self.nodes.set_node_unread_to_zero(node)
        self._cursor.execute(
            "SELECT unread_count FROM Nodes WHERE node_id=?",
            (node.node_id, )
        )

        unread_count, = self._cursor.fetchone()
        self.assertEqual(node.unread_count, 0)
        self.assertEqual(unread_count, 0)

    def test_check_node_exists_true(self):
        node = orm.Node("b")
        node_exists = self.nodes.check_node_exists(node)
        self.assertTrue(node_exists)

    def test_check_node_exists_false(self):
        node = orm.Node("d")
        node_exists = self.nodes.check_node_exists(node)
        self.assertFalse(node_exists)

    def test_add_node(self):
        node = orm.Node("e")
        self.nodes.add_node(node)
        self.assertTrue(self.nodes.check_node_exists(node))

    def test_add_node_failed(self):
        node = orm.Node("c")
        with self.assertRaises(orm.NodeAlreadyExistsError):
            self.nodes.add_node(node)

    def test_delete_node(self):
        node = orm.Node("a")
        self.nodes.delete_node(node)
        self.assertFalse(self.nodes.check_node_exists(node))

    def test_get_node_by_id(self):
        node = self.nodes.get_node_by_id("c")
        self.assertEqual(node.node_id, "c")
        self.assertEqual(node.last_activity, 3000)
        self.assertEqual(node.unread_count, 2)
        self.assertEqual(node.alias, "Steve Jobs")

class TestMessages(unittest.TestCase):
    def setUp(self):
        self._db_name = setup_db()
        self._conn = sqlite3.connect(self._db_name)
        self._cursor = self._conn.cursor()
        self.messages = storage.Messages(self._conn, self._cursor)

    def tearDown(self):
        self._conn.close()
        pathlib.Path(self._db_name).unlink()

    def test_add_message(self):
        message = orm.Message("receiver", "message to a", False, 1000)
        self.messages.add_message(message)
        self._cursor.execute(
            "SELECT * FROM Messages WHERE node_id=?",
            (message.node_id, )
        )

        node_id, text, to_me, timestamp = self._cursor.fetchone()
        self.assertEqual(node_id, message.node_id)
        self.assertEqual(text, message.text)
        self.assertFalse(to_me)
        self.assertEqual(timestamp, message.timestamp)

    def test_get_messages_limit_none_offset_none(self):
        node = orm.Node("c")
        messages = self.messages.get_messages(node)

        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0].node_id, node.node_id)
        self.assertEqual(messages[0].text, "message3 c to me")
        self.assertTrue(messages[0].to_me)
        self.assertEqual(messages[0].timestamp, 6000)

    def test_get_messages_limit_offset(self):
        node = orm.Node("c")
        messages = self.messages.get_messages(node, limit=3, offset=1)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].node_id, node.node_id)
        self.assertEqual(messages[0].text, "message2 c from me")
        self.assertFalse(messages[0].to_me)
        self.assertEqual(messages[0].timestamp, 5000)

    def test_get_messages_limit(self):
        node = orm.Node("c")
        messages = self.messages.get_messages(node, limit=2)
        self.assertEqual(len(messages), 2)

    def test_delete_messages(self):
        node = orm.Node("b")
        old_messages = self.messages.get_messages(node)
        self.messages.delete_messages(node)
        new_messages = self.messages.get_messages(node)

        self.assertEqual(len(old_messages), 2)
        self.assertEqual(len(new_messages), 0)

