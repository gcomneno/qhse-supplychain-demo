# Architecture Deep Dive

This document describes the internal architecture, transaction model, and background processing lifecycle of the QHSE Supply Chain backend.

The focus is on reliability and consistency rather than scalability.

---

# 1. Layered Architecture

The system follows a strict layered structure:

```

API Layer (FastAPI)
↓
Service Layer (Business Logic)
↓
Persistence Layer (SQLAlchemy 2.0)
↓
Database (PostgreSQL / idem for tests)

```

Separately:

```

Worker (Polling Consumer)
↓
Persistence Layer
↓
Database

```

## Dependency Direction

- API depends on Services
- Services depend on Persistence
- Worker depends on Persistence
- No upward dependency is allowed

There is no direct cross-layer coupling.

---

# 2. Transaction Boundary

The transaction boundary is explicitly controlled inside the service layer.

## Example Flow: Creating a Non-Conformity

1. API endpoint validates request.
2. Service function is invoked.
3. Within a single DB session:
   - Insert NonConformity
   - Insert OutboxEvent
4. Commit transaction.
5. Return response.

### Important Property

The domain write and the outbox write occur in the **same database transaction**.

If anything fails before commit:

- Neither the NC nor the OutboxEvent is persisted.
- The system remains consistent.

This guarantees atomicity of:

```

Business State Change + Event Emission

```

---

# 3. Transactional Outbox Pattern

## Why Not Execute Side Effects Directly?

Direct side effects inside the request transaction cause:

- Partial failure risks
- Unclear retry behavior
- Distributed transaction complexity

Instead, this system uses a transactional outbox table:

```

outbox_events

```

### Outbox Event Lifecycle

State machine:

```

PENDING → PROCESSED
→ FAILED

```

- PENDING: written during business transaction
- PROCESSED: successfully handled by worker
- FAILED: permanently failed after retry logic (simplified in demo)

The API never executes side effects directly.

---

# 4. Worker Lifecycle

The worker is a polling consumer.

## Worker Loop

```

while True:
fetch PENDING events (limit N)
for each event:
process event
mark as PROCESSED
sleep(interval)

```

### Design Characteristics

- Pull-based, not push-based
- No external broker
- DB is the coordination mechanism
- Simple and deterministic

---

# 5. Idempotency Model

Idempotency is guaranteed via:

```

processed_events table

```

Before processing an event:

- Worker checks whether it was already processed.
- If yes, it skips safely.

This protects against:

- Worker crashes
- Container restarts
- Duplicate polling
- At-least-once semantics

The system behaves as:

> At-least-once delivery with idempotent consumer.

---

# 6. Failure Modes

## Case 1: API Crash Before Commit

- Nothing persisted.
- No inconsistency.

## Case 2: API Commit Succeeds, Worker Crashes

- Event remains PENDING.
- Will be retried.
- No data loss.

## Case 3: Worker Processes but Crashes Before Marking PROCESSED

- Event retried.
- Idempotency check prevents duplicate side effects.

## Case 4: Worker Permanent Failure

- Event can move to FAILED state.
- System remains consistent.
- Manual inspection possible.

---

# 7. Isolation Between Test and Runtime

Tests use:

- Postgresql
- Fresh DB per test session
- Deterministic transaction boundaries

Runtime uses:

- PostgreSQL (Docker)
- Real DDL
- Real type enforcement

The architecture works identically in both contexts.

---

# 8. Why Sync SQLAlchemy?

Reasons:

- Simpler transaction reasoning
- No implicit concurrency hazards
- Easier deterministic tests
- Clear session lifecycle

Async DB would add complexity without architectural benefit for this scope.

---

# 9. Security Architecture

Security enforcement occurs at the API boundary:

```

Endpoint → require_role() dependency → JWT validation → role check

```

The service layer assumes valid authorization.

This prevents business logic from being polluted with auth checks.

---

# 10. Architectural Constraints

The system intentionally avoids:

- Direct side effects inside API logic
- Shared mutable state across layers
- Implicit session commits
- Hidden transaction scopes
- Cross-layer imports

The design goal is explicitness.

---

# 11. Production Extensions (Not Implemented)

For a production system, the following would likely change:

- Replace polling worker with queue-based consumer
- Structured logging
- Observability (metrics + tracing)
- Retry backoff strategy
- Dead-letter queue
- External identity provider
- Database migration CI enforcement
- Read replicas for KPI endpoints

---

# 12. Summary

This backend is intentionally small but architecturally coherent.

It demonstrates:

- Clear transaction boundaries
- Transactional outbox reliability
- Idempotent background processing
- Role-based access control
- Layered dependency model

The focus is correctness, not feature density.

---

## 13. DEMO Architecture (high level)

- FastAPI (sync)
- Postgres
- Outbox pattern
- Worker (polling, 1-event-1-transaction)
- Prometheus metrics (RED + Outbox health)
- Jaeger tracing

Semantics:
- At-least-once event processing
- No exactly-once guarantees (demo scope)

---

## 14. Known limitations
- No idempotency guarantees (demo scope)
- Single worker
- No horizontal scaling
- No real message broker
