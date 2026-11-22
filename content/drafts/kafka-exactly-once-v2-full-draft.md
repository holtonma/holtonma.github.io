---
title: "Kafka Exactly-Once Semantics (EOS v2)"
date: 2026-07-25T08:00:00-07:00
draft: true
tags: ["kafka", "distributed-systems", "streaming"]
categories: ["technical-architecture"]
description: ""
cover:
    image: ""
    alt: ""
    caption: ""
ShowToc: true
TocOpen: false
---

# Kafka Architecture: Building Verifiably Correct Event Systems

## What “Exactly Once” Really Means in Kafka Streams: Inside `exactly_once_v2`

Distributed systems rarely fail at convenient boundaries.

A service does not politely crash before it begins processing a record. It can crash at anytime for various reasons: A network connection fails after a producer sends a record but before it receives the acknowledgment. A task moves to another application instance while the previous owner is paused. A downstream database commits a write, but the process dies before acknowledging the corresponding Kafka record. As an architect and engineer you need to design for the possibility where it crashes after updating some state but before recording its progress.

These are the moments when the difference between a system that usually works and one that can be trusted becomes clear.

Earlier in my career, I spent more than ten years at Salesforce architecting and building distributed applications, event pipelines, and stream-processing systems. Reliable pipelines became a major part of my work as an engineer.

