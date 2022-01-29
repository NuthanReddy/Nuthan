def fibonacci(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    prev_fib = 0
    curr_fib = 1
    for _ in range(n - 1):
        new_fib = curr_fib + prev_fib
        prev_fib = curr_fib
        curr_fib = new_fib
    return curr_fib


for i in range(10):
    print(fibonacci(i))
