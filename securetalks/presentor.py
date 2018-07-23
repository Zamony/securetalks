from . import orm
from . import storage

class Presentor:
    def __init__(self, sender, db_path, ttl):
        self.sender = sender
        self.db_path = db_path
        self.ttl = ttl

    def get_dialogs(self):
        with storage.Storage(self.db_path, self.ttl) as storage_obj:
            result = [
                dict(
                    talking_to=node.node_id,
                    last_updated=node.last_activity,
                    unread_count=node.unread_count,
                    alias=node.alias,
                    messages=[
                        dict(
                            talking_to=node.node_id,
                            timestamp=message.timestamp,
                            to_me=message.to_me,
                            text=message.text
                        ) for message in storage_obj.messages.get_messages(node)
                    ]
                ) for node in storage_obj.nodes.list_all()
            ]
        return result

    def send_message(self, node_id, msg_text):
        with storage.Storage(self.db_path, self.ttl) as storage_obj:
            try:
                node = storage_obj.nodes.get_node_by_id(node_id)
            except orm.NodeNotFoundError:
                pass
            else:
                message = orm.Message(
                    node.node_id, msg_text, to_me=False
                )
                storage_obj.messages.add_message(message)
                self.sender.send_message_to(node_id, msg_text)


    def add_dialog(self, node_id, alias=""):
        with storage.Storage(self.db_path, self.ttl) as storage_obj:
            try:
                storage_obj.nodes.add_node(
                    orm.Node(node_id, alias=alias)
                )
            except orm.NodeAlreadyExistsError:
                pass

    def delete_dialog(self, node_id):
        with storage.Storage(self.db_path, self.ttl) as storage_obj:
            try:
                storage_obj.nodes.delete_node(orm.Node(node_id))
            except orm.NodeNotFoundError:
                pass

    def make_dialog_read(self, node_id):
        with storage.Storage(self.db_path, self.ttl) as storage_obj:
            try:
                storage_obj.nodes.set_node_unread_to_zero(
                    orm.Node(node_id)
                )
            except orm.NodeNotFoundError:
                pass

    