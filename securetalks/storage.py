import time
import pathlib
import sqlite3

import orm

class Nodes:
    def __init__(self, conn, cursor):
        self._conn = conn
        self._cursor = cursor

    def update_node(self, node):
        self._cursor.execute("""
        UPDATE `Nodes` SET `last_activity`=? WHERE `node_id`=?
        """,
        (node.last_activity, node.node_id)
        )
        self._conn.commit()

    def increment_node_unread(self, node):
        self._cursor.execute("""
        UPDATE `Nodes` SET `unread_count` = `unread_count`+1
        WHERE `node_id`=?
        """,
        (node.node_id,)
        )            
        self._conn.commit()

    def check_node_exists(self, node):
        self._cursor.execute("""
        SELECT EXISTS(SELECT 1 FROM `Nodes`
        WHERE node_id=? LIMIT 1)
        """,
        (node.node_id,)
        )
        node_exists, = self._cursor.fetchone()
        return True if node_exists else False

    def add(self, node):
        self._cursor.execute(
        "INSERT INTO `Nodes` VALUES (?, ?, 0)",
        (node.node_id, node.last_activity, node.unread_count))
        )
        self._conn.commit()

    def delete(self, node):
        self._cursor.execute(
        "DELETE FROM `Nodes` WHERE `node_id`=?",
        (node.node_id,)
        )
        self._conn.commit()

    def get(self, node):
        self._cursor.execute(
            "SELECT * FROM `Nodes` WHERE `node_id`=?",
            (node.node_id, )   
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

    def add(self, message):
        self._cursor.execute(
            "INSERT INTO `Messages` VALUES (?, ?, ?, ?)",
            (
                message.node_id,
                message.text,
                1 if message.to_me else 0,
                message.timestamp
            )
        )
        self.conn.commit()

    def get(self, node, limit=None, offset=None):
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
            (node.node_id,)
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

        for node_id, text, to_me, timestamp in self._cursor.fetchone():
            yield orm.Message(
                node_id,
                text,
                True if to_me else False,
                timestamp
            )

    def delete(self, node):
        self._cursor.execute(
            "DELETE FROM `Messages` WHERE `node_id`=?,
            (node.node_id,)
        )
        self._cursor.commit()

class Ciphergrams:
    def __init__(self, conn, cursor):
        self._conn = conn
        self._cursor = cursor

    def delete_old_ones(self, timespan):
        self._cursor.execute(
            "DELETE FROM `Ciphergrams` WHERE ? - `timestamp` > ?",
            (int(time.time()), timespan)
        )
        self._conn.commit()

    def add(self, ciphergram):
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
            (int(time.time()), timespan)
        )
        self._conn.commit()

    def add(self, ipaddress):
        self._cursor.execute(
            "INSERT INTO `IPAddresses` VALUES (?, ?)",
            (ipaddress.address, ipaddress.last_activity)
        )
        self._conn.commit()

    def update_ipaddress(self, ipaddress):
        self._cursor.execute(
            """
            UPDATE `Nodes` SET `last_activity`=? WHERE `address`=?
            """,
            (ipaddress.last_activity, ipaddress.address)
        )
        self._conn.commit()

    def list_all(self):
        self._cursor.execute("SELECT * FROM `IPAddresses`")
        return [orm.IPAddress(*cph) for ip in self._cursor.fetchall()]

class Storage:
    def __init__(self, db_path, ttl):
        self._ttl = int(ttl)
        self._conn = sqlite3.connect(str(db_path))
        self._cursor = self._conn.cursor()
        self._create_tables_if_needed()

        self.nodes = Nodes(self._conn, self._cursor)
        self.messages = Messages(self._conn, self._cursor)
        self.ciphergrams = Ciphergrams(self._conn, self._cursor, self._ttl)
        self.ipaddresses = IPAddresses(self._conn, self._cursor, self._ttl)

    @property
    def known_addresses(self):
        self.cursor.execute("SELECT `ip_address` FROM `ip_addresses`")
        return (ip for ip, in self.cursor.fetchall())

    def add_known_address(self, ip_address):
        self.cursor.execute(
            "INSERT INTO `ip_addresses` VALUES (?, ?)", (ip_address, int(time.time()))
        )
        self.conn.commit()

    @property
    def ciphergrams(self):
        self.cursor.execute("SELECT `ciphergram`, `timestamp` FROM `ciphergrams`")
        return cursor.fetchall()

    def add_ciphergram(self, ciphergram):
        self.cursor.execute(
            "INSERT INTO `ciphergrams` VALUES (?, ?)", (ciphergram, int(time.time()))
        )
        self.conn.commit()

    @property
    def dialogs(self):
        self.cursor.execute("""
        SELECT `dialog_with`, `last_activity`, `unread_count` FROM `dialogs`
        """)
        return cursor.fetchall()

    def add_dialog(self, uid):
        self.cursor.execute(
            "INSERT INTO `dialogs` VALUES (?, ?, 0)",
            (uid, int(time.time()))
        )
        self.conn.commit()

    def increase_dialog_unread(self, uid, count=1):
        self.cursor.execute("""
        UPDATE `dialogs` SET `unread_count` = `unread_count`+?
        WHERE `dialog_with`=?
        """, (count, uid))
        self.conn.commit()

    def set_dialog_unrad_to_zero(self, uid):
        self.cursor.execute("""
        UPDATE `dialogs` SET `unread_count` = 0 WHERE `dialog_with`=?
        """, (uid,))
        self.conn.commit()

    def update_dialog_activity(self, uid):
        self.cursor.execute(
            "UPDATE `dialogs` SET `last_activity`=? WHERE `dialog_with`=?",
            (int(time.time()), uid)
        )
        self.conn.commit()

    def get_messages_from(self, who, limit=None, offset=None):
        if limit is not None and offset is not None:
            self.cursor.execute("""
            SELECT `text`, `from_me`, `timestamp` FROM `messages`
            WHERE `dialog_with`=? ORDER BY `timestamp` DESC LIMIT ? OFFSET ?;
            """, (who, limit, offset))
        elif limit is None and offset is None:
            self.cursor.execute("""
            SELECT `text`, `from_me`, `timestamp` FROM `messages`
            WHERE `dialog_with`=? ORDER BY `timestamp` DESC;
            """, (who,))
        elif limit is not None:
            self.cursor.execute("""
            SELECT `text`, `from_me`, `timestamp` FROM `messages`
            WHERE `dialog_with`=? ORDER BY `timestamp` DESC LIMIT ?;
            """, (who, limit))
        else:
            raise sqlite3.Error

        return self.cursor.fetchall()

    def add_message_from(who, text):
        self.cursor.execute(
            "INSERT INTO `messages` VALUES (?, ?, ?)",
            (who, text, int(time.time()))
        )
        self.conn.commit()        
        

    def _create_tables_if_needed(self):
        try:
            self.cursor.executescript(
            """
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
            )
        except sqlite3.Error:
            pass

    def delete_old_data(self):
        curr_time = int(time.time())
        self.cursor.execute(
            "DELETE FROM `ciphergrams` WHERE ? - `timestamp` > ?", (curr_time, self.ttl)
        )
        self.cursor.execute(
            "DELETE FROM `ip_addresses` WHERE ? - `timestamp` > ?",
            (curr_time, self.ttl),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    db_path = pathlib.Path.home() / ".securetalks" / "db.sqlite3"
    seconds_in_two_days = 60 * 60 * 24 * 2
    storage = Storage(db_path, seconds_in_two_days)
    storage.update_dialog_activity("b")
    storage.close()
