import heapq

# Define the priority queue
priority_queue = []

# Adding elements to the priority queue (lower number indicates higher priority)
heapq.heappush(priority_queue, (3, "Low priority task"))  # priority 3
heapq.heappush(priority_queue, (1, "High priority task"))  # priority 1
heapq.heappush(priority_queue, (2, "Medium priority task"))  # priority 2

# Processing elements based on priority
while priority_queue:
    priority, task = heapq.heappop(priority_queue)
    print(f"Processing task: '{task}' with priority: {priority}")