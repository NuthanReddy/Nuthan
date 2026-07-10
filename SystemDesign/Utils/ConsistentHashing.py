"""
Consistent Hashing Implementation

A consistent hash ring that distributes keys across nodes with minimal
redistribution when nodes are added or removed.

Key concepts:
    - Hash Ring: A circular space [0, 2^32) where both nodes and keys are mapped
    - Virtual Nodes: Each physical node maps to multiple positions on the ring
      for better load distribution
    - Clockwise Lookup: A key is assigned to the first node found clockwise
      from its hash position

Time Complexity:
    - Lookup:       O(log n) where n = total virtual nodes (binary search)
    - Add node:     O(v * n) — v virtual-node inserts, each an O(n) bisect.insort.
                    The binary search is O(log n) but the underlying list shift
                    to keep _sorted_keys ordered dominates at O(n).
    - Remove node:  O(v * n) — same O(n) list-shift cost per virtual node.

Thread-safety:
    All public operations are guarded by an RLock so the ring can be shared
    across worker threads (add/remove/lookup are internally consistent).

Space Complexity:
    - O(n * v) for the ring positions
"""

from __future__ import annotations

import bisect
import hashlib
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional


def _hash(key: str) -> int:
    """Hash a string to a position on the ring [0, 2^32)."""
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**32)


@dataclass
class Node:
    """Represents a physical node (server) in the hash ring."""
    name: str
    host: str = ""
    port: int = 0

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        return self.name == other.name

    def __repr__(self) -> str:
        if self.host:
            return f"Node({self.name}, {self.host}:{self.port})"
        return f"Node({self.name})"


class ConsistentHashRing:
    """
    A consistent hash ring with virtual nodes for balanced key distribution.

    Each physical node is mapped to `num_replicas` virtual positions on the
    ring. Keys are assigned to the nearest node clockwise from their hash.

    Usage:
        >>> ring = ConsistentHashRing(num_replicas=3)
        >>> ring.add_node(Node("server-1"))
        >>> ring.add_node(Node("server-2"))
        >>> ring.add_node(Node("server-3"))
        >>> ring.get_node("my-key")
        Node(server-...)
        >>> ring.get_node("another-key")
        Node(server-...)
    """

    def __init__(self, num_replicas: int = 150):
        """
        Args:
            num_replicas: Number of virtual nodes per physical node.
                          Higher values give better distribution but use more memory.
        """
        self.num_replicas = num_replicas
        self._ring: dict[int, Node] = {}
        self._sorted_keys: list[int] = []
        self._nodes: set[Node] = set()
        # Reentrant so read methods can be called while holding the lock.
        self._lock = threading.RLock()

    @property
    def nodes(self) -> set[Node]:
        """Return the set of physical nodes in the ring."""
        with self._lock:
            return self._nodes.copy()

    def add_node(self, node: Node) -> None:
        """
        Add a physical node to the ring with its virtual replicas.

        Args:
            node: The node to add
        """
        with self._lock:
            if node in self._nodes:
                return
            self._nodes.add(node)
            for i in range(self.num_replicas):
                virtual_key = f"{node.name}:vnode{i}"
                hash_val = _hash(virtual_key)
                self._ring[hash_val] = node
                bisect.insort(self._sorted_keys, hash_val)

    def remove_node(self, node: Node) -> None:
        """
        Remove a physical node and all its virtual replicas from the ring.

        Args:
            node: The node to remove
        """
        with self._lock:
            if node not in self._nodes:
                return
            self._nodes.discard(node)
            for i in range(self.num_replicas):
                virtual_key = f"{node.name}:vnode{i}"
                hash_val = _hash(virtual_key)
                if hash_val in self._ring:
                    del self._ring[hash_val]
                    idx = bisect.bisect_left(self._sorted_keys, hash_val)
                    if idx < len(self._sorted_keys) and self._sorted_keys[idx] == hash_val:
                        self._sorted_keys.pop(idx)

    def get_node(self, key: str) -> Optional[Node]:
        """
        Find the node responsible for the given key.

        Hashes the key and walks clockwise to find the first node.

        Args:
            key: The key to look up

        Returns:
            The responsible Node, or None if the ring is empty
        """
        with self._lock:
            if not self._ring:
                return None

            hash_val = _hash(key)
            idx = bisect.bisect_right(self._sorted_keys, hash_val)
            # Wrap around if past the last position
            if idx == len(self._sorted_keys):
                idx = 0
            return self._ring[self._sorted_keys[idx]]

    def get_nodes(self, key: str, count: int = 1) -> list[Node]:
        """
        Get multiple distinct nodes for a key (useful for replication).

        Walks clockwise from the key's position and collects distinct
        physical nodes.

        Args:
            key: The key to look up
            count: Number of distinct nodes to return

        Returns:
            List of up to `count` distinct Nodes
        """
        with self._lock:
            if not self._ring:
                return []

            count = min(count, len(self._nodes))
            result: list[Node] = []
            seen: set[str] = set()

            hash_val = _hash(key)
            idx = bisect.bisect_right(self._sorted_keys, hash_val)

            checked = 0
            total_positions = len(self._sorted_keys)
            while len(result) < count and checked < total_positions:
                pos = idx % total_positions
                node = self._ring[self._sorted_keys[pos]]
                if node.name not in seen:
                    seen.add(node.name)
                    result.append(node)
                idx += 1
                checked += 1

            return result

    def get_distribution(self, keys: list[str]) -> dict[str, int]:
        """
        Analyze how keys are distributed across nodes.

        Args:
            keys: List of keys to analyze

        Returns:
            Dict mapping node name to count of assigned keys
        """
        distribution: dict[str, int] = defaultdict(int)
        for key in keys:
            node = self.get_node(key)
            if node:
                distribution[node.name] += 1
        return dict(distribution)

    def __len__(self) -> int:
        """Return the number of physical nodes."""
        return len(self._nodes)

    def __repr__(self) -> str:
        return (
            f"ConsistentHashRing(nodes={len(self._nodes)}, "
            f"replicas={self.num_replicas}, "
            f"ring_positions={len(self._sorted_keys)})"
        )


