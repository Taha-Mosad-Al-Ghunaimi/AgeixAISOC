import asyncio
import logging
from typing import Any

from models.schemas import McpQuery, McpResponse

logger = logging.getLogger("AgeixAI.mcp.orchestrator")

SERVER_MODULES = {
    "wazuh": "mcp_servers.wazuh_mcp",
    "edr": "mcp_servers.edr_mcp",
    "ndr": "mcp_servers.ndr_mcp",
    "red": "mcp_servers.red_mcp",
    "forti": "mcp_servers.forti_mcp",
    "ti": "mcp_servers.ti_mcp",
    "sigma": "mcp_servers.sigma_mcp",
    "rag": "mcp_servers.rag_mcp",
    "forensics": "mcp_servers.forensics_mcp",
    "rl": "rl.mcp_adapter",
}

NATURAL_LANGUAGE_ROUTING = {
    "block": {"server": "forti", "action": "block_ip"},
    "isolate": {"server": "edr", "action": "isolate_host"},
    "scan": {"server": "red", "action": "nmap_scan"},
    "cve": {"server": "red", "action": "cve_lookup"},
    "alert": {"server": "wazuh", "action": "get_alerts"},
    "process": {"server": "edr", "action": "get_processes"},
    "network": {"server": "ndr", "action": "get_flows"},
    "dns": {"server": "ndr", "action": "get_dns_queries"},
    "intel": {"server": "ti", "action": "lookup_ip"},
    "ioc": {"server": "ti", "action": "get_recent_iocs"},
    "sigma": {"server": "sigma", "action": "list_rules"},
    "rule": {"server": "sigma", "action": "get_rule"},
    "forensic": {"server": "forensics", "action": "collect_artifacts"},
    "memory": {"server": "forensics", "action": "analyze_memory"},
}


class McpOrchestrator:
    async def query(self, server_name: str, action: str, params: dict[str, Any] | None = None) -> McpResponse:
        module_path = SERVER_MODULES.get(server_name)
        if not module_path:
            return McpResponse(server=server_name, action=action, status="error", error=f"Unknown MCP server: {server_name}")

        try:
            import importlib
            mod = importlib.import_module(module_path)
            data = await asyncio.to_thread(mod.handle_action, action, params or {})
            return McpResponse(server=server_name, action=action, status="ok", data=data)
        except Exception as exc:
            logger.exception("MCP query failed: %s/%s", server_name, action)
            return McpResponse(server=server_name, action=action, status="error", error=str(exc))

    async def query_parallel(self, queries: list[McpQuery]) -> dict[str, McpResponse]:
        tasks = [self.query(q.server, q.action, q.params) for q in queries]
        results = await asyncio.gather(*tasks)
        return {r.server: r for r in results}

    async def natural_language_query(self, text: str) -> dict[str, Any]:
        text_lower = text.lower()
        matched_servers = set()
        queries: list[McpQuery] = []

        for keyword, route in NATURAL_LANGUAGE_ROUTING.items():
            if keyword in text_lower and route["server"] not in matched_servers:
                matched_servers.add(route["server"])
                queries.append(McpQuery(
                    server=route["server"],
                    action=route["action"],
                    params={"query": text},
                ))

        if not queries:
            queries = [McpQuery(server=s, action="health_check", params={}) for s in SERVER_MODULES]

        results = await self.query_parallel(queries)
        summary = f"Queried {len(results)} MCP servers via natural language request. "
        ok_count = sum(1 for r in results.values() if r.status == "ok")
        summary += f"{ok_count} returned successfully."

        return {
            "query": text,
            "results": {k: v.model_dump() for k, v in results.items()},
            "summary": summary,
        }
