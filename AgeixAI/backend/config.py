"""
AgeixAISOC — Core Configuration.
Loads environment variables via python-dotenv.

VM Lab Network:  192.168.56.0/24
  Host (AI Brain):  192.168.56.1
  FortiGate:        192.168.56.2
  Kali Linux:       192.168.56.10
  Windows 10 Victim: 192.168.56.20
  Wazuh SIEM:       192.168.56.30
  Metasploitable 2: 192.168.56.40
  Windows AD Server: 192.168.56.100
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # ── Ollama ────────────────────────────────────────────────────────────────
    ollama_base_url: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_BASE_URL", "http://192.168.56.1:11434")
    )
    master_brain_model: str = field(
        default_factory=lambda: os.environ.get("MASTER_BRAIN_LLM", "qwen2.5:14b")
    )
    coder_model: str = field(
        default_factory=lambda: os.environ.get("CODER_LLM", "qwen2.5-coder:7b")
    )
    fast_triage_model: str = field(
        default_factory=lambda: os.environ.get("FAST_TRIAGE_LLM", "llama3.1:latest")
    )
    osint_model: str = field(
        default_factory=lambda: os.environ.get("OSINT_LLM", "gemma4:latest")
    )

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    chromadb_path: str = field(
        default_factory=lambda: os.environ.get("CHROMA_DB_PATH", "./chroma_db")
    )

    # ── n8n SOAR Webhook ─────────────────────────────────────────────────────
    n8n_base_url: str = field(
        default_factory=lambda: os.environ.get("N8N_BASE_URL", "http://192.168.56.1:5678")
    )
    n8n_soar_webhook: str = field(
        default_factory=lambda: os.environ.get(
            "N8N_SOAR_WEBHOOK", "http://192.168.56.1:5678/webhook/execute-soar"
        )
    )

    # ── VM Lab (192.168.56.0/24) ──────────────────────────────────────────────
    # Kali Linux (Attacker)
    lab_kali_ip: str = field(
        default_factory=lambda: os.environ.get("KALI_IP", "192.168.56.10")
    )
    lab_kali_user: str = field(
        default_factory=lambda: os.environ.get("KALI_SSH_USER", "aziz")
    )
    lab_kali_pass: str = field(
        default_factory=lambda: os.environ.get("KALI_SSH_PASS", "8394")
    )
    lab_kali_port: int = field(
        default_factory=lambda: int(os.environ.get("KALI_SSH_PORT", "22"))
    )

    # Windows 10 Pro (Victim / Endpoint)
    lab_win10_ip: str = field(
        default_factory=lambda: os.environ.get("WIN10_IP", "192.168.56.20")
    )

    # Metasploitable 2 (Vulnerable target)
    lab_metasploitable_ip: str = field(
        default_factory=lambda: os.environ.get("METASPLOITABLE_IP", "192.168.56.40")
    )
    lab_metasploitable_user: str = field(
        default_factory=lambda: os.environ.get("METASPLOITABLE_SSH_USER", "msfadmin")
    )
    lab_metasploitable_pass: str = field(
        default_factory=lambda: os.environ.get("METASPLOITABLE_SSH_PASS", "msfadmin")
    )

    # Windows Server 2022 (AD)
    lab_ad_ip: str = field(
        default_factory=lambda: os.environ.get("AD_IP", "192.168.56.100")
    )

    # Legacy target (backward compat)
    lab_target_ip: str = field(
        default_factory=lambda: os.environ.get("UBUNTU_IP")
        or os.environ.get("TARGET_IP", "192.168.56.20")
    )

    # Wazuh SIEM
    lab_wazuh_ip: str = field(
        default_factory=lambda: os.environ.get("WAZUH_IP", "192.168.56.30")
    )
    wazuh_api_user: str = field(
        default_factory=lambda: os.environ.get("WAZUH_API_USER", "wazuh-wui")
    )
    wazuh_api_pass: str = field(
        default_factory=lambda: os.environ.get("WAZUH_API_PASS", "wazuh-wui")
    )
    wazuh_api_port: int = field(
        default_factory=lambda: int(os.environ.get("WAZUH_API_PORT", "55000"))
    )

    # FortiGate (Gateway / Firewall)
    lab_fortigate_ip: str = field(
        default_factory=lambda: os.environ.get("FORTIGATE_IP", "192.168.56.2")
    )
    fgt_api_key: str = field(
        default_factory=lambda: os.environ.get("FORTIGATE_API_TOKEN", "")
    )
    fgt_blocked_grp: str = field(
        default_factory=lambda: os.environ.get("FORTIGATE_BLOCK_GROUP", "SOC-BLOCKED-IPs")
    )
    fgt_quarantine_grp: str = field(
        default_factory=lambda: os.environ.get("FORTIGATE_QUARANTINE_GRP", "Quarantine_Hosts")
    )

    # ── Server ────────────────────────────────────────────────────────────────
    host: str = field(default_factory=lambda: os.environ.get("BACKEND_HOST", "0.0.0.0"))
    port: int = field(
        default_factory=lambda: int(os.environ.get("BACKEND_PORT", "8000"))
    )

    # ── Backend URL (for Wazuh webhook response) ─────────────────────────────
    backend_url: str = field(
        default_factory=lambda: os.environ.get("BACKEND_URL", "http://192.168.56.1:8000")
    )

    # ── Wazuh integration level threshold ────────────────────────────────────
    wazuh_integration_level: int = field(
        default_factory=lambda: int(os.environ.get("WAZUH_INTEGRATION_LEVEL", "7"))
    )


settings = Settings()
