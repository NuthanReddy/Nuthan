# Find the minimum number of coins required for a given amount with a given set of coins
import math


def min_coins(amount, allowed_coins=[1, 2, 5, 10]):
    if amount in allowed_coins:
        return 1

    dp = [math.inf] * (amount + 1)

    for coin in allowed_coins:
        if coin < amount:
            dp[coin] = 1

    for i in range(1, amount+1):
        for coin in allowed_coins:
            if i >= coin:
                dp[i] = min(dp[i], dp[i-coin]+1)

    return dp[i]


print(min_coins(1))
print(min_coins(3))
print(min_coins(4))
print(min_coins(5))
print(min_coins(6))
print(min_coins(7))
print(min_coins(8))



