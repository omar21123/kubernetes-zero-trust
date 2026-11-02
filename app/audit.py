"""Exercise real Kubernetes authentication and authorization from a workload."""
import json
from pathlib import Path
import ssl
from urllib.error import HTTPError
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener


def main():
    credentials = Path("/var/run/zt-kubernetes")
    token = (credentials / "token").read_text().strip()
    context = ssl.create_default_context(cafile=str(credentials / "ca.crt"))
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=context))
    base = "https://kubernetes.default.svc"
    checks = [
        ("/api/v1/namespaces/zt-app/configmaps/public-info", 200),
        ("/api/v1/namespaces/zt-app/configmaps/other-info", 403),
        ("/api/v1/namespaces/zt-app/secrets", 403),
        ("/api/v1/namespaces/zt-data/pods", 403),
    ]
    for path, expected in checks:
        request = Request(base + path, headers={"Authorization": "Bearer " + token})
        try:
            with opener.open(request, timeout=8) as response:
                status = response.status
                response.read()
        except HTTPError as error:
            status = error.code
        assert status == expected, f"{path}: expected {expected}, got {status}"
        print(json.dumps({"path": path, "expected": expected, "status": status}), flush=True)


if __name__ == "__main__":
    main()
