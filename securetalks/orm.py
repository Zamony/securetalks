import time
from dataclasses import dataclass, field

@dataclass(order=True)
class Message:
    node_id: str
    text: str = field(compare=False)
    to_me: bool = field(compare=False)
    timestamp: int = field(default_factory=lambda: int(time.time()))
    
@dataclass(order=True)
class IPAddress:
    address: str = field(compare=False)
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