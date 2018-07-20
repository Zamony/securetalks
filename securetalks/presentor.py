from . import orm

class Presentor:
    def __init__(self, storage):
        self.storage = storage

    def get_dialogs(self):
        return [
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
                    ) for message in self.storage.messages.get_messages(node)
                ]
            ) for node in self.storage.nodes.list_all()
        ]

    def send_message(self, node_id, msg_text):
        try:
            node = self.storage.nodes.get_node_by_id(node_id)
        except orm.NodeNotFoundError:
            pass
        else:
            message = orm.Message(node.node_id, msg_text, to_me=False)
            self.storage.messages.add_message(message)
            # TODO send message


    def add_dialog(self, node_id, alias=""):
        try:
            self.storage.nodes.add_node(
                orm.Node(node_id, alias=alias)
            )
        except orm.NodeAlreadyExistsError:
            pass

    def delete_dialog(self, node_id):
        try:
            self.storage.nodes.delete_node(orm.Node(node_id))
        except orm.NodeNotFoundError:
            pass

    def make_dialog_read(self, node_id):
        try:
            self.storage.nodes.set_node_unread_to_zero(
                orm.Node(node_id)
            )
        except orm.NodeNotFoundError:
            pass

    