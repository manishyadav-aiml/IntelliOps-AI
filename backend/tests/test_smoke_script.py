"""Checks the mechanics of scripts/smoke_test.py (multipart upload, JSON handling, step logic) against a tiny stub
server that mimics the documented API. This validates the SCRIPT, not the real backend."""

import importlib.util
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "smoke_test.py"


class Stub(BaseHTTPRequestHandler):
    users: dict[str, str] = {}
    tokens: dict[str, str] = {}
    analyzed = False
    resolved = False

    def log_message(self, *args) -> None:  # silence
        pass

    def _send(self, status: int, body=None, raw: bytes | None = None) -> None:
        payload = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
        self.send_response(status)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _who(self) -> str | None:
        return self.tokens.get(self.headers.get("Authorization", "").replace("Bearer ", ""))

    def _handle(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        path = self.path.removeprefix("/api/v1")
        is_json = "json" in (self.headers.get("Content-Type") or "")
        body = json.loads(raw) if raw and is_json else {}
        me = self._who()
        if path == "/health":
            return self._send(200, {"status": "ok", "database": "ok"})
        if path == "/auth/register":
            self.users[body["email"]] = body["password"]
            return self._send(201, {"id": len(self.users)})
        if path == "/auth/login":
            if self.users.get(body["email"]) != body["password"]:
                return self._send(401, {"error": {"code": "authentication_failed"}})
            token = f"tok-{body['email']}"
            self.tokens[token] = body["email"]
            return self._send(200, {"access_token": token})
        if me is None:
            return self._send(401, {"error": {"code": "authentication_failed"}})
        owner = not me.startswith("smoke2-")
        if path == "/auth/me":
            return self._send(200, {"email": me})
        if path == "/auth/logout":
            return self._send(204)
        if path == "/logs/upload":
            name = re.search(rb'filename="([^"]+)"', raw).group(1)
            return self._send(422, {"error": {"code": "invalid_file"}}) if name.endswith(b".exe") else self._send(202, {"id": 1})
        if path == "/logs/1":
            return self._send(200, {"status": "COMPLETED", "entry_count": 630, "parser_used": "regex", "error_message": None})
        if path == "/logs/1/analyze":
            created = 0 if Stub.analyzed else 1
            Stub.analyzed = True
            return self._send(200, {"incidents_created": created, "method": "baseline", "anomalous_windows": 1})
        if path == "/incidents" and method == "GET":
            return self._send(200, {"items": [{"id": 1}] if owner else [], "total": 1 if owner else 0})
        if path == "/incidents/1" and method == "GET":
            if not owner:
                return self._send(404, {"error": {"code": "not_found"}})
            return self._send(200, {"severity": "P1", "severity_reasons": ["8 CRITICAL log events"],
                                    "anomaly_summary": {"rca": {"summary": ["Errors began earliest in service 'db'."]}},
                                    "resolved_at": "x" if Stub.resolved else None})
        if path == "/incidents/1/timeline":
            return self._send(200, [{"event_type": "ANOMALY_DETECTED"}, {"event_type": "INCIDENT_CREATED"}])
        if path == "/incidents/1/notes":
            return self._send(201, {"id": 1})
        if path == "/incidents/1" and method == "PATCH":
            if Stub.resolved and body.get("status") == "MITIGATED":
                return self._send(409, {"error": {"code": "invalid_state"}})
            Stub.resolved = body.get("status") == "RESOLVED" or Stub.resolved
            return self._send(200, {"resolved_at": "x" if Stub.resolved else None})
        if path == "/incidents/1/investigate":
            return self._send(503, {"error": {"code": "llm_not_configured"}})
        if path == "/documents/upload":
            return self._send(202, {"id": 7})
        if path == "/documents/7":
            return self._send(200, {"status": "COMPLETED", "chunk_count": 8, "embedder_name": "hashing-lexical", "error_message": None})
        if path == "/rag/query":
            q = body["question"]
            if not owner or "bake" in q or "gateway" in q and not owner:
                return self._send(200, {"sufficient": False, "llm_used": False, "citations": []})
            return self._send(200, {"sufficient": True, "llm_used": False, "citations": [{"document_name": "payment_service_runbook.md"}]})
        if path == "/reports/generate":
            return self._send(201, {"id": {"pdf": 1, "csv": 2, "json": 3}[body["format"]]})
        if path.startswith("/reports/") and path.endswith("/download"):
            return self._send(200, raw={"1": b"%PDF-1.4 ...", "2": b"\xef\xbb\xbfsection,source", "3": b'{"incident": {}}'}[path.split("/")[2]])
        if path == "/dashboard/summary":
            return self._send(200, {"total_logs_processed": 630, "active_incidents": 0, "resolved_incidents": 1, "anomalies_detected": 1})
        return self._send(404, {"error": {"code": "not_found"}})

    do_GET = lambda self: self._handle("GET")  # noqa: E731
    do_POST = lambda self: self._handle("POST")  # noqa: E731
    do_PATCH = lambda self: self._handle("PATCH")  # noqa: E731


def run_script(url: str, monkey_argv: list[str]) -> tuple[int, list]:
    spec = importlib.util.spec_from_file_location("smoke_test_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    old = sys.argv
    sys.argv = ["smoke_test.py", url, *monkey_argv]
    try:
        return module.main(), module.results
    finally:
        sys.argv = old


def test_smoke_script_passes_every_step_against_a_conforming_server() -> None:
    server = HTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        code, results = run_script(f"http://127.0.0.1:{server.server_address[1]}", [])
    finally:
        server.shutdown()
    failed = [(n, d) for n, ok, d in results if not ok]
    assert code == 0 and not failed, failed
    assert len(results) >= 29


def test_smoke_script_reports_unreachable_servers_with_exit_code_1() -> None:
    code, results = run_script("http://127.0.0.1:9", [])
    assert code == 1 and results == []
