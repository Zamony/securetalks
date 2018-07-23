import pathlib
import multiprocessing

import webevents

from . import orm
from . import gui
from . import storage
from . import presentor
from . import crypto
from . import sender
from . import receiver

def bootstrap(storage, bootstrap_list):
    try:
        with open(bootstrap_list) as file:
            for line in file:
                try:
                    ip, port = line.strip().split(":")
                    port = int(port)
                except ValueError:
                    continue
                try:
                    storage.ipaddresses.add_address(
                        orm.IPAddress(ip, port)
                    )
                except orm.IPAddressAlreadyExistsError:
                    pass
    except OSError:
        pass
            

def main():
    ttl_two_days = 60 * 60 * 24 * 2
    listening_address = ("0.0.0.0", 8089)
    app_dir = pathlib.Path.home() / ".securetalks"
    app_dir.mkdir(exist_ok=True)
    db_path = app_dir / "db.sqlite3"
    bootstrap_list = app_dir / "bootstrap.list"

    with storage.Storage(db_path, ttl_two_days) as storage_obj:
        bootstrap(storage_obj, bootstrap_list)
        
        presentor_obj = presentor.Presentor(storage_obj)
        gui_obj = gui.WebeventsGUI(presentor_obj)
        keys = crypto.KeysProvider(app_dir)
        mcrypto = crypto.MessageCrypto(keys)

        sender_queue = multiprocessing.Queue()
        receiver_queue = multiprocessing.Queue()

        sender_obj = sender.Sender(storage_obj, mcrypto, sender_queue)
        receiver_obj = receiver.Receiver(
            presentor_obj, sender_obj, storage_obj,
            mcrypto, receiver_queue, listening_address
        )

        gui_obj.add_termination_callback(
            lambda: receiver_obj.terminate()
        )
        gui_obj.add_termination_callback(
            lambda: sender_obj.terminate()
        )

        receiver_obj.run()

    
if __name__ == "__main__":
    main()
