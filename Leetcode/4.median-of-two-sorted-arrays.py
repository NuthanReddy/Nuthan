#
# @lc app=leetcode id=4 lang=python3
#
# [4] Median of Two Sorted Arrays
#

# @lc code=start
class Solution:
    def findMedianSortedArrays(self, nums1: List[int], nums2: List[int]) -> float:
        if not nums1:
            if len(nums2) % 2 == 1:
                return nums2[len(nums2) // 2]
            else:
                return (nums2[len(nums2) // 2 - 1] + nums2[len(nums2) // 2]) / 2
        if not nums2:
            if len(nums1) % 2 == 1:
                return nums1[len(nums1) // 2]
            else:
                return (nums1[len(nums1) // 2 - 1] + nums1[len(nums1) // 2]) / 2
        odd = (len(nums1) + len(nums2)) % 2 == 1
        left_index = (len(nums1) + len(nums2) - 1) // 2
        i = j = 0
        while i + j <= left_index:
            if i < len(nums1) and (j >= len(nums2) or nums1[i] < nums2[j]):
                current = nums1[i]
                i += 1
            else:
                current = nums2[j]
                j += 1
        if odd:
            return current
        if i < len(nums1) and (j >= len(nums2) or nums1[i] < nums2[j]):
            next_val = nums1[i]
        else:
            next_val = nums2[j]
        return (current + next_val) / 2
        
# @lc code=end