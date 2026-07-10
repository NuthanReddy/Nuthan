"""
Message Queue (Kafka-like) Implementation

A simplified in-memory message queue system modeled after Apache Kafka.
Demonstrates core concepts: topics, partitions (append-only logs), producers,
consumers, consumer groups with offset tracking, and group rebalancing.

Key concepts:
    - Topic:          A named feed of messages, divided into partitions
    - Partition:      An ordered, append-only log of messages with offsets
    - Producer:       Publishes messages to topics using key-based or
                      round-robin partitioning
    - Consumer:       Reads messages from assigned partitions, tracks offsets
    - Consumer Group: A set of consumers that cooperatively consume a topic;
                      each partition is assigned to exactly one consumer in the group

Architecture:
    Producer --[key hash / round-robin]--> Partition (append-only log)
    Consumer Group --> rebalance --> each consumer gets subset of partitions
    Consumer --> poll(partition) --> messages from committed offset onward

Time Complexity:
    - Produce:     O(1) amortized (append to partition log)
    - Consume:     O(k) where k = number of messages fetched
    - Rebalance:   O(P) where P = number of partitions in the topic

Space Complexity:
    - O(M) total where M = total messages across all partitions
    - O(P * G) for offset tracking (P partitions, G consumer groups)
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Message:
    """A single message in a partition log."""
    key: Optional[str]
    value: str
    timestamp: float = field(default_factory=time.time)
    headers: dict[str, str] = field(default_factory=dict)
    topic: str = ""
    partition: int = -1
    offset: int = -1

    def __repr__(self) -> str:
        key_str = self.key or "None"
        val_preview = self.value[:40] + "..." if len(self.value) > 40 else self.value
        return (
            f"Message(key={key_str}, value={val_preview}, "
            f"topic={self.topic}, partition={self.partition}, offset={self.offset})"
        )


class OffsetResetPolicy(Enum):
    EARLIEST = "earliest"
    LATEST = "latest"


class AckMode(Enum):
    FIRE_AND_FORGET = 0   # acks=0
    LEADER_ONLY = 1       # acks=1
    ALL_REPLICAS = -1     # acks=all


# ---------------------------------------------------------------------------
# Partition: append-only log
# ---------------------------------------------------------------------------

class Partition:
    """
    An ordered, append-only log of messages.

    Each message is assigned a monotonically increasing offset starting from 0.
    Supports retention by max message count.

    Usage:
        >>> p = Partition(topic="orders", partition_id=0)
        >>> offset = p.append(Message(key="k1", value="order-created"))
        >>> msgs = p.read(start_offset=0, max_count=10)
        >>> len(msgs)
        1
    """

    def __init__(
        self,
        topic: str,
        partition_id: int,
        max_retention_count: int = 100_000,
    ):
        self.topic = topic
        self.partition_id = partition_id
        self.max_retention_count = max_retention_count

        self._log: list[Message] = []
        self._lock = threading.Lock()
        # Tracks the offset of the first message in _log
        # (shifts forward when retention trims old messages)
        self._base_offset: int = 0

    @property
    def log_start_offset(self) -> int:
        """Earliest available offset."""
        return self._base_offset

    @property
    def log_end_offset(self) -> int:
        """Next offset to be written (one past the last message)."""
        return self._base_offset + len(self._log)

    def append(self, message: Message) -> int:
        """
        Append a message to the log and return its offset.

        Automatically applies retention if the log exceeds max_retention_count.
        """
        with self._lock:
            offset = self._base_offset + len(self._log)
            message.topic = self.topic
            message.partition = self.partition_id
            message.offset = offset
            self._log.append(message)
            self._apply_retention()
            return offset

    def read(self, start_offset: int, max_count: int = 100) -> list[Message]:
        """
        Read up to max_count messages starting from start_offset.

        Returns an empty list if start_offset is beyond the log end.
        Clamps start_offset to log_start_offset if it falls below.
        """
        with self._lock:
            if start_offset < self._base_offset:
                start_offset = self._base_offset
            if start_offset >= self.log_end_offset:
                return []

            idx = start_offset - self._base_offset
            return list(self._log[idx: idx + max_count])

    def _apply_retention(self) -> None:
        """Trim old messages if log exceeds retention count."""
        if len(self._log) > self.max_retention_count:
            excess = len(self._log) - self.max_retention_count
            self._log = self._log[excess:]
            self._base_offset += excess

    def __len__(self) -> int:
        return len(self._log)

    def __repr__(self) -> str:
        return (
            f"Partition(topic={self.topic}, id={self.partition_id}, "
            f"offsets=[{self.log_start_offset}, {self.log_end_offset}))"
        )


# ---------------------------------------------------------------------------
# Topic
# ---------------------------------------------------------------------------

class Topic:
    """
    A named message feed divided into multiple partitions.

    Usage:
        >>> t = Topic("orders", num_partitions=3)
        >>> t.partitions[0].append(Message(key="k", value="v"))
        0
    """

    def __init__(self, name: str, num_partitions: int = 4):
        if num_partitions < 1:
            raise ValueError("A topic must have at least 1 partition")
        self.name = name
        self.num_partitions = num_partitions
        self.partitions: list[Partition] = [
            Partition(topic=name, partition_id=i) for i in range(num_partitions)
        ]

    def get_partition(self, key: Optional[str]) -> Partition:
        """
        Select a partition for a message by key.

        If a key is provided, it is consistently hashed (MD5) to a partition so
        that all messages sharing a key land on the same partition (preserving
        per-key ordering).

        If ``key`` is None this returns partition 0 as a deterministic fallback.
        Note: the ``Producer`` never relies on that fallback for keyless
        messages — it round-robins across partitions itself (see
        ``Producer.send``), which is why the return type is always a
        ``Partition`` rather than ``Optional[Partition]``.
        """
        if key is not None:
            h = int(hashlib.md5(key.encode()).hexdigest(), 16)
            return self.partitions[h % self.num_partitions]
        return self.partitions[0]

    def __repr__(self) -> str:
        total = sum(len(p) for p in self.partitions)
        return f"Topic({self.name}, partitions={self.num_partitions}, messages={total})"


# ---------------------------------------------------------------------------
# Producer
# ---------------------------------------------------------------------------

class Producer:
    """
    Publishes messages to topics.

    Supports key-based partitioning (messages with the same key go to the
    same partition) and round-robin partitioning for keyless messages.

    Usage:
        >>> topic = Topic("orders", num_partitions=3)
        >>> producer = Producer()
        >>> producer.send(topic, key="user-1", value="order-created")
        Message(...)
    """

    def __init__(self, ack_mode: AckMode = AckMode.LEADER_ONLY):
        self.ack_mode = ack_mode
        self._round_robin_counters: dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
        self.messages_sent: int = 0

    def send(
        self,
        topic: Topic,
        value: str,
        key: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Message:
        """
        Send a message to a topic.

        Args:
            topic:   Target topic
            value:   Message payload
            key:     Partition routing key (optional). Same key -> same partition.
            headers: Optional key-value metadata

        Returns:
            The Message with its assigned topic, partition, and offset.
        """
        message = Message(
            key=key,
            value=value,
            headers=headers or {},
        )

        if key is not None:
            partition = topic.get_partition(key)
        else:
            # Round-robin for keyless messages
            with self._lock:
                idx = self._round_robin_counters[topic.name] % topic.num_partitions
                self._round_robin_counters[topic.name] = idx + 1
            partition = topic.partitions[idx]

        partition.append(message)
        self.messages_sent += 1
        return message

    def __repr__(self) -> str:
        return f"Producer(ack_mode={self.ack_mode.name}, sent={self.messages_sent})"


# ---------------------------------------------------------------------------
# Consumer Group + Consumer
# ---------------------------------------------------------------------------

class Consumer:
    """
    A consumer that reads messages from assigned partitions.

    Maintains per-partition offsets and supports commit/seek operations.
    Consumers should be used within a ConsumerGroup for coordinated consumption.
    """

    def __init__(
        self,
        consumer_id: str,
        group_id: str,
        auto_offset_reset: OffsetResetPolicy = OffsetResetPolicy.EARLIEST,
    ):
        self.consumer_id = consumer_id
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset

        # Assigned partitions (set by consumer group during rebalance)
        self.assigned_partitions: list[Partition] = []
        # Committed offsets: partition key (topic-partition_id) -> offset
        self._committed_offsets: dict[str, int] = {}
        # Current read position (may be ahead of committed)
        self._current_offsets: dict[str, int] = {}

    def _partition_key(self, partition: Partition) -> str:
        return f"{partition.topic}-{partition.partition_id}"

    def poll(self, max_records: int = 100) -> list[Message]:
        """
        Fetch messages from all assigned partitions.

        Returns up to max_records messages total, round-robin across partitions.
        Advances the current offset but does NOT auto-commit.
        """
        all_messages: list[Message] = []
        per_partition = max(1, max_records // max(len(self.assigned_partitions), 1))

        for partition in self.assigned_partitions:
            pkey = self._partition_key(partition)

            if pkey not in self._current_offsets:
                # Initialize offset based on reset policy
                if self.auto_offset_reset == OffsetResetPolicy.EARLIEST:
                    self._current_offsets[pkey] = partition.log_start_offset
                else:
                    self._current_offsets[pkey] = partition.log_end_offset

            start = self._current_offsets[pkey]
            messages = partition.read(start_offset=start, max_count=per_partition)
            if messages:
                self._current_offsets[pkey] = messages[-1].offset + 1
                all_messages.extend(messages)

        return all_messages[:max_records]

    def commit(self) -> dict[str, int]:
        """
        Commit current offsets for all assigned partitions.

        Returns the committed offsets.
        """
        committed = {}
        for partition in self.assigned_partitions:
            pkey = self._partition_key(partition)
            if pkey in self._current_offsets:
                self._committed_offsets[pkey] = self._current_offsets[pkey]
                committed[pkey] = self._current_offsets[pkey]
        return committed

    def seek(self, partition: Partition, offset: int) -> None:
        """Seek to a specific offset in a partition."""
        pkey = self._partition_key(partition)
        self._current_offsets[pkey] = offset

    def get_committed_offset(self, partition: Partition) -> Optional[int]:
        """Return the committed offset for a partition, or None."""
        return self._committed_offsets.get(self._partition_key(partition))

    def get_lag(self) -> dict[str, int]:
        """Return the offset lag for each assigned partition."""
        lag: dict[str, int] = {}
        for partition in self.assigned_partitions:
            pkey = self._partition_key(partition)
            current = self._current_offsets.get(pkey, partition.log_start_offset)
            lag[pkey] = partition.log_end_offset - current
        return lag

    def __repr__(self) -> str:
        partitions_str = [
            f"{p.topic}-{p.partition_id}" for p in self.assigned_partitions
        ]
        return (
            f"Consumer({self.consumer_id}, group={self.group_id}, "
            f"partitions={partitions_str})"
        )


class ConsumerGroup:
    """
    Manages a group of consumers that cooperatively consume from a topic.

    Handles partition assignment and rebalancing when consumers join or leave.
    Each partition is assigned to exactly one consumer in the group.

    Supports two assignment strategies:
        - round_robin: distribute partitions round-robin across consumers
        - range: divide partitions into contiguous ranges per consumer

    Usage:
        >>> topic = Topic("orders", num_partitions=6)
        >>> group = ConsumerGroup("order-processors", topic)
        >>> c1 = group.add_consumer("consumer-1")
        >>> c2 = group.add_consumer("consumer-2")
        >>> messages = c1.poll()
    """

    def __init__(
        self,
        group_id: str,
        topic: Topic,
        strategy: str = "round_robin",
    ):
        self.group_id = group_id
        self.topic = topic
        self.strategy = strategy
        self.consumers: list[Consumer] = []
        self.generation_id: int = 0
        # Stores committed offsets across rebalances: partition_key -> offset
        self._group_offsets: dict[str, int] = {}

    def add_consumer(
        self,
        consumer_id: str,
        auto_offset_reset: OffsetResetPolicy = OffsetResetPolicy.EARLIEST,
    ) -> Consumer:
        """Add a consumer to the group and trigger a rebalance."""
        consumer = Consumer(
            consumer_id=consumer_id,
            group_id=self.group_id,
            auto_offset_reset=auto_offset_reset,
        )
        self.consumers.append(consumer)
        self._rebalance()
        return consumer

    def remove_consumer(self, consumer_id: str) -> None:
        """Remove a consumer from the group and trigger a rebalance."""
        # Save committed offsets before removal
        for consumer in self.consumers:
            if consumer.consumer_id == consumer_id:
                for partition in consumer.assigned_partitions:
                    pkey = consumer._partition_key(partition)
                    committed = consumer.get_committed_offset(partition)
                    if committed is not None:
                        self._group_offsets[pkey] = committed
                break

        self.consumers = [c for c in self.consumers if c.consumer_id != consumer_id]
        if self.consumers:
            self._rebalance()

    def _rebalance(self) -> None:
        """
        Redistribute partitions across consumers.

        Preserves committed offsets across rebalance. Increments the
        generation ID to track rebalance epochs.
        """
        self.generation_id += 1

        # Save all committed offsets before reassigning
        for consumer in self.consumers:
            for partition in consumer.assigned_partitions:
                pkey = consumer._partition_key(partition)
                committed = consumer.get_committed_offset(partition)
                if committed is not None:
                    self._group_offsets[pkey] = committed

        # Clear current assignments
        for consumer in self.consumers:
            consumer.assigned_partitions = []
            consumer._current_offsets = {}

        if not self.consumers:
            return

        partitions = self.topic.partitions

        if self.strategy == "round_robin":
            self._assign_round_robin(partitions)
        elif self.strategy == "range":
            self._assign_range(partitions)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

        # Restore committed offsets on newly assigned consumers
        for consumer in self.consumers:
            for partition in consumer.assigned_partitions:
                pkey = consumer._partition_key(partition)
                if pkey in self._group_offsets:
                    consumer._committed_offsets[pkey] = self._group_offsets[pkey]
                    consumer._current_offsets[pkey] = self._group_offsets[pkey]

    def _assign_round_robin(self, partitions: list[Partition]) -> None:
        """Assign partitions in round-robin order across consumers."""
        for i, partition in enumerate(partitions):
            consumer = self.consumers[i % len(self.consumers)]
            consumer.assigned_partitions.append(partition)

    def _assign_range(self, partitions: list[Partition]) -> None:
        """Assign contiguous ranges of partitions to each consumer."""
        n_consumers = len(self.consumers)
        n_partitions = len(partitions)
        base = n_partitions // n_consumers
        remainder = n_partitions % n_consumers

        idx = 0
        for i, consumer in enumerate(self.consumers):
            count = base + (1 if i < remainder else 0)
            consumer.assigned_partitions = partitions[idx: idx + count]
            idx += count

    def commit_all(self) -> dict[str, dict[str, int]]:
        """Commit offsets for all consumers in the group."""
        result: dict[str, dict[str, int]] = {}
        for consumer in self.consumers:
            committed = consumer.commit()
            result[consumer.consumer_id] = committed
            self._group_offsets.update(committed)
        return result

    def get_group_lag(self) -> dict[str, int]:
        """Get the total lag across all consumers in the group."""
        lag: dict[str, int] = {}
        for consumer in self.consumers:
            lag.update(consumer.get_lag())
        return lag

    def describe(self) -> str:
        """Return a human-readable description of the group state."""
        lines = [
            f"ConsumerGroup: {self.group_id}",
            f"  Topic: {self.topic.name} ({self.topic.num_partitions} partitions)",
            f"  Strategy: {self.strategy}",
            f"  Generation: {self.generation_id}",
            f"  Members ({len(self.consumers)}):",
        ]
        for consumer in self.consumers:
            partitions = [
                f"P{p.partition_id}" for p in consumer.assigned_partitions
            ]
            lag = consumer.get_lag()
            total_lag = sum(lag.values())
            lines.append(
                f"    {consumer.consumer_id}: "
                f"partitions={partitions}, lag={total_lag}"
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"ConsumerGroup({self.group_id}, topic={self.topic.name}, "
            f"consumers={len(self.consumers)}, gen={self.generation_id})"
        )


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def _separator(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    # ------------------------------------------------------------------
    # 1. Create a topic with partitions
    # ------------------------------------------------------------------
    _separator("1. Create Topic with 4 Partitions")

    topic = Topic("orders", num_partitions=4)
    print(f"Created: {topic}")
    for p in topic.partitions:
        print(f"  {p}")

    # ------------------------------------------------------------------
    # 2. Produce messages with key-based partitioning
    # ------------------------------------------------------------------
    _separator("2. Produce Messages (Key-Based Partitioning)")

    producer = Producer(ack_mode=AckMode.LEADER_ONLY)

    # Messages with the same key always go to the same partition
    orders = [
        ("user-1", "order-1: laptop"),
        ("user-2", "order-2: phone"),
        ("user-1", "order-3: keyboard"),
        ("user-3", "order-4: monitor"),
        ("user-2", "order-5: case"),
        ("user-1", "order-6: mouse"),
        ("user-4", "order-7: headset"),
        ("user-3", "order-8: webcam"),
    ]

    for key, value in orders:
        msg = producer.send(topic, key=key, value=value)
        print(f"  Produced: key={key} -> partition={msg.partition}, offset={msg.offset}")

    print(f"\n  {producer}")
    print(f"  {topic}")

    # Verify same key goes to same partition
    print("\n  Key-partition consistency check:")
    key_partitions: dict[str, set[int]] = defaultdict(set)
    for key, _ in orders:
        p = topic.get_partition(key)
        key_partitions[key].add(p.partition_id)
    for key, parts in sorted(key_partitions.items()):
        print(f"    {key} -> partition(s): {parts}  {'[OK]' if len(parts) == 1 else '[FAIL]'}")

    # ------------------------------------------------------------------
    # 3. Produce keyless messages (round-robin)
    # ------------------------------------------------------------------
    _separator("3. Produce Keyless Messages (Round-Robin)")

    for i in range(8):
        msg = producer.send(topic, value=f"event-{i}")
        print(f"  event-{i} -> partition={msg.partition}")

    print("\n  Partition sizes after all produces:")
    for p in topic.partitions:
        print(f"    Partition {p.partition_id}: {len(p)} messages "
              f"(offsets [{p.log_start_offset}, {p.log_end_offset}))")

    # ------------------------------------------------------------------
    # 4. Consumer Group with rebalancing
    # ------------------------------------------------------------------
    _separator("4. Consumer Group (2 Consumers)")

    group = ConsumerGroup("order-processors", topic, strategy="round_robin")
    c1 = group.add_consumer("consumer-1")
    c2 = group.add_consumer("consumer-2")

    print(group.describe())

    # ------------------------------------------------------------------
    # 5. Consume messages
    # ------------------------------------------------------------------
    _separator("5. Consume Messages")

    msgs_c1 = c1.poll(max_records=50)
    msgs_c2 = c2.poll(max_records=50)

    print(f"  consumer-1 fetched {len(msgs_c1)} messages:")
    for m in msgs_c1:
        print(f"    [{m.topic}-{m.partition}@{m.offset}] key={m.key} value={m.value}")

    print(f"\n  consumer-2 fetched {len(msgs_c2)} messages:")
    for m in msgs_c2:
        print(f"    [{m.topic}-{m.partition}@{m.offset}] key={m.key} value={m.value}")

    # Commit offsets
    committed = group.commit_all()
    print("\n  Committed offsets:")
    for cid, offsets in committed.items():
        for pkey, off in offsets.items():
            print(f"    {cid}: {pkey} -> {off}")

    # ------------------------------------------------------------------
    # 6. Rebalancing: add a third consumer
    # ------------------------------------------------------------------
    _separator("6. Rebalance: Add Consumer-3")

    print("  BEFORE rebalance:")
    print(f"    {c1}")
    print(f"    {c2}")

    c3 = group.add_consumer("consumer-3")

    print(f"\n  AFTER rebalance (generation={group.generation_id}):")
    print(f"    {c1}")
    print(f"    {c2}")
    print(f"    {c3}")

    # ------------------------------------------------------------------
    # 7. Rebalancing: remove a consumer
    # ------------------------------------------------------------------
    _separator("7. Rebalance: Remove Consumer-2")

    group.remove_consumer("consumer-2")

    print(f"  AFTER removal (generation={group.generation_id}):")
    for c in group.consumers:
        print(f"    {c}")

    # ------------------------------------------------------------------
    # 8. Produce more & consume to show offset continuity
    # ------------------------------------------------------------------
    _separator("8. Offset Continuity After Rebalance")

    for i in range(4):
        producer.send(topic, key=f"user-{i+1}", value=f"new-order-{i}")

    for c in group.consumers:
        msgs = c.poll(max_records=50)
        print(f"  {c.consumer_id} polled {len(msgs)} new messages")
        for m in msgs:
            print(f"    [{m.topic}-{m.partition}@{m.offset}] value={m.value}")

    # ------------------------------------------------------------------
    # 9. Consumer lag monitoring
    # ------------------------------------------------------------------
    _separator("9. Consumer Lag Monitoring")

    # Produce some more to create lag
    for i in range(12):
        producer.send(topic, value=f"backlog-{i}")

    print("  Produced 12 more messages (creating lag)")
    lag = group.get_group_lag()
    print(f"  Group lag: {lag}")
    print(f"  Total lag: {sum(lag.values())} messages behind")

    print(f"\n{group.describe()}")

    # ------------------------------------------------------------------
    # 10. Seek / Replay
    # ------------------------------------------------------------------
    _separator("10. Seek & Replay")

    # Pick the first consumer's first partition
    target_consumer = group.consumers[0]
    if target_consumer.assigned_partitions:
        target_partition = target_consumer.assigned_partitions[0]
        print(f"  Seeking {target_consumer.consumer_id} to offset 0 "
              f"on {target_partition.topic}-{target_partition.partition_id}")
        target_consumer.seek(target_partition, 0)

        replayed = target_consumer.poll(max_records=5)
        print(f"  Replayed {len(replayed)} messages:")
        for m in replayed:
            print(f"    [{m.topic}-{m.partition}@{m.offset}] value={m.value}")

    # ------------------------------------------------------------------
    # 11. Range assignment strategy demo
    # ------------------------------------------------------------------
    _separator("11. Range Assignment Strategy")

    topic2 = Topic("payments", num_partitions=6)
    group2 = ConsumerGroup("payment-processors", topic2, strategy="range")
    group2.add_consumer("pay-c1")
    group2.add_consumer("pay-c2")
    group2.add_consumer("pay-c3")

    print(group2.describe())

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    _separator("Summary")
    print(f"  Total messages produced: {producer.messages_sent}")
    print(f"  Topic '{topic.name}': {topic}")
    for p in topic.partitions:
        print(f"    {p}: {len(p)} messages")
    print(f"  Consumer group: {group}")
    print("\n  Done!")
