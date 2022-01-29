import random
from collections.abc import Iterable


def coalesce(obj, attr, substitute):
    if obj is None:
        return substitute
    else:
        return obj.__getattribute__(attr)


class MyBinaryTree:
    def __init__(self, data=None, right=None, left=None):
        assert (isinstance(right, MyBinaryTree) or right is None)
        assert (isinstance(left, MyBinaryTree) or left is None)
        self.data = data
        self.right = right
        self.left = left
        self.height = 0

    def update_height(self):
        self.height = max(coalesce(self.left, "height", 0), coalesce(self.right, "height", 0)) + 1

    @property
    def balance(self):
        return coalesce(self.right, "height", 0) - coalesce(self.left, "height", 0)

    def build_tree(self, iterable):
        assert (isinstance(iterable, Iterable))
        for item in iterable:
            self.add_data(item)
        return self

    def build_balanced_tree(self, iterable):
        assert (isinstance(iterable, Iterable))
        node = self
        for item in iterable:
            node = node.balanced_add_data(item)
        return node

    @staticmethod
    def rotate_to_right(node=None):
        """
        right becomes root
        root becomes left
        left.right becomes right.left
        :param node:
        :return:
        """
        if node is None:
            return None
        left = node.left
        left_right = coalesce(left, "right", None)
        left.right = node
        node.left = left_right
        node.update_height()
        left.update_height()
        return left

    @staticmethod
    def rotate_to_left(node=None):
        """
        right becomes root
        root becomes left
        right.left becomes left.right
        :param node:
        :return:
        """
        if node is None:
            return None
        right = node.right
        right_left = coalesce(right, "left", None)
        node.right.left = node
        node.right = right_left
        node.update_height()
        right.update_height()
        return right

    def rebalance(self):
        if self.balance > 1:
            return self.rotate_to_left(self)
        elif self.balance < -1:
            return self.rotate_to_right(self)
        if self.right is not None:
            self.right = self.right.rebalance()
        if self.left is not None:
            self.left = self.left.rebalance()
        return self

    def add_data(self, data, node=None):
        if node is None:
            node = self
        if self.data is None:
            self.data = data
        elif data < node.data:
            if node.left is None:
                node.left = MyBinaryTree(data)
            else:
                self.add_data(data, node.left)
        else:
            if node.right is None:
                node.right = MyBinaryTree(data)
            else:
                self.add_data(data, node.right)
        return self

    def balanced_add_data(self, data, node=None):
        # add data to the default position
        if node is None:
            node = self
        if self.data is None:
            self.data = data
        elif data < node.data:
            if node.left is None:
                node.left = MyBinaryTree(data)
            else:
                self.balanced_add_data(data, node.left)
        else:
            if node.right is None:
                node.right = MyBinaryTree(data)
            else:
                self.balanced_add_data(data, node.right)

        # rotate the tree if not balanced
        if node.balance
        return self

    def display(self):
        lines, *_ = self._display_aux()
        for line in lines:
            print(line)

    def _display_aux(self):
        """Returns list of strings, width, height, and horizontal coordinate of the root."""
        # No child.
        if self.right is None and self.left is None:
            line = '%s' % self.data
            width = len(line)
            height = 1
            middle = width // 2
            return [line], width, height, middle

        # Only left child.
        if self.right is None:
            lines, n, p, x = self.left._display_aux()
            s = '%s' % self.data
            u = len(s)
            first_line = (x + 1) * ' ' + (n - x - 1) * '_' + s
            second_line = x * ' ' + '/' + (n - x - 1 + u) * ' '
            shifted_lines = [line + u * ' ' for line in lines]
            return [first_line, second_line] + shifted_lines, n + u, p + 2, n + u // 2

        # Only right child.
        if self.left is None:
            lines, n, p, x = self.right._display_aux()
            s = '%s' % self.data
            u = len(s)
            first_line = s + x * '_' + (n - x) * ' '
            second_line = (u + x) * ' ' + '\\' + (n - x - 1) * ' '
            shifted_lines = [u * ' ' + line for line in lines]
            return [first_line, second_line] + shifted_lines, n + u, p + 2, u // 2

        # Two children.
        left, n, p, x = self.left._display_aux()
        right, m, q, y = self.right._display_aux()
        s = '%s' % self.data
        u = len(s)
        first_line = (x + 1) * ' ' + (n - x - 1) * '_' + s + y * '_' + (m - y) * ' '
        second_line = x * ' ' + '/' + (n - x - 1 + u + y) * ' ' + '\\' + (m - y - 1) * ' '
        if p < q:
            left += [n * ' '] * (q - p)
        elif q < p:
            right += [m * ' '] * (p - q)
        zipped_lines = zip(left, right)
        lines = [first_line, second_line] + [a + u * ' ' + b for a, b in zipped_lines]
        return lines, n + m + u, max(p, q) + 2, n + u // 2

    def __str__(self):
        return self.str_repr(self)

    def str_repr(self, node):
        right_arrow = " -> "
        left_arrow = " <- "
        left_brace = " ( "
        right_brace = " ) "
        if node is None:
            return "null"
        elif node.left is None:
            if node.right is None:
                return str(node.data)
            else:
                return str(node.data) + right_arrow + left_brace + self.str_repr(node.right) + right_brace
        else:
            if node.right is None:
                return left_brace + self.str_repr(node.left) + right_brace + left_arrow + str(node.data)
            else:
                return left_brace + self.str_repr(node.left) + right_brace + left_arrow + str(node.data) + \
                       right_arrow + left_brace + self.str_repr(node.right) + right_brace


btn_r = MyBinaryTree()
for i in range(10):
    btn_r = btn_r.balanced_add_data(i)
    btn_r.display()


