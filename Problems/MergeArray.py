def merge(nums1, m, nums2, n):
    """
    Do not return anything, modify nums1 in-place instead.
    """
    if m == 0:
        for i in range(n):
            nums1[i] = nums2[i]
    if n == 0:
        return
    i = m-1
    j = n-1
    count = 0
    while i >= -1 and j >= 0:
        count += 1
        if i < 0 or nums1[i] < nums2[j]:
            nums1[m+n-count] = nums2[j]
            j -= 1
        else:
            nums1[m+n-count] = nums1[i]
            i -= 1float('inf')


a = [2,0]
b = [1]
merge(a, 1, b, 1)
print(a)


