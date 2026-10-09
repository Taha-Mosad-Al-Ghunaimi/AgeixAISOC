"""
AgeixAISOC — AI Exploit Prediction Engine.

Automates Vulnerability Management with four capabilities:

  1. Master Brain PoC Check  —  Web search for public Proof-of-Concept exploits
  2. Risk Scoring Elevation  —  Elevates to CRITICAL when PoC exists in the wild
  3. IPS Patch Generation    —  Auto-drafts FortiGate IPS rule (pending HITL)
  4. Exploit Likelihood Ranking  —  Custom algorithm: CVSS × PoC × age × CISA KEV

Provides two REST endpoints:
  POST /webhook/vuln-scan   —  Ingest new CVEs from scanner (OpenVAS/Nessus mock)
  GET  /api/vulns/predicted  —  List all vulns ranked by Exploit Likelihood
"""

import hashlib
import json
import logging
import random
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("AgeixAI.vuln_predictor")

# ---------------------------------------------------------------------------
# Comprehensive mock CVE database with exploit intelligence
# ---------------------------------------------------------------------------

CVE_DATABASE: dict[str, dict[str, Any]] = {
    "CVE-2025-44228": {
        "description": "Apache Log4j 2.x <= 2.17.0 JNDI injection RCE via crafted log messages",
        "cvss": 9.8,
        "severity": "critical",
        "affected_software": "Apache Log4j 2.x < 2.17.1",
        "affected_assets": ["web-01", "app-03", "api-gw-01"],
        "cisa_kev": True,
        "poc_exists": True,
        "poc_source": "GitHub — multiple public PoCs (log4shell-poc, log4j-rce-exploit)",
        "active_exploitation": True,
        "ransomware_association": True,
        "metasploit_module": "exploit/multi/http/log4j2_rce",
        "published_date": "2025-12-09",
        "vendor_patch_available": True,
        "epss_score": 0.973,
    },
    "CVE-2024-6387": {
        "description": "OpenSSH signal handler race condition (regreSSHion) — unauthenticated RCE on glibc-based systems",
        "cvss": 8.1,
        "severity": "high",
        "affected_software": "OpenSSH < 9.8",
        "affected_assets": ["ssh-gw-01", "linux-bastion-01", "sftp-01"],
        "cisa_kev": True,
        "poc_exists": True,
        "poc_source": "GitHub — regreSSHion PoC (race condition trigger)",
        "active_exploitation": True,
        "ransomware_association": False,
        "metasploit_module": "exploit/linux/ssh/regresshion",
        "published_date": "2024-07-01",
        "vendor_patch_available": True,
        "epss_score": 0.812,
    },
    "CVE-2023-23397": {
        "description": "Microsoft Outlook Elevation of Privilege — NTLM relay via malicious calendar invite",
        "cvss": 9.1,
        "severity": "critical",
        "affected_software": "Microsoft Outlook for Windows",
        "affected_assets": ["mail-01", "exchange-01", "ws-finance-22"],
        "cisa_kev": True,
        "poc_exists": True,
        "poc_source": "GitHub — OutlookNTLMRelay PoC",
        "active_exploitation": True,
        "ransomware_association": True,
        "metasploit_module": "exploit/windows/smb/outlook_ntlm_relay",
        "published_date": "2023-03-14",
        "vendor_patch_available": True,
        "epss_score": 0.891,
    },
    "CVE-2026-3312": {
        "description": "SQL injection in internal web application login form — unauthenticated access to backend database",
        "cvss": 7.5,
        "severity": "high",
        "affected_software": "Internal Web Application v3.2",
        "affected_assets": ["internal-app-01", "portal-01"],
        "cisa_kev": False,
        "poc_exists": True,
        "poc_source": "Exploit-DB — SQLi PoC for similar app framework",
        "active_exploitation": False,
        "ransomware_association": False,
        "metasploit_module": "exploit/multi/http/sqlmap_automation",
        "published_date": "2026-02-15",
        "vendor_patch_available": False,
        "epss_score": 0.534,
    },
    "CVE-2025-3312": {
        "description": "SMB signing disabled — relay attack allows lateral movement across domain",
        "cvss": 7.2,
        "severity": "high",
        "affected_software": "Windows SMB / Samba 4.x",
        "affected_assets": ["dc-01", "fs-01", "app-02"],
        "cisa_kev": False,
        "poc_exists": True,
        "poc_source": "GitHub — SMB relay PoC (Impacket-based)",
        "active_exploitation": True,
        "ransomware_association": True,
        "metasploit_module": "exploit/windows/smb/psexec",
        "published_date": "2025-06-20",
        "vendor_patch_available": True,
        "epss_score": 0.723,
    },
    "CVE-2025-1111": {
        "description": "PowerShell script block logging bypass — AMSI evasion via reflection",
        "cvss": 8.5,
        "severity": "high",
        "affected_software": "Windows PowerShell 5.x, PowerShell 7.x",
        "affected_assets": ["ws-finance-22", "ws-dev-01", "ws-admin-05"],
        "cisa_kev": False,
        "poc_exists": False,
        "poc_source": "",
        "active_exploitation": True,
        "ransomware_association": False,
        "metasploit_module": "exploit/windows/powershell/powerdump",
        "published_date": "2025-03-10",
        "vendor_patch_available": True,
        "epss_score": 0.645,
    },
    "CVE-2024-1709": {
        "description": "ConnectWise ScreenConnect authentication bypass — unauthenticated RCE",
        "cvss": 9.8,
        "severity": "critical",
        "affected_software": "ConnectWise ScreenConnect 23.9.7 and earlier",
        "affected_assets": ["remote-access-01"],
        "cisa_kev": True,
        "poc_exists": True,
        "poc_source": "GitHub — ScreenConnect auth bypass + RCE chain",
        "active_exploitation": True,
        "ransomware_association": True,
        "metasploit_module": "exploit/multi/http/connectwise_screenconnect_rce",
        "published_date": "2024-02-19",
        "vendor_patch_available": True,
        "epss_score": 0.967,
    },
    "CVE-2024-3094": {
        "description": "XZ Utils backdoor (CVE-2024-3094) — SSH backdoor via malicious liblzma",
        "cvss": 9.9,
        "severity": "critical",
        "affected_software": "XZ Utils 5.6.0, 5.6.1",
        "affected_assets": ["linux-bastion-01", "build-server-01", "gitlab-01"],
        "cisa_kev": True,
        "poc_exists": True,
        "poc_source": "GitHub — xz-backdoor-detection scripts & analysis",
        "active_exploitation": True,
        "ransomware_association": False,
        "metasploit_module": "",
        "published_date": "2024-03-29",
        "vendor_patch_available": True,
        "epss_score": 0.999,
    },
    "CVE-2025-0661": {
        "description": "Windows Search Service RCE — unauthenticated OOBR crash leading to arbitrary code execution",
        "cvss": 8.8,
        "severity": "high",
        "affected_software": "Windows 10/11, Windows Server 2022/2025",
        "affected_assets": ["dc-01", "ws-finance-22", "ws-dev-01"],
        "cisa_kev": False,
        "poc_exists": False,
        "poc_source": "",
        "active_exploitation": False,
        "ransomware_association": False,
        "metasploit_module": "",
        "published_date": "2025-04-08",
        "vendor_patch_available": True,
        "epss_score": 0.312,
    },
    "CVE-2026-0001": {
        "description": "Zero-day in VCenter Server — heap overflow via SOAP endpoint",
        "cvss": 9.2,
        "severity": "critical",
        "affected_software": "VMware vCenter Server 8.x < 8.0.3",
        "affected_assets": ["vcenter-01", "esxi-cluster-01"],
        "cisa_kev": False,
        "poc_exists": False,
        "poc_source": "",
        "active_exploitation": False,
        "ransomware_association": False,
        "metasploit_module": "",
        "published_date": "2026-01-05",
        "vendor_patch_available": False,
        "epss_score": 0.850,
    },
}

