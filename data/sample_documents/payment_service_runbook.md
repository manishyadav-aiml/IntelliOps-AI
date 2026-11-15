# Payment Service Runbook

> DEMONSTRATION DOCUMENT for IntelliOps AI. Fictional service and procedures.

## Service overview
The payment service authorises card payments through an external payment gateway and stores results in the primary database. It depends on the database and on gateway network connectivity.

## Common failure: "Payment failed: gateway timeout"
Likely areas to investigate:
- Gateway reachability and latency from the payment hosts.
- Database availability: payment writes fail when the database refuses or times out connections ("database unavailable" in the error text).
- Circuit breaker state: repeated failures open the breaker and produce "Service unavailable: circuit breaker open".

## Severity guidance
Treat repeated payment failures combined with CRITICAL log events as P1. A short burst of failures that recovers on its own is usually P2 or P3.

## Investigation checklist
1. Count failures per minute and note the first failure time.
2. Check whether database errors started before the payment errors.
3. Check gateway status page and network errors in the same window.
4. Review recent deployments of the payment service.

## Never do automatically
Do not replay failed payments, restart services, or change gateway credentials without human approval and a recorded incident note.
