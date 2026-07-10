#!/usr/bin/env python3
"""
Rendezvous (Highest Random Weight) Hashing
==========================================
Rendezvous hashing (a.k.a. HRW — Highest Random Weight) assigns each key to
exactly one of N nodes such that:

  - Every client independently agrees on the same node for a given key
    (no coordination needed), and
  - When a node is added or removed, only the keys that node "wins" (or lost)
    move — roughly ``K / N`` keys — the same minimal-disruption property that
    consistent hashing provides.

For each (node, key) pair we compute a deterministic pseudo-random score and
assign the key to the node with the highest score. This variant is *weighted*:
a node's score is scaled so that a node with weight ``2w`` attracts, on average,
twice as many keys as a node with weight ``w`` (Weighted Rendezvous Hashing,
Schindelhauer & Schomaker).

Hashing uses the standard-library ``hashlib`` (MD5) so the module has no
third-party dependencies, keeping it consistent with the rest of this repo.

Complexity:
    - Lookup: O(n) — every node is scored for each key. Consistent hashing is
      O(log n) per lookup, so HRW trades lookup speed for simpler, index-free
      code and naturally even weighted placement. HRW shines when N is small
      (tens of nodes) or when weighted distribution matters.

Run:
    uv run --no-project python SystemDesign\\Utils\\RendezvousHashing.py
"""

from __future__ import annotations

import hashlib
import math
from typing import Iterable, Optional

# Mask selecting the low 53 bits — the mantissa width of an IEEE-754 double.
_FIFTY_THREE_ONES = 0xFFFFFFFFFFFFFFFF >> (64 - 53)
_FIFTY_THREE_ZEROS = float(1 << 53)


def int_to_float(value: int) -> float:
    """Map a uniformly random 64-bit integer to a uniform float in [0, 1)."""
    return (value & _FIFTY_THREE_ONES) / _FIFTY_THREE_ZEROS


def _hash64(key: str, seed: int) -> int:
    """Return a deterministic unsigned 64-bit hash of ``key`` salted by ``seed``.

    Uses MD5 over ``"<seed>:<key>"`` and folds the first 8 digest bytes into a
    64-bit integer. Deterministic and dependency-free (replaces the previous
    ``mmh3`` dependency).
    """
    digest = hashlib.md5(f"{seed}:{key}".encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


class Node:
    """A node that competes for keys in a weighted rendezvous hash."""

    def __init__(self, name: str, seed: int = 0, weight: float = 1.0) -> None:
        self.name = name
        self.seed = seed
        self.weight = weight

    def __str__(self) -> str:
        return f"[{self.name} (seed={self.seed}, weight={self.weight})]"

    def __repr__(self) -> str:
        return f"Node(name={self.name!r}, seed={self.seed}, weight={self.weight})"

    def compute_weighted_score(self, key: str) -> float:
        """Deterministic weighted HRW score for ``key`` on this node.

        The raw hash is mapped to ``h in [0, 1)`` and transformed by
        ``1 / -ln(h)``; scaling by ``weight`` yields Weighted Rendezvous
        Hashing, where a node's expected key share is proportional to its
        weight.
        """
        h = int_to_float(_hash64(str(key), self.seed))
        # Guard against h == 0.0 (log(0) is undefined); nudge to a tiny epsilon.
        if h <= 0.0:
            h = 1e-18
        score = 1.0 / -math.log(h)
        return self.weight * score


def determine_responsible_node(nodes: Iterable[Node], key: str) -> Optional[Node]:
    """Return the node responsible for ``key`` (highest weighted score).

    Returns ``None`` if ``nodes`` is empty. Ties (astronomically unlikely) are
    broken deterministically by node name so all clients agree.
    """
    champion: Optional[Node] = None
    highest_score = -1.0
    for node in nodes:
        score = node.compute_weighted_score(key)
        if score > highest_score or (
            score == highest_score
            and champion is not None
            and node.name < champion.name
        ):
            champion, highest_score = node, score
    return champion


def _demo() -> None:
    """Show placement, weighting, and minimal remapping on node removal."""
    nodes = [
        Node("node-A", seed=1, weight=1.0),
        Node("node-B", seed=2, weight=1.0),
        Node("node-C", seed=3, weight=2.0),  # double weight -> ~2x the keys
    ]
    keys = [f"key-{i}" for i in range(10_000)]

    def assign(active: list[Node]) -> dict[str, str]:
        return {k: determine_responsible_node(active, k).name for k in keys}

    print("=" * 56)
    print("  Weighted Rendezvous Hashing — distribution (10k keys)")
    print("=" * 56)
    before = assign(nodes)
    counts: dict[str, int] = {}
    for owner in before.values():
        counts[owner] = counts.get(owner, 0) + 1
    for node in nodes:
        pct = counts.get(node.name, 0) / len(keys) * 100
        print(f"  {node.name} (weight={node.weight}): {counts.get(node.name, 0):>5} keys ({pct:4.1f}%)")
    print("  Note: node-C has weight 2.0 and should win ~2x the keys of A/B.")

    print("\n" + "=" * 56)
    print("  Minimal remapping when node-B is removed")
    print("=" * 56)
    remaining = [n for n in nodes if n.name != "node-B"]
    after = assign(remaining)
    moved = sum(1 for k in keys if before[k] != after[k])
    b_keys = sum(1 for k in keys if before[k] == "node-B")
    print(f"  Keys previously on node-B : {b_keys}")
    print(f"  Keys that changed owner   : {moved}")
    print(f"  Keys NOT on node-B moved  : {moved - b_keys} (should be 0)")
    assert moved == b_keys, "only keys owned by the removed node should move"
    print("\n  [OK] Only keys owned by the removed node were remapped.")


if __name__ == "__main__":
    _demo()
