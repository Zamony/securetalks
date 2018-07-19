import shutil
import pathlib
import sqlite3

from securetalks import storage

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