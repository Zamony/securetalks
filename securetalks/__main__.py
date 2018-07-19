import pathlib

from . import gui
from . import storage

def main():
    db_path = pathlib.Path.home() / ".securetalks" / "db.sqlite3"
    two_days_secs = 60 * 60 * 24 * 2

    with storage.Storage(db_path, two_days_secs) as local_storage:
        pass

    events = webevents.run(("localhost", 8080), "../web")

if __name__ == "__main__":
    main()