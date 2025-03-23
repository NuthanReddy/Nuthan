from time import time


def fib(n):
    if n==0:
        return 1
    if n==1:
        return 1
    return fib(n-2) +fib(n-1)


def fib2(n):
    dp = [0]*(n+1)
    dp[0] = 1
    dp[1] = 1

    for i in range(2, n+1):
        dp[i] = dp[i-1] + dp[i-2]

    return dp[n]


fib_arr = [1, 1]


def fib3(n):
    global fib_arr
    l = len(fib_arr)

    for i in range(l, n+1):
        fib_arr.append(fib_arr[i-2]+ fib_arr[i-1])
    return fib_arr[n]


print("Bottom Up - Global")
t1 = time()
print(fib3(1000))
t2 = time()
print(f'Function fib3 executed in {(t2 - t1):.4f}s')

t1 = time()
print(fib3(1001))
t2 = time()
print(f'Function fib3 - run2 executed in {(t2 - t1):.4f}s')
print("")

print("Bottom Up")
t1 = time()
print(fib2(1000))
t2 = time()
print(f'Function fib2 executed in {(t2 - t1):.4f}s')

t1 = time()
print(fib2(1001))
t2 = time()
print(f'Function fib2 - run2 executed in {(t2 - t1):.4f}s')

print("")

print("Top Down")
t1 = time()
print(fib(30))
t2 = time()
print(f'Function fib executed in {(t2 - t1):.4f}s')
