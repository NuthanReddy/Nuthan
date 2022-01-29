'''
# Sample code to perform I/O:

name = input()                  # Reading input from STDIN
print('Hi, %s.' % name)         # Writing output to STDOUT

# Warning: Printing unwanted or ill-formatted data to output will cause the test cases to fail
'''

from collections import deque

class MAryTree:
    def __init__(self, m, data, parent=None):
        assert(m is not None)
        self.m = m
        self.children=[]
        self.data=data
        self.is_locked=False
        self.locked_by=None
        self.dependant_locks=0
        self.parent=parent

    def insert(self, node):
        if len(self.children) < self.m:
            self.children.append(node)
            return True
        else:
            print("Trying to insert more than m children per node")
            return False

    def lock(self, user):
        if self.is_locked == True or self.dependant_locks > 0:
            return False
        else:
            parent = self.parent
            while parent is not None:
                if parent.is_locked:
                    return False
                parent = parent.parent
            self.is_locked = True
            self.locked_by = user
            parent = self.parent
            while parent is not None:
                parent.dependant_locks += 1
                parent = parent.parent
            return True

    def unlock(self, user):
        if self.is_locked and self.locked_by == user:
            self.is_locked = False
            self.locked_by = None
            parent = self.parent
            while parent is not None:
                parent.dependant_locks -= 1
                parent = parent.parent
            return True
        else:
            return False

    def upgrade_lock(self, user):
        if self.dependant_locks == 0 or self.is_locked:
            return False
        else:
            lock_count = self.dependant_locks
            nodes_to_unlock = []
            search = [self]
            while lock_count > 0 and len(search) > 0:
                curr = search.pop(0)
                for child in curr.children:
                    if child.is_locked and child.locked_by != user:
                        return False
                    elif child.dependant_locks > 0:
                        search.append(child)
                    elif child.is_locked and child.locked_by == user:
                        nodes_to_unlock.append(child)
                        lock_count = lock_count - 1
        if len(nodes_to_unlock) == 0:
            return False
        for node in nodes_to_unlock:
            node.unlock(user)
        self.lock(user)
        return True

    def __str__(self):
        return str(self.m) + "AryTree(" + str(self.data) + ")"

    def __repr__(self):
        return str(self.parent) + " -> " + str(self.data)

no_of_nodes=int(input())
m_ary=int(input())
no_of_queries=int(input())

operation_map = {"1": "lock", "2": "unlock", "3": "upgrade_lock"}

# generate tree
node_data = input()
#print("node_data: {}".format(node_data))
m_ary_tree = MAryTree(m_ary, node_data)
curr_m_ary_tree = m_ary_tree
# node name to node map
nodes = {}
nodes[node_data] = MAryTree(m_ary, node_data)

# tracking leaves to add nodes to
leaves = deque()
for i in range(no_of_nodes-1):
    node_data = input()
    # print(curr_m_ary_tree)
    # print(len(curr_m_ary_tree.children))
    if len(curr_m_ary_tree.children) >= m_ary:
        curr_m_ary_tree = leaves.popleft()
    nodes[node_data] = MAryTree(m_ary, node_data, curr_m_ary_tree)
    leaves.append(nodes[node_data])
    curr_m_ary_tree.insert(nodes[node_data])
# print(nodes)

# run queries
for i in range(no_of_queries):
    query = str(input()).split(" ")
    operation = operation_map[query[0]]
    node = nodes[query[1]]
    user = int(query[2])
    # print(node, operation, user)
    print(str(eval("node.{}({})".format(operation, user))).lower())



