# API Timeout Guide

> DEMONSTRATION DOCUMENT for IntelliOps AI. Generic example content.

## What a timeout usually means
An API timeout means a caller stopped waiting for a response. The slow component is often a dependency of the service that returned the error, not the service itself.

## Triage steps
1. Identify which endpoint and which upstream dependency show the highest latency (look for "Upstream latency" and "slow" log lines).
2. Compare latency before and after the first error; a sudden jump points to a change or a failing dependency, a slow climb points to saturation.
3. Check retry behaviour. Aggressive retries can multiply load on a struggling dependency (retry storm).
4. Verify circuit breaker state. An open circuit breaker means the dependency has been failing repeatedly.

## Timeout settings
Client timeouts should be shorter than the timeout of the caller above them, so errors surface quickly and consistently. Document the timeout chain for each critical request path.

## Safe mitigation ideas (for a human to evaluate)
Reduce retry counts, enable backoff with jitter, shed non-critical traffic, or temporarily route around the failing dependency if a fallback exists.
