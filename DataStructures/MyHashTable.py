import hashlib


def str_to_int(str):
    return int(hashlib.md5(str).hexdigest(), 16)


class MyHashTable:
    def __init__(self):
        self.table = []