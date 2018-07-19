import pathlib

import webevents

from . import gui
from . import storage
from . import presentor

def main():
    seconds_in_two_hours = 60 * 60 * 24 * 2
    db_path = pathlib.Path.home() / ".securetalks" / "db.sqlite3"

    with storage.Storage(db_path, seconds_in_two_hours) as local_storage:
        presentor_obj = presentor.Presentor(local_storage)
        gui_obj = gui.WebeventsGUI(presentor_obj)
    
if __name__ == "__main__":
    main()
