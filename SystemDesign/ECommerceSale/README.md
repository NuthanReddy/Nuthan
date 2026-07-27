# Flash Sale System Design

## 1. Problem Statement

Design a backend system to host a **flash sale** for a single product (or small set of SKUs) on an e-commerce platform.

### Hard Constraints
1. **Limited inventory** — `N` products where `N << M` (number of users). e.g. 1,000 units vs 10M users hitting Buy.
2. **One purchase per user** — a user can win at most one unit, even if they retry/spam.
3. **FIFO ordering** — the first `N` *valid* requests (by arrival time at the system boundary) win. No lottery, no random.
4. **Scalable** — must withstand a huge spike (e.g. 1M+ RPS at `t=0`) without melting the DB.

### Non-Functional Requirements
- Low latency on the "you won / you lost" response (ideally < 1s).
- Strong correctness: never oversell, never let one user buy twice.
- Graceful degradation under overload (queue/reject, don't crash).
- Observability: how many in queue, how many sold, how many rejected.

---

## 2. Back-of-the-envelope

| Quantity | Value |
|---|---|
| Inventory `N` | 1,000 units |
| Concurrent users `M` | 10,000,000 |
| Peak RPS at sale open | ~1,000,000 |
| Sale window | 30s – few minutes |
| Read:write ratio | 99:1 (most users only check status) |

Key insight: **the write path is tiny (1k successful writes total) but the request path is enormous.** The whole game is to *cheaply reject the 99.99% of requests that won't win* while keeping FIFO honest for the few that will.

---

## 3. Core Sub-problems

Any solution must answer four questions:

| Sub-problem | What it means |
|---|---|
| **Admission / Rate shedding** | How do we stop 1M RPS from reaching the DB? |
| **FIFO ordering** | How do we decide who arrived first across many servers/regions? |
| **Atomic decrement** | How do we hand out exactly `N` units, no more, no less? |
| **Per-user dedup** | How do we ensure a single user gets at most one unit? |

---

## 4. Design Options

Four realistic approaches, from simplest to most sophisticated.

---

### Option A — Redis Atomic Counter + Lua Script (single-node hot path)

#### Architecture
```
Client → CDN → API Gateway (rate-limit per IP/user) → Stateless App Servers
                                                          │
                                                          ▼
                                                    Redis (single shard for SKU)
                                                    [INVENTORY:sku, BOUGHT:sku set]
                                                          │
                                                  async ▼
                                                  Kafka topic "orders"
                                                          │
                                                          ▼
                                                  Order Service → Postgres (durable)
```

#### How each constraint is solved
- **FIFO**: Redis is single-threaded — order of `EVAL` commands at the Redis instance defines the winner order.
- **Atomic decrement + dedup**: One Lua script runs atomically:
  ```lua
  -- KEYS[1]=inventory:sku, KEYS[2]=bought:sku, ARGV[1]=user_id
  if redis.call('SISMEMBER', KEYS[2], ARGV[1]) == 1 then
      return -1  -- already bought
  end
  local n = tonumber(redis.call('GET', KEYS[1]) or '0')
  if n <= 0 then
      return 0   -- sold out
  end
  redis.call('DECR', KEYS[1])
  redis.call('SADD', KEYS[2], ARGV[1])
  return 1       -- won
  ```
- **Persistence**: on `return 1`, app server publishes an event to Kafka; Order Service writes to Postgres. The user sees "you won" immediately; payment/fulfillment happens asynchronously with a hold timeout.

#### Pros
- Dead simple, maybe 50 lines of code.
- Lua script gives both atomicity and FIFO essentially for free.
- Sub-millisecond decision per request.
- Easy to reason about correctness.

#### Cons
- **Single Redis shard is the bottleneck** — caps you at ~100k–200k ops/sec per node. For 1M RPS, you must shed load *before* Redis (rate limiter, queue page, captcha, edge admission).
- Single point of failure unless using Redis replication + Sentinel/Cluster, but a single SKU's keys live on one shard.
- "FIFO" is FIFO at Redis arrival, not at user click — network jitter reorders things. This is acceptable for almost all flash sales.

#### When to pick it
Inventory is small (≤ a few thousand), sale is short, and you can do upstream load shedding. **This is the default industry choice.**

---

### Option B — Distributed Message Queue (Kafka / RabbitMQ) as the source of truth

#### Architecture
```
Client → API Gateway → Producer Service
                          │  (writes one msg per attempt, key=user_id)
                          ▼
                    Kafka topic "flashsale.sku123" (single partition!)
                          │
                          ▼
                  Single Consumer (the "ticket master")
                  - reads in order
                  - keeps in-memory: remaining, bought_users set
                  - emits "win" / "lose" to per-user topic or DB
                          │
                          ▼
                    Postgres (orders) + Redis (status cache)
```

#### How each constraint is solved
- **FIFO**: A Kafka topic with **one partition** preserves total order. Producer-side ordering gets a bit fuzzy across producers, but partition-append order is authoritative.
- **Dedup**: Consumer keeps a `Set<userId>` in memory and filters duplicates. Producer can also use `user_id` as the message key with idempotent producer + transactional writes.
- **Atomic decrement**: Trivially safe — only one consumer ever decrements.
- **Result delivery**: User polls `GET /sale/status?user=...` against Redis/DB, or receives result via WebSocket/SSE.

#### Pros
- **Durable** — if the consumer crashes, it resumes from offset; no orders lost.
- Strong audit trail (every attempt is on the log).
- Decouples "request accepted" from "order processed" — can absorb spikes by lengthening the queue.
- Good when sale lasts longer (minutes/hours) and durability matters more than latency.

#### Cons
- **Single-partition consumer is the throughput ceiling** (often lower than Redis Lua).
- Higher latency — user waits for "did I win?" until the consumer processes their offset.
- More moving parts (Kafka cluster, schema registry, consumer health).
- Producer side can still reorder slightly (multiple producers, retries).

#### When to pick it
You need **durable, auditable** ordering (e.g. regulated goods, ticketing where disputes matter), or the sale runs long enough that a small queue lag is acceptable.

---

### Option C — Database with Pessimistic / Optimistic Locking

#### Architecture
```
Client → API → App Server → Postgres
                              [products(id, stock), orders(user_id UNIQUE per sku)]
```

Two flavors:

**C1 — Pessimistic (`SELECT ... FOR UPDATE`)**
```sql
BEGIN;
SELECT stock FROM products WHERE id = :sku FOR UPDATE;
-- check stock > 0
INSERT INTO orders (user_id, sku) VALUES (:u, :sku);  -- UNIQUE(user_id, sku) catches dups
UPDATE products SET stock = stock - 1 WHERE id = :sku;
COMMIT;
```

**C2 — Optimistic (CAS via version/conditional update)**
```sql
UPDATE products
   SET stock = stock - 1, version = version + 1
 WHERE id = :sku AND stock > 0 AND version = :v;
-- if 0 rows affected, retry or fail
INSERT INTO orders (user_id, sku) VALUES (:u, :sku) ON CONFLICT DO NOTHING;
```

#### How each constraint is solved
- **FIFO**: Roughly — order is the order locks/transactions are granted. Under contention this is *not* a strict arrival FIFO; the lock manager may grant in any order.
- **Atomic decrement**: Yes, transaction-level.
- **Dedup**: `UNIQUE(user_id, sku)` index.

#### Pros
- Zero new infra: just your existing RDBMS.
- ACID guarantees, easy rollback, easy to audit.
- Fine if the sale is a "soft" flash (10s–100s RPS).

#### Cons
- **Doesn't scale** — pessimistic locks serialize on the row; thousands of waiters back up the connection pool, then the DB falls over.
- Optimistic CAS turns the sale into a thundering-herd retry storm; effective throughput collapses.
- Real FIFO is **not guaranteed** (lock-grant order ≠ wall-clock arrival).
- Connection-pool exhaustion is the typical failure mode.

#### When to pick it
Small sales, internal tools, low-traffic merchants. **Do not use this for a viral consumer flash sale.**

---

### Option D — Virtual Waiting Room + Token Queue (the "big-event" pattern)

This is what large platforms (Ticketmaster, Shopify Launchpad, big retail drops) actually run.

#### Architecture
```
Client (browser)
   │  1. GET /sale/queue → assigns waiting-room token + position
   ▼
CDN / Edge Worker (Cloudflare Workers / Akamai EdgeKV)
   - issues signed tokens with monotonic sequence number
   - serves "you are #482,193 in line" static-ish page
   │
   │  Edge → Regional Aggregator → Global Sequencer (Redis Streams / Kafka)
   │                                  - assigns global FIFO sequence
   │                                  - persists user_id → seq
   ▼
Pacer Service
   - "windowing": every second, admits next K tokens (K tuned to backend capacity)
   - publishes admitted users to "checkout-allowed" topic
   ▼
Checkout Service (now operating at sane RPS)
   - uses Option A (Redis Lua) or Option C2 internally
   - actually decrements inventory & creates the order
   ▼
Postgres (orders), Inventory cache
```

Client behavior: long-poll or WebSocket to `/sale/position`. When admitted, gets a short-lived signed checkout token and is redirected to the actual buy endpoint.

#### How each constraint is solved
- **FIFO**: The sequencer (e.g. a single-partition Kafka topic, or `INCR` on a Redis key) issues monotonically increasing positions. The pacer admits in that order.
- **Admission control**: Backend never sees more than K RPS regardless of how many are waiting. This is the killer feature.
- **Dedup**: Token issuance is keyed on `user_id` (or device fingerprint for guests); duplicate joins return the existing position.
- **Atomic decrement**: Delegated to inner Option A/C — but now under controlled load.

#### Pros
- **Actually scales to tens of millions of waiters** — the edge holds them, not your origin.
- Great UX: users see a position, an ETA, and a fairness signal.
- Backend can be sized for `K` RPS, not `M` RPS — orders of magnitude cheaper.
- Decouples "fairness/FIFO" (sequencer) from "correctness" (inventory). Each layer does one thing.
- Bot/abuse mitigation can sit at the edge (captcha, JWT challenge) before a token is issued.

#### Cons
- Most complex of the four — multiple services, edge logic, state to coordinate.
- True global FIFO across regions requires a single sequencer, which is itself a hot spot (mitigated by batching: edge pushes batches every 50–100ms).
- "Position #482,193" UX requires session pinning so users see consistent numbers.
- Overkill for small sales.

#### When to pick it
Inventory is a few thousand, expected concurrency is millions, and the brand cares about fairness perception. **This is the right answer for a real "drop" or "ticket on-sale".**

---

## 5. Comparison Table

| Aspect | A: Redis+Lua | B: Kafka queue | C: DB locking | D: Virtual queue |
|---|---|---|---|---|
| Throughput ceiling | ~100k–200k RPS | ~50k–100k RPS (1 partition) | ~1k–5k RPS | Effectively unlimited (edge) |
| FIFO strictness | Strong (Redis arrival order) | Strong (partition order) | Weak (lock grant order) | Strong (sequencer order) |
| Dedup mechanism | Redis SET | In-memory consumer set + UNIQUE index | UNIQUE index | Token issuance keyed on user |
| Durability of ordering | Until snapshot/AOF | Strong (log) | Strong (WAL) | Strong (sequencer log) |
| Latency to "won/lost" | < 10 ms | 10s–100s ms | 10s–100s ms | seconds (waiting) + < 100 ms (buy) |
| Operational complexity | Low | Medium | Very low | High |
| Cost at scale | Low | Medium | High (DB scaling) | Medium (edge $$$, but origin cheap) |
| Risk of overload | Yes — must shed upstream | Less, queue absorbs | Falls over fast | Lowest — by design |
| Best inventory size | Small–medium | Small–large | Tiny | Any |
| Best concurrency | up to ~1M with rate-limiting | up to ~500k | < 10k | 10M+ |

---

## 6. Recommended Approach

For the stated scenario (`products << users`, FIFO, one-per-user, scalable):

> **Production recommendation: Option D (virtual queue) on the outside, Option A (Redis + Lua) on the inside.**

Reasoning:
- Option A alone is correct but assumes you can shed load to ~100k RPS. For a true viral drop, this is unsafe — a slashdot/twitter spike will saturate the rate limiter itself.
- Option D's edge layer turns "1M RPS for 30s" into "5k RPS for 5 min", which is a *boring* engineering problem.
- Inside the admitted lane, Option A's Lua script is the cleanest, fastest way to enforce inventory + dedup atomically.
- Option B is a great fit if you must have a durable audit log of every attempt; you can swap it in for the inner layer with minimal change to the outer one.

If the team is small or the sale is modest (≤ a few hundred thousand users), **start with just Option A** plus a good rate limiter and a friendly "sold out" page. Don't over-engineer.

---

## 7. Recommended Architecture (detailed)

```
┌────────────┐
│  Browser   │
└─────┬──────┘
      │ HTTPS
      ▼
┌──────────────────────────┐
│ CDN + Edge Worker        │  ← static sale page, JS client, bot challenges
│  - issues queue token    │
│  - long-poll position    │
└──────┬───────────────────┘
       │ batch every 50ms
       ▼
┌──────────────────────────┐
│ Sequencer                │  ← Redis INCR or single-partition Kafka topic
│  - assigns global seq#   │
│  - stores user_id→seq    │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Pacer (admission ctrl)   │  ← admits next K users / sec; publishes "go" tokens
└──────┬───────────────────┘
       │ signed token (user_id, sku, expiry)
       ▼
┌──────────────────────────┐
│ Checkout API (stateless) │  ← validates token, calls Redis Lua
└──────┬───────────────────┘
       │ EVAL (Lua: dedup + decrement)
       ▼
┌──────────────────────────┐
│ Redis (per-SKU shard)    │  ← inventory:sku, bought:sku set
└──────┬───────────────────┘
       │ async event "won"
       ▼
┌──────────────────────────┐
│ Kafka (orders topic)     │
└──────┬───────────────────┘
       ▼
┌──────────────────────────┐
│ Order Service → Postgres │  ← durable order, payment, fulfillment
└──────────────────────────┘
```

### Key sequence (success case)

```
User              Edge          Sequencer    Pacer      Checkout    Redis    Kafka    Orders
 │  GET /sale     │              │            │           │           │         │         │
 │───────────────▶│              │            │           │           │         │         │
 │                │ INCR seq#=42 │            │           │           │         │         │
 │                │─────────────▶│            │           │           │         │         │
 │ "you are #42"  │              │            │           │           │         │         │
 │◀───────────────│              │            │           │           │         │         │
 │  (long-poll)   │              │            │           │           │         │         │
 │                │              │  admits 42 │           │           │         │         │
 │  "go" + token  │              │            │           │           │         │         │
 │◀───────────────│              │            │           │           │         │         │
 │  POST /buy     │              │            │           │           │         │         │
 │────────────────────────────────────────────────────────▶           │         │         │
 │                │              │            │           │ EVAL Lua  │         │         │
 │                │              │            │           │──────────▶│         │         │
 │                │              │            │           │   1 (won) │         │         │
 │                │              │            │           │◀──────────│         │         │
 │                │              │            │           │   publish "won"     │         │
 │                │              │            │           │────────────────────▶│         │
 │   "you won"    │              │            │           │           │         │         │
 │◀───────────────────────────────────────────────────────│           │         │         │
 │                │              │            │           │           │  INSERT order     │
 │                │              │            │           │           │ ───────────────────▶│
```

---

## 8. API Design (sketch)

| Endpoint | Method | Purpose |
|---|---|---|
| `POST /sale/{sku}/queue` | POST | Join the waiting room. Body: auth token. Returns `{queue_token, position}`. Idempotent on `user_id`. |
| `GET /sale/{sku}/position` | GET | Long-poll / SSE for current position and admission status. |
| `POST /sale/{sku}/buy` | POST | Headers: `X-Admit-Token`. Returns `{status: "won"|"lost"|"sold_out"|"already_bought"}`. |
| `GET /sale/{sku}/order` | GET | Fetch the user's order (after winning). |
| `GET /sale/{sku}/stats` | GET | Public: remaining, queue size. (Cached at edge ~1s.) |

Idempotency: every write endpoint accepts `Idempotency-Key`. The Lua script's `SISMEMBER bought` check is naturally idempotent on `user_id`.

---

## 9. Data Model

### Redis (hot path, ephemeral but persisted via AOF)
```
inventory:{sku}        STRING  -- remaining count, e.g. "1000"
bought:{sku}           SET     -- user_ids that won (cap by inventory size)
queue:{sku}:seq        STRING  -- INCR for global sequence
queue:{sku}:pos:{u}    STRING  -- user → assigned seq# (TTL = sale window + 1h)
admitted:{sku}         STRING  -- pacer cursor
```

### Postgres (durable)
```sql
CREATE TABLE products (
    sku       TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    initial_stock INT NOT NULL
);

CREATE TABLE orders (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT  NOT NULL,
    sku        TEXT    NOT NULL REFERENCES products(sku),
    seq_no     BIGINT  NOT NULL,             -- from sequencer, FIFO record
    status     TEXT    NOT NULL,             -- pending|paid|cancelled
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, sku)                    -- enforces one-per-user
);
CREATE INDEX ON orders (sku, seq_no);
```

### Kafka topics
- `flashsale.{sku}.attempts` — every buy attempt (audit, partitioned by `user_id`).
- `flashsale.{sku}.wins` — winners only, single partition, consumed by Order Service.

---

## 10. Failure Modes and Mitigations

| Failure | Effect | Mitigation |
|---|---|---|
| Redis primary dies | Hot path stops | Redis Sentinel + replica with AOF; brief outage acceptable, resume from AOF; idempotent Lua re-runs are safe. |
| Order Service down | Wins not persisted | Kafka buffers; consumer catches up; user already saw "won". |
| Sequencer single-point | Can't issue positions | Run sequencer as Raft group (e.g. etcd `INCR`-style), or pre-allocate ranges per region. |
| Pacer admits too aggressively | Inner layer overloads | Pacer reads inner-layer p99 latency and back-pressures. |
| User wins but never pays | Inventory locked | Hold expires (e.g. 5 min); script re-increments inventory and removes from `bought` set, slot returns to next-in-line. |
| Bot floods queue | Real users starved | Edge captcha + per-account-age weighting + IP throttle before token issuance. |
| Network partition | Some users see stale position | Position is advisory; final result is decided at `/buy`, which is the source of truth. |

---

## 11. Observability

Per-SKU dashboards:
- Inventory remaining (gauge)
- Queue length (gauge)
- Admission rate (rate)
- Win / loss / sold-out / already-bought counters
- Lua script p50/p99 latency
- Kafka consumer lag (orders topic)

Alerts:
- Inventory mismatch between Redis and Postgres after sale ends
- Pacer back-pressuring > 30s
- Order Service consumer lag > N seconds

---

## 12. Trade-off Summary (TL;DR)

| If you have... | Use |
|---|---|
| < 10k concurrent users, small team | **Option A** (Redis + Lua), nothing fancy |
| Strong audit requirement, durable ordering | **Option B** (Kafka single-partition) |
| Truly tiny sale on existing stack | **Option C2** (optimistic CAS in DB) |
| Millions of users, brand-critical fairness | **Option D** (virtual queue) over Option A |

The recommended production design is **D + A**: edge waiting room + Redis Lua at the inner core. It cleanly separates the four sub-problems (admission, FIFO, atomic decrement, dedup) so each can be scaled and reasoned about on its own.

---

## 13. Appendix: FIFO by Gateway / App-Server Timestamp (not Redis arrival)

In Option A, "FIFO" means *order of `EVAL` arrival at the Redis instance*. That's usually fine, but it can disagree with the order in which requests actually entered the system because:

- Different app servers have different network paths and load.
- A GC pause / cold container can delay one request by 50–200ms.
- LB hashing, TLS handshake reuse, and retries all reorder things.
- A request that hit the API gateway at `t=10ms` may reach Redis *after* one that hit at `t=30ms`.

If the contract is *"the user whose request reached **the gateway** first wins"*, you must capture the timestamp earlier and have the inventory layer respect it.

### 13.1 What you actually need

A FIFO that respects gateway/app-server arrival time requires three things:

1. **A trusted timestamp source** — gateway or app server clocks (NOT the client). All gateway nodes must be NTP-synced; ideally use a monotonic source plus a tie-breaker.
2. **A unique sequence carried with the request** — `(timestamp_ns, gateway_id, local_seq)` is a safe tuple. This is essentially a *Hybrid Logical Clock* (HLC).
3. **A decision point that is allowed to wait briefly** — to let stragglers arrive before declaring winners. Without a drain window, you cannot know whether a slightly older request is still in flight.

That last point is the fundamental cost: **strict gateway-FIFO trades latency for fairness.** You decide whether a user won only after a small grace window (e.g. 50–500 ms) elapses.

### 13.2 Approach 1 — Sorted-set reservation + drain window (recommended)

Replace the immediate "decrement" pattern with a two-phase pattern:

**Phase 1 (immediate, on every request):**

The API gateway stamps each request with `t = wall_clock_ns()` and a tie-breaker `req_id`. The app server runs:

```lua
-- KEYS[1]=pending:{sku}      ZSET, score = timestamp
-- KEYS[2]=bought:{sku}        SET,  user_ids already won (idempotency)
-- ARGV[1]=user_id, ARGV[2]=score (gateway timestamp ns), ARGV[3]=req_id
if redis.call('SISMEMBER', KEYS[2], ARGV[1]) == 1 then
    return 'already_bought'
end
-- ZADD NX: keeps the EARLIEST score per user (first attempt wins for that user)
redis.call('ZADD', KEYS[1], 'NX', ARGV[2], ARGV[1])
return 'pending'
```

Response to user: `{status: "pending", check_back_after_ms: 300}`.

**Phase 2 (deferred, runs every ~50ms or when inventory is reached):**

A single "auctioneer" coroutine — leader-elected — runs:

```lua
-- KEYS[1]=pending:{sku}, KEYS[2]=bought:{sku}, KEYS[3]=inventory:{sku}
-- ARGV[1]=cutoff_score (now - drain_window_ns)
local stock = tonumber(redis.call('GET', KEYS[3]))
if stock <= 0 then return 0 end

-- Take only entries whose timestamp is older than the drain window:
-- guarantees no one earlier is still in flight.
local winners = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1],
                           'LIMIT', 0, stock)
for i, u in ipairs(winners) do
    redis.call('SADD', KEYS[2], u)
    redis.call('ZREM', KEYS[1], u)
    redis.call('DECR', KEYS[3])
end
return winners
```

The auctioneer publishes `(user_id, won)` events that the user's polling endpoint picks up.

**Why this works:**

- ZADD with `NX` enforces *one timestamp per user* — first attempt wins for that user, retries don't change the score.
- The drain window (`now - cutoff`) guarantees you only commit a winner once *no earlier-stamped request can still arrive*. (Cutoff = `max_expected_inflight_latency`.)
- Across many app servers, ordering is decided strictly by gateway timestamp.
- One Redis shard still holds the truth, so atomicity is preserved.

**Trade-offs:**

| Property | Value |
|---|---|
| Extra latency for user | one drain window (e.g. 100–300 ms) |
| Throughput impact | minor — ZADD is O(log n), still 100k+/s per shard |
| Complexity | +1 service (auctioneer with leader election via Redis lock or etcd) |
| Clock requirement | NTP-synced gateways; HLC if you have multi-region |

### 13.3 Approach 2 — Sequencer ticket at the gateway

Every request, on arrival at the gateway, calls a global sequencer to get a strictly-increasing integer ticket *before* doing anything else:

```
Gateway → INCR seq:{sku}  → ticket = 482193
       → forward request to app server with header X-Ticket: 482193
```

The app server then pushes `{ticket, user_id}` into Redis (or Kafka), and the inventory layer awards winners in ticket order.

**Pros:**
- Truly monotonic, no clock-sync dependency.
- Ticket ordering is unambiguous and audit-friendly.

**Cons:**
- The sequencer becomes the new hot single point — one network hop on every request, including losers.
- For 1M RPS that's 1M `INCR`s/sec, which exceeds a single Redis shard. You then need partitioned sequencers (one per region) and a *cross-region merge*, which reintroduces the same ordering problem at a coarser granularity.
- Effectively this is what **Option D** (virtual queue) already does, but at the edge instead of the gateway.

### 13.4 Approach 3 — Per-app-server batching window

Each app server buffers incoming requests for a short window (e.g. 20 ms), sorts them by gateway timestamp, then submits to Redis in sorted order via a single pipelined Lua call:

```
[t=10] req A ─┐
[t=15] req B ─┼─► sort ─► EVAL_BATCH([A, B, C]) ─► Redis
[t=12] req C ─┘
```

**Pros:**
- Removes most intra-server reordering with negligible code.
- No new services.

**Cons:**
- **Doesn't fix cross-server reordering** — server X's batch can still hit Redis before server Y's older requests. Only a global ordering point fixes that.
- Adds latency (the batch window).
- Failure of a server mid-batch loses ordering of those requests.

Useful as a *micro-optimization on top of* Approach 1, not as a standalone solution.

### 13.5 Approach 4 — Move ordering to a log (Kafka) and let Redis just dedup

This is essentially the **Option B** pattern, rephrased to honor gateway timestamps:

1. Gateway stamps `t`, sends to Kafka with `key=sku` (so all attempts for one SKU land in one partition).
2. The single consumer reads in *partition* order (which is roughly arrival order at the broker), but **also re-sorts within a small window** by gateway timestamp before deciding winners. This is the Kafka equivalent of Approach 1's drain window.
3. Consumer maintains in-memory `(remaining, bought_users)`, awards winners to the lowest-`t` requests, and emits a "won" event keyed on user.

**Pros:**
- Durable log of every attempt with its gateway timestamp — perfect audit trail.
- No sorted-set state to worry about; the log *is* the state.
- Producer-side idempotency keys handle dedup for retries.

**Cons:**
- Same single-partition throughput ceiling as Option B (~50–100k msg/s).
- Latency is consumer-lag plus drain window.
- Producer-side timestamp must be set explicitly (Kafka's default is broker append time, which defeats the point).

### 13.6 Comparison

| Approach | FIFO source | Extra latency | Throughput hit | Ops complexity | Notes |
|---|---|---|---|---|---|
| **A1** Sorted-set + drain | gateway timestamp | drain window (100–300 ms) | small | medium (auctioneer) | **Best general fit** when you must respect gateway time |
| **A2** Gateway sequencer | sequencer ticket | one extra round-trip | sequencer is hot | medium | Subsumed by Option D virtual queue |
| **A3** Per-server batch | gateway timestamp (intra-server only) | batch window (20 ms) | tiny | low | Only fixes part of the problem |
| **A4** Kafka + re-sort | gateway timestamp | consumer lag + drain | partition cap | medium-high | Pick when audit log is mandatory |

### 13.7 Practical recommendation

For the system in this document:

1. **Default**: stick with Option A's "Redis arrival order" — it's within a few ms of true gateway order on a healthy network, and that's more than fair enough for a flash sale.
2. **If contract is strict gateway-FIFO**: use **Approach 13.2 (sorted-set + drain window)** layered onto the same Redis. Minimal new infra, well-defined semantics, and the drain window is a tunable knob between latency and fairness.
3. **If you also need a durable, auditable log of every attempt**: switch the inner layer to **Approach 13.5 (Kafka + re-sort)** — same idea, durable substrate.

A pitfall to avoid: **never use the client (browser) timestamp** for ordering. Trust starts at the first server-controlled hop (CDN edge worker or gateway). If you need cross-region fairness, use HLC (server timestamp + logical counter + node id) so a small clock skew between regions doesn't let one region "win" the race trivially.

---

## 14. Generic / Technology-Agnostic View

Strip away the specific tools (Redis, Kafka, Postgres) and every option above is just a different way of building **four primitives**. If you understand the primitives, you can build this on any sensible stack.

### 14.1 The four primitives

| Primitive | Job | Generic requirement |
|---|---|---|
| **Admission Gate** | Bound the rate at which the inner system sees requests | back-pressure aware; can emit a fairness signal (queue position / "you are next") |
| **Order Establisher** | Produce a total order over admitted requests | each request gets a unique, comparable rank; ranks never regress |
| **Inventory Allotter** | Grant exactly `N` tokens, once each, in rank order | atomic state transition: some form of CAS or single-writer |
| **Dedup Registrar** | Record `(user_id, sku) → won` at-most-once | linearizable read-then-write on a per-user key |

If any of those four is missing or weak, the system breaks one of the stated constraints (oversells, or gives one user two units, or randomizes order, or melts under load).

### 14.2 What does "FIFO" actually require?

To produce a total order across many concurrent requests, *something* must serialize them. There is no distributed magic that gives strict FIFO without a single-writer choke point somewhere — this is a **CAP / linearizability fact, not a Redis fact**. The only real question is: where does the choke point live, and what is it made of?

Three families of choke point — pick one for the **Order Establisher**:

| Family | Examples | What you get |
|---|---|---|
| **Single-threaded process** | in-memory cache (Redis, KeyDB), dedicated Go/Rust coordinator holding `atomic.Int64`, single Postgres row | sub-ms decisions; trivially correct |
| **Append-only log with single consumer** | Kafka partition, Kinesis shard, AWS SQS FIFO, Pulsar partition | durable order, replayable, audit trail |
| **Lease / lock manager** | Etcd, ZooKeeper, Spanner TrueTime, Postgres advisory locks | strong consistency with explicit leader semantics |

You **cannot** scale-out the Order Establisher without weakening FIFO — partitioning or sharding the order means cross-shard order is undefined. To handle more load, one of two things must happen:

1. Reduce the rate at which requests reach it (Admission Gate does this), or
2. Loosen the ordering contract (per-region FIFO, per-bucket FIFO, time-bucketed FIFO, …).

### 14.3 Mapping the four options to the four primitives

| Option | Admission Gate | Order Establisher | Inventory Allotter | Dedup Registrar |
|---|---|---|---|---|
| **A — single-arbiter cache** | upstream rate limiter | arrival order at the arbiter | atomic op on a counter | set / hash on the arbiter |
| **B — durable log** | upstream rate limiter | append order in the log | single consumer's local state | unique index in DB + idempotency key |
| **C — RDBMS locks** | connection pool (de facto) | lock-grant order (weak) | row update inside txn | unique constraint |
| **D — virtual queue** | edge waiting room | sequencer (counter or log) | inner Allotter (A/B/C) | token issuance keyed on user |

Reading this table, the design space becomes clear: **each cell is independent and replaceable**. The "recommended D + A" just means *pick D's column for Admission and A's column for the other three*. You could equally pick D + B, or even build a custom coordinator that does its own thing for all four cells.

### 14.4 The generic recommended design (no product names)

```
┌────────────────────────────────────────────────────────────────┐
│                        Admission Gate                          │
│  - bounds inflight to ~K requests/sec (K << peak demand)       │
│  - issues a "you are admitted" credential bound to user_id     │
│  - holds the surplus elsewhere (close to the user, cheaply)    │
└─────────────────────────┬──────────────────────────────────────┘
                          │ admitted requests, at controlled rate
                          ▼
┌────────────────────────────────────────────────────────────────┐
│                     Order Establisher                          │
│  - assigns a unique monotonic rank to each admitted request    │
│  - durable enough to survive its own restart (or replayable)   │
└─────────────────────────┬──────────────────────────────────────┘
                          │ (request, rank)
                          ▼
┌────────────────────────────────────────────────────────────────┐
│         Inventory Allotter   +   Dedup Registrar               │
│   atomic step: "if user not yet won AND stock > 0,             │
│                  decrement stock AND mark user won"            │
│   correctness: single linearizable transition per (user, sku)  │
└─────────────────────────┬──────────────────────────────────────┘
                          │ "won" decisions
                          ▼
┌────────────────────────────────────────────────────────────────┐
│            Durable Order Store (system of record)              │
│  - persists who won, in rank order                             │
│  - downstream payment / fulfillment reads from here            │
└────────────────────────────────────────────────────────────────┘
```

Each box is *one* responsibility. You can implement each box in whatever your team operates best.

### 14.5 What changes when you swap technology

Each cell above only depends on whether the chosen tool delivers the **generic guarantee** for that cell:

- **Order Establisher** needs *"unique, monotonic rank per request, no regressions, fast enough"*. An in-memory `INCR`, a log append, a Postgres `nextval()`, a ZooKeeper sequential znode, even an HTTP call to a Go service holding `atomic.Int64` — all valid. Pick on operational grounds (latency budget, durability, team familiarity), not on feature.
- **Inventory Allotter** needs *"compare-and-set with linearizable visibility"*. A Lua script in Redis, `UPDATE ... WHERE stock>0` in Postgres, a DynamoDB conditional write, an Etcd transaction, a `compareAndSet` on a coordinator — all interchangeable.
- **Dedup Registrar** needs *"linearizable, at-most-once per-user write"*. A unique index does this. So does `SETNX`. So does Cassandra `IF NOT EXISTS`. So does a single-writer in-memory map persisted to a log.
- **Admission Gate** needs *"back-pressure with fairness"*. Token bucket, leaky bucket, edge waiting room, per-pod connection cap, even `nginx limit_req_zone` — all acceptable; differ in fairness quality and how nice the UX is.

### 14.6 Generic decision rubric

When picking a technology for each cell, ask:

1. **Latency budget** — can it answer in time? (Choke-point latency × QPS must fit in your SLA.)
2. **Durability requirement** — if the choke point dies mid-sale, is it OK to lose its state? If yes, in-memory tools fit. If not, pick a logged or replicated tool.
3. **Operational familiarity** — what does your team already run well? A boring choice you operate well beats a fashionable one you don't.
4. **Throughput ceiling** — single-shard caps for common tools (rough numbers):
   - in-memory single-threaded store: ~100–200k ops/s
   - single log partition: ~50–100k msg/s
   - single hot DB row under contention: ~1–5k tx/s
   - consensus-based KV (etcd/ZK) writes: ~10–30k/s
5. **Failure-mode story** — what happens at leader loss? You want bounded-time failover with clear recovery semantics (idempotent retries, replayable log, stateless callers).

If two technologies score the same on (1)–(4), pick on (3).

### 14.7 Reframing the gateway-FIFO question

> *"What if I want FIFO based on gateway timestamp, not Redis arrival?"*

Generically: **move the Order Establisher upstream of where network/processing jitter lives.** It doesn't matter whether the upstream point is an in-memory cache, a log, a coordinator service, or a Postgres sequence — the property you need is *"rank is assigned at the gateway and honored downstream"*. The four approaches in §13 are just four placements of that Order Establisher and four ways of resolving stragglers (drain window, pre-issued ticket, batch sort, log re-sort).

### 14.8 The takeaway

**The design is the choice of where the choke point lives and what generic guarantees it provides. The technology is an implementation detail.**

If a future reader of this document wants to rebuild the system in a different stack, they should start from §14.1's four primitives, decide which §14.2 family backs each one, and only then reach for product names.
