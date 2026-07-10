"""
SSTable (Sorted String Table) + LSM Tree Implementation

An LSM (Log-Structured Merge) tree storage engine that provides:
- Fast writes via an in-memory sorted buffer (MemTable)
- Durability via a write-ahead log (WAL) replayed on restart (crash recovery)
- Persistent storage via immutable SSTable files on disk
- Efficient reads using sparse indexes and right-sized bloom filters
- Background compaction to merge and clean up SSTables
- Thread-safe public API (put/get/delete/compact) via a reentrant lock

Architecture:
    Write Path: Client → MemTable (sorted, in-memory) → flush to SSTable on disk
    Read Path:  Client → MemTable → SSTable files (newest first) using sparse index
    Compaction:  Merge multiple SSTables → single compacted SSTable, removing tombstones

Time Complexity:
    - Write: O(log n) where n = memtable size (red-black tree / sorted dict)
    - Read:  O(log n) memtable + O(log k) per SSTable via sparse index (k = index entries)
    - Compaction: O(n) merge of sorted runs

Space Complexity:
    - MemTable: O(n) in memory
    - SSTable: O(n) on disk per table, O(sqrt(n)) sparse index in memory
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Sentinel value for deleted keys
TOMBSTONE = "__TOMBSTONE__"


@dataclass
class SSTableEntry:
    """A single key-value entry with a timestamp for versioning."""
    key: str
    value: str
    timestamp: float = field(default_factory=time.time)

    def is_deleted(self) -> bool:
        return self.value == TOMBSTONE

    def to_dict(self) -> dict:
        return {"key": self.key, "value": self.value, "timestamp": self.timestamp}

    @staticmethod
    def from_dict(d: dict) -> "SSTableEntry":
        return SSTableEntry(key=d["key"], value=d["value"], timestamp=d["timestamp"])


class BloomFilter:
    """
    Simple bloom filter to quickly check if a key might exist in an SSTable.

    Uses multiple hash functions to set bits in a bit array.
    False positives are possible; false negatives are not.
    """

    def __init__(self, size: int = 1024, num_hashes: int = 3):
        self.size = size
        self.num_hashes = num_hashes
        self.bit_array = [False] * size

    @classmethod
    def optimal(cls, expected_items: int, false_positive_rate: float = 0.01) -> "BloomFilter":
        """Build a bloom filter sized for ``expected_items`` at a target FP rate.

        Uses the standard formulas:
            m = ceil(-(n * ln p) / (ln 2)^2)   # number of bits
            k = round((m / n) * ln 2)          # number of hash functions

        A fixed 1024-bit filter saturates once n approaches ~1000 keys (its
        false-positive rate climbs toward 100%, defeating the point of the
        filter). Sizing ``m`` from ``n`` keeps the FP rate at ``p`` regardless of
        how many keys the SSTable holds.
        """
        n = max(1, expected_items)
        p = min(max(false_positive_rate, 1e-6), 0.5)
        m = max(8, math.ceil(-(n * math.log(p)) / (math.log(2) ** 2)))
        k = max(1, round((m / n) * math.log(2)))
        return cls(size=m, num_hashes=k)

    def _hashes(self, key: str) -> list[int]:
        """Generate multiple hash positions for a key."""
        positions = []
        for i in range(self.num_hashes):
            h = hashlib.md5(f"{key}:{i}".encode()).hexdigest()
            positions.append(int(h, 16) % self.size)
        return positions

    def add(self, key: str) -> None:
        for pos in self._hashes(key):
            self.bit_array[pos] = True

    def might_contain(self, key: str) -> bool:
        return all(self.bit_array[pos] for pos in self._hashes(key))

    def to_list(self) -> list[bool]:
        return self.bit_array

    @staticmethod
    def from_list(bits: list[bool], num_hashes: int = 3) -> "BloomFilter":
        bf = BloomFilter(size=len(bits), num_hashes=num_hashes)
        bf.bit_array = bits
        return bf


class SparseIndex:
    """
    Sparse index that maps sampled keys to their byte offset in the SSTable file.

    Instead of indexing every key, we sample every `interval` keys.
    To find a key, binary search the index to find the nearest preceding entry,
    then scan forward from that offset.
    """

    def __init__(self, interval: int = 16):
        self.interval = interval
        self.entries: list[tuple[str, int]] = []  # (key, byte_offset)

    def add(self, key: str, offset: int) -> None:
        self.entries.append((key, offset))

    def find_offset(self, key: str) -> int:
        """Return the byte offset to start scanning from for the given key."""
        if not self.entries:
            return 0
        lo, hi = 0, len(self.entries) - 1
        result = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.entries[mid][0] <= key:
                result = self.entries[mid][1]
                lo = mid + 1
            else:
                hi = mid - 1
        return result

    def to_list(self) -> list[list]:
        return [[k, off] for k, off in self.entries]

    @staticmethod
    def from_list(data: list[list], interval: int = 16) -> "SparseIndex":
        idx = SparseIndex(interval=interval)
        idx.entries = [(k, off) for k, off in data]
        return idx


class SSTable:
    """
    An immutable sorted string table stored on disk.

    File format:
        - One JSON-encoded entry per line, sorted by key
        - Accompanied by a metadata file (.meta) containing the sparse index
          and bloom filter for fast lookups
    """

    def __init__(self, filepath: str, sparse_index: SparseIndex, bloom: BloomFilter):
        self.filepath = filepath
        self.sparse_index = sparse_index
        self.bloom = bloom

    def get(self, key: str) -> Optional[SSTableEntry]:
        """
        Look up a key in this SSTable.

        Returns the entry if found, None otherwise.
        Uses bloom filter for fast negative lookups, then sparse index
        to find the right region, then linear scan.
        """
        if not self.bloom.might_contain(key):
            return None

        offset = self.sparse_index.find_offset(key)
        try:
            with open(self.filepath, "r") as f:
                f.seek(offset)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = SSTableEntry.from_dict(json.loads(line))
                    if entry.key == key:
                        return entry
                    if entry.key > key:
                        break
        except FileNotFoundError:
            pass
        return None

    @staticmethod
    def flush_to_disk(
        entries: dict[str, SSTableEntry],
        filepath: str,
        index_interval: int = 16,
    ) -> "SSTable":
        """
        Write sorted entries to an SSTable file and create its metadata.

        Args:
            entries: Dict of key -> SSTableEntry (will be sorted by key)
            filepath: Path to write the SSTable data file
            index_interval: How often to sample keys for the sparse index

        Returns:
            SSTable instance ready for reads
        """
        bloom = BloomFilter.optimal(len(entries) or 1)
        sparse_index = SparseIndex(interval=index_interval)

        sorted_keys = sorted(entries.keys())
        with open(filepath, "w") as f:
            for i, key in enumerate(sorted_keys):
                entry = entries[key]
                bloom.add(key)
                offset = f.tell()
                if i % index_interval == 0:
                    sparse_index.add(key, offset)
                f.write(json.dumps(entry.to_dict()) + "\n")

        # Write metadata (sparse index + bloom filter)
        meta_path = filepath + ".meta"
        meta = {
            "sparse_index": sparse_index.to_list(),
            "bloom_filter": bloom.to_list(),
            "index_interval": index_interval,
            "num_hashes": bloom.num_hashes,
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        return SSTable(filepath, sparse_index, bloom)

    @staticmethod
    def load_from_disk(filepath: str) -> "SSTable":
        """Load an SSTable and its metadata from disk."""
        meta_path = filepath + ".meta"
        with open(meta_path, "r") as f:
            meta = json.load(f)
        sparse_index = SparseIndex.from_list(
            meta["sparse_index"], meta.get("index_interval", 16)
        )
        bloom = BloomFilter.from_list(
            meta["bloom_filter"], meta.get("num_hashes", 3)
        )
        return SSTable(filepath, sparse_index, bloom)

    def all_entries(self) -> list[SSTableEntry]:
        """Read all entries from this SSTable (used during compaction)."""
        results = []
        with open(self.filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(SSTableEntry.from_dict(json.loads(line)))
        return results


class MemTable:
    """
    In-memory sorted buffer that accepts writes before flushing to disk.

    Uses a Python dict (backed by insertion-order preservation) with
    sorted flush. Provides O(1) average writes and O(n log n) flush.
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.entries: dict[str, SSTableEntry] = {}

    def put(self, key: str, value: str) -> None:
        self.entries[key] = SSTableEntry(key=key, value=value)

    def put_entry(self, entry: SSTableEntry) -> None:
        """Insert a pre-built entry (used for WAL replay and timestamp fidelity)."""
        self.entries[entry.key] = entry

    def delete(self, key: str) -> None:
        """Mark a key as deleted with a tombstone."""
        self.entries[key] = SSTableEntry(key=key, value=TOMBSTONE)

    def get(self, key: str) -> Optional[SSTableEntry]:
        return self.entries.get(key)

    def is_full(self) -> bool:
        return len(self.entries) >= self.max_size

    def clear(self) -> None:
        self.entries.clear()

    def __len__(self) -> int:
        return len(self.entries)


