# Using memoizatoin to solve the partition problem.

# Function to check if input string is pallindrome or not
def ispallindrome(input, start, end):
    # Using two pointer technique to check pallindrome
    while (start < end):
        if (input[start] != input[end]):
            return False
        start += 1
        end -= 1
    return True


# Function to find keys for the Hashmap
def convert(a, b):
    return str(a) + str(b)


# Returns the minimum number of cuts needed to partition a string
# such that every part is a palindrome
def minpalparti_memo(input, i, j, memo):
    if i > j:
        return 0

    # Key for the Input String
    ij = convert(i, j)

    # If the no of partitions for string "ij" is already calculated
    # then return the calculated value using the Hashmap
    if (ij in memo):
        return memo[ij]

    # Every String of length 1 is a pallindrome
    if (i == j):
        memo[ij] = 0
        return 0
    if (ispallindrome(input, i, j)):
        memo[ij] = 0
        return 0
    minimum = 1000000000

    # Make a cut at every possible location starting from i to j
    for k in range(i, j):
        left_min = 1000000000
        right_min = 1000000000
        left = convert(i, k)
        right = convert(k + 1, j)

        # If left cut is found already
        if (left in memo):
            left_min = memo[left]

        # If right cut is found already
        if (right in memo):
            right_min = memo[right]

        # Recursively calculating for left and right strings
        if (left_min == 1000000000):
            left_min = minpalparti_memo(input, i, k, memo)
        if (right_min == 1000000000):
            right_min = minpalparti_memo(input, k + 1, j, memo)

        # Taking minimum of all k possible cuts
        minimum = min(minimum, left_min + 1 + right_min)
    memo[ij] = minimum

    # Return the min cut value for complete string.
    return memo[ij]


# Driver code
if __name__ == '__main__':
    input = "ababbbabbababa"
    memo = dict()
    print(minpalparti_memo(input, 0, len(input) - 1, memo))



