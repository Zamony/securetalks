import time
import socket
import threading

import snakesockets

def worker(client_socket):
    message = client_socket.recv()
    client_socket.send(f"клиент {message[-2]}, привет от сервера!")
    client_socket.close()
    print(message)

if __name__ == "__main__":
    server_socket = snakesockets.TCP(reuseaddr=True)
    server_socket.bind(("localhost", 9000))
    server_socket.listen()

    while True:
        start_time = time.time()
        client_socket, _ = server_socket.accept()
        client_thread = threading.Thread(target=worker, args=(client_socket,))
        client_thread.start()