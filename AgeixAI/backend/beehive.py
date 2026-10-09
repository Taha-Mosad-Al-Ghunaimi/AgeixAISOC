"""
Hive-Mind Shared State (Blackboard Pattern) — The Beehive.

Each agent writes its findings to this shared state. The Master Brain
reads the collective data to formulate holistic Decision Packages.

Conceptual flow:
   Red Team Agent ─┐
   Blue Team Agent ─┤
   Threat Detection─┤  ──▶  BEEHIVE (shared dict)  ──▶  Master Brain
   Risk Scoring ────┤                                       │
   Recommendation ──┤                                  OSINT Tool
   Threat Hunter ───┘                                       │
   Forensics ───────────────────────────────────────────────┘

The beehive supports LangGraph-style state transitions via:
  - write(agent_name, key, value) — any agent can write
  - read(agent_name=None) — Master Brain reads all or filtered
  - get_activity() — returns which agents are currently processing
"""

import threading
import time
from datetime import datetime, timezone
from typing import Any


class BeehiveState:
    def __init__(self):
        self._lock = threading.Lock()
        self._honey: dict[str, dict[str, Any]] = {}
        self._activity: dict[str, dict[str, Any]] = {}
        self._cycle_counter = 0

    # ── Write: agent deposits findings into the beehive ────────────────────

    def write(self, agent_name: str, key: str, value: Any) -> dict[str, Any]:
        with self._lock:
            if agent_name not in self._honey:
                self._honey[agent_name] = {}
            self._honey[agent_name][key] = {
                "value": value,
                "written_at": datetime.now(timezone.utc).isoformat(),
                "cycle": self._cycle_counter,
            }
            self._mark_active(agent_name, "writing")
            return {"agent": agent_name, "key": key, "status": "stored"}

    # ── Read: Master Brain reads all or specific agent findings ────────────

    def read(self, agent_name: str | None = None) -> dict[str, Any]:
        with self._lock:
            if agent_name:
                return {agent_name: dict(self._honey.get(agent_name, {}))}
            return {k: dict(v) for k, v in self._honey.items()}

    def read_agent(self, agent_name: str) -> dict[str, Any]:
        return dict(self._honey.get(agent_name, {}))

    # ── Clear: reset for next cycle ───────────────────────────────────────

    def new_cycle(self) -> int:
        with self._lock:
            self._cycle_counter += 1
            self._honey.clear()
            self._mark_active("system", f"cycle_{self._cycle_counter}")
            return self._cycle_counter

    @property
    def current_cycle(self) -> int:
        return self._cycle_counter

    # ── Activity tracking ──────────────────────────────────────────────────

    def _mark_active(self, agent_name: str, action: str) -> None:
        self._activity[agent_name] = {
            "action": action,
            "since": datetime.now(timezone.utc).isoformat(),
            "timestamp": time.time(),
        }

    def mark_processing(self, agent_name: str) -> None:
        with self._lock:
            self._mark_active(agent_name, "processing")

    def mark_completed(self, agent_name: str) -> None:
        with self._lock:
            self._mark_active(agent_name, "completed")

    def get_activity(self) -> dict[str, Any]:
        with self._lock:
            now = time.time()
            result = {}
            for agent, info in self._activity.items():
                elapsed = now - info["timestamp"]
                status = "active" if elapsed < 30 else "idle" if elapsed < 300 else "inactive"
                result[agent] = {
                    "status": status,
                    "action": info["action"],
                    "since": info["since"],
                    "idle_seconds": round(elapsed, 1),
                }
            return result

    def is_any_active(self) -> bool:
        activity = self.get_activity()
        return any(a["status"] == "active" for a in activity.values())


beehive = BeehiveState()
