# default dict usage
from collections import defaultdict


# Create a defaultdict with default value of 0
dd = defaultdict(int)

# Increment the count for each key
dd['apple'] += 1
dd['banana'] += 2
dd['apple'] += 3

# Print the defaultdict
print(dd)  # Output: defaultdict(<class 'int'>, {'apple': 4, 'banana': 2})