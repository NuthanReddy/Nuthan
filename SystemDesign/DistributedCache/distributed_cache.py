"""
Distributed Cache (Redis-like) — Simulation
============================================
Demonstrates:
  - CacheNode with LRU eviction and TTL expiration (thread-safe)
  - CacheCluster with consistent hashing (virtual nodes)
  - GET / SET / DELETE operations across the cluster
  - Publish/subscribe messaging (Redis-style channels)
  - Eviction and expiration statistics
"""

from __future__ import annotations

import hashlib
import threading
import time
from bisect import bisect_right, insort
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Cache Entry
# ---------------------------------------------------------------------------

@dataclass
class CacheEntry:
    """Single key-value entry stored inside a cache node."""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    expire_at: Optional[float] = None  # absolute epoch; None = no expiry

    def is_expired(self) -> bool:
        return self.expire_at is not None and time.time() > self.expire_at

    def touch(self) -> None:
        self.last_accessed = time.time()


# ---------------------------------------------------------------------------
# Cache Node — LRU + TTL
# ---------------------------------------------------------------------------

class CacheNode:
    """
    In-memory cache node with:
      - LRU eviction (OrderedDict, items at the front are oldest)
      - TTL support (lazy expiration on access + active sweep)
    """

    def __init__(self, node_id: str, max_keys: int = 1000) -> None:
        self.node_id = node_id
        self.max_keys = max_keys
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        # Guards _store and the stat counters so a node can be shared
        # safely across worker threads. RLock lets public methods call
        # internal helpers (_remove/_evict_lru) without self-deadlock.
        self._lock = threading.RLock()

        # stats
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.expirations = 0
        self.sets = 0
        self.deletes = 0

    # -- public API ---------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value by key.  Returns None on miss or expiry."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                return None
            if entry.is_expired():
                self._remove(key)
                self.expirations += 1
                self.misses += 1
                return None
            # promote to most-recently-used end
            self._store.move_to_end(key)
            entry.touch()
            self.hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Insert or update a key.  Evicts LRU entries if capacity exceeded."""
        expire_at = (time.time() + ttl_seconds) if ttl_seconds else None

        with self._lock:
            if key in self._store:
                # update in-place, promote to MRU
                entry = self._store[key]
                entry.value = value
                entry.expire_at = expire_at
                entry.touch()
                self._store.move_to_end(key)
            else:
                # evict if at capacity
                while len(self._store) >= self.max_keys:
                    self._evict_lru()
                self._store[key] = CacheEntry(key=key, value=value, expire_at=expire_at)

            self.sets += 1

    def delete(self, key: str) -> bool:
        """Explicitly remove a key.  Returns True if the key existed."""
        with self._lock:
            if key in self._store:
                self._remove(key)
                self.deletes += 1
                return True
            return False

    def keys(self) -> list[str]:
        """Return all non-expired keys (triggers lazy expiration)."""
        with self._lock:
            expired = [k for k, e in self._store.items() if e.is_expired()]
            for k in expired:
                self._remove(k)
                self.expirations += 1
            return list(self._store.keys())

    def active_expire_sweep(self, sample_size: int = 20) -> int:
        """
        Active expiration: sample random keys and delete expired ones.
        Returns the number of keys expired in this sweep.
        """
        import random

        with self._lock:
            all_keys = list(self._store.keys())
            if not all_keys:
                return 0

            sample = random.sample(all_keys, min(sample_size, len(all_keys)))
            count = 0
            for k in sample:
                entry = self._store.get(k)
                if entry and entry.is_expired():
                    self._remove(k)
                    self.expirations += 1
                    count += 1
            return count

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total_ops = self.hits + self.misses
            hit_ratio = (self.hits / total_ops * 100) if total_ops else 0.0
            return {
                "node_id": self.node_id,
                "keys_stored": len(self._store),
                "max_keys": self.max_keys,
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio_pct": round(hit_ratio, 2),
                "evictions": self.evictions,
                "expirations": self.expirations,
                "sets": self.sets,
                "deletes": self.deletes,
            }

    # -- internals ----------------------------------------------------------

    def _evict_lru(self) -> None:
        """Remove the least-recently-used entry (front of OrderedDict)."""
        if self._store:
            key, _ = self._store.popitem(last=False)
            self.evictions += 1

    def _remove(self, key: str) -> None:
        self._store.pop(key, None)

    def __repr__(self) -> str:
        return f"CacheNode(id={self.node_id!r}, keys={len(self._store)}/{self.max_keys})"


# ---------------------------------------------------------------------------
# Consistent Hash Ring
# ---------------------------------------------------------------------------

class ConsistentHashRing:
    """
    Consistent hash ring with virtual nodes for even key distribution.
    Uses MD5 to map both nodes and keys onto a 2^32 ring.
    """

    def __init__(self, virtual_nodes: int = 150) -> None:
        self.virtual_nodes = virtual_nodes
        self._ring: list[int] = []            # sorted positions
        self._ring_map: dict[int, str] = {}   # position -> node_id
        self._nodes: set[str] = set()

    def add_node(self, node_id: str) -> None:
        if node_id in self._nodes:
            return
        self._nodes.add(node_id)
        for i in range(self.virtual_nodes):
            pos = self._hash(f"{node_id}#vnode_{i}")
            self._ring_map[pos] = node_id
            insort(self._ring, pos)

    def remove_node(self, node_id: str) -> None:
        if node_id not in self._nodes:
            return
        self._nodes.discard(node_id)
        positions_to_remove = [
            pos for pos, nid in self._ring_map.items() if nid == node_id
        ]
        for pos in positions_to_remove:
            del self._ring_map[pos]
            self._ring.remove(pos)

    def get_node(self, key: str) -> Optional[str]:
        """Return the node_id responsible for *key*."""
        if not self._ring:
            return None
        h = self._hash(key)
        idx = bisect_right(self._ring, h) % len(self._ring)
        return self._ring_map[self._ring[idx]]

    @property
    def node_ids(self) -> set[str]:
        return set(self._nodes)

    @staticmethod
    def _hash(value: str) -> int:
        digest = hashlib.md5(value.encode()).hexdigest()
        return int(digest, 16) % (2 ** 32)

    def __repr__(self) -> str:
        return (
            f"ConsistentHashRing(nodes={len(self._nodes)}, "
            f"vnodes_per_node={self.virtual_nodes}, "
            f"ring_size={len(self._ring)})"
        )


# ---------------------------------------------------------------------------
# Cache Cluster
# ---------------------------------------------------------------------------

class CacheCluster:
    """
    Distributed cache cluster built on top of a consistent hash ring.
    Routes GET/SET/DELETE to the correct CacheNode automatically.
    """

    def __init__(self, virtual_nodes: int = 150) -> None:
        self.ring = ConsistentHashRing(virtual_nodes=virtual_nodes)
        self._nodes: dict[str, CacheNode] = {}
        # Pub/Sub: channel name -> list of subscriber callbacks.
        # Guarded by its own lock so publishing from one thread while
        # another subscribes is safe.
        self._channels: dict[str, list[Callable[[str, Any], None]]] = {}
        self._pubsub_lock = threading.RLock()

    def add_node(self, node: CacheNode) -> None:
        self._nodes[node.node_id] = node
        self.ring.add_node(node.node_id)

    def remove_node(self, node_id: str) -> None:
        self.ring.remove_node(node_id)
        self._nodes.pop(node_id, None)

    def get(self, key: str) -> Optional[Any]:
        node = self._route(key)
        if node is None:
            return None
        return node.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        node = self._route(key)
        if node is None:
            raise RuntimeError("No cache nodes available")
        node.set(key, value, ttl_seconds=ttl_seconds)

    def delete(self, key: str) -> bool:
        node = self._route(key)
        if node is None:
            return False
        return node.delete(key)

    def cluster_stats(self) -> dict[str, Any]:
        per_node = {nid: n.stats() for nid, n in self._nodes.items()}
        total_hits = sum(s["hits"] for s in per_node.values())
        total_misses = sum(s["misses"] for s in per_node.values())
        total_ops = total_hits + total_misses
        return {
            "total_nodes": len(self._nodes),
            "total_keys": sum(s["keys_stored"] for s in per_node.values()),
            "total_hits": total_hits,
            "total_misses": total_misses,
            "hit_ratio_pct": round(total_hits / total_ops * 100, 2) if total_ops else 0.0,
            "total_evictions": sum(s["evictions"] for s in per_node.values()),
            "total_expirations": sum(s["expirations"] for s in per_node.values()),
            "per_node": per_node,
        }

    # -- pub/sub ------------------------------------------------------------

    def subscribe(self, channel: str, callback: Callable[[str, Any], None]) -> None:
        """Register *callback* to receive every message published to *channel*.

        The callback is invoked as ``callback(channel, message)``.  This mirrors
        Redis SUBSCRIBE and is independent of the key/value store above.
        """
        with self._pubsub_lock:
            self._channels.setdefault(channel, []).append(callback)

    def unsubscribe(self, channel: str, callback: Callable[[str, Any], None]) -> bool:
        """Remove a previously registered *callback*.  Returns True if removed."""
        with self._pubsub_lock:
            subscribers = self._channels.get(channel)
            if not subscribers or callback not in subscribers:
                return False
            subscribers.remove(callback)
            if not subscribers:
                del self._channels[channel]
            return True

    def publish(self, channel: str, message: Any) -> int:
        """Publish *message* to all subscribers of *channel* (fan-out).

        Returns the number of subscribers that received the message.  A copy of
        the subscriber list is taken under the lock so callbacks run without
        holding it (a slow/faulty subscriber can't block publishers).
        """
        with self._pubsub_lock:
            subscribers = list(self._channels.get(channel, []))
        for callback in subscribers:
            callback(channel, message)
        return len(subscribers)

    # -- internals ----------------------------------------------------------

    def _route(self, key: str) -> Optional[CacheNode]:
        node_id = self.ring.get_node(key)
        if node_id is None:
            return None
        return self._nodes.get(node_id)

    def __repr__(self) -> str:
        return f"CacheCluster(nodes={len(self._nodes)}, ring={self.ring})"


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def demo() -> None:
    """End-to-end demonstration of the distributed cache."""

    # ---- 1. Build a 3-node cluster ----------------------------------------
    _print_section("1. Build a 3-node cluster (max 5 keys each for demo)")
    cluster = CacheCluster(virtual_nodes=50)
    for i in range(1, 4):
        node = CacheNode(node_id=f"node-{i}", max_keys=5)
        cluster.add_node(node)
        print(f"  Added {node}")

    # ---- 2. SET keys -------------------------------------------------------
    _print_section("2. SET 12 keys (will trigger LRU evictions)")
    for i in range(1, 13):
        key = f"user:{i}"
        value = f"profile_data_{i}"
        cluster.set(key, value)
        node_id = cluster.ring.get_node(key)
        print(f"  SET {key:10s} -> routed to {node_id}")

    # ---- 3. GET keys -------------------------------------------------------
    _print_section("3. GET a few keys")
    for key in ["user:1", "user:5", "user:10", "user:99"]:
        result = cluster.get(key)
        status = result if result else "<MISS>"
        print(f"  GET {key:10s} -> {status}")

    # ---- 4. TTL expiration -------------------------------------------------
    _print_section("4. TTL expiration (0.3 s)")
    cluster.set("session:abc", "token_xyz", ttl_seconds=0.3)
    print(f"  SET session:abc with TTL=0.3s")
    val = cluster.get("session:abc")
    print(f"  GET session:abc immediately -> {val}")
    time.sleep(0.4)
    val = cluster.get("session:abc")
    print(f"  GET session:abc after 0.4s  -> {val if val else '<EXPIRED>'}")

    # ---- 5. DELETE ---------------------------------------------------------
    _print_section("5. DELETE")
    cluster.set("temp:key", "will_be_deleted")
    print(f"  SET temp:key")
    deleted = cluster.delete("temp:key")
    print(f"  DEL temp:key -> deleted={deleted}")
    print(f"  GET temp:key -> {cluster.get('temp:key') or '<MISS>'}")

    # ---- 6. Key distribution -----------------------------------------------
    _print_section("6. Key distribution across nodes")
    for nid, node in sorted(cluster._nodes.items()):
        print(f"  {nid}: {node.keys()}")

    # ---- 7. Cluster stats --------------------------------------------------
    _print_section("7. Cluster statistics")
    stats = cluster.cluster_stats()
    print(f"  Total nodes      : {stats['total_nodes']}")
    print(f"  Total keys       : {stats['total_keys']}")
    print(f"  Total hits       : {stats['total_hits']}")
    print(f"  Total misses     : {stats['total_misses']}")
    print(f"  Hit ratio        : {stats['hit_ratio_pct']}%")
    print(f"  Total evictions  : {stats['total_evictions']}")
    print(f"  Total expirations: {stats['total_expirations']}")
    print()
    for nid, ns in sorted(stats["per_node"].items()):
        print(f"  [{nid}] keys={ns['keys_stored']}/{ns['max_keys']}  "
              f"hits={ns['hits']}  misses={ns['misses']}  "
              f"evictions={ns['evictions']}  expirations={ns['expirations']}")

    # ---- 8. Node addition (rebalancing demo) -------------------------------
    _print_section("8. Add node-4 and observe routing change")
    cluster.add_node(CacheNode(node_id="node-4", max_keys=5))
    print(f"  Added node-4")
    for key in ["user:1", "user:5", "user:10"]:
        new_node = cluster.ring.get_node(key)
        print(f"  {key:10s} now routes to {new_node}")

    # ---- 9. Publish/Subscribe ---------------------------------------------
    _print_section("9. Publish/Subscribe (cache invalidation channel)")
    received: list[str] = []
    cluster.subscribe("invalidate", lambda ch, msg: received.append(msg))
    cluster.subscribe("invalidate", lambda ch, msg: print(f"  [subscriber] {ch}: {msg}"))
    delivered = cluster.publish("invalidate", "user:1")
    delivered += cluster.publish("invalidate", "user:5")
    print(f"  Published 2 messages, each delivered to {delivered // 2} subscribers")
    print(f"  Collector received: {received}")

    print("\n--- Demo complete ---\n")


if __name__ == "__main__":
    demo()
