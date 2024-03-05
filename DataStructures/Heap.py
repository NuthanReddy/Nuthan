class MyHeap:
    def __init__(self, initial=None, key=lambda x: x):
        self.key = key
        if initial: