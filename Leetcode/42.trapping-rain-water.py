#
# @lc app=leetcode id=42 lang=python3
#
# [42] Trapping Rain Water
#

# @lc code=start
class Solution:
    def trap(self, height: List[int]) -> int:
        stack = []  # stores indices
        water = 0

        for i in range(len(height)):
            # While current bar is taller than the bar at stack top,
            # we found a bounded region — pop and calculate trapped water.
            while stack and height[i] > height[stack[-1]]:
                bottom = stack.pop()

                if not stack:
                    break  # no left boundary

                # Width between current bar and new stack top (left boundary)
                width = i - stack[-1] - 1
                # Height is bounded by the shorter of the two walls, minus the bottom
                bounded_height = min(height[i], height[stack[-1]]) - height[bottom]

                water += width * bounded_height

            stack.append(i)

        return water
# @lc code=end

