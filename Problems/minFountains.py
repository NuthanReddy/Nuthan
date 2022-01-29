

def min_cnt_foun(a, N):
    # dp[i]: Stores the position of
    # rightmost fountain that can
    # be covered by water of leftmost
    # fountain of the i-th fountain
    dp = [-1] * N

    # Traverse the array
    for i in range(N):
        idx_left = max(i - a[i], 0)
        idx_right = min(i + (a[i] + 1), N)
        dp[idx_left] = max(dp[idx_left], idx_right)

    cnt_fount = 1
    idx_right = dp[0]

    # Stores index of next fountain
    # that needed to be activated
    idx_next = 0

    # Traverse dp[] array
    for i in range(N):
        idx_next = max(idx_next, dp[i])

        # If left most fountain
        # cover all its range
        if i == idx_right:
            cnt_fount += 1
            idx_right = idx_next

    return cnt_fount


if __name__ == '__main__':
    a = [1, 2, 1]
    N = len(a)

    print(min_cnt_foun(a, N))
