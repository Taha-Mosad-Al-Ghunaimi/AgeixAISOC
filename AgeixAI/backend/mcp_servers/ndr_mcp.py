import random
from datetime import datetime, timezone
from typing import Any


SERVER_NAME = "ndr-mcp"

def handle_action(action: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    if action == "get_flows":
        return _mock_flows()
    elif action == "get_dns_queries":
        return _mock_dns()
    elif action == "get_tls_certificates":
        return _mock_tls()
    elif action == "get_anomalies":
        return _mock_anomalies()
    elif action == "sweep_iocs":
        iocs = params.get("iocs", [])
        return _mock_ioc_sweep(iocs)
    else:
        return [{"error": f"Unknown action: {action}"}]


def _mock_flows() -> list[dict[str, Any]]:
    flows = []
    for _ in range(8):
        flows.append({
            "src_ip": f"10.0.{random.randint(1,5)}.{random.randint(1,255)}",
            "dst_ip": f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}",
            "bytes": random.randint(1024, 10485760),
            "proto": random.choice(["TCP", "UDP"]),
            "dport": random.choice([80, 443, 53, 445, 3389]),
        })
    return flows


def _mock_dns() -> list[dict[str, Any]]:
    return [
        {"query": "evil-c2.example.com", "type": "A", "response": "185.130.5.23", "count": 47},
        {"query": "update-service.azure.com", "type": "A", "response": "13.89.178.12", "count": 3},
        {"query": random.choice(["dns-tunnel-1.xyz", "data-exfil.net", "beacon.pw"]), "type": "TXT", "response": "base64encodeddata==", "count": 120},
    ]


def _mock_tls() -> list[dict[str, Any]]:
    return [
        {"server_name": "malicious-c2.com", "issuer": "CN=Fake CA", "not_after": "2027-01-01", "self_signed": True},
        {"server_name": "login.microsoftonline.com", "issuer": "CN=Microsoft RSA", "not_after": "2027-06-01", "self_signed": False},
    ]


def _mock_anomalies() -> list[dict[str, Any]]:
    return [
        {"type": "dns_tunneling", "severity": "high", "src_ip": "10.0.3.22", "detail": "47 DNS queries to suspicious domain in 60s"},
        {"type": "data_exfil", "severity": "critical", "src_ip": "10.0.2.100", "detail": "12GB outbound to unknown IP in 5 minutes"},
    ]


def _mock_ioc_sweep(iocs: list[str]) -> list[dict[str, Any]]:
    """Return NDR network traffic matches for a list of IOCs."""
    results = []
    for ioc in iocs[:5]:
        hits = random.randint(0, 2)
        for _ in range(hits):
            results.append({
                "ioc": ioc,
                "source": "ndr-mcp",
                "src_ip": f"10.0.{random.randint(1,5)}.{random.randint(1,255)}",
                "dst_ip": ioc if "." in ioc and ioc.count(".") == 3 else f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}",
                "protocol": random.choice(["TCP", "UDP"]),
                "dport": random.choice([80, 443, 53, 139, 445, 8080, 4444]),
                "bytes": random.randint(1024, 104857600),
                "flow_duration_sec": random.randint(1, 3600),
                "matched_on": random.choice(["dst_ip", "domain", "tls_sni", "dns_query"]),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    return results
