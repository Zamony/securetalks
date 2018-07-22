import time
from dataclasses import dataclass, field

class MessageAlreadyExistsError(ValueError):
    """An error occurring when message already exists"""

class IPAddressAlreadyExistsError(ValueError):
    """An error occurring when ip address already exists"""

class IPAddressNotFoundError(ValueError):
    """An error occurring when ip address doesn't exists"""

class CiphergramAlreadyExistsError(ValueError):
    """An error occurring when ciphergram already exists"""

class NodeAlreadyExistsError(ValueError):
    """An error occurring when node already exists"""

class NodeNotFoundError(ValueError):
    """An error occurring when node doesn't exists"""

@dataclass(order=True)
class Message:
    node_id: str
    text: str = field(compare=False)
    to_me: bool = field(compare=False)
    sender_timestamp: int = field(
        default_factory=lambda: int(time.time()), compare=False
    )
    timestamp: int = field(default_factory=lambda: int(time.time()))
    
@dataclass(order=True)
class IPAddress:
    address: str = field(compare=False)
    port: int = field(compare=False)
    last_activity: int = field(default_factory=lambda: int(time.time()))

    def update_activity(self):
        self.last_activity = int(time.time())

@dataclass(order=True)
class Ciphergram:
    content: str = field(compare=False)
    timestamp: int

@dataclass
class Node:
    node_id: str
    last_activity: int = field(default_factory=lambda: int(time.time()))
    unread_count: int = 0
    alias: str = ""

    def update_activity(self):
        self.last_activity = int(time.time())

    def increment_unread(self):
        self.unread_count += 1

    def set_unread_to_zero(self):
        self.unread_count = 0