# Database Troubleshooting Guide

> DEMONSTRATION DOCUMENT for IntelliOps AI. Generic example content, not a real company runbook.

## Connection timeouts
Symptoms: log lines such as "Connection timeout after 30000 ms", slow API responses, and payment or order failures that mention the database.

Checks, in order:
1. Confirm the database host is reachable from the application host (network path, security group, DNS).
2. Inspect the connection pool: active connections close to the pool maximum means requests are queueing. Compare against `max_connections` on the server.
3. Look for long-running queries or locks that hold connections open.
4. Check recent deployments or configuration changes to pool size and timeouts.

## Connection pool exhaustion
A pool at 90 percent or more for several minutes is an early warning. Typical contributing factors: slow queries, connection leaks in application code, a traffic spike, or a pool that is too small for the number of application instances.

## Slow queries
Review the slow query log, look for missing indexes and full table scans, and check whether the slowdown started at the same time as an error burst.

## Escalation
Page the database on-call engineer when connection errors persist for more than 10 minutes or when replication lag keeps growing. Record findings in the incident notes before changing anything.
