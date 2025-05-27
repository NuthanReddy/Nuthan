# In the game of cricket, players can score runs by hitting the ball delivered at them(by another player called bowler)
# and running between designated spots(wickets).
# suppose if a player is only allowed to score 1,2,4 and 6 runs in a ball.How many ways the player can score N runs
# without hitting consecutive 4s?
# for ex, to score 4 runs, the player can hit the runs in subsequent balls in the following ways.

#
# def ways_to_score(N, prev=None, ways=0):
#     if N < 0:
#         return 0
#
#         # Initialize DP array
#     dp = [0] * (N + 1)
#
#     # Base case
#     dp[0] = 1
#
#     for i in range(1, N + 1):
#         dp[i] += dp[i - 1] if i >= 1 else 0  # Scoring 1 run
#         dp[i] += dp[i - 2] if i >= 2 else 0  # Scoring 2 runs
#         if i >= 4 and (i == 4 or (i >= 5 and dp[i - 5] != dp[i - 4])):  # Ensuring no consecutive 4s
#             dp[i] += dp[i - 4]
#         dp[i] += dp[i - 6] if i >= 6 else 0  # Scoring 6 runs
#
#     return dp[N]
#
#
# print(ways_to_score(4))


def countWays(N, prevWasFour, memo):
    if N < 0:
        return 0
    if N == 0:
        return 1
    if (N, prevWasFour) in memo:
        return memo[(N, prevWasFour)]

    # Choices: 1, 2, 4, 6 runs
    ways = countWays(N - 1, False, memo) + countWays(N - 2, False, memo) + countWays(N - 6, False, memo)

    # Only add 4 if the previous run was NOT a 4
    if not prevWasFour:
        ways += countWays(N - 4, True, memo)

    memo[(N, prevWasFour)] = ways
    return ways


# Example usage:
N = 4
memo = {}
print(countWays(N, False, memo))  # Output: 6

#
# def generate_sequences(N, current_seq, last_was_four, solutions):
#     if N == 0:  # Valid sequence found
#         solutions.append(tuple(current_seq))
#         return
#
#     for run in [1, 2, 4, 6]:
#         if run <= N:
#             # Prevent consecutive 4s
#             if run == 4 and last_was_four:
#                 continue
#
#             current_seq.append(run)
#             generate_sequences(N - run, current_seq, run == 4, solutions)
#             current_seq.pop()  # Backtrack
#
#
# def countWays(N):
#     solutions = []
#     generate_sequences(N, [], False, solutions)
#     return len(solutions)
#
#
# # Example usage:
# N = 4
# print(countWays(N))  # Output: 6
