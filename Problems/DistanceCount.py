matrix = [
    [1, 0, 1, 0, 1],
    [0, 1, 1, 0, 0],
    [1, 1, 0, 1, 0],
    [1, 0, 1, 0, 1],
    [0, 1, 0, 1, 0]
]



'''
result = [
    [2, 4, 3, 3, 1],
    [4, 6, 5, 4, 2],
    [4, 6, 5, 4, 2],
    [4, 5, 5, 4, 3],
    [2, 3, 3, 3, 2]
]
'''


def count_neighbours(input):
    rows = len(input)
    if rows == 0:
        return input
    cols = len(input[0])
    output = [[0 for x in range(cols + 2)] for x in range(rows + 2)]
    indices = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,0), (0,1), (1,-1), (1,0), (1,1)]
    for r in range(rows):
        for c in range(cols):
            output[r][c] = sum([safe_get(input, r+x, c+y) for (x, y) in indices])
            print(output)
    return [x for x in output[1:-1]]


def safe_get(input, r, c):
    rows = len(input)
    cols = len(input[0])
    if 0 <= r < rows and 0 <= c < cols:
        return input[r][c]
    else:
        return 0


print(count_neighbours(matrix))