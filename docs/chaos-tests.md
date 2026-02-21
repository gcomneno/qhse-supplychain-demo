# Chaos tests (observability)

These recipes are meant to be **repeatable** and **didactic**: each one has a clear trigger, expected Prometheus signals, and a “done” checklist.

Prereqs:
- `docker compose up -d --build`
- Prometheus UI: `http://localhost:9090`
- Targets: `Status → Targets` shows `api` and `worker` **UP**

---

## Test 1 — Stop worker → outbox lag/backlog grows

### Goal
Validate outbox health metrics and “worker no progress” behavior.

### Steps
1. Stop the worker:
   ```bash
   docker compose stop worker
   ```

2. Generate a few outbox events (use your normal API endpoint that creates outbox rows).
   - If you don’t have a convenient endpoint, any action that inserts outbox events is fine.

3. Watch metrics in Prometheus (**Graph** tab):

   **Backlog**
   ```promql
   outbox_unprocessed_total
   ```

   **Oldest age**
   ```promql
   outbox_oldest_unprocessed_age_seconds
   ```

   **Worker progress (should flatline)**
   ```promql
   sum(increase(worker_jobs_processed_total[5m]))
   ```

4. Start the worker again:
   ```bash
   docker compose start worker
   ```

### Expected results
- `outbox_unprocessed_total` **increases** while the worker is stopped.
- `outbox_oldest_unprocessed_age_seconds` **increases steadily** while stopped.
- Once worker restarts: backlog **decreases** and oldest age trends toward **0**.

### Done checklist
- [ ] backlog grows with worker stopped
- [ ] oldest age grows with worker stopped
- [ ] backlog drains after worker restart
- [ ] oldest age returns near 0 after drain

---

## Test 2 — Worker failures → failed counter increases

### Goal
Validate `worker_jobs_processed_total{status="failed"}` and that failures don’t break scrape/loop.

### Method
Temporarily inject a failure in `process_one_event(...)` (or at the start of your event processing) and rebuild.

### Steps
1. Inject a temporary failure:
   ```python
   raise RuntimeError("chaos test")
   ```

2. Rebuild only the worker:
   ```bash
   docker compose up -d --build worker
   ```

3. Generate events so the worker processes them.

4. Watch metrics:

   **Failed jobs**
   ```promql
   sum(increase(worker_jobs_processed_total{status="failed"}[5m]))
   ```

   **Success vs failed**
   ```promql
   sum by (status) (increase(worker_jobs_processed_total[5m]))
   ```

   **Job duration p95 (optional)**
   ```promql
   histogram_quantile(0.95, sum by (le) (rate(worker_job_duration_seconds_bucket[5m])))
   ```

5. Remove the injected failure and rebuild again:
   ```bash
   docker compose up -d --build worker
   ```

### Expected results
- `worker_jobs_processed_total{status="failed"}` **increases** while the failure is injected.
- After reverting, `status="success"` starts increasing again.

### Done checklist
- [ ] failures increase the failed counter
- [ ] worker continues exposing `/metrics` during failures
- [ ] after revert, success counter increases again

---

## Test 3 — API 5xx burst → error ratio spikes

### Goal
Validate API error metrics and alert thresholds.

### Method A (recommended)
Add a temporary endpoint that always errors (remove afterwards).

Example:
```python
@app.get("/boom")
def boom():
    raise RuntimeError("chaos")
```

### Steps
1. Generate a burst of requests:
   ```bash
   for i in {1..50}; do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/boom; done
   ```

2. Watch metrics:

   **5xx rate**
   ```promql
   sum(rate(http_requests_total{status=~"5.."}[1m]))
   ```

   **Error ratio**
   ```promql
   sum(rate(http_requests_total{status=~"5.."}[5m]))
   /
   sum(rate(http_requests_total[5m]))
   ```

3. Remove the endpoint (or stop calling it).

### Expected results
- `http_requests_total{status=~"5.."}` and its rate **spike** during the burst.
- Error ratio rises above baseline and then returns toward baseline.

### Done checklist
- [ ] 5xx rate spikes during burst
- [ ] error ratio increases during burst
- [ ] values return toward baseline after stop

---

## Optional — Latency inflation (p95 rises)

### Goal
Validate histogram-based latency quantiles.

### Method
Introduce a temporary delay on a chosen endpoint or in worker processing:
```python
import time
time.sleep(1.0)
```

### Queries
**API p95**
```promql
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
```

**Worker job p95**
```promql
histogram_quantile(0.95, sum by (le) (rate(worker_job_duration_seconds_bucket[5m])))
```

### Expected results
- p95 increases while the delay is active, then decreases after removal.

---

## Notes / gotchas
- If a metric looks “stuck”, make sure you have enough traffic and a time window that matches your scrape interval (e.g., `[5m]` is usually safe).
- Keep labels low-cardinality: avoid anything per-request/per-id (e.g., `request_id`, `traceparent`, `outbox_id`).
