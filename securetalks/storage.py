import pathlib
import sqlite3
import time

from . import orm

class Nodes:
    def __init__(self, conn, cursor):
        self._conn = conn
        self._cursor = cursor

    def update_node_activity(self, node):
        if not self.check_node_exists(node):
            raise orm.NodeNotFoundError
        node.update_activity()
        self._cursor.execute(
            "UPDATE `Nodes` SET `last_activity`=? WHERE `node_id`=?",
            (node.last_activity, node.node_id)
        )
        self._conn.commit()

    def increment_node_unread(self, node):
        if not self.check_node_exists(node):
            raise orm.NodeNotFoundError
        node.increment_unread()
        self._cursor.execute(
            """
            UPDATE `Nodes` SET `unread_count` = `unread_count`+1
            WHERE `node_id`=?
            """,
            (node.node_id,)
        )
        self._conn.commit()

    def set_node_unread_to_zero(self, node):
        if not self.check_node_exists(node):
            raise orm.NodeNotFoundError
        node.set_unread_to_zero()
        self._cursor.execute(
            """
            UPDATE `Nodes` SET `unread_count` = 0
            WHERE `node_id`=?
            """,
            (node.node_id,)
        )
        self._conn.commit()

    def check_node_exists(self, node):
        self._cursor.execute(
            """
            SELECT EXISTS(SELECT 1 FROM `Nodes`
            WHERE node_id=? LIMIT 1)
            """,
            (node.node_id,)
        )
        node_exists, = self._cursor.fetchone()
        return True if node_exists else False

    def add_node(self, node):
        if self.check_node_exists(node):
            raise orm.NodeAlreadyExistsError
        self._cursor.execute(
            "INSERT INTO `Nodes` VALUES (?, ?, ?, ?)",
            (
                node.node_id, node.last_activity,
                node.unread_count, node.alias
            ),
        )
        self._conn.commit()

    def delete_node(self, node):
        if not self.check_node_exists(node):
            raise orm.NodeNotFoundError
        self._cursor.execute(
            "DELETE FROM `Nodes` WHERE `node_id`=?",
            (node.node_id,)
        )
        self._conn.commit()

    def get_node_by_id(self, node_id):
        if not self.check_node_exists(orm.Node(node_id)):
            raise orm.NodeNotFoundError
        self._cursor.execute(
            "SELECT * FROM `Nodes` WHERE `node_id`=?",
            (node_id,)
        )
        node = self._cursor.fetchone()
        return orm.Node(*node)

    def list_all(self):
        self._cursor.execute(
            "SELECT * FROM `Nodes` ORDER BY `last_activity`"
        )
        return [orm.Node(*node) for node in self._cursor.fetchall()]


class Messages:
    def __init__(self, conn, cursor):
        self._conn = conn
        self._cursor = cursor

    def add_message(self, message):
        self._cursor.execute(
            "INSERT INTO `Messages` VALUES (?, ?, ?, ?)",
            (
                message.node_id,
                message.text,
                1 if message.to_me else 0, message.timestamp
            )
        )
        self._conn.commit()

    def get_messages(self, node, limit=None, offset=None):
        if limit is not None and offset is not None:
            self._cursor.execute(
                """
                SELECT * FROM `Messages` WHERE `node_id`=?
                ORDER BY `timestamp` DESC LIMIT ? OFFSET ?;
                """,
                (node.node_id, limit, offset)
            )
        elif limit is None and offset is None:
            self._cursor.execute(
                """
                SELECT * FROM `Messages` WHERE `node_id`=?
                ORDER BY `timestamp` DESC;
                """,
                (node.node_id, )
            )
        elif limit is not None:
            self._cursor.execute(
                """
                SELECT * FROM `Messages` WHERE `node_id`=?
                ORDER BY `timestamp` DESC LIMIT ?;
                """,
                (node.node_id, limit)
            )
        else:
            raise sqlite3.Error

        return [
            orm.Message(nid, txt, True if to_me else False, tm)
            for nid, txt, to_me, tm in self._cursor.fetchall()
        ]

    def delete_message(self, node):
        self._cursor.execute(
            "DELETE FROM `Messages` WHERE `node_id`=?",
            (node.node_id, )
        )
        self._cursor.commit()


