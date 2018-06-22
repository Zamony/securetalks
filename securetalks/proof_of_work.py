import struct
import hashlib

def compute_pow(bmessage):
    nonce = 0
    target = compute_target(bmessage)
    trial = target + 1
    while trial > target:
        nonce += 1
        bnonce = struct.pack("!Q", nonce)
        hash1 = hashlib.sha512(bnonce + bmessage).digest()
        hash2 = hashlib.sha512(hash1).digest()
        trial = struct.unpack("!Q", hash2[:8])[0]

    return nonce

def check_pow_valid(bmessage, nonce):
    target = compute_target(bmessage)
    bnonce = struct.pack("!Q", nonce)
    hash1 = hashlib.sha512(bnonce + bmessage).digest()
    hash2 = hashlib.sha512(hash1).digest()
    trial = struct.unpack("!Q", hash2[:8])[0]

    return trial <= target

def compute_target(bmessage):
    return (1 << 56) / (1 + len(bmessage))


if __name__ == "__main__":
    message = b"hello, folks!"
    proof = compute_pow(message)
    print(f"Checking proof={proof}:")
    print(check_pow_valid(message, proof))