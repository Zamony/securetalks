import pathlib
import sqlite3
import time

from . import orm


class Nodes:
    def __init__(self, db_path):
        self.db_path = db_path

    def update_node_activity(self, node):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if not self.check_node_exists(node):
                raise orm.NodeNotFoundError

            node.update_activity()
            cursor.execute(
                "UPDATE `Nodes` SET `last_activity`=? WHERE `node_id`=?",
                (node.last_activity, node.node_id)
            )
            conn.commit()

    def increment_node_unread(self, node):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if not self.check_node_exists(node):
                raise orm.NodeNotFoundError

            node.increment_unread()
            cursor.execute(
                """
                UPDATE `Nodes` SET `unread_count` = `unread_count`+1
                WHERE `node_id`=?
                """,
                (node.node_id,)
            )
            conn.commit()

    def set_node_unread_to_zero(self, node):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if not self.check_node_exists(node):
                raise orm.NodeNotFoundError

            node.set_unread_to_zero()
            cursor.execute(
                """
                UPDATE `Nodes` SET `unread_count` = 0
                WHERE `node_id`=?
                """,
                (node.node_id,)
            )
            conn.commit()

    def check_node_exists(self, node):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT EXISTS(SELECT 1 FROM `Nodes`
                WHERE node_id=? LIMIT 1)
                """,
                (node.node_id,)
            )
            node_exists, = cursor.fetchone()

            return True if node_exists else False

    def add_node(self, node):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if self.check_node_exists(node):
                raise orm.NodeAlreadyExistsError

            cursor.execute(
                "INSERT INTO `Nodes` VALUES (?, ?, ?, ?)",
                (
                    node.node_id, node.last_activity,
                    node.unread_count, node.alias
                ),
            )
            conn.commit()

    def delete_node(self, node):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if not self.check_node_exists(node):
                raise orm.NodeNotFoundError

            cursor.execute(
                "DELETE FROM `Nodes` WHERE `node_id`=?",
                (node.node_id,)
            )
            conn.commit()

    def get_node_by_id(self, node_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if not self.check_node_exists(orm.Node(node_id)):
                raise orm.NodeNotFoundError

            cursor.execute(
                "SELECT * FROM `Nodes` WHERE `node_id`=?",
                (node_id,)
            )
            node = cursor.fetchone()
            return orm.Node(*node)

    def list_all(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM `Nodes` ORDER BY `last_activity` DESC"
            )
            return [orm.Node(*node) for node in cursor.fetchall()]


class Messages:
    def __init__(self, db_path):
        self.db_path = db_path

    def check_message_exists(self, message):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT EXISTS(SELECT 1 FROM `Messages`
                WHERE node_id=? AND text=? AND to_me=? AND sender_timestamp=?
                LIMIT 1)
                """,
                (
                    message.node_id,
                    message.text,
                    1 if message.to_me else 0,
                    message.sender_timestamp
                )
            )
            message_exists, = cursor.fetchone()
            return True if message_exists else False

    def add_message(self, message):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if self.check_message_exists(message):
                raise orm.MessageAlreadyExistsError
            
            cursor.execute(
                "INSERT INTO `Messages` VALUES (?, ?, ?, ?, ?)",
                (
                    message.node_id,
                    message.text,
                    1 if message.to_me else 0,
                    message.sender_timestamp,
                    message.timestamp
                )
            )
            conn.commit()

    def get_messages(self, node, limit=None, offset=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if limit is not None and offset is not None:
                cursor.execute(
                    """
                    SELECT * FROM `Messages` WHERE `node_id`=?
                    ORDER BY `timestamp` LIMIT ? OFFSET ?;
                    """,
                    (node.node_id, limit, offset)
                )
            elif limit is None and offset is None:
                cursor.execute(
                    """
                    SELECT * FROM `Messages` WHERE `node_id`=?
                    ORDER BY `timestamp`;
                    """,
                    (node.node_id, )
                )
            elif limit is not None:
                cursor.execute(
                    """
                    SELECT * FROM `Messages` WHERE `node_id`=?
                    ORDER BY `timestamp` LIMIT ?;
                    """,
                    (node.node_id, limit)
                )
            else:
                raise sqlite3.Error

            return [
                orm.Message(nid, txt, True if to_me else False, stm, tm)
                for nid, txt, to_me, stm, tm in cursor.fetchall()
            ]

    def delete_messages(self, node):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM `Messages` WHERE `node_id`=?",
                (node.node_id, )
            )
            conn.commit()


