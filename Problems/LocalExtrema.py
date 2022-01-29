# you can write to stdout for debugging purposes, e.g.
# print("this is a debug message")

def solution(A):
    # write your code in Python 3.6
    local_extrema_count = 0
    length = len(A)
    if length == 1:
        return 1
    if length == 2:
        return 1 + (A[0] != A[1])
    size = 1
    prev_height = A[0]
    for i in range(1, length):
        if A[i] == prev_height:
            size += 1
            local_extrema_count += (A[i] > A[i - size] and A[i] > A[i + 1])
            local_extrema_count += (A[i] < A[i - size] and A[i] < A[i + 1])
        else:
            size = 1
            if i == length - 1:
                local_extrema_count += 1
                continue
            local_extrema_count += (A[i] > A[i - 1] and A[i] > A[i + 1])
            local_extrema_count += (A[i] < A[i - 1] and A[i] < A[i + 1])
            prev_height = A[i]
    return local_extrema_count


#
# print(solution([2, 2, 3, 4, 3, 3, 2, 2, 1, 1, 2, 5]))
#
# print(solution([-3, -3]))

def foo(arr):
    a = dict()
    # [[1,2,3,4], [5,6,7,8], [9,10,11,12]]
    assert (len(arr) > 0)
    rows = len(arr)
    cols = len(arr[0])
    print(cols, rows)
    curr_col = 0
    curr_row = 0
    diag_no = 0
    while curr_col < cols or curr_row < rows:
        print(arr[curr_row][curr_col])
        if curr_row + 1 >= curr_row or curr_col - 1 <= 0:
            curr_col = min(cols - 1, diag_no + 1)
            curr_row = min(0, diag_no - curr_col + 1)
            diag_no += 1
            print(curr_col, curr_row, diag_no)
        else:
            curr_row = curr_row + 1
            curr_col = curr_col - 1


foo([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
