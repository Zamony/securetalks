import dataclasses

from . import orm


class Presentor:
    def __init__(self, sender, keys, storage):
        self.sender = sender
        self.keys = keys
        self.storage = storage

    def get_dialogs(self):
        return [
            dict(
                **dataclasses.asdict(node),
                messages= [
                    {
                        **dataclasses.asdict(node),
                        **dataclasses.asdict(message)
                    }
                    for message in self.storage.messages.get_messages(node)
                ]
            ) for node in self.storage.nodes.list_all()
        ]

    def send_message(self, node_id, msg_text):
        try:
            node = self.storage.nodes.get_node_by_id(node_id)
        except orm.NodeNotFoundError:
            pass
        else:
            message = orm.Message(
                node.node_id, msg_text, to_me=False
            )
            self.storage.messages.add_message(message)
            self.sender.send_message_to(node_id, msg_text)

    def add_dialog(self, node_id, alias=""):
        try:
            self.storage.nodes.add_node(
                orm.Node(node_id, alias=alias)
            )
        except orm.NodeAlreadyExistsError:
            pass

    def delete_dialog(self, node_id):
        node = orm.Node(node_id)
        try:
            self.storage.nodes.delete_node(node)
            self.storage.messages.delete_messages(node)
        except orm.NodeNotFoundError:
            pass

    def make_dialog_read(self, node_id):
        try:
            self.storage.nodes.set_node_unread_to_zero(
                orm.Node(node_id)
            )
        except orm.NodeNotFoundError:
            pass

    def get_my_id(self):
        return self.keys.pub_key_str

    def change_node_alias(self, node_id, alias):
        try:
            node = self.storage.nodes.get_node_by_id(node_id)
        except orm.NodeNotFoundError:
            pass
        else:
            node_new_alias = dataclasses.replace(node, alias=alias)
            self.storage.nodes.delete_node(node)
            self.storage.nodes.add_node(node_new_alias)
