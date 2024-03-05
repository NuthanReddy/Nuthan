# There is a square field which is full of trees planted in a grid.
# Each tree takes up one position and has a height between `0` and `10`.
#
# You are tasked with hanging an electric wire that runs straight over the field.
# The wire may enter the field from the north (vertically) or west (horizontally) direction.
# The wire can only pass above trees that are of a lesser height.
# The wire hangs at the same height for its entire length over the field.
#
# Write a program that takes as input the height of each tree in the field.
# It should return the direction (`N` or `W`) and the index from which the wire should enter the field,
# so that it is hanging closest to the ground.

arr = [[3, 2, 4, 4], [5, 6, 3, 4], [2, 1, 4, 5], [5, 2, 1, 3]]


4
# 2nd-3, 3rd-4 - 0,1 cols out
# 1,2,3

# 3 2
# 6 6

row_maxs = [4, 6, 5, 5]
#4 - row1
#W - 0th index

col_maxs = [5, 6, 4, 5]
# 4 - col3
# N 2


def pull_the_wire(arr):
    min_row_heigth = None
    min_row_index = 0
    no_of_rows = len(arr)

    row_max_indices = {}
    for row_n in range(no_of_rows):
        curr_row_max = arr[row_n][0]
        curr_row_sec_max = None
        for col_n in range(no_of_rows):
            if curr_row_max < arr[row_n][col_n]:
                if curr_row_sec_max is None:
                    row_max_indices[row_n] = col_n
                curr_row_sec_max = curr_row_max
                curr_row_max = col_n        
        if min_row_heigth is None or min_row_heigth > curr_row_sec_max:
            min_row_heigth = curr_row_sec_max
            min_row_index = row_n

    min_col_height = None
    min_col_index = 0
    col_max_indices = {}
    for col_n in range(no_of_rows):
        curr_col_max = arr[0][col_n]
        curr_col_sec_max = None
        for row_n in range(no_of_rows):
            if curr_col_max < arr[row_n][col_n]:
                if curr_col_sec_max is None:
                    col_max_indices[col_n] = row_n
                curr_col_sec_max = curr_col_max
                curr_col_max = col_n
        if min_col_height is None or min_col_height > curr_col_sec_max:
            min_col_height = curr_col_sec_max
            min_col_index = col_n

    print(row_max_indices)
    print(col_max_indices)
    if min_row_heigth <= min_col_height:
        print("W", min_row_index)
    else:
        print("N", min_col_index)


pull_the_wire(arr)