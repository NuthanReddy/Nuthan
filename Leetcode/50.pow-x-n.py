#
# @lc app=leetcode id=50 lang=python3
#
# [50] Pow(x, n)
#

# @lc code=start
class Solution:
    def myPow(self, x: float, n: int) -> float:
        if n < 0:
            x = 1 / x
            n = -n
        result = 1
        # fast exponentiation
        # 13 can be represented as 1101 in binary, which means x^13 = x^(1*2^0) * x^(0*2^1) * x^(1*2^2) * x^(1*2^3)
        while n > 0:
            if n % 2 == 1:
                result *= x
            x *= x
            n //= 2
        return result
# @lc code=end

