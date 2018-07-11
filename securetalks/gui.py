import time
import webbrowser

import webevents

class WebeventsGUI:
    def __init__(self, presentor_obj):
        self.presentor_obj = presentor_obj
        address = ("localhost", 8080)
        self.events = webevents.run(address, "web")
        self.events.add_event_listener(
            "get_dialogs", self._get_dialogs
        )
        self.events.add_event_listener(
            "send_message", self._send_message
        )
        self.events.add_event_listener(
            "add_dialog", self._add_dialog
        )
        self.events.add_event_listener(
            "delete_dialog", self._delete_dialog
        )
        self.events.add_event_listener(
            "make_dialog_read", self._make_dialog_read
        )
        webbrowser.open_new_tab("http://{}:{}".format(*address))

    def push_message(self, message):
        self.events.fire_event("push_message", message)

    def terminate(self):
        self.events.terminate()

    def _get_dialogs(self, data):
        self.events.fire_event(
            "get_dialogs_result", self.presentor_obj.get_dialogs()
        )

    def _send_message(self, data):
        uid, message = data
        self.presentor_obj.send_message(uid, message)

    def _add_dialog(self, data):
        try:
            uid, alias = data
        except ValueError:
            self.presentor_obj.add_dialog(data)
        else:
            self.presentor_obj.add_dialog(uid, alias)

    def _delete_dialog(self, uid):
        self.presentor_obj.delete_dialog(uid)

    def _make_dialog_read(self, uid):
        self.presentor_obj.make_dialog_read(uid)


if __name__ == "__main__":
    presentor_obj = presentor.Presentor()
    gui = WebeventsGUI(presentor_obj)

    time.sleep(3)
    gui.push_message({
        "to_me": True,
        "text": "Hello! This is from Python!)))",
        "timestamp": int(time.time()),
        "talking_to": "fj4398r32j0029329dij",
    })
    time.sleep(3)
    gui.push_message({
        "to_me": True,
        "text": "Second message!)))",
        "timestamp": int(time.time()),
        "talking_to": "8dws712edgyw198h21us",
    })
    time.sleep(3)
    gui.push_message({
        "to_me": True,
        "text": "Third message!)))",
        "timestamp": int(time.time()),
        "talking_to": "8dws712edgyw198h21us",
    })
    time.sleep(3)
    gui.push_message({
        "to_me": True,
        "text": "It's me!)))",
        "timestamp": int(time.time()),
        "talking_to": "fj4398r32j0029329dij",
    })

    try:
        while True:
            pass
    except KeyboardInterrupt:
        gui.terminate()



