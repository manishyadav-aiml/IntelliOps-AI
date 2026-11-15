"""End-to-end smoke test against a RUNNING backend. Standard library only.

    python scripts/smoke_test.py http://localhost:8000            # AI key not configured (default expectation)
    python scripts/smoke_test.py http://localhost:8000 --llm      # AI key configured: expects a real investigation

Walks the whole workflow with a throw-away account and prints one PASS/FAIL line per step. Exit code 1 if any
step fails. Uses only the synthetic files in data/. It talks to a real server, so run it against a dev/demo
instance, never against a database you care about (it creates a user, logs, an incident, a document and reports).
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
results: list[tuple[str, bool, str]] = []


class Client:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/") + "/api/v1"
        self.token: str | None = None

    def call(self, method: str, path: str, body=None, files=None, raw=False):
        headers = {}
        data = None
        if files:
            boundary = uuid.uuid4().hex
            parts = []
            for field, (name, content, mime) in files.items():
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{name}"\r\nContent-Type: {mime}\r\n\r\n'.encode() + content + b"\r\n")
            data = b"".join(parts) + f"--{boundary}--\r\n".encode()
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        elif body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
                return response.status, (payload if raw else (json.loads(payload) if payload else None))
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            try:
                return exc.code, json.loads(payload)
            except ValueError:
                return exc.code, payload.decode(errors="replace")


def step(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    return ok


def wait_for(client: Client, path: str, done=lambda d: d["status"] == "COMPLETED", seconds: int = 60):
    deadline = time.time() + seconds
    status, data = 0, None
    while time.time() < deadline:
        status, data = client.call("GET", path)
        if status == 200 and (done(data) or data["status"] == "FAILED"):
            break
        time.sleep(1)
    return status, data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("--llm", action="store_true", help="expect a configured AI provider")
    args = parser.parse_args()
    c = Client(args.base_url)
    email, password = f"smoke-{uuid.uuid4().hex[:8]}@example.com", "SmokePassw0rd"
    other_email = f"smoke2-{uuid.uuid4().hex[:8]}@example.com"

    try:
        status, body = c.call("GET", "/health")
    except urllib.error.URLError as exc:
        print(f"Cannot reach {args.base_url}: {exc.reason}\nStart the backend first (see README) and check the URL.")
        return 1
    if not step("health endpoint", status == 200 and body["database"] == "ok", str(body)):
        return 1

    status, _ = c.call("POST", "/auth/register", {"email": email, "full_name": "Smoke Test", "password": password})
    step("register", status == 201, f"HTTP {status}")
    status, body = c.call("POST", "/auth/login", {"email": email, "password": password})
    ok = status == 200 and "access_token" in body
    step("login", ok, f"HTTP {status}")
    if not ok:
        return 1
    c.token = body["access_token"]
    step("current user", c.call("GET", "/auth/me")[1].get("email") == email)
    step("unauthenticated request is rejected", Client(args.base_url).call("GET", "/incidents")[0] == 401)

    sample = (ROOT / "data/sample_logs/incident_payment_failure.log").read_bytes()
    status, up = c.call("POST", "/logs/upload", files={"file": ("incident_payment_failure.log", sample, "text/plain")})
    step("log upload accepted", status == 202, f"HTTP {status}")
    _, log = wait_for(c, f"/logs/{up['id']}")
    step("log parsed", log["status"] == "COMPLETED" and log["entry_count"] > 500, f"{log['status']}, {log['entry_count']} entries, parser={log.get('parser_used')}, {log.get('error_message') or ''}")
    step("invalid upload rejected", c.call("POST", "/logs/upload", files={"file": ("x.exe", b"MZ\x90\x00", "application/octet-stream")})[0] == 422)

    status, analysis = c.call("POST", f"/logs/{up['id']}/analyze")
    step("anomaly detection finds the synthetic incident", status == 200 and analysis["incidents_created"] >= 1, f"{analysis.get('method')}, {analysis.get('anomalous_windows')} anomalous windows")
    step("re-running analysis does not duplicate incidents", c.call("POST", f"/logs/{up['id']}/analyze")[1].get("incidents_created") == 0)

    _, listing = c.call("GET", "/incidents")
    incident_id = listing["items"][0]["id"] if listing["items"] else None
    step("one grouped incident exists", listing["total"] == 1, f"total={listing['total']}")
    if incident_id is None:
        return finish()
    _, detail = c.call("GET", f"/incidents/{incident_id}")
    rca = (detail.get("anomaly_summary") or {}).get("rca", {})
    step("severity is explained", detail["severity"] in ("P1", "P2") and bool(detail["severity_reasons"]), f"{detail['severity']}: {detail['severity_reasons']}")
    step("root-cause evidence present", bool(rca.get("summary")), (rca.get("summary") or [""])[0])
    _, events = c.call("GET", f"/incidents/{incident_id}/timeline")
    step("timeline has real events", {"ANOMALY_DETECTED", "INCIDENT_CREATED"} <= {e["event_type"] for e in events}, ", ".join(e["event_type"] for e in events))
    step("note added", c.call("POST", f"/incidents/{incident_id}/notes", {"content": "smoke test note"})[0] == 201)

    doc = (ROOT / "data/sample_documents/payment_service_runbook.md").read_bytes()
    status, d = c.call("POST", "/documents/upload", files={"file": ("payment_service_runbook.md", doc, "text/markdown")})
    _, d = wait_for(c, f"/documents/{d['id']}")
    step("document indexed", d["status"] == "COMPLETED" and d["chunk_count"] > 0, f"{d['status']}, {d['chunk_count']} chunks, embedder={d.get('embedder_name')}, {d.get('error_message') or ''}")
    _, ans = c.call("POST", "/rag/query", {"question": "what should I check when payments time out?"})
    step("RAG answer carries real citations", bool(ans["citations"]) and ans["citations"][0]["document_name"] == "payment_service_runbook.md", f"llm_used={ans['llm_used']}")
    _, off = c.call("POST", "/rag/query", {"question": "How do I bake sourdough bread?"})
    step("off-topic question is refused", off["sufficient"] is False and not off["citations"])

    status, inv = c.call("POST", f"/incidents/{incident_id}/investigate", {"question": "Why is db failing?"})
    if args.llm:
        step("AI investigation returns a labelled result", status == 200 and inv["result"]["status"].startswith("AI-generated"), f"HTTP {status}")
    else:
        step("AI investigation fails gracefully without a key", status == 503 and inv["error"]["code"] == "llm_not_configured", f"HTTP {status}")
    step("rest of the app still works after an AI failure", c.call("GET", f"/incidents/{incident_id}")[0] == 200)

    for fmt, magic in (("pdf", b"%PDF"), ("csv", b"section"), ("json", b"{")):
        status, rep = c.call("POST", "/reports/generate", {"incident_id": incident_id, "format": fmt})
        got = c.call("GET", f"/reports/{rep['id']}/download", raw=True) if status == 201 else (0, b"")
        step(f"{fmt.upper()} report downloads", status == 201 and got[0] == 200 and got[1].lstrip(b"\xef\xbb\xbf").startswith(magic), f"{len(got[1])} bytes")

    step("status moves to INVESTIGATING", c.call("PATCH", f"/incidents/{incident_id}", {"status": "INVESTIGATING"})[0] == 200)
    resolved = c.call("PATCH", f"/incidents/{incident_id}", {"status": "RESOLVED"})
    step("incident resolved with a resolved_at timestamp", resolved[0] == 200 and resolved[1].get("resolved_at") is not None)
    bad = c.call("PATCH", f"/incidents/{incident_id}", {"status": "MITIGATED"})  # RESOLVED -> MITIGATED is not allowed
    step("invalid status transition is rejected (409)", bad[0] == 409, f"HTTP {bad[0]}")
    _, summary = c.call("GET", "/dashboard/summary")
    step("dashboard reflects real data", summary["total_logs_processed"] > 500 and summary["resolved_incidents"] >= 1, str({k: summary[k] for k in ("total_logs_processed", "active_incidents", "resolved_incidents", "anomalies_detected")}))

    c2 = Client(args.base_url)
    c2.call("POST", "/auth/register", {"email": other_email, "full_name": "Other User", "password": password})
    c2.token = c2.call("POST", "/auth/login", {"email": other_email, "password": password})[1]["access_token"]
    step("another user cannot see the incident", c2.call("GET", f"/incidents/{incident_id}")[0] == 404 and c2.call("GET", "/incidents")[1]["total"] == 0)
    step("another user's document search is empty", c2.call("POST", "/rag/query", {"question": "payment gateway timeout"})[1]["citations"] == [])
    step("logout", c.call("POST", "/auth/logout")[0] == 204)
    return finish()


def finish() -> int:
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} steps passed")
    if failed:
        print("Failed: " + "; ".join(name for name, _, _ in failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
