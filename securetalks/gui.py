import time
import webbrowser

import webevents

class WebeventsGUI:
    def __init__(self, presentor_obj, gui_port):
        self.presentor_obj = presentor_obj
        address = ("localhost", gui_port)
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
        self.events.add_event_listener(
            "get_my_id", self._get_my_id
        )
        webbrowser.open_new_tab("http://{}:{}".format(*address))

    def push_message(self, message):
        self.events.fire_event("push_message", message)

    def terminate(self):
        self.events.terminate()

    def add_termination_callback(self, callback):
        self.events.add_termination_callback(callback)

    def _get_dialogs(self, data):
        self.events.fire_event(
            "get_dialogs_result", self.presentor_obj.get_dialogs()
        )

    def _send_message(self, data):
        uid, message = data
        self.presentor_obj.send_message(uid, message)

    def _add_dialog(self, data):
        if len(data) == 1:
            self.presentor_obj.add_dialog(data)
        else:
            self.presentor_obj.add_dialog(*data)

    def _delete_dialog(self, uid):
        self.presentor_obj.delete_dialog(uid)

    def _make_dialog_read(self, uid):
        self.presentor_obj.make_dialog_read(uid)

    def _get_my_id(self, data):
        self.events.fire_event(
            "get_my_id_result", self.presentor_obj.get_my_id()
        )
