# -*- coding: utf-8 -*-
"""
Mini-server HTTP in pura libreria standard (niente FastAPI da installare).
Espone la pipeline al frontend per una demo "live".

Avvio:
    python server.py          # ascolta su http://localhost:8000

Endpoint (tutti JSON, CORS aperto per lo sviluppo locale):
    GET  /health
    POST /api/queries  {topic, method, field}            -> {queries:[...]}
    POST /api/seed     {queries:[...], sort}              -> {papers:[...]}
    POST /api/graph    {positiveIds:[...], negativeIds:[...]} -> {nodes, edges, profileVector, stats}
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from query_builder import build_queries
from pipeline import get_seed_papers, build_graph_and_profile

PORT = 8000


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.rstrip("/") == "/health":
            self._send(200, {"status": "ok"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.rstrip("/")
        data = self._read_json()
        try:
            if path == "/api/queries":
                q = build_queries(data.get("topic"), data.get("method"), data.get("field"))
                self._send(200, {"queries": q})
            elif path == "/api/seed":
                papers = get_seed_papers(data.get("queries") or [],
                                         sort_choice=data.get("sort", "citations"),
                                         per_query=int(data.get("perQuery", 2)))
                self._send(200, {"papers": papers})
            elif path == "/api/graph":
                g = build_graph_and_profile(data.get("positiveIds") or [],
                                            data.get("negativeIds") or [],
                                            rec_limit=int(data.get("recLimit", 40)))
                self._send(200, g)
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:
            self._send(500, {"error": str(e)})

    def log_message(self, fmt, *args):
        print("[server]", self.address_string(), fmt % args)


if __name__ == "__main__":
    print("NEXUS backend in ascolto su http://localhost:%d" % PORT)
    print("Prova:  curl http://localhost:%d/health" % PORT)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