# ---------------------------------------------------------------------------
# Exploit Likelihood Scoring Algorithm
# ---------------------------------------------------------------------------

def compute_exploit_likelihood(cve: dict[str, Any]) -> float:
    """
    Compute a 0–100 "Exploit Likelihood" score using a weighted multi-factor model.

    Factors (weights):
      - CVSS Score          (30%)  —  Base severity
      - PoC Exists          (25%)  —  Public exploit code available
      - Active Exploitation (20%)  —  Observed in the wild
      - CISA KEV            (10%)  —  Known Exploited Vulnerabilities catalog
      - EPSS Score          (10%)  —  Exploit Prediction Scoring System (mock)
      - Recency Factor      ( 5%)  —  Newer CVEs are more likely to be exploited

    Returns a float between 0 and 100.
    """
    cvss = cve.get("cvss", 5.0)
    cvss_component = (cvss / 10.0) * 30.0

    poc = cve.get("poc_exists", False)
    poc_component = 25.0 if poc else 0.0

    active = cve.get("active_exploitation", False)
    active_component = 20.0 if active else 0.0

    kev = cve.get("cisa_kev", False)
    kev_component = 10.0 if kev else 0.0

    epss = cve.get("epss_score", 0.5)
    epss_component = epss * 10.0

    published = cve.get("published_date", "2020-01-01")
    try:
        pub_date = datetime.strptime(published, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        days_old = (datetime.now(timezone.utc) - pub_date).days
        recency = max(0, 1.0 - (days_old / 730.0))  # linear decay over 2 years
    except (ValueError, TypeError):
        recency = 0.5
    recency_component = recency * 5.0

    score = cvss_component + poc_component + active_component + kev_component + epss_component + recency_component
    clamped = max(0.0, min(100.0, score))
    return round(clamped, 1)


def get_likelihood_label(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# In-memory vulnerability store (thread-safe)
# ---------------------------------------------------------------------------

class VulnerabilityStore:
    """Thread-safe in-memory store for scanned vulnerabilities."""

    def __init__(self):
        self._lock = threading.Lock()
        self._vulns: list[dict[str, Any]] = []
        self._scan_count = 0

    def ingest(self, cve_id: str, target: str = "", port: int = 0, service: str = "") -> dict[str, Any]:
        """Ingest a CVE from a scanner. Returns the enriched vuln record."""
        cve_data = CVE_DATABASE.get(cve_id, {
            "description": "Unknown CVE — no details available",
            "cvss": 5.0,
            "severity": "medium",
            "affected_software": service or "unknown",
            "affected_assets": [target] if target else [],
            "cisa_kev": False,
            "poc_exists": False,
            "poc_source": "",
            "active_exploitation": False,
            "ransomware_association": False,
            "metasploit_module": "",
            "published_date": "2020-01-01",
            "vendor_patch_available": False,
            "epss_score": 0.1,
        })

        # Determine if PoC exists (web search mock)
        poc_check = self._check_poc_web_search(cve_id, cve_data)

        # Compute exploit likelihood
        likelihood = compute_exploit_likelihood({**cve_data, "poc_exists": poc_check["poc_exists"]})
        likelihood_label = get_likelihood_label(likelihood)

        # Build FortiGate IPS rule if PoC exists or likelihood is high+
        ips_rule = self._generate_fortigate_ips_rule(cve_id, cve_data) if poc_check["poc_exists"] or likelihood >= 60 else ""

        vuln = {
            "vuln_id": f"VULN-{hashlib.md5(f'{cve_id}{target}{datetime.now().isoformat()}'.encode()).hexdigest()[:8].upper()}",
            "cve_id": cve_id,
            "cvss": cve_data["cvss"],
            "cvss_severity": cve_data["severity"],
            "description": cve_data["description"],
            "affected_software": cve_data["affected_software"],
            "affected_asset": target,
            "port": port,
            "service": service,
            "ransomware_associated": cve_data.get("ransomware_association", False),
            "published_date": cve_data.get("published_date", "unknown"),
            "vendor_patch_available": cve_data.get("vendor_patch_available", False),
        }

        # ── Master Brain PoC Check ──────────────────────────────────────
        vuln["poc_exists"] = poc_check["poc_exists"]
        vuln["poc_source"] = poc_check["poc_source"]
        vuln["poc_check_timestamp"] = datetime.now(timezone.utc).isoformat()

        # ── Risk Scoring Agent — elevation ──────────────────────────────
        base_severity = cve_data["severity"]
        if poc_check["poc_exists"]:
            vuln["risk_level"] = "critical"
            vuln["risk_elevated"] = True
            vuln["risk_elevation_reason"] = f"Public PoC exploit confirmed — severity elevated from {base_severity} to CRITICAL"
        else:
            vuln["risk_level"] = likelihood_label
            vuln["risk_elevated"] = False
            vuln["risk_elevation_reason"] = f"Risk scored at {likelihood_label} based on multi-factor likelihood model"

        # ── Exploit Likelihood (computed before mitigation for comparison) ─
        vuln["exploit_likelihood"] = likelihood
        vuln["exploit_likelihood_label"] = likelihood_label

        # ── Recommendation Agent — IPS patch ────────────────────────────
        vuln["ips_rule"] = ips_rule
        vuln["ips_rule_generated"] = bool(ips_rule)
        vuln["mitigation_recommended"] = self._recommend_mitigation(vuln, cve_data)

        vuln["scan_timestamp"] = datetime.now(timezone.utc).isoformat()
        vuln["requires_human_approval"] = True

        with self._lock:
            self._vulns.append(vuln)
            self._scan_count += 1

        logger.info(
            "Vuln ingested: %s on %s — cvss=%.1f poc=%s risk=%s likelihood=%.1f ips=%s",
            cve_id, target or "?", cve_data["cvss"], poc_check["poc_exists"],
            vuln["risk_level"], likelihood, bool(ips_rule),
        )
        return vuln

    def _check_poc_web_search(self, cve_id: str, cve_data: dict[str, Any]) -> dict[str, Any]:
        """
        Master Brain PoC Check — uses web search to find public exploit code.

        Mocks a DuckDuckGo/GitHub search for PoC exploits. In production,
        this queries Exploit-DB, GitHub, and NVD.
        """
        if cve_data.get("poc_exists", False):
            return {
                "poc_exists": True,
                "poc_source": cve_data.get("poc_source", "Discovered via web search"),
                "poc_detail": (
                    f"Web search for '{cve_id} PoC exploit' returned {random.randint(3, 15)} results. "
                    f"Public exploit code found on {random.choice(['GitHub', 'Exploit-DB', 'Packet Storm', 'GitLab'])}. "
                    f"Metasploit module available: {cve_data.get('metasploit_module', 'N/A')}"
                ),
            }

        # For CVEs marked without PoC, try mock web search anyway
        if random.random() < 0.05:  # 5% chance of discovering a new PoC
            return {
                "poc_exists": True,
                "poc_source": f"Newly discovered PoC for {cve_id} via web search",
                "poc_detail": f"Web search found a proof-of-concept uploaded to GitHub 2 days ago.",
            }

        return {
            "poc_exists": False,
            "poc_source": "",
            "poc_detail": f"Web search for '{cve_id} PoC exploit' returned no public exploit code.",
        }

    def _generate_fortigate_ips_rule(self, cve_id: str, cve_data: dict[str, Any]) -> str:
        """
        Recommendation Agent — auto-drafts a FortiGate IPS rule (virtual patch).

        Returns a FortiGate CLI config snippet that blocks exploitation attempts.
        """
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', cve_id)
        sig_id = abs(hash(cve_id)) % 90000000 + 10000000
        protocol = "tcp"
        port_hint = 80 if "web" in cve_data.get("affected_software", "").lower() else 443 if "outlook" in cve_data.get("affected_software", "").lower() else 445 if "smb" in cve_data.get("affected_software", "").lower() else 22 if "ssh" in cve_data.get("affected_software", "").lower() else 0

        return (
            f"config ips sensor\n"
            f"    edit \"virtual-patch-{sanitized}\"\n"
            f"        config entry\n"
            f"            edit {sig_id}\n"
            f"                set rule {sig_id}\n"
            f"                set action block\n"
            f"                set application {random.randint(1, 65535)}\n"
            f"                set severity critical\n"
            f"                set protocol {protocol}\n"
            f"                set status enable\n"
            f"                set comment \"AgeixAI auto-generated virtual patch for {cve_id} — {cve_data.get('description', '')[:80]}\"\n"
            + (f"                set dst-port {port_hint}\n" if port_hint else "") +
            f"            next\n"
            f"        end\n"
            f"    next\n"
            f"end\n"
            f"# Deploy: execute ips-sensor virtual-patch-{sanitized} apply"
        )

    def _recommend_mitigation(self, vuln: dict[str, Any], cve_data: dict[str, Any]) -> str:
        """Generate a human-readable mitigation recommendation."""
        parts = []
        if cve_data.get("vendor_patch_available"):
            parts.append(f"Apply vendor patch for {vuln['cve_id']} on affected assets: {', '.join(cve_data.get('affected_assets', ['unknown']))}.")
        else:
            parts.append(f"No vendor patch available — virtual patch via FortiGate IPS is strongly recommended.")
        if vuln.get("ips_rule_generated"):
            parts.append("Deploy the auto-generated FortiGate IPS rule (pending human approval).")
        if vuln["exploit_likelihood"] >= 60:
            parts.append("High exploit likelihood — prioritize remediation within 48 hours.")
        vuln_data = cve_data.get("ransomware_association")
        if vuln_data:
            parts.append("Ransomware association detected — treat as emergency.")
        return " ".join(parts)

    def get_ranked_vulns(self) -> list[dict[str, Any]]:
        """Return all vulnerabilities sorted by exploit_likelihood descending."""
        with self._lock:
            sorted_vulns = sorted(self._vulns, key=lambda v: v["exploit_likelihood"], reverse=True)
            return [dict(v) for v in sorted_vulns]

    def get_statistics(self) -> dict[str, Any]:
        """Return aggregate statistics about the vulnerability store."""
        with self._lock:
            total = len(self._vulns)
            if total == 0:
                return {"total_vulns": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "avg_exploit_likelihood": 0.0}

            critical = sum(1 for v in self._vulns if v["exploit_likelihood_label"] == "critical")
            high = sum(1 for v in self._vulns if v["exploit_likelihood_label"] == "high")
            medium = sum(1 for v in self._vulns if v["exploit_likelihood_label"] == "medium")
            low = sum(1 for v in self._vulns if v["exploit_likelihood_label"] == "low")
            poc_count = sum(1 for v in self._vulns if v.get("poc_exists"))
            ips_count = sum(1 for v in self._vulns if v.get("ips_rule_generated"))
            avg_likelihood = round(sum(v["exploit_likelihood"] for v in self._vulns) / total, 1)

            return {
                "total_vulns": total,
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low,
                "poc_confirmed": poc_count,
                "ips_rules_generated": ips_count,
                "avg_exploit_likelihood": avg_likelihood,
                "scan_count": self._scan_count,
            }


# Singleton
VULN_STORE = VulnerabilityStore()


# ---------------------------------------------------------------------------
# Pre-populate with known CVEs
# ---------------------------------------------------------------------------

def seed_vuln_store() -> None:
    """Seed the store with known CVEs as if a scan had already run."""
    seeds = [
        ("CVE-2025-44228", "web-01", 80, "Apache Tomcat"),
        ("CVE-2024-6387", "ssh-gw-01", 22, "OpenSSH"),
        ("CVE-2023-23397", "exchange-01", 443, "Microsoft Outlook"),
        ("CVE-2025-3312", "dc-01", 445, "SMB"),
        ("CVE-2025-1111", "ws-finance-22", 0, "PowerShell"),
        ("CVE-2024-1709", "remote-access-01", 443, "ConnectWise"),
        ("CVE-2024-3094", "linux-bastion-01", 22, "XZ Utils"),
        ("CVE-2026-3312", "internal-app-01", 8080, "Web Application"),
        ("CVE-2025-0661", "dc-01", 0, "Windows Search"),
        ("CVE-2026-0001", "vcenter-01", 443, "VMware vCenter"),
    ]
    for cve_id, target, port, service in seeds:
        VULN_STORE.ingest(cve_id=cve_id, target=target, port=port, service=service)
    logger.info("Vuln store seeded with %d CVEs", len(seeds))


# Seed on import
seed_vuln_store()
