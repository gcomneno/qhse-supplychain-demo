# Architecture Decision Records (ADR)

This document captures key architectural decisions made in the project.

Each decision includes context, the chosen solution, and its consequences.

---

# ADR-001: Use Transactional Outbox Pattern

## Context

The system performs domain writes (e.g., creating a Non-Conformity) and must trigger side effects (audit logging).

Executing side effects directly inside request handling introduces:

- Risk of partial failures
- Unclear retry semantics
- Tight coupling between business logic and external actions

## Decision

Use a transactional outbox table:

- Write domain state and an `outbox_event` in the same DB transaction.
- Process events asynchronously via a polling worker.
- Ensure idempotency at the worker level.

## Consequences

### Positive

- Atomic domain + event persistence
- Safe retries
- Crash tolerance
- Deterministic behavior
- Clear transaction boundary

### Negative

- Additional table
- Background worker complexity
- Slight processing latency

---

# ADR-002: Use Sync SQLAlchemy (Not Async)

## Context

FastAPI supports async endpoints and async DB drivers.

However:

- The system prioritizes clarity of transaction boundaries.
- Concurrency demands are minimal.
- Deterministic test behavior is preferred.

## Decision

Use SQLAlchemy 2.0 in synchronous mode.

## Consequences

### Positive

- Simpler mental model
- Clear commit/rollback lifecycle
- Easier testing
- No async session pitfalls

### Negative

- Lower theoretical throughput
- Blocking I/O under load

This is acceptable for the intended scope.

---

# ADR-003: Use PostgreSQL for Runtime and Tests

## Context

Tests should be:

- Fast
- Isolated
- Deterministic
- Independent of external services

Production-like behavior should use a real RDBMS.

## Decision

- PostgreSQL (Docker) for runtime/demo

## Consequences

### Positive

- Fast CI runs
- No external test dependency
- Realistic production demo

### Negative

- Minor SQL dialect differences must be handled carefully
- Cross-database compatibility must be explicitly considered

---

# ADR-004: Use Static Users for RBAC

## Context

The focus of this project is authorization structure, not identity management.

Implementing full user CRUD, password hashing, and persistence would add noise.

## Decision

Use static demo users:

- quality
- procurement
- auditor
- admin

Embed roles directly in login logic.

## Consequences

### Positive

- Minimal auth surface
- Clear RBAC demonstration
- Focus remains on architecture

### Negative

- Not production-ready identity system
- No user lifecycle management

---

# ADR-005: Enforce RBAC at API Layer

## Context

Authorization can be implemented in:

- Business layer
- Persistence layer
- API boundary

Embedding authorization deep inside services mixes concerns.

## Decision

Enforce RBAC via FastAPI dependencies at endpoint level.

Services assume valid authorization.

## Consequences

### Positive

- Clean separation of concerns
- Business logic remains pure
- Easy to audit role policies per route

### Negative

- Services are not self-protecting
- Requires discipline in API design

---

# ADR-006: Polling Worker Instead of Message Broker

## Context

Production systems often use:

- Kafka
- RabbitMQ
- SQS

However, adding a broker increases:

- Operational complexity
- Infrastructure overhead
- Cognitive load

## Decision

Use a simple polling worker reading from the database.

## Consequences

### Positive

- Minimal infrastructure
- Deterministic behavior
- Easier local development

### Negative

- Increased DB load
- Not horizontally scalable
- No backpressure control

---

# ADR-007: Explicit Transaction Scope via Session Context Manager

## Context

Implicit session lifecycle often leads to:

- Hidden commits
- Partial writes
- Hard-to-debug states

## Decision

Use explicit session context managers (`with get_session():`) to define transaction boundaries.

Commit occurs at exit if no exception.

## Consequences

### Positive

- Clear atomic boundaries
- Predictable rollback behavior
- Easier reasoning about state

### Negative

- Slightly more verbose code

---

# ADR-008: Keep Business Logic in Services Layer

## Context

Putting logic directly inside route handlers leads to:

- Fat controllers
- Poor testability
- Tight coupling

## Decision

Routes handle:

- Validation
- Auth
- Delegation

Services handle:

- Business logic
- State transitions
- Outbox emission

## Consequences

### Positive

- Better separation
- Easier refactoring
- Easier testing

### Negative

- Slight abstraction overhead

---

# ADR-009: Idempotent Worker Design

## Context

Polling workers can:

- Restart unexpectedly
- Re-process events
- Experience partial failures

Without idempotency, side effects may duplicate.

## Decision

Maintain a `processed_events` table.

Before handling an event, verify it was not already processed.

## Consequences

### Positive

- Safe restarts
- At-least-once semantics
- Crash resilience

### Negative

- Additional storage
- Slight overhead per event

---

# ADR-010: Favor Explicitness Over Abstraction

## Context

The project could use:

- Repository pattern
- Dependency injection containers
- CQRS frameworks

However, over-abstraction reduces clarity for demonstration purposes.

## Decision

Keep the architecture explicit and lightweight.

No unnecessary indirection layers.

## Consequences

### Positive

- Easier to understand
- Cleaner demo
- Direct mapping between code and architecture

### Negative

- Less extensible in large-scale systems
- Some duplication possible

---

# Final Note

This project intentionally optimizes for:

- Architectural clarity
- Transactional correctness
- Reliability patterns
- Explicit design decisions

It is not optimized for:

- Horizontal scalability
- Feature completeness
- Enterprise integration

The goal is demonstrable architectural maturity.
