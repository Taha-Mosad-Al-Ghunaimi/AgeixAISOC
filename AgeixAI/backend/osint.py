"""AlienVault OTX intelligence fetcher."""

import hashlib
import time
from typing import Any
import requests
from config import get_settings


class OTXClient:
    BASE_URL = "https://otx.alienvault.com/api/v1"

    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.otx_api_key
        if not self.api_key:
            raise ValueError(
                "OTX_API_KEY is not set. Get one free at https://otx.alienvault.com"
            )
        self.session = requests.Session()
        self.session.headers.update({"X-OTX-API-KEY": self.api_key})

    def get_recent_pulses(self, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch the most recent public pulses from AlienVault OTX."""
        url = f"{self.BASE_URL}/pulses/subscribed"
        params = {"limit": min(limit, 50), "modified_since": None}
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            pulses = data.get("results", [])
            return [self._format_pulse(p) for p in pulses]
        except requests.RequestException as e:
            return [{"error": f"Failed to fetch OTX pulses: {e}"}]

    def get_pulse_details(self, pulse_id: str) -> dict[str, Any]:
        """Fetch details for a specific pulse by its ID."""
        url = f"{self.BASE_URL}/pulses/{pulse_id}"
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return self._format_pulse(resp.json())
        except requests.RequestException as e:
            return {"error": f"Failed to fetch pulse details: {e}"}

    def search_pulses(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search pulses by text query."""
        url = f"{self.BASE_URL}/pulses/subscribed"
        params = {"limit": min(limit, 50), "q": query}
        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            pulses = data.get("results", [])
            return [self._format_pulse(p) for p in pulses]
        except requests.RequestException as e:
            return [{"error": f"Failed to search OTX pulses: {e}"}]

    def _format_pulse(self, pulse: dict[str, Any]) -> dict[str, Any]:
        """Normalize an OTX pulse into a standardised intelligence format."""
        indicators = pulse.get("indicators", [])
        iocs = []
        for ind in indicators:
            iocs.append(
                {
                    "type": ind.get("type", "unknown"),
                    "value": ind.get("indicator", ""),
                    "description": ind.get("description", ""),
                }
            )

        return {
            "id": pulse.get("id", ""),
            "title": pulse.get("name", "Untitled Pulse"),
            "description": pulse.get("description", ""),
            "author": pulse.get("author", {}).get("username", "unknown"),
            "tags": [t.get("name", "") for t in pulse.get("tags", [])],
            "severity": self._infer_severity(pulse),
            "tlp": pulse.get("tlp", "amber"),
            "created": pulse.get("created", ""),
            "modified": pulse.get("modified", ""),
            "iocs": iocs,
            "reference_count": pulse.get("reference_count", 0),
            "source": "AlienVault OTX",
        }

    def _infer_severity(self, pulse: dict[str, Any]) -> str:
        """Heuristic to assign a severity label based on pulse metadata."""
        tags = [t.get("name", "").lower() for t in pulse.get("tags", [])]
        critical_keywords = {"ransomware", "cve", "exploit", "zero-day", "apt"}
        high_keywords = {"malware", "botnet", "phishing", "trojan", "backdoor"}
        if any(kw in tags for kw in critical_keywords):
            return "critical"
        if any(kw in tags for kw in high_keywords):
            return "high"
        return "medium"

    def health_check(self) -> bool:
        """Quick check that the API key works."""
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/user/me", timeout=10
            )
            return resp.status_code == 200
        except requests.RequestException:
            return False


# Convenience functions --------------------------------------------------------

def fetch_recent_threats(limit: int = 10) -> list[dict]:
    """Shortcut: build a client and return recent pulses."""
    client = OTXClient()
    return client.get_recent_pulses(limit=limit)


def fetch_threats_by_tag(tag: str, limit: int = 10) -> list[dict]:
    """Shortcut: search pulses by a tag keyword."""
    client = OTXClient()
    return client.search_pulses(query=tag, limit=limit)
