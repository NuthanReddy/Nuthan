import hashlib
from MyLinkedList import Node, MyLinkedList


def str_to_int(elem, max):
    return int(hashlib.md5(str(elem).encode()).hexdigest(), 16) % max


class MyHashTable:
    array = None
    arr_len = 0
    key_count = 0
    fill_threshold = 0.7
    scaling_factor = 2

    def __init__(self, init_size=2, fill_threshold=0.7, scaling_factor=2):
        self.array = [None] * init_size
        self.arr_len = init_size
        self.key_count = 0
        self.fill_threshold = fill_threshold
        self.scaling_factor = scaling_factor

    def add(self, key, value=None):
        if self.key_count > 0.7 * self.arr_len:
            new_len = self.arr_len * self.scaling_factor
            temp_arr = [None] * new_len
            for ll in self.array:
                if ll is not None:
                    for elem in ll:
                        self.__add_to_list(temp_arr, elem.data, elem.value, new_len)
            self.array = temp_arr
            self.arr_len = new_len
            self.add(key, value)
        else:
            self.__add_to_list(self.array, key, value, self.arr_len)
            self.key_count += 1
        return self

    @staticmethod
    def __add_to_list(array, key, value, length):
        new_key = str_to_int(key, length)
        curr_node = Node(key, value)
        if array[new_key] is None:
            array[new_key] = MyLinkedList(curr_node)
        else:
            for node in array[new_key]:
                if node == curr_node:
                    return
            array[new_key].tail.next = curr_node

    def print(self):
        for i, ll in enumerate(self.array):
            print(i, ll)


ht = MyHashTable(1, 2, 2).add(2).add(5, "fff").add(5, "wr").add(8, "ggg").add(9, "efr").add(10, "rf")
ht.print()