class Ciphergrams:
    def __init__(self, conn, cursor):
        self._conn = conn
        self._cursor = cursor

    def delete_old_ones(self, timespan):
        self._cursor.execute(
            "DELETE FROM `Ciphergrams` WHERE ? - `timestamp` > ?",
            (
                int(time.time()),
                timespan,
            )
        )
        self._conn.commit()

    def add_ciphergram(self, ciphergram):
        self._cursor.execute(
            "INSERT INTO `Ciphergrams` VALUES (?, ?)",
            (ciphergram.content, ciphergram.timestamp)
        )
        self._conn.commit()

    def list_all(self):
        self._cursor.execute("SELECT * FROM `Ciphergrams`")
        return [orm.Ciphergram(*cph) for cph in self._cursor.fetchall()]


class IPAddresses:
    def __init__(self, conn, cursor):
        self._conn = conn
        self._cursor = cursor

    def delete_old_ones(self, timespan):
        self._cursor.execute(
            "DELETE FROM `IPAddresses` WHERE ? - `last_activity` > ?",
            (
                int(time.time()), timespan
            )
        )
        self._conn.commit()

    def add_ipaddress(self, ipaddress):
        self._cursor.execute(
            "INSERT INTO `IPAddresses` VALUES (?, ?)",
            (ipaddress.address, ipaddress.last_activity)
        )
        self._conn.commit()

    def update_ipaddress(self, ipaddress):
        ipaddress.update_activity()
        self._cursor.execute(
            """
            UPDATE `Nodes` SET `last_activity`=? WHERE `address`=?
            """,
            (ipaddress.last_activity, ipaddress.address)
        )
        self._conn.commit()

    def list_all(self):
        self._cursor.execute("SELECT * FROM `IPAddresses`")
        return [orm.IPAddress(*ip) for ip in self._cursor.fetchall()]


class Storage:

    storage_init_script = """
        CREATE TABLE `IPAddresses` (
            `address`	TEXT NOT NULL,
            `last_activity`	INTEGER NOT NULL,
            PRIMARY KEY(address)
        );
        CREATE TABLE `Ciphergrams` (
            `content`	TEXT NOT NULL,
            `timestamp`	INTEGER NOT NULL
        );
        CREATE TABLE `Nodes` (
            `node_id`	TEXT NOT NULL,
            `last_activity`	INTEGER NOT NULL,
            `unread_count`	INTEGER NOT NULL DEFAULT 0,
            `alias`	TEXT,
            PRIMARY KEY(node_id)
        );
        CREATE TABLE `Messages` (
            `node_id`	TEXT NOT NULL,
            `text`	TEXT NOT NULL,
            `to_me`	INTEGER NOT NULL DEFAULT 0,
            `timestamp`	INTEGER NOT NULL,
            PRIMARY KEY(node_id)
        );
    """

    def __init__(self, db_path, ttl):
        self._ttl = int(ttl)
        self._conn = sqlite3.connect(str(db_path))
        self._cursor = self._conn.cursor()
        self._create_tables_if_needed()

        self.nodes = Nodes(self._conn, self._cursor)
        self.messages = Messages(self._conn, self._cursor)
        self.ciphergrams = Ciphergrams(self._conn, self._cursor)
        self.ipaddresses = IPAddresses(self._conn, self._cursor)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._conn.close()

    def _create_tables_if_needed(self):
        try:
            self._cursor.executescript(self.storage_init_script)
        except sqlite3.Error:
            pass

    def delete_old_data(self):
        self.ciphergrams.delete_old_ones(self._ttl)
        self.ipaddresses.delete_old_ones(self._ttl)


if __name__ == "__main__":
    db_path = pathlib.Path.home() / ".securetalks" / "db.sqlite3"
    two_days_secs = 60 * 60 * 24 * 2

    with Storage(db_path, two_days_secs) as storage:
        pass
