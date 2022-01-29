# Dynamic Programming Solution for
# Palindrome Partitioning Problem
import sys


# Returns the minimum number of cuts
# needed to partition a string such
# that every part is a palindrome
def minPalPartion(str1):
    # Get the length of the string
    n = len(str1)

    # Create two arrays to build the solution
    # in bottom up manner
    # C[i] = Minimum number of cuts needed
    # for palindrome partitioning of
    # substring str[0..i]
    # P[i][j] = true if substring str[i..j]
    # is palindrome, else false
    # Note that C[i] is 0 if P[0][i] is true
    C = [0] * (n + 1)
    P = [[False for x in range(n + 1)] for y in range(n + 1)]

    # Every substring of length 1 is
    # a palindrome
    for i in range(n):
        P[i][i] = True

    # L is substring length. Build the solution
    # in bottom up manner by considering all
    # substrings of length starting from 2 to n.
    for L in range(2, n + 1):

        # For substring of length L, set
        # different possible starting indexes
        for i in range(n - L + 1):
            j = i + L - 1

            # Set ending index
            # If L is 2, then we just need to
            # compare two characters. Else need
            # to check two corner characters and
            # value of P[i + 1][j-1]
            if L == 2:
                P[i][j] = (str1[i] == str1[j])
            else:
                P[i][j] = ((str1[i] == str1[j]) and P[i + 1][j - 1])
    for i in range(n):
        if (P[0][i] == True):
            C[i] = 0
        else:
            C[i] = sys.maxsize
            for j in range(i):
                if P[j + 1][i] == True and 1 + C[j] < C[i]:
                    C[i] = 1 + C[j]

    # Return the min cut value for complete
    # string. i.e., str[0..n-1]
    return C[n - 1]


# Driver Code
str1 = "ababbbabbababa"
print("Min cuts needed for Palindrome Partitioning is", minPalPartion(str1))

# This code is contributed by mits
