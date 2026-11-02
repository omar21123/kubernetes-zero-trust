import importlib.util
import json
from pathlib import Path
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener

SPEC = importlib.util.spec_from_file_location("server", Path(__file__).resolve().parents[1] / "app/server.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
OPENER = build_opener(ProxyHandler({}))


class ApplicationTest(unittest.TestCase):
    def setUp(self):
        self.servers = []

    def tearDown(self):
        for server, thread in reversed(self.servers):
            server.shutdown()
            thread.join(timeout=3)
            server.server_close()

    def start(self, tier, upstream=""):
        server = ThreadingHTTPServer(("127.0.0.1", 0), MODULE.make_handler(tier, upstream))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.servers.append((server, thread))
        return "http://127.0.0.1:" + str(server.server_address[1])

    def test_three_tier_end_to_end(self):
        catalog = self.start("catalog")
        api = self.start("api", catalog)
        frontend = self.start("frontend", api)
        with OPENER.open(frontend + "/", timeout=4) as response:
            body = json.load(response)
        self.assertEqual(body["tier"], "frontend")
        self.assertEqual(body["catalog"]["items"][0]["name"], "Livre DevSecOps")

    def test_upstream_failure_is_not_success(self):
        api = self.start("api", "http://127.0.0.1:1")
        with self.assertRaises(HTTPError) as result:
            OPENER.open(api + "/catalog", timeout=4)
        self.assertEqual(result.exception.code, 502)

    def test_health_and_unknown_route(self):
        catalog = self.start("catalog")
        with OPENER.open(catalog + "/health", timeout=4) as response:
            self.assertEqual(json.load(response)["status"], "ok")
        with self.assertRaises(HTTPError) as result:
            OPENER.open(catalog + "/missing", timeout=4)
        self.assertEqual(result.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
