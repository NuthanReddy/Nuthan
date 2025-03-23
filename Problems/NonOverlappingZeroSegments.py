def max_beautiful_segments(n, arr):
    prefix_sum = 0
    prefix_map = {0: -1}
    beautiful_segments = 0
    last_index = -1

    for i in range(n):
        prefix_sum += arr[i]

        if prefix_sum in prefix_map:
            if prefix_map[prefix_sum] >= last_index:
                beautiful_segments += 1
                last_index = i
        prefix_map[prefix_sum] = i

    return beautiful_segments

# Example Inputs and Outputs
n1, arr1 = 5, [2, 1, -3, 2, 1]
print(max_beautiful_segments(n1, arr1))  # Output: 1

n2, arr2 = 7, [12, -4, 4, 43, -3, -5, 8]
print(max_beautiful_segments(n2, arr2))  # Output: 2

n3, arr3 = 6, [-4, 0, 3, 0, 1, 0]
print(max_beautiful_segments(n3, arr3))  # Output: 3
