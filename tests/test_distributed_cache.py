"""Tests for the DistributedCache additions: Redis-style pub/sub fan-out and
thread-safe cluster operations.

Basic key/value routing is exercised too, but the focus is the newly added
pub/sub channel support and lock safety.
"""

import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from SystemDesign.DistributedCache.distributed_cache import CacheCluster, CacheNode


@pytest.fixture()
def cluster() -> CacheCluster:
    c = CacheCluster(virtual_nodes=50)
    for i in range(3):
        c.add_node(CacheNode(f"node-{i}"))
    return c


class TestRouting:
    def test_set_get_roundtrip(self, cluster: CacheCluster) -> None:
        cluster.set("user:1", {"name": "Alice"})
        assert cluster.get("user:1") == {"name": "Alice"}

    def test_get_missing_returns_none(self, cluster: CacheCluster) -> None:
        assert cluster.get("does-not-exist") is None

    def test_delete(self, cluster: CacheCluster) -> None:
        cluster.set("k", "v")
        assert cluster.delete("k") is True
        assert cluster.get("k") is None

    def test_set_with_no_nodes_raises(self) -> None:
        empty = CacheCluster()
        with pytest.raises(RuntimeError):
            empty.set("k", "v")


class TestPubSub:
    def test_publish_fans_out_to_all_subscribers(self, cluster: CacheCluster) -> None:
        received_a: list[tuple[str, object]] = []
        received_b: list[tuple[str, object]] = []
        cluster.subscribe("news", lambda ch, msg: received_a.append((ch, msg)))
        cluster.subscribe("news", lambda ch, msg: received_b.append((ch, msg)))

        count = cluster.publish("news", "hello")

        assert count == 2
        assert received_a == [("news", "hello")]
        assert received_b == [("news", "hello")]

    def test_publish_to_channel_without_subscribers(self, cluster: CacheCluster) -> None:
        assert cluster.publish("empty-channel", "x") == 0

    def test_subscribers_are_channel_scoped(self, cluster: CacheCluster) -> None:
        sports: list[object] = []
        cluster.subscribe("sports", lambda ch, msg: sports.append(msg))
        cluster.publish("weather", "sunny")
        assert sports == []
        cluster.publish("sports", "goal")
        assert sports == ["goal"]

    def test_unsubscribe_stops_delivery(self, cluster: CacheCluster) -> None:
        got: list[object] = []
        cb = lambda ch, msg: got.append(msg)
        cluster.subscribe("ch", cb)

        assert cluster.unsubscribe("ch", cb) is True
        assert cluster.publish("ch", "after-unsub") == 0
        assert got == []

    def test_unsubscribe_unknown_callback_returns_false(self, cluster: CacheCluster) -> None:
        assert cluster.unsubscribe("ch", lambda ch, msg: None) is False


class TestThreadSafety:
    def test_concurrent_publish_and_subscribe(self, cluster: CacheCluster) -> None:
        counter = {"n": 0}
        lock = threading.Lock()

        def on_msg(_ch: str, _msg: object) -> None:
            with lock:
                counter["n"] += 1

        # One thread keeps subscribing while another publishes; must not raise
        # (the pub/sub lock guards the channel dict).
        stop = threading.Event()

        def subscriber_churn() -> None:
            while not stop.is_set():
                cluster.subscribe("live", on_msg)
                cluster.unsubscribe("live", on_msg)

        churn = threading.Thread(target=subscriber_churn)
        churn.start()
        try:
            for _ in range(500):
                cluster.publish("live", "tick")
        finally:
            stop.set()
            churn.join()
        # No assertion on exact count (race by design); the point is no crash.

    def test_concurrent_writes_do_not_corrupt(self, cluster: CacheCluster) -> None:
        def writer(base: int) -> None:
            for i in range(base, base + 200):
                cluster.set(f"key_{i}", i)

        threads = [threading.Thread(target=writer, args=(b * 200,)) for b in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        for i in range(800):
            assert cluster.get(f"key_{i}") == i
