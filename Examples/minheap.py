import heapq


min_heap = []  # Create an empty heap
heapq.heappush(min_heap, 5)  # Push an element onto the heap
heapq.heappush(min_heap, 2)
heapq.heappush(min_heap, 8)

# Pop the smallest element from the heap
print(heapq.heappop(min_heap))  # Output: 2
# Peek at the smallest element without popping it
print(min_heap[0])  # Output: 5
# Add more elements
heapq.heappush(min_heap, 1)
# Pop all elements in sorted order
while min_heap:
    print(heapq.heappop(min_heap))  # Output: 1, 5, 8
