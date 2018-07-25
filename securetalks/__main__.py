import pathlib
import configparser
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

def read_config(app_dir):
    parser = configparser.ConfigParser()
    parser.read(str(app_dir / "config.txt"))
    return dict(
        server_address=parser.get("Server", "address", fallback="0.0.0.0"),
        server_port=parser.getint("Server", "port", fallback=8001),
        gui_port=parser.getint("GUI", "port", fallback=8002)
    )
            

def main():
    ttl_two_days = 60 * 60 * 24 * 2
    app_dir = pathlib.Path.home() / ".securetalks"
    app_dir.mkdir(exist_ok=True)
    db_path = app_dir / "db.sqlite3"
    bootstrap_list = app_dir / "bootstrap.list"
    config = read_config(app_dir)

    with storage.Storage(db_path, ttl_two_days) as storage_obj:
        bootstrap(storage_obj, bootstrap_list)
        
        keys = crypto.KeysProvider(app_dir)
        mcrypto = crypto.MessageCrypto(keys)

        sender_queue = multiprocessing.Queue()
        receiver_queue = multiprocessing.Queue()

        sender_obj = sender.Sender(
            mcrypto, db_path, ttl_two_days, sender_queue
        )
        presentor_obj = presentor.Presentor(
            sender_obj, keys, db_path, ttl_two_days
        )
        receiver_obj = receiver.Receiver(
            presentor_obj, sender_obj, storage_obj,
            mcrypto, receiver_queue,
            (config["server_address"], config["server_port"])
        )

        gui_obj = gui.WebeventsGUI(presentor_obj, config["gui_port"])
        gui_obj.add_termination_callback(
            lambda: receiver_obj.terminate()
        )
        gui_obj.add_termination_callback(
            lambda: sender_obj.terminate()
        )
        sender_obj.request_offline_data()
        receiver_obj.run()

    
if __name__ == "__main__":
    main()
