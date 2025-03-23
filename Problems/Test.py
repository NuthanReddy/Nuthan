from typing import List


class Solution:
    def fun(self, v: List[int], k: int) -> int:
        mp = {}
        total_sum = 0
        count = 0
        for i in range(len(v)):
            total_sum += v[i]
            if total_sum == k:
                count += 1
            if total_sum - k in mp:
                count += mp[total_sum - k]
            mp[total_sum] = mp.get(total_sum, 0) + 1
        return count

    def numSubmatrixSumTarget(self, mat: List[List[int]], target: int) -> int:
        m, n = len(mat), len(mat[0])
        ans = 0
        for i in range(m):
            v = [0] * n
            for j in range(0, i):
                for k in range(n):
                    v[k] += mat[j][k]
                ans += self.fun(v, target)
        return ans
