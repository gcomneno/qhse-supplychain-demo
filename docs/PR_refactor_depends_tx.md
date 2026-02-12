# PR: Refactor DB Session to FastAPI Dependency + Reliability Hardening

## Summary

This PR refactors database session handling from a contextmanager
pattern to a FastAPI dependency (`get_db`), improving:

-   Testability
-   Transaction clarity
-   Architectural consistency

## Key Changes

-   Introduced `get_db()` generator dependency
-   Updated routers to use `Depends(get_db)`
-   Unified transaction lifecycle management
-   Added automated tests covering:
    -   Transactional Outbox behavior
    -   Worker idempotency
    -   Failure & retry policy

## Reliability Impact

-   Verified at-least-once semantics
-   Deduplication guaranteed via UUID event_id
-   Explicit failure handling with bounded retries
-   Improved observability via KPI endpoint

## No Breaking Changes

-   Domain model unchanged
-   Outbox pattern preserved
-   Worker remains broker-agnostic

## Future Evolution

-   Optional broker integration (Kafka/RabbitMQ)
-   Backoff strategy with next_retry_at
-   Observability metrics (Prometheus)
-   Hash-chained audit integrity

This PR strengthens architectural guarantees without increasing system
complexity.
