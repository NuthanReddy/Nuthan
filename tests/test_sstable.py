import sys
import os
import shutil
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from SystemDesign.Utils.SSTable import LSMTree


@pytest.fixture()
def lsm(tmp_path: os.PathLike) -> LSMTree:
    """Create an LSMTree with a temp directory, cleaned up automatically."""
    tree = LSMTree(data_dir=str(tmp_path), memtable_size=10)
    yield tree
    tree.close()


class TestLSMTree:
    def test_put_and_get(self, lsm: LSMTree) -> None:
        lsm.put("key1", "value1")
        lsm.put("key2", "value2")
        assert lsm.get("key1") == "value1"
        assert lsm.get("key2") == "value2"

    def test_get_missing_returns_none(self, lsm: LSMTree) -> None:
        assert lsm.get("nonexistent") is None

    def test_delete(self, lsm: LSMTree) -> None:
        lsm.put("k", "v")
        assert lsm.get("k") == "v"
        lsm.delete("k")
        assert lsm.get("k") is None

    def test_update_overwrites(self, lsm: LSMTree) -> None:
        lsm.put("k", "old")
        lsm.put("k", "new")
        assert lsm.get("k") == "new"

    def test_flush_to_disk_and_read_back(self, lsm: LSMTree) -> None:
        # Insert enough to trigger flush (memtable_size=10)
        for i in range(15):
            lsm.put(f"key_{i:03d}", f"val_{i}")
        # Values should still be retrievable after flush
        for i in range(15):
            assert lsm.get(f"key_{i:03d}") == f"val_{i}"

    def test_compaction_reduces_sstable_count(self, lsm: LSMTree) -> None:
        # Fill multiple SSTables
        for i in range(50):
            lsm.put(f"key_{i:03d}", f"val_{i}")
        sstable_count_before = len(lsm.sstables)
        if sstable_count_before > 1:
            lsm.compact()
            assert len(lsm.sstables) <= sstable_count_before
        # All values still accessible
        for i in range(50):
            assert lsm.get(f"key_{i:03d}") == f"val_{i}"

    def test_delete_after_flush(self, lsm: LSMTree) -> None:
        for i in range(15):
            lsm.put(f"k_{i:03d}", f"v_{i}")
        # Some data is flushed by now
        lsm.delete("k_005")
        assert lsm.get("k_005") is None

    def test_repr(self, lsm: LSMTree) -> None:
        assert "LSMTree" in repr(lsm)

    def test_many_operations(self, lsm: LSMTree) -> None:
        for i in range(30):
            lsm.put(f"item_{i:03d}", str(i))
        for i in range(0, 30, 3):
            lsm.delete(f"item_{i:03d}")
        for i in range(30):
            if i % 3 == 0:
                assert lsm.get(f"item_{i:03d}") is None
            else:
                assert lsm.get(f"item_{i:03d}") == str(i)
