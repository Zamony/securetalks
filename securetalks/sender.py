from . import snakesockets

class Sender:
    def __init__(self, queue, port):
        self.queue = queue
        self.port = port

    def _send_message(self, ip_addresses, message):
        for ip_address in ip_addresses:
            client_socket = snakesockets.TCP()
            client_socket.connect( (ip_address.address, self.port) )
            client_socket.send(message)

    def run(self):
        while True:
            addresses, message = self.queue.get()
            self._send_message(addresses, message)