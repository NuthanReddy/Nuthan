def max_beautiful_segments(n, a):
    prefix_sum = 0
    seen = set()
    seen.add(0)
    count = 0

    for i in range(n):
        prefix_sum += a[i]
        print("before:", prefix_sum, i, seen, count)
        if prefix_sum in seen:
            # when the sum is zero, treat the rest as new problem and proceed.
            count += 1
            # Reset for non-overlapping segments
            seen = set()
            seen.add(0)
            prefix_sum = 0
        else:
            seen.add(prefix_sum)
        print("after:", prefix_sum, i, seen, count)

    return count


# Testing the example cases:
print(max_beautiful_segments(5, [2, 1, -3, 2, 1]))  # Output: 1
print(max_beautiful_segments(7, [12, -4, 4, 43, -3, -5, 8]))  # Output: 2
print(max_beautiful_segments(6, [-4, 0, 3, 0, 1, 0]))  # Output: 3
