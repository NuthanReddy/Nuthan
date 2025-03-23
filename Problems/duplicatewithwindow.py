class Solution:
    def removeDuplicates(self, nums: List[int]) -> int:
        occurance=0
        new_index=0
        old_index=0
        if nums[new_index] == 0 and nums[old_index] ==0:
            new_index =2
            old_index =2
        while(len(nums)!=old_index+1):
            # both are same and occ <= 2 - move both forward
            # occ > 2 - move old forward
            # both are diff and occ <= 2 - copy old to new
            if nums[old_index]==nums[old_index+1]:
                occurance += 1
                old_index += 1
            else:
                occurance = 1
                old_index += 1
            if occurance <=2:
                nums[new_index] = nums[old_index]
                new_index +=1
        return new_index

