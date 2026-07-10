"""Tests for the dependency-free Weighted Rendezvous (HRW) hashing module.

Covers determinism (all clients agree), weighted distribution, and the
minimal-remapping property when a node is removed.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from SystemDesign.Utils.RendezvousHashing import (
    Node,
    determine_responsible_node,
    int_to_float,
)


class TestScoring:
    def test_int_to_float_in_unit_interval(self) -> None:
        for v in [0, 1, 2 ** 32, 2 ** 63, 2 ** 64 - 1]:
            f = int_to_float(v)
            assert 0.0 <= f < 1.0

    def test_score_is_deterministic(self) -> None:
        node = Node("n1", seed=7)
        assert node.compute_weighted_score("key") == node.compute_weighted_score("key")


class TestResponsibleNode:
    def test_empty_nodes_returns_none(self) -> None:
        assert determine_responsible_node([], "key") is None

    def test_deterministic_assignment(self) -> None:
        nodes = [Node(f"n{i}", seed=i) for i in range(5)]
        for key in [f"key-{i}" for i in range(200)]:
            first = determine_responsible_node(nodes, key)
            # A different Node object list with the same identities must agree.
            same = determine_responsible_node(list(nodes), key)
            assert first.name == same.name

    def test_all_keys_assigned_to_a_real_node(self) -> None:
        nodes = [Node(f"n{i}", seed=i) for i in range(4)]
        names = {n.name for n in nodes}
        for i in range(500):
            owner = determine_responsible_node(nodes, f"k{i}")
            assert owner.name in names

    def test_single_node_wins_everything(self) -> None:
        solo = Node("solo")
        for i in range(100):
            assert determine_responsible_node([solo], f"k{i}").name == "solo"


class TestDistributionAndRemapping:
    def _assign(self, nodes: list[Node], keys: list[str]) -> dict[str, str]:
        return {k: determine_responsible_node(nodes, k).name for k in keys}

    def test_weighted_node_gets_more_keys(self) -> None:
        nodes = [
            Node("A", seed=1, weight=1.0),
            Node("B", seed=2, weight=1.0),
            Node("C", seed=3, weight=3.0),  # 3x weight
        ]
        keys = [f"key-{i}" for i in range(6000)]
        assignment = self._assign(nodes, keys)
        counts: dict[str, int] = {}
        for owner in assignment.values():
            counts[owner] = counts.get(owner, 0) + 1
        # The heavily weighted node should clearly win the most keys.
        assert counts["C"] > counts["A"]
        assert counts["C"] > counts["B"]

    def test_removal_only_moves_owned_keys(self) -> None:
        nodes = [Node(f"n{i}", seed=i) for i in range(5)]
        keys = [f"key-{i}" for i in range(5000)]
        before = self._assign(nodes, keys)

        remaining = [n for n in nodes if n.name != "n2"]
        after = self._assign(remaining, keys)

        moved = sum(1 for k in keys if before[k] != after[k])
        owned_by_removed = sum(1 for k in keys if before[k] == "n2")
        # HRW guarantees ONLY keys owned by the removed node move.
        assert moved == owned_by_removed

    def test_adding_node_only_steals_keys(self) -> None:
        nodes = [Node(f"n{i}", seed=i) for i in range(4)]
        keys = [f"key-{i}" for i in range(4000)]
        before = self._assign(nodes, keys)

        expanded = nodes + [Node("n_new", seed=99)]
        after = self._assign(expanded, keys)

        # Every key that moved must have moved TO the new node (nothing reshuffles
        # among the pre-existing nodes).
        for k in keys:
            if before[k] != after[k]:
                assert after[k] == "n_new"
