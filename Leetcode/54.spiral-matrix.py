#
# @lc app=leetcode id=54 lang=python3
#
# [54] Spiral Matrix
#

# @lc code=start
class Solution:
    def spiralOrder(self, matrix: List[List[int]]) -> List[int]:
        output = []
        if not matrix:
            return output
        top, bottom = 0, len(matrix) - 1
        left, right = 0, len(matrix[0]) - 1
        while left <= right and top <= bottom:
            for i in range(left, right + 1):
                output.append(matrix[top][i])
            top += 1
            for i in range(top, bottom + 1):
                output.append(matrix[i][right])
            right -= 1
            # Check if there are more rows and columns to traverse 
            # before traversing the bottom row and left column
            if top <= bottom:
                for i in range(right, left - 1, -1):
                    output.append(matrix[bottom][i])
                bottom -= 1
            if left <= right:
                for i in range(bottom, top - 1, -1):
                    output.append(matrix[i][left])
                left += 1
        return output
# @lc code=end

