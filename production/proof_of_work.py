import struct
import hashlib

def proof_of_work(bmessage):
    nonce = 0
    target = (1 << 48) / (1000 + len(bmessage))
    trial = target + 1
    while trial > target:
        nonce += 1
        bnonce = struct.pack("!Q", nonce)
        hash1 = hashlib.sha512(bnonce + bmessage).digest()
        hash2 = hashlib.sha512(hash1).digest()
        trial = struct.unpack("!Q", hash2[:8])[0]

    return nonce, trial, target

print(proof_of_work(b"hello world"))
