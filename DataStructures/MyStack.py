from MyLinkedList import MyLinkedList
import math


class MyStack:
    ll = None

    def __init__(self, data=None):
        if data is not None:
            self.ll = MyLinkedList(data)
        else:
            self.ll = MyLinkedList()

    def push(self, data):
        self.ll.prepend_value(data)
        return self

    def push_values(self, values):
        self.ll.prepend_values(values)
        return self

    def pop(self):
        if self.ll.head is None:
            raise EmptyStackException()
        head = self.ll.head
        self.ll.delete_head()
        return head.data

    def peek(self):
        if self.ll.head is None:
            raise EmptyStackException()
        return self.ll.head.data

    def __len__(self):
        return self.ll.length

    def __str__(self):
        return self.ll.__str__()

    def is_empty(self):
        return self.ll.length == 0


class MinStack(MyStack):
    mins = MyStack()

    def __init__(self, data=None):
        super().__init__(data)
        if data is not None:
            self.mins = [data]

    def push(self, data):
        self.ll.prepend_value(data)
        try:
            prev_min = self.mins.peek()
        except EmptyStackException:
            prev_min = math.inf
        self.mins.push(min(data, prev_min))
        return self

    def push_values(self, values):
        for value in values:
            self.push(value)
        return self

    def pop(self):
        head = self.ll.head
        self.ll.delete_head()
        self.mins.pop()
        return head.data

    def min(self):
        return self.mins.peek()


class EmptyStackException(Exception):
    pass


if __name__ == '__main__':
    st = MyStack().push_values([1, 2, 3, 4, 5, 6])
    st.print()
    print(st.pop())
    st.print()

    mst = MinStack().push_values([6, 2, 1, 8, 5, 7])
    print(mst.min())
    mst.pop()
    mst.pop()
    mst.pop()
    mst.pop()
    print(mst.min())
    mst.pop()
    print(mst.min())
