# Reliability Guarantees

This demo intentionally prioritizes **correctness and traceability**
over horizontal scalability.

## Delivery Semantics

-   **At-least-once processing**
-   Idempotent event handling via `processed_events`
-   Explicit retry policy with bounded attempts
-   Failed events are visible and measurable via KPI

## Transactional Consistency

-   Domain data and Outbox events share the same database transaction.
-   Either both are committed or both are rolled back.
-   No "ghost events" and no "invisible state changes".

## Idempotency Strategy

-   Each event carries a stable `event_id` (UUID).
-   `processed_events` enforces uniqueness on `event_id`.
-   Reprocessing the same event does not duplicate side effects.

## Auditability

-   Every handled event produces an append-only audit record.
-   No destructive updates in `audit_log`.
-   Operational decisions are verifiable post‑factum.

## Failure Policy

-   Unknown or failing events increment `attempts`.
-   Events transition to `FAILED` after a bounded number of retries.
-   Failed events are observable via `/kpi`.

These guarantees are verified by automated tests in the repository.
