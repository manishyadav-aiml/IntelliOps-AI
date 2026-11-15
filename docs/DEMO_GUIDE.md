# Demo guide (about 10 minutes)

All sample data is synthetic (`data/sample_logs`, `data/sample_documents`). Use a throwaway account; never put real credentials or production logs in a public demo.

1. Start the stack (`docker compose up --build`, or the README's local setup) and open http://localhost:5173.
2. **Register** a disposable account (it signs you in).
3. **Overview**: everything reads 0 / "No data yet" (nothing is pre-filled).
4. **Logs**: upload `data/sample_logs/incident_payment_failure.log`; watch PENDING -> COMPLETED; open it: ~630 entries, 10 templates, e.g. `Payment <*> failed: database unavailable host=pay-<*>` (digits inside host names are masked too).
5. **Anomalies**: choose the file, 1 minute, *Run anomaly detection*. Expect the baseline to flag the minute with the database-timeout/payment burst and to create **one** incident. `normal_activity.log` produces none.
6. **Incidents** -> open the new incident: severity P1/P2 with reasons, the *Root-cause evidence* panel (which service failed first, new error patterns, templates that stopped), timeline (abnormal activity, first error, anomaly detected, incident created), linked error logs.
7. **Documents**: upload `data/sample_documents/payment_service_runbook.md`; wait for COMPLETED. **Assistant**: ask "what should I check when payments time out?"; open the Sources panel (document, chunk). Without an API key you get excerpts and a notice; with `GEMINI_API_KEY` you get a cited answer.
8. Back on the incident: **Investigate** (needs the key; otherwise you see the clear "not configured" message, which is the intended behaviour). Add a human note.
9. **Reports**: generate the PDF; note the separate "AI-generated suggestions" and "Human-confirmed findings" sections.
10. Mark the incident **INVESTIGATING -> RESOLVED**; the Overview now shows a resolved incident and a time-to-resolve.

Optional: `make train-demo` trains a demo model on the synthetic samples (for demonstration only), then re-run step 5 and compare the method shown.
