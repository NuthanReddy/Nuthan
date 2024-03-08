from deepdiff import DeepDiff
from pprint import pprint
t1 = {1:1, 2:2, 3:3}
t2 = t1
print(DeepDiff(t1, t2))

t1 = {1:1, 2:2, 3:3}
t2 = {1:1, 2:"2", 3:3}
pprint(DeepDiff(t1, t2), indent=2)

t1 = {1:1, 2:2, 3:3}
t2 = {1:1, 2:4, 3:3}
pprint(DeepDiff(t1, t2, verbose_level=0), indent=2)

t1 = {1:1, 3:3, 4:4}
t2 = {1:1, 3:3, 5:5, 6:6}
ddiff = DeepDiff(t1, t2)
pprint (ddiff)

t1 = {1:1, 3:3, 4:4}
t2 = {1:1, 3:3, 5:5, 6:6}
ddiff = DeepDiff(t1, t2, verbose_level=2)
pprint(ddiff, indent=2)

t1 = {1:1, 2:2, 3:3, 4:{"a":"hello", "b":"world"}}
t2 = {1:1, 2:4, 3:3, 4:{"a":"hello", "b":"world!"}}
ddiff = DeepDiff(t1, t2)
pprint (ddiff, indent = 2)

t1 = {1:1, 2:2, 3:3, 4:{"a":"hello", "b":"world!\nGoodbye!\n1\n2\nEnd"}}
t2 = {1:1, 2:2, 3:3, 4:{"a":"hello", "b":"world\n1\n2\nEnd"}}
ddiff = DeepDiff(t1, t2)
pprint (ddiff, indent = 2)

print (ddiff['values_changed']["root[4]['b']"]["diff"])


t1 = [
    {'id': 'AA', 'name': 'Joe', 'last_name': 'Nobody', 'int_id': 2},
    {'id': 'BB', 'name': 'James', 'last_name': 'Blue', 'int_id': 20},
    {'id': 'BB', 'name': 'Jimmy', 'last_name': 'Red', 'int_id': 3},
    {'id': 'CC', 'name': 'Mike', 'last_name': 'Apple', 'int_id': 4},
]

t2 = [
    {'id': 'AA', 'name': 'Joe', 'last_name': 'Nobody', 'int_id': 2},
    {'id': 'BB', 'name': 'James', 'last_name': 'Brown', 'int_id': 20},
    {'id': 'CC', 'name': 'Mike', 'last_name': 'Apple', 'int_id': 4},
]

diff = DeepDiff(t1, t2, group_by='id', group_by_sort_key='name')

pprint(diff)