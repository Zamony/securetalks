import time
import shutil
import pathlib
import sqlite3
import unittest

from securetalks import storage
from securetalks import orm


class TestNodes(unittest.TestCase):
    def setUp(self):
        db_path = pathlib.Path(__file__).parent / "test.db"
        if not db_path.exists():
            self._create_empty_db(db_path)

        self._db_name = str(db_path.parent / "test_active.db")
        shutil.copyfile(db_path, self._db_name)

        self._conn = sqlite3.connect(self._db_name)
        self._cursor = self._conn.cursor()

        self.nodes = storage.Nodes(self._conn, self._cursor)

    def _create_empty_db(self, db_path):
        db_name = str(db_path)
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.executescript(storage.Storage.storage_init_script)
        conn.close()

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