class Ciphergrams:
    def __init__(self, db_path):
        self.db_path = db_path

    def delete_expired(self, timespan):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM `Ciphergrams` WHERE ? - `timestamp` > ?",
                (
                    int(time.time()),
                    timespan,
                )
            )
            conn.commit()

    def check_ciphergram_exists(self, ciphergram):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT EXISTS(SELECT 1 FROM `Ciphergrams`
                WHERE content=? AND timestamp=? LIMIT 1)
                """,
                (ciphergram.content, ciphergram.timestamp)
            )
            node_exists, = cursor.fetchone()
            return True if node_exists else False

    def add_ciphergram(self, ciphergram):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if self.check_ciphergram_exists(ciphergram):
                raise orm.CiphergramAlreadyExistsError
            
            cursor.execute(
                "INSERT INTO `Ciphergrams` VALUES (?, ?)",
                (ciphergram.content, ciphergram.timestamp)
            )
            conn.commit()

    def list_all(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM `Ciphergrams`")
            return [orm.Ciphergram(*cph) for cph in cursor.fetchall()]


class IPAddresses:
    def __init__(self, db_path):
        self.db_path = db_path

    def check_address_exists(self, ipaddress):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT EXISTS(SELECT 1 FROM `IPAddresses`
                WHERE address=? AND port=? LIMIT 1)
                """,
                (ipaddress.address, ipaddress.port)
            )
            address_exists, = cursor.fetchone()
            return True if address_exists else False

    def delete_expired(self, timespan):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM `IPAddresses` WHERE ? - `last_activity` > ?",
                (
                    int(time.time()), timespan
                )
            )
            conn.commit()

    def add_address(self, ipaddress):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if self.check_address_exists(ipaddress):
                raise orm.IPAddressAlreadyExistsError
            
            cursor.execute(
                "INSERT INTO `IPAddresses` VALUES (?, ?, ?)",
                (ipaddress.address, ipaddress.port, ipaddress.last_activity)
            )
            conn.commit()

    def update_address(self, ipaddress):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if not self.check_address_exists(ipaddress):
                raise orm.IPAddressNotFoundError
            
            ipaddress.update_activity()
            cursor.execute(
                """
                UPDATE `IPAddresses` SET `last_activity`=?
                WHERE `address`=? AND `port`=?
                """,
                (ipaddress.last_activity, ipaddress.address, ipaddress.port)
            )
            conn.commit()

    def list_all(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM `IPAddresses`")
            return [orm.IPAddress(*ip) for ip in cursor.fetchall()]


class Storage:

    storage_init_script = """
        CREATE TABLE `IPAddresses` (
            `address`	TEXT NOT NULL,
            `port`	INTEGER NOT NULL,
            `last_activity`	INTEGER NOT NULL,
            PRIMARY KEY(address,port)
        );
        CREATE TABLE `Ciphergrams` (
            `content`	TEXT NOT NULL,
            `timestamp`	INTEGER NOT NULL,
            PRIMARY KEY(content,timestamp)
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
            `sender_timestamp`	INTEGER NOT NULL,
            `timestamp`	INTEGER NOT NULL
        );
    """

    def __init__(self, db_path, ttl):
        self._ttl = int(ttl)
        self._db_path = str(db_path)
        self._create_tables_if_needed()

        self.nodes = Nodes(self._db_path)
        self.messages = Messages(self._db_path)
        self.ciphergrams = Ciphergrams(self._db_path)
        self.ipaddresses = IPAddresses(self._db_path)

    def _create_tables_if_needed(self):
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.cursor()
                cursor.executescript(self.storage_init_script)
        except sqlite3.Error:
            pass

    def delete_expired_data(self):
        self.ciphergrams.delete_expired(self._ttl)
        self.ipaddresses.delete_expired(self._ttl)
