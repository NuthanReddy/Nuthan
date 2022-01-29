from MyLinkedList import MyLinkedList


class MyQueue:
    ll = None

    def __init__(self, data=None):
        if data is not None:
            self.ll = MyLinkedList(data)
        else:
            self.ll = MyLinkedList()

    def enqueue(self, value):
        self.ll.append_value(value)
        return self

    def enqueue_values(self, values):
        self.ll.append_values(values)
        return self

    def dequeue(self):
        if self.ll.head is None:
            raise EmptyQueueException()
        head = self.ll.head
        self.ll.delete_head()
        return head.data

    def peek(self):
        if self.ll.head is None:
            raise EmptyQueueException()
        return self.ll.head.data

    def peek_tail(self):
        if self.ll.tail is None:
            raise EmptyQueueException()
        return self.ll.tail.data

    def __len__(self):
        return self.ll.length

    def __str__(self):
        return self.ll.__str__()

    def is_empty(self):
        return self.ll.length == 0


class EmptyQueueException(Exception):
    pass

#
# class MinQueue(Queue):
#         mins = Queue()
#
#     def __init__(self, data=None):
#         super().__init__(data)
#         if data is not None:
#             self.mins = [data]
#
#     def enqueue(self, data):
#         self.ll.append_value(data)
#         try:
#             prev_min = self.mins.peek_tail()
#         except EmptyQueueException:
#             prev_min = math.inf
#         self.mins.enqueue(min(data, prev_min))
#         return self
#
#     def enqueue_values(self, values):
#         for value in values:
#             self.enqueue(value)
#         return self
#
#     def dequeue(self):
#         head = self.ll.head
#         self.ll.delete_head()
#         self.mins.dequeue()
#         return head.data
#
#     def min(self):
#         return self.mins.peek()


if __name__ == '__main__':
    st = MyQueue().enqueue_values([1, 2, 3, 4, 5, 6])
    print(st)
    print(st.dequeue())
    print(st)
    #
    # mst = MinQueue().enqueue_values([6, 2, 1, 8, 5, 7])
    # mst.print()
    # mst.mins.print()
    # print(mst.min())
    # mst.dequeue()
    # mst.print()
    # mst.mins.print()
    # print(mst.min())
    # mst.dequeue()
    # mst.dequeue()
    # mst.print()
    # mst.mins.print()
    # print(mst.min())
    # mst.dequeue()
    # mst.print()
    # mst.mins.print()
    # print(mst.min())
    # mst.dequeue()
    # mst.print()
    # mst.mins.print()
    # print(mst.min())
