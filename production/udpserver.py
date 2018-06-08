import socket

import snakesockets

if __name__ == "__main__":
    sock = snakesockets.UDP(reuseaddr=True)
    sock.bind(("localhost", 9000))

    while True:
        message, addr = sock.recvfrom()
        sock.sendto([2, "serv"], addr)
        
        print(message)