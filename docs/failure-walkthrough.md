# Failure Walkthrough

This document describes how the system behaves under failure conditions.

The goal is to demonstrate deterministic failure handling and consistency guarantees.

---

# 1. Failure During API Request (Before Commit)

## Scenario

A client calls:

```

POST /ncs

```

An exception occurs before the transaction commits.

## What Happens

1. A DB session is opened.
2. Service attempts:
   - INSERT into `nonconformities`
   - INSERT into `outbox_events`
3. An exception is raised before commit.
4. Session context manager triggers ROLLBACK.

## Result

- No NonConformity row persisted.
- No OutboxEvent row persisted.
- Client receives error response.
- Database remains consistent.

### Guarantee

Atomicity of domain write + event emission.

---

# 2. Failure After Commit, Before Worker Runs

## Scenario

The API successfully commits:

- NonConformity row inserted
- OutboxEvent inserted (status=PENDING)

Then the worker is not running.

## What Happens

- The OutboxEvent remains in PENDING state.
- Domain data is visible.
- No side effects are executed yet.

## Result

System remains consistent.

When the worker starts later:

- It polls the pending event.
- It processes it normally.

### Guarantee

No event loss.
At-least-once processing model.

---

# 3. Worker Crash Before Marking Event Processed

## Scenario

Worker fetches a PENDING event.
It performs side effect (e.g., writes to audit_log).
Then crashes before:

- inserting into `processed_events`
- updating `outbox_events` to PROCESSED

## What Happens

Event remains PENDING.

On restart:

- Worker fetches the same event again.
- It checks `processed_events`.
- If the side effect was already recorded, duplicate execution is prevented.

## Result

Idempotent behavior.
No duplicate logical side effects.

### Guarantee

Crash safety via idempotent consumer design.

---

# 4. Worker Crash After Marking Processed

## Scenario

Worker:

- Writes audit_log
- Inserts processed_events
- Updates outbox_events to PROCESSED
- Crashes after commit

## What Happens

- Event remains PROCESSED.
- No duplicate processing.
- System stable.

### Guarantee

Stable post-commit state.

---

# 5. Database Connection Failure (API)

## Scenario

Database is unavailable when API request arrives.

## What Happens

- Session cannot open.
- SQLAlchemy raises exception.
- FastAPI returns 500 (or handled error).

## Result

- No partial writes.
- No inconsistent state.
- Request fails fast.

---

# 6. Database Connection Failure (Worker)

## Scenario

Worker cannot connect to DB.

## What Happens

- Poll attempt fails.
- Worker crashes or retries (depending on container restart policy).
- No state mutation occurs.

## Result

- System safe.
- Events remain in PENDING.
- Worker resumes when DB is available.

---

# 7. Partial Domain Failure

## Scenario

Closing a Non-Conformity:
- NonConformity exists
- But constraint violation occurs during update

## What Happens

- Exception raised
- Session rolled back
- No outbox event written

## Result

Domain state remains unchanged.
No ghost event emitted.

---

# 8. Idempotency Guarantee

The system behaves as:

> At-least-once delivery with idempotent consumer.

It does NOT guarantee:

- Exactly-once distributed processing
- Real-time event propagation

But it guarantees:

- No inconsistent domain state
- No lost events
- No duplicate side effects

---

# 9. Consistency Model Summary

The system guarantees:

- Strong consistency inside a single transaction
- Eventual consistency between API and side effects
- Crash safety at both API and worker layers

It intentionally does NOT guarantee:

- Immediate side effect execution
- Distributed transaction semantics
- High-throughput event streaming

---

# 10. Why This Matters

Many CRUD demos ignore failure modes.

This project explicitly documents:

- Where transactions begin and end
- What happens on rollback
- What happens on crash
- How idempotency is achieved

The design is small but failure-aware.

That is the architectural focus.
