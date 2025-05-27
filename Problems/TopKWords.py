import hashlib
import heapq


class CountMinSketch:
    def __init__(self, width, depth):
        self.width = width
        self.depth = depth
        self.table = [[0] * width for _ in range(depth)]
        self.hash_functions = [lambda x, seed=i: int(hashlib.md5((str(x) + str(seed)).encode()).hexdigest(), 16) % width
                               for i in range(depth)]

    def update(self, word):
        for i, h in enumerate(self.hash_functions):
            self.table[i][h(word)] += 1

    def query(self, word):
        return min(self.table[i][h(word)] for i, h in enumerate(self.hash_functions))


def get_top_k_words(descriptions, k):
    sketch = CountMinSketch(width=1000, depth=5)
    word_freq = {}

    for desc in descriptions:
        words = desc.lower().split()
        for word in words:
            sketch.update(word)
            word_freq[word] = sketch.query(word)

    # Using min-heap to track top-K words
    top_k_words = heapq.nlargest(k, word_freq.items(), key=lambda x: x[1])
    return top_k_words


# Example Usage
amazon_descriptions = [
    "This smartphone has an excellent battery life and camera.",
    "Amazing battery performance with fast charging support.",
    "Camera quality is outstanding with AI-enhanced features."
]

top_words = get_top_k_words(amazon_descriptions, k=5)
print(top_words)
