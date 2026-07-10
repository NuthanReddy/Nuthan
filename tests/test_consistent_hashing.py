import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from SystemDesign.Utils.ConsistentHashing import ConsistentHashRing, Node


class TestConsistentHashRing:
    def test_add_node_and_get_node(self) -> None:
        ring = ConsistentHashRing(num_replicas=50)
        n1 = Node("server1", "10.0.0.1", 8080)
        n2 = Node("server2", "10.0.0.2", 8080)
        ring.add_node(n1)
        ring.add_node(n2)
        result = ring.get_node("my_key")
        assert result in (n1, n2)

    def test_get_node_empty_ring_returns_none(self) -> None:
        ring = ConsistentHashRing()
        assert ring.get_node("key") is None

    def test_remove_node_minimal_remapping(self) -> None:
        ring = ConsistentHashRing(num_replicas=150)
        nodes = [Node(f"s{i}") for i in range(5)]
        for n in nodes:
            ring.add_node(n)

        keys = [f"key_{i}" for i in range(1000)]
        before = {k: ring.get_node(k) for k in keys}

        ring.remove_node(nodes[2])  # remove one of 5 nodes
        after = {k: ring.get_node(k) for k in keys}

        moved = sum(1 for k in keys if before[k] != after[k])
        # Ideally ~1/N (20%) keys move; allow up to 40% for variance
        assert moved < 400, f"{moved}/1000 keys moved, expected ~200"

    def test_get_nodes_returns_distinct(self) -> None:
        ring = ConsistentHashRing(num_replicas=50)
        nodes = [Node(f"s{i}") for i in range(5)]
        for n in nodes:
            ring.add_node(n)
        result = ring.get_nodes("some_key", count=3)
        assert len(result) == 3
        assert len(set(n.name for n in result)) == 3

    def test_get_nodes_more_than_available(self) -> None:
        ring = ConsistentHashRing(num_replicas=50)
        n1 = Node("only_server")
        ring.add_node(n1)
        result = ring.get_nodes("key", count=5)
        # Can only return 1 distinct node
        assert len(result) == 1

    def test_len(self) -> None:
        ring = ConsistentHashRing(num_replicas=50)
        assert len(ring) == 0
        ring.add_node(Node("s1"))
        assert len(ring) == 1
        ring.add_node(Node("s2"))
        assert len(ring) == 2

    def test_single_node_all_keys(self) -> None:
        ring = ConsistentHashRing()
        n = Node("solo")
        ring.add_node(n)
        for i in range(100):
            assert ring.get_node(f"k{i}") == n

    def test_distribution(self) -> None:
        ring = ConsistentHashRing(num_replicas=150)
        nodes = [Node(f"server_{i}") for i in range(3)]
        for n in nodes:
            ring.add_node(n)
        keys = [f"key_{i}" for i in range(3000)]
        dist = ring.get_distribution(keys)
        # Each node should get roughly 1000 keys; allow wide margin
        for n in nodes:
            assert dist.get(n.name, 0) > 500, f"{n.name} got too few keys"

    def test_repr(self) -> None:
        ring = ConsistentHashRing()
        ring.add_node(Node("test"))
        assert "ConsistentHashRing" in repr(ring)
