def is_safe(x, y, N, M):
    return 0 <= x < N and 0 <= y < M and maze[x][y] == 1


def solve_maze(x, y, solution):
    N = len(solution)
    M = len(solution[0])
    if x == N - 1 and y == M - 1:
        solution[x][y] = 1
        return True

    if is_safe(x, y, N, M):
        solution[x][y] = 1
        print("")
        print("before", x, y)
        print_maze(solution)
        if solve_maze(x + 1, y, solution):
            return True
        if solve_maze(x, y + 1, solution):
            return True
        solution[x][y] = 0  # Backtrack
        print("after", x, y)
        print_maze(solution)

    return False


def print_maze(maze):
    for row in maze:
        print(" ".join(map(str, row)))


if __name__ == "__main__":
    maze = [
        [1, 0, 0, 0],
        [1, 1, 0, 1],
        [0, 1, 0, 0],
        [1, 1, 1, 1]
    ]
    if solve_maze(0, 0, maze):
        print("")
        print_maze(maze)
    else:
        print("No solution found")