Two earlier Salesforce Engineering articles describe some of that foundational event-pipeline work: [the first](https://engineering.salesforce.com/building-a-fault-tolerant-data-pipeline-for-chatbots-47d74bc31f5b/) explains an architecture for asynchronously and reliably exporting chatbot events through Kafka, and [the second](https://engineering.salesforce.com/building-a-scalable-event-pipeline-with-heroku-and-salesforce-2549cb20ce06/) examines fault-tolerance patterns such as replay, retries, circuit breakers, and bulkheads. Those systems were designed to support large-scale products while isolating their primary runtime responsibilities from potentially slow or unreliable downstream delivery.

That work was an important part of my development as an engineer and architect. It gave me extensive experience thinking about event delivery, recoverability, isolation, stateful processing, and the failure modes that appear when distributed systems operate at scale.

> This series builds on that experience, but it is not an account of any proprietary implementations. The examples, code, diagrams, and sample applications are independently created educational materials based on publicly documented Kafka and Kafka Streams capabilities.

This new series will go deeper into additional Kafka architectures, including those leveraging Kafka Streams

The goal is not simply to review APIs. It is to understand the mechanisms, boundaries, and design choices that make one Kafka application more reliable than another.

The goal is to explore Kafka architecture in enough depth that engineers can reason about the guarantees themselves: what Kafka commits, where those guarantees end, how state is recovered, how failures affect observable results, and what additional design mechanisms are needed to build systems whose outputs can be verified.

## exactly_once_v2
In this first article, we will examine one of Kafka Streams’ most important, and most frequently misunderstood, features:

```properties
# Spring Boot application.properties for KafkaStreams application
processing.guarantee=exactly_once_v2
```

```properties
# // Plain ol Java Kafka Streams configuration
props.put(
    StreamsConfig.PROCESSING_GUARANTEE_CONFIG,
    StreamsConfig.EXACTLY_ONCE_V2
);
```

The central question is:

> What does Kafka Streams actually commit when it claims “exactly once”?

The answer is powerful, but it has a precise boundary.

Within Kafka, `exactly_once_v2` can atomically coordinate:

1. the offsets of consumed input records;
2. the records representing state-store changes in changelog topics; and
3. records written to Kafka output topics.

Kafka Streams therefore should not successfully record that it consumed an event while failing to commit the corresponding state change or output record. i.e. it does them together.

If the transaction fails, its transactional writes are aborted. The input offsets do not advance as part of that failed transaction, and the input can be processed again.

That is the essential guarantee.

But exactly once stops at the Kafka boundary. A PostgreSQL database, external API, billing platform, object store, or other system does not automatically join the Kafka transaction.

A verifiably correct architecture must therefore combine several mechanisms:

* Kafka exactly-once processing inside the Kafka pipeline;
* durable Kafka topics as transactional handoff points;
* deterministic and idempotent writes at external boundaries;
* explicit handling of corrections and business duplicates;
* and reconciliation across the system’s major stages.

Let’s make those ideas concrete.

---

# A Running Example: AI Usage Metering

Imagine that we are building a multi-tenant AI platform.

Every completed model request produces a usage event:

```java
public record ModelUsageEvent(
    String tenantId,
    String requestId,
    String modelId,
    long inputTokens,
    long outputTokens,
    Instant completedAt,
    int eventVersion
) {}
```

A few example events might look like this:

```text
10:01:04  Request A  1,200 tokens
10:02:17  Request B    800 tokens
10:04:51  Request C  2,000 tokens
```

All three belong to:

```text
tenant: tenant-42
model: model-a
window: 10:00–10:05
```

The Kafka Streams application aggregates them into a finalized usage record:

```text
tenantId: tenant-42
modelId: model-a
window: 10:00–10:05
totalTokens: 4,000
requestCount: 3
aggregationVersion: 1
```

This may look like a simple counting application, but correctness matters.

An undercount might cause inaccurate cost allocation, incorrect quota enforcement, lost revenue, or misleading customer reports. An overcount could cause a customer to be charged for usage that never occurred. A duplicated aggregate could affect billing, capacity planning, abuse detection, or usage dashboards.

The application must not:

* lose the effect of a request after marking it consumed;
* count the same request twice because of a recovery attempt;
* publish an aggregate that does not match its recoverable state;
* silently treat a corrected event as a retry;
* or assume that Kafka’s transaction automatically includes an external database.

This makes usage metering a useful example of a broader class of correctness-sensitive systems.

---

# The Topology

A simplified Kafka Streams topology might look like this:

```java
KStream<String, ModelUsageEvent> usageEvents =
    builder.stream(
        "model-usage-events",
        Consumed.with(Serdes.String(), usageEventSerde)
    );

KTable<Windowed<String>, UsageAggregate> usageByWindow =
    usageEvents
        .selectKey((ignoredKey, event) ->
            event.tenantId() + ":" + event.modelId())
        .groupByKey(
            Grouped.with(Serdes.String(), usageEventSerde)
        )
        .windowedBy(
            TimeWindows.ofSizeAndGrace(
                Duration.ofMinutes(5),
                Duration.ofMinutes(1)
            )
        )
        .aggregate(
            UsageAggregate::empty,
            (key, event, aggregate) -> aggregate.add(event),
            Materialized.<String, UsageAggregate, WindowStore<Bytes, byte[]>>
                as("usage-aggregate-store")
                .withKeySerde(Serdes.String())
                .withValueSerde(usageAggregateSerde)
        );

usageByWindow
    .suppress(
        Suppressed.untilWindowCloses(
            Suppressed.BufferConfig.unbounded()
        )
    )
    .toStream()
    .map((windowedKey, aggregate) ->
        KeyValue.pair(
            finalizedUsageId(windowedKey, aggregate),
            FinalizedUsage.from(windowedKey, aggregate)
        )
    )
    .to(
        "finalized-model-usage",
        Produced.with(Serdes.String(), finalizedUsageSerde)
    );
```

The example is intentionally small. A production implementation would require additional validation, schema-evolution rules, error handling, observability, capacity planning, and possibly source-level deduplication.

For this article, however, the topology gives us the elements we need:

* input records;
* a grouping key;
* a five-minute window;
* a materialized aggregate;
* a state-store changelog;
* suppression of intermediate results;
* a suppression buffer and its changelog;
* and a finalized Kafka output topic.

At first glance, the processing path appears linear:

```text
Input
  │
  ▼
Group
  │
  ▼
Windowed aggregate
  │
  ▼
Suppress intermediate updates
  │
  ▼
Finalized output
```

Internally, however, one input record can cause several related effects.

---

# Processing One Record Has Multiple Consequences

Suppose Request C is stored at offset 417 of input partition 3.

When Kafka Streams processes that event, several things may happen:

1. The consumer advances through input partition 3.
2. The local aggregate changes from 2,000 tokens to 4,000 tokens.
3. A change representing the aggregate update is written to the aggregate store’s changelog topic.
4. The suppression buffer’s state changes.
5. If the window is ready to close, a finalized usage record is written to the output topic.
6. The application records that processing has completed through offset 417, meaning the next offset is 418.

These effects are logically related.

If Kafka permanently records the consumed offset but loses the state change, the application could resume at offset 418 with an aggregate that does not include Request C.

If it records the aggregate change but loses its progress marker, Request C may be processed again after restart.

If it publishes the finalized output but fails to record the consumed offset, the same source input can be replayed and potentially generate another output.

The key architectural question is therefore:

> What prevents Kafka from committing only some of these consequences?

**[Graphic opportunity: One source event branching into input progress, aggregate state, suppression state, and output.]**

---

# The Failure Window Under At-Least-Once Processing

Consider an ordinary consume-process-produce sequence:

```text
1. Read input offset 417
2. Update the aggregate
3. Write the output
4. Commit input offset 418
```

Now imagine that the process crashes between steps three and four:

```text
Input read
    │
    ▼
State updated
    │
    ▼
Output written
    │
    ✕ CRASH
    │
    ▼
Offset never committed
```

The output may already exist, but the consumer group still believes that offset 417 has not been completed.

After restart, the application reads offset 417 again.

This is normal at-least-once behavior. The system protects against losing the input, but it may execute the processing logic again and produce duplicate effects.

Committing the input offset only after processing is complete is better than committing it before processing. It prevents the application from skipping an input whose work was never performed.

But commit-after-processing is not atomic processing.

The output write and the input-offset commit remain separate actions. A crash can occur between them.

Without a transaction, the application cannot guarantee:

```text
Both effects become committed
```

or:

```text
Neither effect becomes committed
```

There is a dangerous gap between them.

**[Animation opportunity: The output becomes visible, the application crashes, and the same input record re-enters the topology after restart.]**

---

# The Exact Kafka Boundary

Kafka Streams exactly-once processing addresses this problem by using Kafka transactions.

The official Kafka Streams documentation describes the guarantee in terms of three related effects:

* input-topic offset commits;
* state-store updates;
* output-topic writes.

Kafka Streams coordinates those effects atomically rather than treating each as an independent side effect.

Conceptually, our usage-metering application might create a transaction containing:

```text
Kafka transaction T-892
│
├── consumed input offset
│   model-usage-events-3 → 418
│
├── aggregate changelog update
│   tenant-42:model-a:10:00 → 4,000 tokens
│
├── suppression-state changelog update
│   final window result ready for release
│
└── output record
    finalized-model-usage → usage record U-1001
```

Kafka then reaches one of two outcomes.

## Commit

All transactional effects become committed together:

```text
COMMIT
├── offset 418 becomes the committed recovery position
├── state changes become committed
└── output record becomes committed
```

## Abort

The transaction does not become a successful processing result:

```text
ABORT
├── the transactional offset advance does not become committed
├── aborted changelog writes are not treated as committed state
└── aborted output records are hidden from read_committed consumers
```

The input can then be processed again in a new transaction.

This is the central principle:

> Kafka exactly-once processing does not necessarily prevent code from executing more than once. It prevents failed attempts from becoming multiple committed effects inside the Kafka transaction boundary.

That distinction matters.

A record may be read during one attempt, processed, and written transactionally. If the process crashes before the transaction commits, Kafka Streams may process the record again.

The physical calculation executed twice.

The committed result, however, is reflected once.

A more accurate description is therefore:

> The committed effects of the processing operation are reflected once within Kafka.

Not:

> The business code can only execute once.

---

# Transactional Visibility and `read_committed`

Kafka must also prevent downstream applications from treating aborted records as valid output.

With exactly-once processing enabled, Kafka Streams configures its consumers with:

```properties
isolation.level=read_committed
```

and enables producer idempotence. The documented configuration also changes the default `commit.interval.ms` for exactly-once processing to 100 milliseconds.

A `read_committed` consumer only returns transactional records from successfully committed transactions. Records from aborted transactions remain in the physical log, but they are not exposed as committed application results to such consumers.

Conceptually:

```text
Attempt 1
read → calculate → produce → crash
                       │
                       └── transaction aborted
                           output not visible to read_committed consumer

Attempt 2
read → calculate → produce → commit
                       │
                       └── committed output visible
```

This means downstream Kafka consumers must participate in the intended visibility model. A consumer configured to read uncommitted data does not receive the same protection from aborted transactional records.

**[Graphic opportunity: A Kafka log containing both aborted and committed records, with a `read_committed` consumer seeing only the committed path.]**

---

# What Happens During a Kafka Streams Commit?

It is tempting to imagine one transaction per input record:

```text
one input → one transaction → one commit
```

That is not the right general model.

Kafka Streams processes records continuously and commits groups of processing work according to its runtime behavior and configuration.

Conceptually, a stream thread does the following:

1. Polls records from its assigned input partitions.
2. Dispatches those records to stream tasks.
3. Executes the topology.
4. Updates local state.
5. Produces state-store changelog records.
6. Produces application output records.
7. Adds processed input offsets to the transaction.
8. Commits the transaction.
9. Begins the next unit of transactional work.

This distinction matters for both performance and failure recovery.

A transaction may contain effects from multiple records and multiple tasks handled by the same stream thread. The transaction is the atomic boundary, not necessarily the individual source event.

---

# Local State Is Not the Complete Durability Model

Kafka Streams commonly uses local state stores, frequently backed by RocksDB, for stateful operations such as:

* aggregations;
* joins;
* windowed calculations;
* tables;
* and suppression.

Local state makes processing efficient because a task does not need to query a remote database for every record.

But a local RocksDB write by itself is not the distributed durability guarantee.

The machine can fail. Its disk can be lost. The task can move to another Kafka Streams instance during a rebalance.

Kafka Streams therefore represents recoverable state changes in Kafka changelog topics.

For the usage application, the local store might hold:

```text
key:
tenant-42:model-a:window-10:00

value:
inputTokens: 1,500
outputTokens: 2,500
totalTokens: 4,000
requestCount: 3
```

A corresponding changelog record allows Kafka Streams to reconstruct that state elsewhere.

The recovery model involves several related components:

* the source Kafka topics;
* the committed input offsets;
* the state-store changelog topics;
* local state and local checkpoint information;
* and the topology’s processing logic.

After a task is restarted or moved, Kafka Streams can restore its local store from the changelog and resume from the appropriate committed input position.

The state and the progress marker must agree.

Suppose offset 417 changes the aggregate from:

```text
2,000 tokens
```

to:

```text
4,000 tokens
```

The application must not permanently commit:

```text
next input offset = 418
```

while restoring state that still says:

```text
aggregate = 2,000 tokens
```

If that happened, the application would resume after Request C even though Request C’s contribution was absent from state.

The atomic coordination of offsets and state changes is what prevents this disagreement within Kafka.

---

# Where `suppress()` Fits

A Kafka Streams aggregation produces an evolving `KTable`.

As each request arrives, the aggregate may change:

```text
Request A → 1,200 tokens
Request B → 2,000 tokens
Request C → 4,000 tokens
```

Without suppression, downstream processing can receive successive updates to the same logical windowed result:

```text
1,200
2,000
4,000
```

These values are not necessarily three independent business facts. They may be three versions of one still-developing five-minute aggregate.

For some use cases, seeing every update is desirable.

For finalized usage reporting, however, we may want one result after the window closes:

```text
tenant-42
model-a
10:00–10:05
4,000 tokens
3 requests
```

That is where `suppress()` enters the topology.

```java
.suppress(
    Suppressed.untilWindowCloses(
        Suppressed.BufferConfig.unbounded()
    )
)
```

Conceptually, suppression acts as a stateful gate:

```text
Window opens
│
├── Request A → aggregate 1,200 → buffer
├── Request B → aggregate 2,000 → replace buffered result
└── Request C → aggregate 4,000 → replace buffered result

Window closes after grace period
│
└── emit final aggregate: 4,000
```

The suppression buffer is not merely an ordinary Java collection whose contents are unrelated to Kafka Streams state management.

Kafka’s KIP-446 describes the suppress operator as using an internal changelog topic. It notes that records are written to the changelog as they enter the suppression buffer and tombstoned after they are emitted. Logging is enabled by default, although the API allows it to be configured or disabled—with loss of fault tolerance if it is disabled.

That gives us an important connection:

Under `exactly_once_v2`, the transactional work can include:

* source-offset progress;
* aggregate-store changelog records;
* suppression-store changelog records;
* and the finalized output record.

The suppression state is not an entirely separate, independently committed result.

## Failure as a window closes

Suppose the window is ready to close.

Kafka Streams releases the final 4,000-token aggregate from the suppression buffer and produces it to `finalized-model-usage`.

Then the process crashes before the transaction commits.

Conceptually:

```text
Release final result
        │
        ▼
Produce output transactionally
        │
        ✕ CRASH
        │
        ▼
Transaction aborts
```

Because the transaction did not commit successfully:

* the final output is not visible to `read_committed` consumers;
* the new input-offset position does not become committed as part of that transaction;
* the corresponding transactional state changes are not accepted as a committed unit;
* and Kafka Streams can recover and produce the final result again in a later successful transaction.

The reader sees the committed result, not every failed attempt.

---

# Suppression Does Not Remove Operational Risk

Suppression improves the semantics of final-only output, but it introduces capacity concerns.

This configuration is particularly important:

```java
Suppressed.BufferConfig.unbounded()
```

“Unbounded” does not mean “free.”

The suppression buffer may grow because of:

* large numbers of open windows;
* high-cardinality keys;
* long window durations;
* long grace periods;
* stalled stream time;
* skewed partitions;
* or one tenant producing far more traffic than others.

Kafka Streams must retain buffered results until their windows are ready to close. Depending on the store implementation and configuration, this can consume substantial local storage and memory-related resources.

If stream time stops advancing because one or more relevant partitions stop receiving records, windows may remain open longer than an engineer expects from wall-clock time alone.

Exactly-once semantics do not solve these capacity problems.

They do not prevent:

* local-disk exhaustion;
* memory pressure;
* long restoration times;
* hot keys;
* insufficient changelog retention;
* or poorly chosen window and grace-period settings.

A correctness guarantee is not a substitute for resource modeling.

**[Graphic opportunity: Thousands of open tenant windows accumulating behind the suppression gate while stream time remains stationary.]**

---

# What `exactly_once_v2` Changed

Kafka introduced the foundations for transactional and idempotent production in Kafka 0.11. Kafka Streams then used those capabilities to coordinate state, output, and input progress.

The original Kafka Streams exactly-once implementation worked, but its producer model had scaling costs.

The key problem was fencing.

Kafka must prevent an old or stale producer from continuing to commit work after partition ownership has transferred to another application instance.

Imagine this sequence:

1. Instance A owns a task.
2. Instance A pauses because of a long garbage-collection event or network problem.
3. The consumer group rebalances.
4. Instance B receives the task.
5. Instance A resumes and attempts to continue processing.

Instance A is now a zombie. It must not be allowed to commit results for work it no longer owns.

Kafka transactions use transactional IDs, producer IDs, and producer epochs to fence obsolete producer instances. For a given transactional identity, an older producer epoch can be rejected after a newer producer has taken ownership. KIP-447 explains this fencing model and the scalability problem caused by the original mapping between transactional producers and input partitions.

## EOS v1: producer per task

The first Kafka Streams implementation used a producer at task-level granularity:

```text
Stream thread
│
├── Task 0 ── Transactional producer 0
├── Task 1 ── Transactional producer 1
├── Task 2 ── Transactional producer 2
└── Task 3 ── Transactional producer 3
```

As task counts increased, this architecture could create:

* many producers;
* separate producer buffers;
* more threads and network connections;
* additional metadata overhead;
* more concurrent transactions;
* and weaker opportunities for batching across tasks.

KIP-447 describes this model as failing to scale efficiently as input-partition counts increase.

## EOS v2: producer per stream thread

The improved design passed fuller consumer-group metadata when sending offsets to the Kafka transaction.

This allowed Kafka’s coordination logic to determine whether the producer still belonged to the valid consumer-group generation and assignment. Stale producers could be fenced using consumer-group ownership information rather than requiring a permanently fixed producer-to-input-partition mapping.

Kafka Streams could therefore use a transactional producer per stream thread:

```text
Stream thread
│
├── Task 0
├── Task 1
├── Task 2
├── Task 3
│
└── Shared transactional producer
```

This improved batching and reduced client and broker resource consumption. Kafka’s Streams documentation describes exactly-once v2 as more efficient, with lower client and broker resource use and improved throughput and scalability.

The relevant version history is:

* Kafka 0.11 introduced transactional capabilities underlying Kafka Streams exactly-once processing.
* Kafka 2.5 added the broker-side support required by the improved fencing model.
* Kafka Streams 2.6 introduced the improved implementation.
* The supported configuration name is now `exactly_once_v2`.
* The earlier `exactly_once` and `exactly_once_beta` values were deprecated and have since been removed from current valid configuration values.

The most important point is what v2 did **not** change.

It did not expand the transaction into PostgreSQL, Salesforce, an HTTP API, or an arbitrary external service.

Version 2 improved Kafka Streams’ internal fencing, efficiency, and scalability. It did not turn Kafka transactions into distributed transactions across unrelated systems.

---

# The Kafka Boundary

Our usage-metering topology writes a finalized record to:

```text
finalized-model-usage
```

Suppose another service consumes that topic and writes the result into a usage database used for reporting and cost allocation.

```text
Model usage events
        │
        ▼
Kafka Streams aggregation
        │
        ▼
Finalized usage topic
        │
        ▼
Usage database writer
        │
        ▼
PostgreSQL
```

The Kafka Streams transaction ends at the Kafka output topic.

The PostgreSQL transaction is separate.

The database writer may:

1. Read finalized usage record U-1001.
2. Commit U-1001 to PostgreSQL.
3. Crash before committing its Kafka consumer offset.
4. Restart.
5. Receive U-1001 again.

Kafka has behaved correctly. The consumer did not commit its progress, so Kafka redelivered the record.

But unless the database write is idempotent, the external system may now contain two rows representing the same finalized usage window.

This is the dual-write problem appearing at a new boundary.

A durable Kafka topic provides a strong handoff point, but the next system must still handle retries correctly.

---

# Stable Business Identity

Each finalized usage record should have a deterministic identity.

For example:

```text
tenantId
+ modelId
+ windowStart
+ aggregationVersion
```

That might produce:

```text
tenant-42:model-a:2026-07-25T10:00:00Z:v1
```

The value should represent one logical finalized result.

The usage database can enforce a uniqueness constraint on that identity:

```sql
CREATE TABLE finalized_usage (
    usage_id             VARCHAR(255) PRIMARY KEY,
    tenant_id            VARCHAR(100) NOT NULL,
    model_id             VARCHAR(100) NOT NULL,
    window_start         TIMESTAMP NOT NULL,
    window_end           TIMESTAMP NOT NULL,
    input_tokens         BIGINT NOT NULL,
    output_tokens        BIGINT NOT NULL,
    request_count        BIGINT NOT NULL,
    aggregation_version  INTEGER NOT NULL
);
```

When the writer receives U-1001 for the first time, it inserts it.

If Kafka delivers U-1001 again after a crash, the writer finds the same `usage_id`.

There are then two important possibilities.

## Matching retry

Existing row:

```text
usageId: tenant-42:model-a:10:00:v1
totalTokens: 4,000
requestCount: 3
```

Retried record:

```text
usageId: tenant-42:model-a:10:00:v1
totalTokens: 4,000
requestCount: 3
```

This is a matching retry.

The result can be treated as a successful no-op.

## Conflicting retry

Existing row:

```text
usageId: tenant-42:model-a:10:00:v1
totalTokens: 4,000
```

Incoming record:

```text
usageId: tenant-42:model-a:10:00:v1
totalTokens: 4,300
```

This is not a harmless duplicate.

The same identity now maps to two different values.

The writer should reject, quarantine, and alert on the conflict. Silently accepting it would hide nondeterministic processing, incorrect replay data, a versioning bug, or corruption elsewhere in the pipeline.

Idempotency should suppress repeated delivery of the same fact.

It should not conceal contradictory facts.

---

# Duplicate Delivery Is Not the Same as a Correction

Suppose a model provider later reports that Request C used 2,300 tokens rather than 2,000.

That is not merely another delivery attempt for the original event.

It is a correction.

The architecture must distinguish:

```text
Same logical fact, delivered again
```

from:

```text
A previously reported fact has changed
```

A correction may require:

* a new event version;
* an explicit correction event;
* a new aggregation version;
* a replacement record with well-defined semantics;
* or a compensating adjustment.

For example:

```text
original:
requestId: C
eventVersion: 1
tokens: 2,000

correction:
requestId: C
eventVersion: 2
tokens: 2,300
replacesVersion: 1
```

The appropriate correction strategy depends on the business model, but the distinction must be explicit.

Otherwise, a deduplication layer might incorrectly discard a legitimate correction as a retry—or accept a duplicate as a new correction.

---

# Exactly Once Does Not Deduplicate Business Events

There is another subtle but important boundary.

Suppose the input topic contains:

```text
offset 417 → requestId C, version 1, 2,000 tokens
offset 418 → requestId C, version 1, 2,000 tokens
```

Both records were successfully committed by the upstream producer.

From Kafka’s perspective, these are two input records at two different offsets.

`exactly_once_v2` will process the committed effects of each Kafka record exactly once. It does not inherently know that the two records represent the same business request.

Without explicit business-level deduplication, the aggregate may become:

```text
6,000 tokens
```

rather than:

```text
4,000 tokens
```

This gives us a crucial architectural distinction:

> Kafka exactly-once processing protects against duplicate committed effects caused by transactional retries and recovery. It does not automatically identify two separate source records as the same business event.

Business-level uniqueness still requires:

* a stable event identity such as `requestId`;
* a clear version model;
* a deduplication store or upstream uniqueness guarantee;
* sufficient retention for deduplication state;
* and an explicit policy for corrections.

Exactly-once transaction semantics and business deduplication solve related but different problems.

---

# The Complete End-to-End Model

A robust design can be understood in three layers.

## Layer 1: Kafka transactional correctness

Inside the Kafka Streams topology:

```text
input offsets
+ aggregate changelog updates
+ suppression-state updates
+ Kafka output records
```

commit or abort together.

This protects the relationship between consumed input, recoverable state, and Kafka output.

## Layer 2: Idempotent external materialization

At the Kafka-to-database boundary:

* each finalized output has a deterministic identity;
* the destination enforces uniqueness;
* matching retries become no-ops;
* conflicting retries are rejected and surfaced;
* corrections use explicit versioning or adjustment semantics.

## Layer 3: Reconciliation

Across the complete system, periodic reconciliation compares:

```text
raw request events
        ↓
accepted usage events
        ↓
finalized Kafka usage records
        ↓
database materializations
        ↓
rated or billed usage
```

Every committed calculated output should be explainable.

Every finalized external record should map back to a committed Kafka output.

Every rejected record should have a reason.

Every correction should be traceable to the fact it changes.

This is where “exactly once” becomes part of a broader correctness architecture rather than a configuration checkbox.

---

# Failure-Mode Walkthrough

A useful way to evaluate the design is to ask what happens at each possible failure point.

## Failure 1: Crash before state or output is produced

```text
Input read
    │
    ✕ CRASH
```

Expected behavior:

* no successful transaction is committed;
* the input offset does not advance;
* the input is processed again.

## Failure 2: Aggregate changelog is produced, but the transaction aborts

```text
Input read
    │
State updated
    │
Changelog produced
    │
✕ CRASH
```

Expected behavior:

* the changelog record is part of the aborted transaction;
* the consumed offset does not advance as a committed transaction result;
* processing is replayed from the committed position.

## Failure 3: Kafka output is produced, but the transaction aborts

```text
Input read
    │
State updated
    │
Output produced
    │
✕ CRASH
```

Expected behavior:

* the output is not visible to `read_committed` consumers;
* the new source offset is not committed;
* the record can be processed again.

## Failure 4: Transaction commits, then the process crashes

```text
Input read
    │
State updated
    │
Output produced
    │
Transaction committed
    │
✕ CRASH
```

Expected behavior:

* the input offset remains committed;
* the state changes remain committed;
* the output remains committed;
* recovery resumes after the completed work.

## Failure 5: Database commits, writer crashes before Kafka offset commit

```text
Kafka output consumed
        │
Database insert committed
        │
✕ CRASH
        │
Kafka offset not committed
```

Expected behavior:

* Kafka redelivers the output;
* the deterministic usage ID maps to the existing database row;
* a matching retry becomes a successful no-op.

## Failure 6: Replay uses changed business logic

Suppose the original aggregation excluded a class of internal test requests, but a later version does not.

Replaying the same historical topic may now produce a different result even though Kafka’s transactional mechanics work perfectly.

Exactly-once infrastructure cannot guarantee deterministic business logic.

Replay determinism may require:

* versioned calculation logic;
* historically correct reference data;
* stable event schemas;
* versioned enrichment data;
* and explicit migration rules.

## Failure 7: Suppression state grows without bound

Suppose hundreds of thousands of tenants have open windows and stream time stops progressing.

The suppression buffer may continue to grow.

Possible consequences include:

* local disk pressure;
* increased memory pressure;
* slower state restoration;
* longer startup times;
* and application failure.

Exactly-once semantics preserve transaction consistency. They do not create infinite capacity.

---

# What `exactly_once_v2` Does Not Guarantee

This section may be more important than the configuration itself.

`exactly_once_v2` does not guarantee:

* exactly one physical execution of application code;
* exactly one delivery to an arbitrary external consumer;
* atomicity with PostgreSQL or another external database;
* automatic deduplication of repeated business events;
* correct business logic;
* deterministic replay after logic changes;
* historically correct enrichment data;
* correct handling of event corrections;
* bounded suppression state;
* adequate changelog retention;
* protection from poison events;
* absence of hot keys;
* correct topology migration;
* safe arbitrary partition-count changes;
* sufficient replication;
* or successful end-to-end reconciliation.

It guarantees atomic committed effects inside a defined Kafka boundary.

That is extremely valuable.

It is not the same as claiming that the entire distributed system is exactly once.

---

# Operational Requirements

Enable the feature explicitly:

```java
properties.put(
    StreamsConfig.PROCESSING_GUARANTEE_CONFIG,
    StreamsConfig.EXACTLY_ONCE_V2
);
```

or:

```properties
processing.guarantee=exactly_once_v2
```

The default remains `at_least_once`, and current Kafka documentation requires Kafka brokers version 2.5 or newer for `exactly_once_v2`.

Exactly-once processing also relies on durable Kafka infrastructure.

Relevant components include:

* `__transaction_state`;
* `__consumer_offsets`;
* source topics;
* application output topics;
* aggregate changelog topics;
* suppression changelog topics;
* repartition topics;
* transaction coordinators;
* group coordinators;
* replication;
* in-sync replicas;
* and transaction timeouts.

Kafka’s documentation strongly recommends replication factor 3 with `min.insync.replicas=2` for topics involved in exactly-once processing, including transaction state, consumer offsets, Kafka Streams internal topics, and application topics. Current documentation warns that using replication below 3 effectively undermines the intended exactly-once durability assumptions.

Turning on EOS while leaving critical topics weakly replicated is not a robust production architecture.

---

# Performance Is Part of the Design

Exactly-once processing is not free.

Potential costs include:

* transactional coordination;
* commit and abort markers;
* state changelog traffic;
* additional broker writes;
* visibility delays for `read_committed` consumers;
* transaction-commit latency;
* local state and restore costs;
* and operational complexity.

Commit frequency also matters.

A shorter commit interval can reduce the amount of work repeated after an aborted transaction, but it may increase transaction overhead and reduce batching efficiency.

A longer interval may improve batching, but it increases the amount of in-flight work that may need to be replayed after a failure and can increase the latency before results become transactionally visible.

The correct question is not:

> Is exactly once free?

It is:

> Are the cost and complexity of exactly-once processing justified by the consequences of duplicate, missing, or inconsistent committed results?

For correctness-sensitive applications—usage metering, entitlements, inventory changes, billing calculations, regulatory processing, durable workflow transitions—the answer may be yes.

For disposable telemetry, approximate analytics, noncritical caches, or naturally idempotent workloads, at-least-once processing may be sufficient.

The guarantee should be selected deliberately rather than reflexively.

---

# How to Verify the Architecture

A system is not verifiably correct merely because:

* no exception appeared in the logs;
* the consumer lag returned to zero;
* the output topic contains plausible records;
* or a happy-path integration test passed.

The design should be tested against its failure model.

## Fault injection

A serious test suite should intentionally terminate or interrupt processing:

* after input consumption;
* after aggregate mutation;
* after producing changelog records;
* as a suppressed result is released;
* after producing an output;
* before transaction commit;
* immediately after transaction commit;
* after external database commit;
* and before the downstream Kafka offset is committed.

The tests should verify externally visible invariants rather than merely expecting a particular sequence of method calls.

## Useful invariants

For the usage-metering application:

> Every finalized usage record has one stable logical identity.

> A matching retry cannot create a second database row.

> Two different values cannot silently occupy the same logical usage identity.

> Every committed finalized usage record can be derived from committed input events under a known aggregation version.

> No input offset is treated as completed without the corresponding committed state transition.

> Replaying the same inputs with the same logic and historically equivalent reference data produces the same logical outputs.

> Every committed finalized output is either materialized downstream, explicitly rejected, or awaiting retry.

## Reconciliation

Reconciliation should compare:

```text
raw source events
        │
        ▼
validated and accepted events
        │
        ▼
windowed aggregates
        │
        ▼
finalized Kafka outputs
        │
        ▼
database materializations
        │
        ▼
rated or billed usage
```

Counts alone may not be sufficient.

Useful reconciliation dimensions might include:

* tenant;
* model;
* time window;
* request count;
* input-token total;
* output-token total;
* event version;
* aggregation version;
* correction count;
* rejected-event count.

Reconciliation is how the architecture detects problems that the transactional mechanism cannot prevent, including incorrect source data, business duplicates, changed logic, rejected records, and downstream inconsistencies.

---

# A Proof-of-Work Application

The sample application accompanying this article can make these concepts observable.

It should include:

* a Spring Boot Kafka Streams application;
* a model-usage input topic;
* a five-minute windowed aggregation;
* materialized local state;
* `suppress(untilWindowCloses(...))`;
* `processing.guarantee=exactly_once_v2`;
* a finalized usage output topic;
* deterministic finalized usage IDs;
* a downstream idempotent database writer;
* a uniqueness constraint;
* matching-retry handling;
* conflicting-retry quarantine;
* source-level duplicate examples;
* correction-event examples;
* fault injection;
* state restoration;
* replay tests;
* and reconciliation queries.

The application should make failure visible rather than hiding it.

For example, one test could deliberately terminate the Streams process immediately after output production but before transaction commit. A `read_committed` observer should verify that the aborted result never becomes visible.

Another test could commit the database write and terminate the writer before its Kafka offset commit. After restart, the same finalized record should be redelivered and resolved as a matching no-op.

A third test could publish two separately committed source events with the same `requestId`. The result should demonstrate that `exactly_once_v2` does not provide business-level deduplication by itself.

These tests turn an abstract guarantee into observable proof.

---

# Conclusion

Kafka Streams’ `exactly_once_v2` guarantee is not magic, and it is not unlimited.

Its strength comes from a precise transactional boundary.

Within Kafka, Kafka Streams can atomically coordinate:

* consumed input offsets;
* state-store changelog updates;
* suppression-state changes;
* and records written to Kafka output topics.

If the transaction commits, those effects become committed together.

If it aborts, the attempted work does not become a successful committed result, and the input can be processed again.

Beyond Kafka, additional mechanisms are required:

* deterministic business identities;
* idempotent external writers;
* uniqueness enforcement;
* explicit correction semantics;
* replay determinism;
* fault injection;
* and reconciliation.

The most reliable event systems are not those that merely enable a configuration named “exactly once.”

They are those whose transactional boundaries are understood, whose failure modes are deliberately tested, and whose outputs can be independently verified.

> **Architect’s principle**
>
> Exactly once is not a property of an entire distributed system.
>
> It is a guarantee within a defined boundary.
>
> Verifiable correctness comes from connecting those boundaries deliberately.
