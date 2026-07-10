"""Tests for the SSTable additions: write-ahead log crash recovery, right-sized
bloom filters, and thread-safe concurrent writes.

These complement ``test_sstable.py`` (which covers basic put/get/delete/compaction).
"""

import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from SystemDesign.Utils.SSTable import BloomFilter, LSMTree


class TestBloomFilterSizing:
    def test_optimal_scales_bits_with_item_count(self) -> None:
        small = BloomFilter.optimal(10)
        large = BloomFilter.optimal(10_000)
        # More expected items must allocate more bits.
        assert large.size > small.size
        assert small.num_hashes >= 1
        assert large.num_hashes >= 1

    def test_optimal_keeps_false_positive_rate_low_at_scale(self) -> None:
        n = 1000
        bf = BloomFilter.optimal(n, false_positive_rate=0.01)
        for i in range(n):
            bf.add(f"key_{i}")
        # No false negatives allowed.
        for i in range(n):
            assert bf.might_contain(f"key_{i}")
        # Measure false-positive rate on keys that were never added.
        false_positives = sum(1 for i in range(n, n + 2000) if bf.might_contain(f"key_{i}"))
        fp_rate = false_positives / 2000
        # A fixed 1024-bit filter would saturate (~100% FP) at n=1000; the
        # right-sized filter should stay well under 5%.
        assert fp_rate < 0.05, f"false-positive rate too high: {fp_rate:.2%}"

    def test_optimal_handles_zero_items(self) -> None:
        bf = BloomFilter.optimal(0)
        assert bf.size >= 8
        assert bf.num_hashes >= 1


class TestWriteAheadLog:
    def test_recovers_unflushed_writes_after_crash(self, tmp_path) -> None:
        data_dir = str(tmp_path)
        # memtable_size high enough that these writes never flush -> they live
        # only in the WAL, exactly the data a crash would otherwise lose.
        tree = LSMTree(data_dir=data_dir, memtable_size=100)
        tree.put("a", "1")
        tree.put("b", "2")
        tree.put("a", "1-updated")
        # Simulate a crash: close only the OS file handle, never call close().
        tree._wal_file.close()
        del tree

        recovered = LSMTree(data_dir=data_dir, memtable_size=100)
        assert recovered.get("a") == "1-updated"
        assert recovered.get("b") == "2"
        recovered.close()

    def test_recovers_tombstones(self, tmp_path) -> None:
        data_dir = str(tmp_path)
        tree = LSMTree(data_dir=data_dir, memtable_size=100)
        tree.put("keep", "yes")
        tree.put("gone", "temp")
        tree.delete("gone")
        tree._wal_file.close()
        del tree

        recovered = LSMTree(data_dir=data_dir, memtable_size=100)
        assert recovered.get("keep") == "yes"
        assert recovered.get("gone") is None  # tombstone survived recovery
        recovered.close()

    def test_wal_truncated_after_flush(self, tmp_path) -> None:
        data_dir = str(tmp_path)
        tree = LSMTree(data_dir=data_dir, memtable_size=5)
        # Write enough to force at least one flush.
        for i in range(12):
            tree.put(f"k{i:03d}", f"v{i}")
        # After a flush the WAL only holds the still-in-memtable tail, so it must
        # be smaller than the total number of writes.
        wal_lines = sum(1 for _ in open(tree.wal_path, encoding="utf-8"))
        assert wal_lines < 12
        tree.close()

    def test_clean_close_then_reopen_reads_from_sstables(self, tmp_path) -> None:
        data_dir = str(tmp_path)
        tree = LSMTree(data_dir=data_dir, memtable_size=5)
        for i in range(20):
            tree.put(f"k{i:03d}", f"v{i}")
        tree.close()  # flushes remaining memtable to an SSTable

        reopened = LSMTree(data_dir=data_dir, memtable_size=5)
        for i in range(20):
            assert reopened.get(f"k{i:03d}") == f"v{i}"
        reopened.close()


class TestThreadSafety:
    def test_concurrent_writes_are_all_persisted(self, tmp_path) -> None:
        tree = LSMTree(data_dir=str(tmp_path), memtable_size=25)
        errors: list[Exception] = []

        def writer(start: int) -> None:
            try:
                for i in range(start, start + 100):
                    tree.put(f"key_{i:05d}", str(i))
            except Exception as exc:  # pragma: no cover - fail loudly if raised
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(base * 100,)) for base in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"writer threads raised: {errors}"
        for i in range(400):
            assert tree.get(f"key_{i:05d}") == str(i)
        tree.close()
