# Project overview

IntelliOps AI helps an engineer move from raw log files to an investigated, documented incident:

1. **Upload** `.log`, `.txt` or `.csv` files (validated, stored safely, parsed in the background).
2. **Parse** each line into timestamp, level, service, host and message, and mine a *template* per message
   (`User <*> connected to server <*>`) with Drain3 or a regex fallback. The original line is always kept.
3. **Detect** unusual time windows with a transparent baseline (always available) or a trained Isolation Forest.
4. **Group** anomalous windows into one incident per episode, with a rule-based P1-P4 severity and written reasons.
5. **Investigate**: timeline, similar past incidents, an optional evidence-grounded AI assistant, and a
   documentation assistant (RAG) that answers only from the user's own runbooks and cites its sources.
6. **Report** as PDF, CSV or JSON, with AI suggestions and human-confirmed findings kept visibly separate.

Design principles: nothing is faked (empty data shows empty states), AI output is labelled unconfirmed and validated
against real evidence, every optional AI dependency can fail without taking the application down, and every user only
ever sees their own data.

Status of each capability is tracked in [FINAL_AUDIT_REPORT.md](FINAL_AUDIT_REPORT.md).
