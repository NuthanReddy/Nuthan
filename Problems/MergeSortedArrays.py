# def merge_sorted_arrays(arr1, arr2):
#     """
#     Merge two sorted arrays into a single sorted array
#     """
#     if not arr1:
#         return arr2
#     if not arr2:
#         return arr1
#     i = 0
#     j = 0
#     result = []
#     while i < len(arr1) or j < len(arr2):
#         if j == len(arr2):
#             result += arr1[i:]
#             return result
#         elif i == len(arr1):
#             result += arr2[j:]
#             return result
#         elif arr1[i] <= arr2[j]:
#             result.append(arr1[i])
#             i += 1
#         elif arr1[i] > arr2[j]:
#             result.append(arr2[j])
#             j += 1
#     return result
#
#
# def merge_sorted_arrays2(arr1, arr2):
#     """
#     Merge two sorted arrays into a single sorted array
#     """
#     if not arr1:
#         return arr2
#     if not arr2:
#         return arr1
#     result = []
#     if arr1[0] <= arr2[0]:
#         result.append(arr1[0])
#         result += merge_sorted_arrays2(arr1[1:], arr2)
#     else:
#         result.append(arr2[0])
#         result += merge_sorted_arrays2(arr1, arr2[1:])
#     return result


def merge_sorted_arrays3(arr1, arr2):
    if len(arr1) == 0:
        return arr2
    if len(arr2) == 0:
        return arr1
    r = []
    if arr1[0]<=arr2[0]:
        r.append(arr1[0])
        r+= merge_sorted_arrays3(arr1[1:],arr2)
    else:
        r.append(arr2[0])
        r += merge_sorted_arrays3(arr1, arr2[1:])
    return r




print(merge_sorted_arrays3([1, 2, 3], [4, 5, 6]))
print(merge_sorted_arrays3([1, 3, 5], [2, 4, 6]))
print(merge_sorted_arrays3([1, 2, 3], [1, 2, 3]))