import sys
import socket

import snakesockets

client_socket = snakesockets.TCP()
client_socket.connect( ("80.211.205.161", 9000) )
client_socket.send("привет от клиента {}!".format(sys.argv[1]))
data = client_socket.recv()
print(data)
client_socket.close()