class LSMTree:
    """
    Log-Structured Merge Tree storage engine.

    Coordinates writes through a MemTable, flushes to SSTables on disk,
    reads across all levels, and runs compaction to merge SSTables.

    Usage:
        >>> import tempfile, os
        >>> db_dir = tempfile.mkdtemp()
        >>> db = LSMTree(data_dir=db_dir, memtable_size=3)
        >>> db.put("name", "Alice")
        >>> db.put("age", "30")
        >>> db.get("name")
        'Alice'
        >>> db.delete("age")
        >>> db.get("age") is None
        True
        >>> db.close()
    """

    def __init__(self, data_dir: str = "./lsm_data", memtable_size: int = 1000):
        self.data_dir = data_dir
        self.memtable_size = memtable_size
        self.memtable = MemTable(max_size=memtable_size)
        self.sstables: list[SSTable] = []  # newest first
        self._sstable_counter = 0
        # Reentrant: put()/delete() may call _flush() while holding the lock.
        self._lock = threading.RLock()
        self.wal_path = os.path.join(data_dir, "wal.log")
        self._wal_file = None

        os.makedirs(data_dir, exist_ok=True)
        self._load_existing_sstables()
        # Replay any writes that were in the MemTable but not yet flushed when
        # the process last stopped (crash recovery), then open the WAL for
        # appending new writes.
        self._recover_from_wal()
        self._wal_file = open(self.wal_path, "a", encoding="utf-8")

    def _load_existing_sstables(self) -> None:
        """Load any existing SSTable files from the data directory."""
        meta_files = sorted(Path(self.data_dir).glob("*.meta"), reverse=True)
        for meta_file in meta_files:
            data_file = str(meta_file)[: -len(".meta")]
            if os.path.exists(data_file):
                self.sstables.append(SSTable.load_from_disk(data_file))
                # Track counter to avoid filename collisions
                name = Path(data_file).stem
                if name.startswith("sstable_"):
                    try:
                        num = int(name.split("_")[1])
                        self._sstable_counter = max(self._sstable_counter, num + 1)
                    except (ValueError, IndexError):
                        pass

    def put(self, key: str, value: str) -> None:
        """
        Write a key-value pair. Flushes MemTable to disk if full.

        The write is appended to the write-ahead log (and fsync'd) before being
        applied to the MemTable, so it survives a crash before the next flush.

        Args:
            key: The key to store
            value: The value to associate with the key
        """
        with self._lock:
            entry = SSTableEntry(key=key, value=value)
            self._append_wal(entry)
            self.memtable.put_entry(entry)
            if self.memtable.is_full():
                self._flush()

    def delete(self, key: str) -> None:
        """
        Delete a key by writing a tombstone marker.

        The actual removal happens during compaction.
        """
        with self._lock:
            entry = SSTableEntry(key=key, value=TOMBSTONE)
            self._append_wal(entry)
            self.memtable.put_entry(entry)
            if self.memtable.is_full():
                self._flush()

    def get(self, key: str) -> Optional[str]:
        """
        Read a value by key.

        Search order: MemTable → SSTables (newest to oldest).
        Returns None if the key doesn't exist or has been deleted.
        """
        with self._lock:
            # Check memtable first
            entry = self.memtable.get(key)
            if entry is not None:
                return None if entry.is_deleted() else entry.value

            # Check SSTables from newest to oldest
            for sstable in self.sstables:
                entry = sstable.get(key)
                if entry is not None:
                    return None if entry.is_deleted() else entry.value

            return None

    def _flush(self) -> None:
        """Flush the current MemTable to a new SSTable on disk."""
        if len(self.memtable) == 0:
            return

        filepath = os.path.join(self.data_dir, f"sstable_{self._sstable_counter:010d}")
        self._sstable_counter += 1

        sstable = SSTable.flush_to_disk(self.memtable.entries, filepath)
        self.sstables.insert(0, sstable)  # newest first
        self.memtable.clear()
        # The flushed writes are now durable in the SSTable, so the WAL that was
        # protecting them can be truncated.
        self._truncate_wal()

    # -- write-ahead log ----------------------------------------------------

    def _append_wal(self, entry: SSTableEntry) -> None:
        """Append an entry to the WAL and fsync so it survives a crash."""
        if self._wal_file is None:
            return
        self._wal_file.write(json.dumps(entry.to_dict()) + "\n")
        self._wal_file.flush()
        os.fsync(self._wal_file.fileno())

    def _truncate_wal(self) -> None:
        """Reset the WAL after a successful flush (its entries are now on disk)."""
        if self._wal_file is not None:
            self._wal_file.close()
        # Truncate to empty, then reopen for appending.
        open(self.wal_path, "w", encoding="utf-8").close()
        self._wal_file = open(self.wal_path, "a", encoding="utf-8")

    def _recover_from_wal(self) -> None:
        """Replay un-flushed WAL entries back into the MemTable on startup."""
        if not os.path.exists(self.wal_path):
            return
        recovered = 0
        with open(self.wal_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = SSTableEntry.from_dict(json.loads(line))
                except (json.JSONDecodeError, KeyError):
                    continue  # skip a torn final record from a mid-write crash
                self.memtable.put_entry(entry)
                recovered += 1
        if recovered:
            print(f"[WAL] recovered {recovered} un-flushed entr(y|ies) from {self.wal_path}")

    def compact(self) -> None:
        """
        Merge all SSTables into a single compacted SSTable.

        - Keeps only the latest version of each key (by timestamp)
        - Removes tombstoned entries
        - Replaces all existing SSTables with one merged file
        """
        with self._lock:
            if len(self.sstables) < 2:
                return

            # Collect all entries from all SSTables
            merged: dict[str, SSTableEntry] = {}
            # Process oldest first so newer entries overwrite older ones
            for sstable in reversed(self.sstables):
                for entry in sstable.all_entries():
                    if entry.key not in merged or entry.timestamp >= merged[entry.key].timestamp:
                        merged[entry.key] = entry

            # Remove tombstones
            live_entries = {k: v for k, v in merged.items() if not v.is_deleted()}

            # Write compacted SSTable
            filepath = os.path.join(self.data_dir, f"sstable_{self._sstable_counter:010d}")
            self._sstable_counter += 1
            new_sstable = SSTable.flush_to_disk(live_entries, filepath)

            # Remove old SSTable files
            for sstable in self.sstables:
                try:
                    os.remove(sstable.filepath)
                    os.remove(sstable.filepath + ".meta")
                except FileNotFoundError:
                    pass

            self.sstables = [new_sstable]

    def close(self) -> None:
        """Flush any remaining MemTable data to disk and close the WAL."""
        with self._lock:
            self._flush()
            if self._wal_file is not None:
                self._wal_file.close()
                self._wal_file = None

    def __repr__(self) -> str:
        return (
            f"LSMTree(data_dir='{self.data_dir}', "
            f"memtable_entries={len(self.memtable)}, "
            f"sstables={len(self.sstables)})"
        )


if __name__ == "__main__":
    import tempfile
    import shutil

    db_dir = tempfile.mkdtemp(prefix="lsm_")
    print(f"Using temp directory: {db_dir}")

    db = LSMTree(data_dir=db_dir, memtable_size=5)
    print(f"Created: {db}")

    # Write some data
    sample_data = {
        "user:1": "Alice",
        "user:2": "Bob",
        "user:3": "Charlie",
        "user:4": "Diana",
        "user:5": "Eve",
        "user:6": "Frank",
        "user:7": "Grace",
        "config:timeout": "30",
        "config:retries": "3",
        "session:abc": "active",
    }

    print("\n--- Writing data ---")
    for k, v in sample_data.items():
        db.put(k, v)
        print(f"  PUT {k} = {v}")

    print(f"\nState after writes: {db}")

    # Read back
    print("\n--- Reading data ---")
    for key in ["user:1", "user:5", "config:timeout", "nonexistent"]:
        val = db.get(key)
        print(f"  GET {key} = {val}")

    # Delete and verify
    print("\n--- Deleting user:2 ---")
    db.delete("user:2")
    print(f"  GET user:2 = {db.get('user:2')}")  # Should be None

    # Update and verify
    print("\n--- Updating user:1 ---")
    db.put("user:1", "Alice Updated")
    print(f"  GET user:1 = {db.get('user:1')}")

    # Compact
    print(f"\n--- Before compaction: {len(db.sstables)} SSTables ---")
    db.compact()
    print(f"--- After compaction: {len(db.sstables)} SSTables ---")

    # Verify data after compaction
    print("\n--- Reads after compaction ---")
    print(f"  GET user:1 = {db.get('user:1')}")  # Alice Updated
    print(f"  GET user:2 = {db.get('user:2')}")  # None (deleted)
    print(f"  GET user:3 = {db.get('user:3')}")  # Charlie

    db.close()

    # Cleanup
    shutil.rmtree(db_dir)
    print(f"\nCleaned up {db_dir}")

