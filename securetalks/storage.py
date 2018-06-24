import time
import pathlib
import sqlite3


class Storage:
    def __init__(self, db_path, ttl):
        self.ttl = int(ttl)
        db_path = str(db_path)
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables_if_needed()

    @property
    def known_addresses(self):
        self.cursor.execute("SELECT `ip_address` FROM `ip_addresses`")
        return (ip for ip, in self.cursor.fetchall())

    def add_known_address(self, ip_address):
        self.cursor.execute(
            "INSERT INTO `ip_addresses` VALUES (?, ?)", (ip_address, int(time.time()))
        )
        self.cursor.commit()

    @property
    def ciphergrams(self):
        self.cursor.execute("SELECT `ciphergram`, `timestamp` FROM `ciphergrams`")
        return cursor.fetchall()

    def add_ciphergram(self, ciphergram):
        self.cursor.execute(
            "INSERT INTO `ciphergrams` VALUES (?, ?)", (ciphergram, int(time.time()))
        )
        self.cursor.commit()

    def get_messages_from(self, who, limit=None, offset=None):
        if limit is not None and offset is not None:
            self.cursor.execute("""
            SELECT `text`, `timestamp` FROM `messages`
            WHERE `from`=? ORDER BY `timestamp` DESC LIMIT ? OFFSET ?;
            """, (who, limit, offset))
        elif limit is None and offset is None:
            self.cursor.execute("""
            SELECT `text`, `timestamp` FROM `messages`
            WHERE `from`=? ORDER BY `timestamp` DESC;
            """, (who,))
        elif limit is not None:
            self.cursor.execute("""
            SELECT `text`, `timestamp` FROM `messages`
            WHERE `from`=? ORDER BY `timestamp` DESC LIMIT ?;
            """, (who, limit))
        else:
            raise sqlite3.Error

        return self.cursor.fetchall()

    def add_message_from(who, text):
        self.cursor.execute(
            "INSERT INTO `messages` VALUES (?, ?, ?)", (who, text, int(time.time()))
        )
        self.cursor.commit()        
        

    def _create_tables_if_needed(self):
        try:
            self.cursor.executescript(
                """
            CREATE TABLE `ip_addresses` (
                `ip_address`	TEXT NOT NULL,
                `timestamp`	INTEGER NOT NULL
            );
            CREATE TABLE `ciphergrams` (
	            `ciphergram`	TEXT NOT NULL,
	            `timestamp`	INTEGER NOT NULL
            );
            CREATE TABLE `messages` (
                `from`	TEXT NOT NULL,
                `text`	TEXT NOT NULL,
                `timestamp`	INTEGER NOT NULL
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
    print(storage.known_addresses)
    storage.close()
