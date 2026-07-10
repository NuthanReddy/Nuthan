# SystemDesign — Review & Suggestions

This document reviews the `SystemDesign/` collection and proposes improvements. It has
two parts:

1. **Gap analysis** — new system-design topics worth adding (what's missing from the canon).
2. **Improvement notes** — per-implementation review of what already exists.

> **On confidence:** Items marked **✓ Verified** were confirmed directly against the
> source. Everything else is a *suggestion* or an *area to check* — not an assertion that
> the current code is broken. (An automated first pass produced several false-positive bug
> claims, so unverified line-level bug reports were deliberately excluded.)

---

## 1. Inventory (what exists today)

**Polished topics** (each has a `README.md` design doc + a single Python implementation):

| Category | Implementations |
|----------|-----------------|
| Infra / primitives | `CDN`, `DistributedCache`, `DistributedRateLimiter`, `MessageQueue` |
| Data & streaming | `BatchDataPipeline`, `StreamingPipeline`, `DataLakehouse`, `MetricsMonitoring`, `DistributedKVStore`, `FileStorage`, `WebCrawler`, `SearchAutocomplete` |
| Product systems | `URLShortener`, `ChatSystem`, `NotificationSystem`, `PaymentSystem`, `ECommerce`, `RideSharing`, `HotelBooking`, `TicketBooking`, `SocialGraph`, `TwitterFeed`, `VideoStreaming`, `FoodOrderingMetrics` |

**Loose scripts** (single files at the `SystemDesign/` root, no folder/README):
`ConsistentHashing.py`, `RendezvousHashing.py`, `RateLimiter.py`, `LoadBalancerSocket.py`,
`SSTable.py`, and `Cache` (a plain-text notes file with **no extension**).

**Observation:** there is **no top-level `SystemDesign/README.md`** index, and **none of the
implementations ship tests** despite the repo convention (`test_*.py` + `uv run pytest`).

---

## 2. Gap analysis — suggested new implementations

The collection is already broad. The highest-value additions fill gaps in **distributed-systems
primitives** and a few classic product designs. Each item lists the core concepts to practice and
which existing code it can reuse.

### Tier 1 — high value, clear gaps

| Topic | Why it's worth adding | Concepts to model | Reuse |
|-------|----------------------|-------------------|-------|
| **Distributed Lock / Lease service** | Ubiquitous primitive (Redlock, ZooKeeper, etcd); nothing here covers mutual exclusion or fencing. | Lease TTL, fencing tokens, lock acquire/renew/release, failure of lock holder | `ConsistentHashing.py`, `DistributedKVStore` |
| **Leaderboard / Ranking service** | Classic interview design (gaming, "top-K"); not covered. | Sorted sets / skip list, rank & percentile queries, score updates, sharding by score range | `SSTable.py` (sorted runs) |
| **Unique ID generator (Snowflake)** | Fundamental building block; only implicit inside `URLShortener`. | Timestamp + worker-id + sequence bits, clock skew, ID monotonicity | — |
| **Consensus / Leader election (Raft)** | Pairs naturally with the KV store; teaches replication correctness. | Log replication, terms, elections, commit index, membership change | `DistributedKVStore` |
| **Ad-click aggregator / real-time counter** | Canonical streaming-analytics design distinct from the generic pipeline. | Event dedup, tumbling windows, approximate counting (HLL), hot-key handling | `StreamingPipeline`, `MetricsMonitoring` |
| **Proximity / "Nearby" service (Yelp)** | Geospatial search as a standalone topic; only implicit in ride-sharing. | Geohash / quadtree, radius queries, ranking by distance+rating | `RideSharing` (geohash) |
| **Full-text search engine (inverted index)** | `SearchAutocomplete` is typeahead only; no document search / ranking. | Inverted index, tokenization, TF-IDF/BM25, sharded index + merge | `SearchAutocomplete`, `SSTable.py` |
| **Collaborative document editing (Google Docs)** | High-value, teaches conflict resolution deeply. | Operational Transform or CRDTs, cursor/presence, offline merge | `ChatSystem` (presence) |
| **AuthN/AuthZ service (OAuth2 / JWT / sessions)** | Very common design; currently absent. | Token issuance/refresh, session store, RBAC, revocation | `DistributedCache` (session store) |
| **Stock exchange / order-matching engine** | Popular, latency-critical design; absent. | Order book (price-time priority), matching, partial fills, sequencing | `PaymentSystem` (ledger) |

### Tier 2 — valuable, some overlap with existing work

- **Distributed task/cron scheduler** — delayed jobs, at-least-once execution, leader-elected dispatcher (distinct from the DAG batch pipeline).
- **API Gateway** — routing, auth, rate-limit + circuit-breaker composition (turns `LoadBalancerSocket.py` into something real).
- **Service discovery / registry** — health checks, heartbeat TTL, watch/notify.
- **Saga / distributed-transaction coordinator** — orchestration + compensation (generalizes the e-commerce checkout flow).
- **Distributed logging & tracing** — log ingestion, trace/span propagation, sampling (complements `MetricsMonitoring`).
- **Dropbox-style file sync** — chunk-level delta sync, conflict copies, watch/notify (distinct from `FileStorage`'s object-store model).
- **Live streaming** — low-latency HLS/RTMP ingest & fan-out (distinct from `VideoStreaming`'s VOD model).
- **Recommendation engine** — candidate generation + ranking, collaborative filtering.
- **Feature-flag / config service** — targeting rules, gradual rollout, streaming updates.
- **Distributed counter** — likes/views at scale (sharded counters, write-back aggregation).

### Tier 3 — nice to have / niche

Calendar & scheduling (Calendly), email-delivery service, online code judge/sandbox, digital
wallet (extends `PaymentSystem`), pub/sub push service (extends `MessageQueue`), Google-Maps
routing (shortest path at scale).

---

## 3. Cross-cutting improvements (apply across many folders)

These give the most leverage because they touch the whole collection:

1. **Add a top-level `SystemDesign/README.md` index** — a table linking each subfolder with a
   one-line description and difficulty. Nothing currently ties the collection together.
2. **Add tests** — the repo standard is `test_*.py` + `uv run pytest`, but no implementation
   has tests. Even a handful of unit tests per design (happy path + one edge case + one
   concurrency case) would materially raise quality and catch the kinds of bugs reviewers guess at.
3. **Normalize the loose scripts** into the established `folder/ + README.md + <name>.py` shape
   (or a `primitives/` subfolder). In particular, the `Cache` file has **no extension**, is raw
   Q&A prose (won't render as Markdown), has no code, and overlaps `DistributedCache` — convert it
   to `Cache/README.md` or fold it into `DistributedCache`.
4. **Audit thread-safety** where a design claims concurrency. Some in-memory implementations have
   **no locking at all** (**✓ Verified:** `DistributedCache`, `ConsistentHashing.py`, `SSTable.py`),
   while others already lock correctly (e.g. `ECommerce`, `PaymentSystem`, `TicketBooking`). Add
   `threading.Lock`/`RLock` around shared mutable state where concurrent use is part of the story.
5. **Guard module-level side effects.** **✓ Verified:** `RateLimiter.py` runs a packet loop at
   *import* time. Wrap all demos in `if __name__ == "__main__":` so files are import-safe (and testable).
6. **Extract configuration.** Replace scattered magic numbers (thresholds, TTLs, capacities,
   failure rates) with named constants or a small config object — this also unblocks testing and tuning.
7. **Close README ↔ code gaps.** Several READMEs promise features the code doesn't implement
   (e.g. **✓ Verified:** `DistributedCache` documents pub/sub but the code has none). Either add a
   minimal implementation or mark the section **"design-only / not implemented"** so the docs stay honest.
8. **Modernize typing.** `pyproject.toml` targets Python ≥3.10, so prefer built-in generics
   (`dict`, `list`) over `typing.Dict`/`List` in files that still use the old style.
9. **Dependency hygiene.** **✓ Verified:** `RendezvousHashing.py` imports third-party `mmh3`;
   either declare it as a dependency/extra or switch to `hashlib` for consistency with
   `ConsistentHashing.py`.
10. **Add diagrams.** This environment renders ```mermaid``` blocks — a small architecture or
    sequence diagram in each README pays off quickly.

---

## 4. Per-implementation notes

Format: one-line summary, then concrete suggestions. **✓ Verified** = confirmed against source.

### Infrastructure & primitives

**ConsistentHashing.py** — Hash ring with virtual nodes, replication lookup, distribution stats. Solid.
- **✓ Verified:** module docstring claims `add_node = O(v log n)`, but `bisect.insort` is O(n) per
  insert (list shift), so it's O(v·n). Fix the comment or switch to a structure with O(log n) insert.
- **✓ Verified:** not thread-safe — add a lock if concurrent ring mutation is intended.
- Give it a folder + README (design-doc format) and a `test_*.py` (distribution balance, remap % on node removal).

**RendezvousHashing.py** — Weighted HRW hashing (highest-random-weight).
- **✓ Verified:** depends on third-party `mmh3` while the rest of the repo uses `hashlib` — align them, or declare the dep.
- Add a module docstring, complexity note (O(n) per lookup vs. ring's O(log n)), a `__main__` demo, and tests. Bring it up to `ConsistentHashing.py`'s quality bar; a short "HRW vs. consistent hashing" note in a README would be valuable.

**RateLimiter.py** — Single sliding-window-counter throttle.
- **✓ Verified:** executes a packet loop at import (module-level side effects) and has no
  `if __name__ == "__main__":` guard — makes it unimportable/untestable. Wrap the demo.
- Overlaps `DistributedRateLimiter/` (which has four algorithms). Consider folding this in as the
  single-node reference, or deleting it to avoid duplication. Add type hints/docstrings.

**LoadBalancerSocket.py** — Toy TCP forwarder.
- **✓ Verified:** it doesn't actually *balance* — it connects every client to one hardcoded backend
  (`localhost:8000`), with no backend pool or selection algorithm. It's also serial (no threading),
  forwards a single `recv(1024)`, never sends the response back to the client, and has no error
  handling/cleanup.
- Turn it into a real exercise: a backend pool + pluggable strategy (round-robin / least-conn /
  random), bidirectional proxying, a thread/async per connection, and health checks — with a README.

**SSTable.py** — LSM engine: MemTable → SSTable (bloom + sparse index), tombstones, compaction, persistence. High quality.
- **✓ Verified:** no **WAL** despite being "log-structured" — a crash between `put` and `_flush`
  loses the MemTable. Add a simple append-only WAL + replay on startup for real durability.
- **✓ Verified:** `BloomFilter` defaults to 1024 bits regardless of key count; at `memtable_size≈1000`
  the false-positive rate approaches 100%. Size bits from expected `n` and target FP rate.
- **✓ Verified:** not thread-safe. Also consider size-tiered vs. leveled compaction (currently
  single-level "merge all"), range scans/iterators, and a folder + README + tests.

**Cache** (no extension) — Raw InterviewBit-style Q&A notes on cache design.
- **✓ Verified:** no `.md` extension (won't render), prose-only (no code), inconsistent with the
  repo's format, and conceptually overlaps `DistributedCache/`. Convert to `Cache/README.md` (or
  merge into `DistributedCache/README.md`) and, if kept standalone, add a small LRU/LFU code sample.

**DistributedCache/** — In-memory cache with consistent hashing, LRU, TTL, virtual nodes.
- **✓ Verified:** the code has **no locking** and **no pub/sub**, though the README describes both.
  Add `RLock` around node state, and either implement a minimal pub/sub (`channels: dict[str, set[Callable]]`)
  or mark it design-only.
- Suggest documenting node membership/discovery and replica failover; add tests.

**DistributedRateLimiter/** — Four algorithms (token bucket, sliding-window log & counter, leaky bucket) via strategy + factory. Nice.
- The README emphasizes Redis + Lua + clock-skew handling, but the code is a single-node simulation.
  Add a thread-safe wrapper for per-client state and (optionally) a Redis-backed variant to match the doc.
- Add boundary tests (exact-capacity, zero refill, burst-then-idle).

**MessageQueue/** — Kafka-like broker: topics, partitions, consumer groups, offsets, rebalancing.
- **✓ Verified:** `Topic.get_partition` returns `self.partitions[0]` when key is `None`, but its
  docstring says it "returns None (caller should use round-robin)" — reconcile the doc and the code
  (and confirm keyless messages actually round-robin).
- Suggest adding consumer heartbeat/session-timeout so failed consumers trigger rebalance; document
  the rebalance strategy (range/round-robin/sticky) and ISR/replication model.

**CDN/** — Multi-tier edge/shield cache: LRU, TTL, origin pull, purge by URL/tag, geo routing. Strong.
- Enhancements (not bugs): parse `Cache-Control` (`max-age`, `s-maxage`, `no-cache`) instead of a
  fixed TTL; add stale-while-revalidate on origin error; add a tag→URLs index if tag purges are O(n).
- Document PoP cache-coherence on purge and cold-start/bootstrap for a newly added PoP.

### Data & streaming

**BatchDataPipeline/** — DAG ETL orchestrator: multi-source extract, transform, quality checks, lineage.
- Add stage-level **idempotency/checkpointing** (skip already-completed stages on rerun) and
  composite-key dedup to back the terabyte-scale claim. Persist lineage so it's queryable. Add tests.

**StreamingPipeline/** — Flink-like windowing (tumbling/sliding/session), watermarks, late events, checkpoints. Strong.
- Audit locking on `_windows`/`_results`/`_late_events` if concurrent use is intended; document
  crash-recovery semantics and the `allowed_lateness` ↔ watermark relationship. Add tests for
  session-window merges and out-of-order events.

**DataLakehouse/** — Transaction log, medallion (Bronze/Silver/Gold), schema evolution, time-travel. Already uses locks.
- Add explicit error handling for schema violations on write/merge (log rejected records); document
  compaction, old-version GC, and concurrent-writer conflict resolution. Consider caching recent
  versions to avoid replay on time-travel. Add tests.

**MetricsMonitoring/** — In-memory TSDB: time-partitioned storage, downsampling/rollups, alert state machine, aggregation queries.
- (Note: downsampling bucket alignment is **correct** — `ts - (ts % resolution)`.) Enhancements:
  add a **PENDING** alert state (`INACTIVE→PENDING→FIRING`) to prevent flapping; add per-series
  cardinality limits; use a streaming percentile (t-digest) instead of retaining all raw samples.

**DistributedKVStore/** — Dynamo-style: consistent hashing, quorum R/W, vector clocks, gossip, hinted handoff, read repair.
- (Note: `_read_repair`/`_reconcile`/`_get_healthy_preference_list` **do exist** — earlier "missing"
  reports were false.) Enhancements: validate quorum config in `__init__` (e.g. `assert r + w > n`
  for strong reads; `w ≤ n`); guard the `ConsistentHashRing` against concurrent `add_node`/`remove_node`
  vs. `get_preference_list`; document when reads are strong vs. eventual. Add tests.

**FileStorage/** — Dropbox/S3-style: 4 MB chunking, content-addressed dedup, versioning, sharing, sync.
- Add chunk **garbage collection** (decrement/collect `ref_count` on version delete), checksum
  verification on reassembly, and an explicit optimistic-concurrency check (`expected_version`) on
  new versions. If delta-sync is only described in the README, implement a minimal `compute_delta`
  (changed-chunk hashes) or mark it design-only. Add tests.

**WebCrawler/** — Frontier (priority + politeness), bloom-filter dedup, BFS, robots simulation.
- Add **URL canonicalization** before the bloom check (normalize scheme/host case, strip trailing
  slash and volatile query params) to avoid duplicate crawls. Enforce `max_depth` in the crawl loop.
  If SimHash near-dup detection is in the README only, implement a minimal version or mark design-only. Add tests.

**SearchAutocomplete/** — Trie with precomputed top-K per node, query-frequency logging, offline rebuild, trending overlay. Strong.
- Add thread-safety around trie updates if online trending mutates it concurrently with reads;
  add input limits (max prefix length, allowed charset). Flesh out the `AutocompleteService` wrapper
  and add trie-correctness tests.

### Product systems

**URLShortener/** — Base62 counter, custom aliases, TTL, click analytics, URL dedup. Clean.
- Use `urllib.parse` instead of `split("/")[-1]` when extracting the code (robust to trailing
  slashes/query params); validate custom-alias format *before* the collision check; add a lock
  around the counter; document counter-exhaustion behavior. Add tests.

**ChatSystem/** — 1:1 & group chat, delivery state machine (SENT→DELIVERED→READ), presence, offline queue. Strong.
- Add message **dedup via `client_msg_id`** (resend safety), content validation (length/sanitization),
  and explicit concurrency handling. Deliver typing indicators in the demo; add delivery tests.

**NotificationSystem/** — Multi-channel (push/SMS/email), priority queue, templates, preferences, retry + circuit breaker.
- **✓ Verified:** quiet-hours uses `datetime.utcnow().hour` — it should use the **user's timezone**,
  otherwise quiet hours are wrong for non-UTC users. Also add a dedup store (notification-id + TTL)
  and per-channel delivery metrics. Guard the priority queue with a lock.

**PaymentSystem/** — Stripe-like: state machine, double-entry ledger, idempotency, provider retry, webhooks. Strong; already locks and checks idempotency.
- Enhancements: validate `refund_amount ≤ captured_amount − refunded_amount`; confirm ledger
  account keys use a customer/merchant id consistently; consider persisting the idempotency store with a TTL. Add tests.

**ECommerce/** — Catalog search, cart, inventory reservation w/ TTL, saga checkout, order lifecycle. `reserve()` is already lock-guarded.
- Add saga **compensation** (release the reservation if payment fails after reserve) and a
  background sweep to expire stale reservations. Replace substring catalog search with an index if
  scale matters. Mention the saga pattern in the README. Add tests.

**RideSharing/** — Geohash matching, trip state machine, surge pricing, location streaming.
- Validate lat/lng bounds in geohash encode/decode and document edge cases (poles, ±180° meridian);
  make matching atomic (driver location can change between lookup and assignment — lock or CAS);
  document the surge formula and state transitions. Add tests.

**HotelBooking/** — Per-date room inventory, optimistic locking, booking state machine, search. Uses locks.
- Shard/partition inventory by hotel to avoid a single global lock at scale; validate date ranges
  (`check_in < check_out`, max horizon) and guest counts. Add concurrent-booking tests (e.g. last room contended).

**TicketBooking/** — Seat holds (TTL), per-seat optimistic locking, high-contention booking.
- **✓ Verified:** `_global_lock` is created but never used — remove it or use it intentionally.
  Ensure `hold_seats` reverts *all* seats already marked HELD if a later seat fails (all-or-nothing);
  replace manual hold-expiry polling with a background sweeper. Add race tests (many users, one seat).

**SocialGraph/** — Adjacency-list friendships, mutual friends, FoF recommendations, BFS degrees-of-separation. Clean.
- Validate that both users exist in `add_friend` (raise on missing); implement the blocked-users
  feature the README lists (and filter it out of recommendations/mutuals); add a graph-consistency
  check (every edge is bidirectional). Add tests.

**TwitterFeed/** — Hybrid fan-out (push/pull for celebrities), engagement ranking, timeline cache. Strong.
- Dedup likes/retweets **per (user, tweet)** to prevent double counting; extract ranking weights
  into named constants (swappable model); make celebrity threshold configurable; avoid full re-sort
  in `_backfill_cache` (incremental/bisect insert). Add tests.

**VideoStreaming/** — Upload, transcoding DAG (multi-resolution + retry), adaptive bitrate, views, recommendations.
- Replace `print` with the `logging` module; add upload **idempotency** (dedup transcode jobs on
  retry) and cleanup of partial outputs on permanent failure; fully specify/implement the ABR
  selection heuristic (buffer- or bandwidth-based). Add tests.

**FoodOrderingMetrics/** — User-lifecycle metrics, churn risk scoring, automated interventions. Large & thorough.
- Add **event dedup by `event_id`** (avoid double-counting late/duplicate events); make risk
  thresholds and retention-week milestones configurable (unblocks tuning/A-B tests); harden the
  ISO-week keying across year boundaries. Modernize `Dict`/`List` → `dict`/`list`. Add tests.

---

## 5. Suggested next steps (highest leverage first)

1. Add `SystemDesign/README.md` (index of all topics) — quick win, ties the collection together.
2. Normalize the six loose scripts (fold/relocate + give `Cache` a real README).
3. Fix the small **✓ Verified** items (import-time side effects, bloom sizing, missing WAL,
   unused/needed locks, doc↔code mismatches, timezone-aware quiet hours).
4. Add a per-implementation `test_*.py` starter (happy path + one edge + one concurrency case).
5. Pick **2–3 Tier-1 gap topics** to implement next (recommended: **Distributed Lock**,
   **Leaderboard**, **Unique ID generator** — they're compact and reuse existing primitives).
