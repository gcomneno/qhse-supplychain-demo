# Observability Dashboard (Prometheus UI)

Apri Prometheus: http://localhost:9090

## API — RED
RPS (totale)
    sum(rate(http_requests_total[5m]))

RPS per route (top-ish)
    sum by (route, method) (rate(http_requests_total[5m]))

Error ratio 5xx
    sum(rate(http_requests_total{status=~"5.."}[5m]))

/
    sum(rate(http_requests_total[5m]))

5xx rate
    sum(rate(http_requests_total{status=~"5.."}[5m]))

Latency p50/p95/p99
    histogram_quantile(0.50, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
    histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
    histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))

In-flight requests
    sum(http_in_flight_requests)

## Worker — RED

Poll iterations (ok/empty/error)
    sum by (result) (increase(worker_poll_iterations_total[5m]))

Poll duration p95
    histogram_quantile(0.95, sum by (le) (rate(worker_poll_duration_seconds_bucket[5m])))

Jobs processed success/fail (rate)
    sum by (status) (rate(worker_jobs_processed_total[5m]))

Failure ratio
    sum(rate(worker_jobs_processed_total{status="failed"}[5m]))

/
    sum(rate(worker_jobs_processed_total[5m]))

Job duration p95 (overall)
    histogram_quantile(0.95, sum by (le) (rate(worker_job_duration_seconds_bucket[5m])))

Job duration p95 by event_type
    histogram_quantile(0.95, sum by (le, event_type) (rate(worker_job_duration_seconds_bucket[5m])))


## Outbox — Health

Backlog (PENDING + PROCESSING)
    outbox_unprocessed_total

Oldest unprocessed age (seconds)
    outbox_oldest_unprocessed_age_seconds

Oldest age in minutes (nicer)
    outbox_oldest_unprocessed_age_seconds / 60


## Alerts
Alert rules are defined in:
    observability/prometheus/rules.yml

To view active alerts:
    Prometheus UI → Alerts

### Quick sanity checks
- Worker stopped → outbox_unprocessed_total and outbox_oldest_unprocessed_age_seconds should grow.
- Worker running → backlog should decrease and oldest age should trend to 0.
- Error endpoint hit → http_requests_total{status=~"5.."} should spike; error ratio should increase.
