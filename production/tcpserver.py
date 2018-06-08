import time
import socket
import threading

import snakesockets

def worker(client_socket):
    message = client_socket.recv()
    client_socket.send("клиент {}, привет от сервера!".format(message[-2]))
    client_socket.close()
    print(message)

if __name__ == "__main__":
    server_socket = snakesockets.TCP(reuseaddr=True)
    server_socket.bind(("0.0.0.0", 9000))
    server_socket.listen()

    while True:
        start_time = time.time()
        client_socket, _ = server_socket.accept()
        client_thread = threading.Thread(target=worker, args=(client_socket,))
        client_thread.start()