if __name__ == "__main__":
    ring = ConsistentHashRing(num_replicas=150)

    # Add servers
    servers = [
        Node("server-1", "10.0.0.1", 8080),
        Node("server-2", "10.0.0.2", 8080),
        Node("server-3", "10.0.0.3", 8080),
        Node("server-4", "10.0.0.4", 8080),
        Node("server-5", "10.0.0.5", 8080),
    ]

    print("--- Adding servers ---")
    for server in servers:
        ring.add_node(server)
        print(f"  Added {server}")
    print(f"Ring: {ring}")

    # Generate test keys and check distribution
    test_keys = [f"user:{i}" for i in range(10000)]
    dist = ring.get_distribution(test_keys)

    print("\n--- Key distribution (10,000 keys across 5 servers) ---")
    for name, count in sorted(dist.items()):
        pct = count / len(test_keys) * 100
        bar = "█" * int(pct / 2)
        print(f"  {name}: {count:5d} ({pct:.1f}%) {bar}")

    # Show key assignments
    print("\n--- Sample key lookups ---")
    sample_keys = ["user:42", "session:abc", "config:timeout", "order:12345"]
    for key in sample_keys:
        node = ring.get_node(key)
        replicas = ring.get_nodes(key, count=3)
        print(f"  {key} → {node.name} (replicas: {[n.name for n in replicas]})")

    # Remove a server and check redistribution
    print(f"\n--- Removing {servers[2].name} ---")
    before = {k: ring.get_node(k).name for k in test_keys}
    ring.remove_node(servers[2])
    after = {k: ring.get_node(k).name for k in test_keys}

    moved = sum(1 for k in test_keys if before[k] != after[k])
    print(f"  Keys remapped: {moved}/{len(test_keys)} ({moved/len(test_keys)*100:.1f}%)")
    print(f"  (Ideal: ~{100/len(servers):.1f}% of keys should move)")

    dist_after = ring.get_distribution(test_keys)
    print("\n--- Distribution after removal ---")
    for name, count in sorted(dist_after.items()):
        pct = count / len(test_keys) * 100
        bar = "█" * int(pct / 2)
        print(f"  {name}: {count:5d} ({pct:.1f}%) {bar}")

