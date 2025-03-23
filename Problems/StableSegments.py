# find segments >=3 length where egde nodes value - sum(values of nodes in between)
from collections import defaultdict


def count_stable_segments(input):
    n = len(input)
    if n < 3:
        return 0
    d = defaultdict(int)
    d[(0, input[0])] = 1
    r, s = 0, 0
    for i in range(n - 1):
        s += input[i]
        r += d[(s - 3 * input[i], input[i])]
        d[(s, input[i + 1])] += 1
    return r


print(count_stable_segments([9, 3, 3, 3, 9]))
print(count_stable_segments([9, 3, 1, 2, 3, 9, 10]))
print(count_stable_segments([10, 9, 3, 1, 2, 3, 9]))