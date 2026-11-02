"""Ensure a broken DNS or HTTP application cannot be reported as policy isolation."""
import importlib.util
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch, Mock
from urllib.error import HTTPError, URLError

SPEC = importlib.util.spec_from_file_location("check", Path(__file__).resolve().parents[1] / "app/check.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class ProbeTest(unittest.TestCase):
    def execute(self, mode, error):
        opener = Mock()
        opener.open.side_effect = error
        with patch.object(sys, "argv", ["check.py", mode, "http://test:8080"]), \
                patch.object(CHECK, "build_opener", return_value=opener):
            CHECK.main()

    def test_timeout_can_be_network_denial(self):
        self.execute("deny", URLError(TimeoutError()))

    def test_dns_failure_is_not_network_denial(self):
        with self.assertRaises(AssertionError):
            self.execute("deny", URLError(socket.gaierror("DNS broken")))

    def test_http_500_is_not_network_denial(self):
        with self.assertRaises(AssertionError):
            self.execute("deny", HTTPError("http://test", 500, "error", {}, None))

    def test_allow_timeout_fails(self):
        with self.assertRaises(AssertionError):
            self.execute("allow", URLError(TimeoutError()))

    def test_l7_requires_403(self):
        self.execute("http403", HTTPError("http://test", 403, "forbidden", {}, None))
        with self.assertRaises(AssertionError):
            self.execute("http403", HTTPError("http://test", 401, "unauthorized", {}, None))


if __name__ == "__main__":
    unittest.main()
