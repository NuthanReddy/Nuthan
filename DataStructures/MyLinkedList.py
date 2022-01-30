class Node:
    def __init__(self, data=None, value=None, next_node=None):
        assert (data is not None)
        assert (isinstance(next_node, Node) or next_node is None)
        self.data = data
        self.value = value
        self.next = next_node

    def __eq__(self, other):
        return self.data == other.data

    def has_next(self):
        return self.next is not None


class MyLinkedList:
    def __init__(self, head=None):
        assert (isinstance(head, Node) or head is None)
        if head is not None:
            self.head = head
            self.tail = head
            self.length = 1
        else:
            self.head = None
            self.tail = None
            self.length = 0

    def append_value(self, value):
        node = Node(value)
        if self.length > 0:
            self.tail.next = node
            self.tail = node
        else:
            self.head = node
            self.tail = node
        self.length += 1
        return self

    def append_values(self, values):
        for value in values:
            self.append_value(value)
        return self

    def prepend_value(self, value):
        node = Node(value)
        if self.length > 0:
            node.next = self.head
            self.head = node
        else:
            self.head = node
            self.tail = node
        self.length += 1
        return node

    def prepend_values(self, values):
        for value in values:
            self.prepend_value(value)
        return self

    def delete_head(self):
        self.head = self.head.next
        self.length -= 1
        return self

    def delete_tail(self):
        node = self.goto_position(self.length - 1)
        node.next = None
        self.length -= 1
        return self

    def delete_at_position(self, position):
        node = self.goto_position(position - 1)
        node.next = node.next.next
        self.length -= 1
        return self

    def goto_position(self, position):
        """
        Returns node at given position.
        :param position: starts from 1 to length
        :return:
        """
        node = self.head
        for _ in range(0, position - 1):
            node = node.next
        return node

    def __str__(self):
        node = self.head
        str_value = ""
        while node.next is not None:
            str_value += str(node.data) + " -> "
            node = node.next
        str_value += str(node.data)
        return str_value

    def __len__(self):
        return self.length

    def __eq__(self, other):
        if self.length == other.length:
            n1 = self.head
            n2 = other.head
            for _ in range(0, self.length):
                if n1 != n2:
                    return False
                else:
                    n1 = n1.next
                    n2 = n2.next
            return True
        return False

    def __iter__(self):
        if self.head is None:
            raise StopIteration
        curr = self.head
        yield curr
        while curr.has_next():
            curr = curr.next
            yield curr


if __name__ == '__main__':
    ll = MyLinkedList().append_values([5, 1, 2, 3, 4, 5, 6, 7])
    print(ll)

    ll.delete_head()
    ll.delete_tail()
    ll.delete_at_position(2)
    print(ll)

    ll2 = MyLinkedList().append_values([1, 3, 4, 5, 6])

    print(ll == ll2)

    for node in ll:
        print(node.data)
