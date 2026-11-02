"""Network probes: only timeout/refusal is accepted as a denied TCP flow."""
import argparse
import errno
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["allow", "deny", "dns", "dns-tcp", "http403"])
    parser.add_argument("target")
    args = parser.parse_args()
    if args.mode == "dns":
        addresses = socket.getaddrinfo(args.target, 8080, type=socket.SOCK_STREAM)
        assert addresses, "DNS returned no address"
        print(json.dumps({"dns": args.target, "address": addresses[0][4][0]}))
        return
    if args.mode == "dns-tcp":
        # A real DNS request over TCP, not just a successful socket connection.
        import struct
        query = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
        query += b"".join(bytes([len(p)]) + p.encode() for p in args.target.split("."))
        query += b"\x00\x00\x01\x00\x01"
        with open("/etc/resolv.conf", encoding="utf-8") as resolv:
            resolver = next(line.split()[1] for line in resolv if line.startswith("nameserver"))
        with socket.create_connection((resolver, 53), timeout=4) as stream:
            stream.sendall(struct.pack("!H", len(query)) + query)
            data = b""
            while len(data) < 2:
                chunk = stream.recv(2 - len(data))
                assert chunk, "truncated DNS length"
                data += chunk
            size = struct.unpack("!H", data)[0]
            answer = b""
            while len(answer) < size:
                chunk = stream.recv(size - len(answer))
                assert chunk, "truncated DNS response"
                answer += chunk
        assert answer[:2] == b"\x12\x34" and answer[3] & 15 == 0
        assert struct.unpack("!H", answer[6:8])[0] > 0, "DNS has no answer"
        print("DNS TCP OK")
        return
    try:
        with build_opener(ProxyHandler({})).open(args.target, timeout=4) as response:
            payload = response.read().decode()
            assert args.mode == "allow", "unexpected HTTP success"
            assert response.status == 200
            json.loads(payload)
            print(payload)
    except HTTPError as error:
        assert args.mode == "http403" and error.code == 403, f"unexpected HTTP {error.code}"
        print("L7 HTTP 403 confirmed")
    except (URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", error)
        assert not isinstance(reason, socket.gaierror), "DNS failure is not proof of isolation"
        is_denial = isinstance(reason, TimeoutError) or getattr(reason, "errno", None) in {
            errno.ETIMEDOUT, errno.ECONNREFUSED, errno.EHOSTUNREACH, errno.ENETUNREACH,
            10060, 10061, 10065,
        }
        assert args.mode == "deny" and is_denial, f"unexpected network error: {error}"
        print("TCP blocked (correlate with Hubble):", reason)


if __name__ == "__main__":
    main()
