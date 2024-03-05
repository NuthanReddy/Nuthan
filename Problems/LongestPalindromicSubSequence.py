def longestPalindrome(s: str) -> str:
    n = len(s)
    if n == 1:
        return s

    max_l = 0
    max_p = ""
    # odd
    for i in range(n):
        right_i = i
        left_i = i
        while (right_i < n and left_i >= 0):
            if s[right_i] == s[left_i]:
                if max_l < (right_i - left_i + 1):
                    max_l = (right_i - left_i + 1)
                    max_p = s[left_i:right_i + 1]
            else:
                break
            right_i += 1
            left_i -= 1
        print(i, max_p)
    # even
    for i in range(n - 1):
        right_i = i
        left_i = i + 1
        while (right_i < n and left_i >= 0):
            if s[right_i] == s[left_i]:
                if max_l < (right_i - left_i + 1):
                    max_l = (right_i - left_i + 1)
                    max_p = s[left_i:right_i + 1]
            else:
                break
            right_i += 1
            left_i -= 1
        print(i, max_p)
    return max_p

longestPalindrome("aacabdkacaa")