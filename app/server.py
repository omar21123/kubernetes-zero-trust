"""Three deliberately small HTTP tiers, without external Python dependencies."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener

OPENER = build_opener(ProxyHandler({}))


def fetch(url):
    with OPENER.open(url, timeout=3) as response:
        return json.load(response)


def make_handler(tier, upstream):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            status, body = 200, {"tier": tier, "status": "ok"}
            try:
                if self.path == "/health":
                    pass
                elif tier == "frontend" and self.path == "/":
                    body = {"tier": tier, "catalog": fetch(upstream + "/catalog")}
                elif tier == "api" and self.path == "/catalog":
                    body = {"tier": tier, "items": fetch(upstream + "/items")["items"]}
                elif tier == "api" and self.path == "/admin":
                    body = {"demo": "L7 target; no real administrative action"}
                elif tier == "catalog" and self.path == "/items":
                    body = {"items": [{"id": 1, "name": "Livre DevSecOps"}]}
                else:
                    status, body = 404, {"error": "not found"}
            except (URLError, HTTPError, TimeoutError, OSError, ValueError, KeyError):
                status, body = 502, {"error": "upstream unavailable"}
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return Handler


if __name__ == "__main__":
    server = ThreadingHTTPServer(
        ("0.0.0.0", int(os.getenv("PORT", "8080"))),
        make_handler(os.environ["TIER"], os.getenv("UPSTREAM", "")),
    )
    server.serve_forever()
