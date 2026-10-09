"""
AgeixAISOC — OSINT & Dark Web Swarm Engine.

Architecture:
  1. Clear Web Agent  — mocks Google Dorks for public records
  2. Social Media Agent — mocks LinkedIn/X scraping for employee intel
  3. Dark Web Agent   — mocks Ahmia/Tor search for leaked credentials
  4. Reasoning Agent  — deduplicates, removes false positives, compiles OSINT Report

The Reasoning Agent's final report is embedded into the RAG vector store
under the "external_threat_intel" collection, so the Master Brain can later
query it when processing internal alerts.
"""

import hashlib
import json
import logging
import random
import threading
from datetime import datetime, timezone
from typing import Any

from crewai import Agent, Crew, Process, Task
from crewai.tools import tool

from llm_config import get_master_brain_llm, get_coder_llm, get_fast_triage_llm

logger = logging.getLogger("AgeixAI.osint_swarm")

master_brain_llm = get_master_brain_llm()
coder_llm = get_coder_llm()
fast_triage_llm = get_fast_triage_llm()

from rag.vector_store import get_vector_store
from adaptive_rag import inject_rag_context, format_rag_context_for_prompt

vector_store = get_vector_store()

# ═══════════════════════════════════════════════════════════════════════════════
# In-memory research tracker — avoids polluting the main beehive
# ═══════════════════════════════════════════════════════════════════════════════

_research_store: dict[str, dict[str, Any]] = {}
_store_lock = threading.Lock()


def _store_finding(research_id: str, agent: str, data: Any) -> None:
    with _store_lock:
        if research_id not in _research_store:
            _research_store[research_id] = {"id": research_id, "findings": {}}
        _research_store[research_id]["findings"][agent] = {
            "data": data,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }


def _get_findings(research_id: str) -> dict[str, Any]:
    with _store_lock:
        return _research_store.get(research_id, {}).get("findings", {})


def _store_report(research_id: str, report: dict[str, Any]) -> None:
    with _store_lock:
        if research_id not in _research_store:
            _research_store[research_id] = {"id": research_id, "findings": {}}
        _research_store[research_id]["report"] = report


def _get_report(research_id: str) -> dict[str, Any] | None:
    with _store_lock:
        entry = _research_store.get(research_id)
        return entry.get("report") if entry else None


def _get_research_status(research_id: str) -> dict[str, Any]:
    with _store_lock:
        entry = _research_store.get(research_id)
        if not entry:
            return {"status": "not_found", "research_id": research_id}
        findings = entry.get("findings", {})
        has_report = "report" in entry
        agents_done = list(findings.keys())
        return {
            "status": "completed" if has_report else "in_progress",
            "research_id": research_id,
            "agents_completed": agents_done,
            "all_agents_done": len(agents_done) >= 3,
            "report_ready": has_report,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Mock data generators per agent
# ═══════════════════════════════════════════════════════════════════════════════

MOCK_COMPANIES = {
    "acme": {
        "name": "Acme Security Inc.",
        "domain": "acmesec.com",
        "industry": "cybersecurity",
        "employees": 450,
        "revenue_m": 120,
        "hq": "San Francisco, CA",
    },
    "megacorp": {
        "name": "MegaCorp International",
        "domain": "megacorp.com",
        "industry": "finance",
        "employees": 12000,
        "revenue_m": 4500,
        "hq": "New York, NY",
    },
    "democorp": {
        "name": "Demo Corporation",
        "domain": "democorp.io",
        "industry": "technology",
        "employees": 80,
        "revenue_m": 15,
        "hq": "Austin, TX",
    },
}

MOCK_DORK_RESULTS = [
    {"title": "Employee Directory — {domain}",
     "url": f"https://www.google.com/search?q=site:{'{domain}'}+employee+directory",
     "snippet": "List of employee names, roles, and email addresses on the company about page."},
    {"title": "{name} SEC Filing Q2 2026 — Revenue Forecast",
     "url": f"https://www.sec.gov/edgar/{'{domain}'}/10q-2026",
     "snippet": "Quarterly financial filing revealing $XX.XM revenue, 22% YoY growth, and new market expansion."},
    {"title": "{name} — Internal VPN Portal Exposed",
     "url": f"https://vpn.{'{domain}'}/login",
     "snippet": "VPN login page discovered via dork 'inurl:vpn {company_keyword}'. No MFA observed."},
    {"title": "{name} — Confluence Wiki (Public)",
     "url": f"https://confluence.{'{domain}'}/spaces/IT",
     "snippet": "Public Confluence space containing network diagrams, IP allocations, and IT procedures."},
    {"title": "{name} — Jenkins CI (no auth)",
     "url": f"https://jenkins.{'{domain}'}/script",
     "snippet": "Jenkins instance accessible without authentication. Script console exposed."},
    {"title": "{name} — AWS S3 Bucket Listing",
     "url": f"http://{'{domain}'}-backup.s3.amazonaws.com/",
     "snippet": "Open S3 bucket containing database backups dated last month (approx 2.4GB)."},
]

MOCK_SOCIAL_RESULTS = [
    {"platform": "LinkedIn", "profile": f"https://linkedin.com/in/john-doe-{'{hash}'}",
     "name": "John Doe", "role": "VP of Engineering",
     "summary": "Overseeing engineering at {name}. 200+ employees. Previously at Google."},
    {"platform": "LinkedIn", "profile": f"https://linkedin.com/in/jane-smith-{'{hash}'}",
     "name": "Jane Smith", "role": "SOC Manager",
     "summary": "Managing SOC team of 15 analysts at {name}. CISSP, GCIA, GCIH."},
    {"platform": "LinkedIn", "profile": f"https://linkedin.com/in/bob-wilson-{'{hash}'}",
     "name": "Bob Wilson", "role": "DevOps Engineer",
     "summary": "Infrastructure engineer. AWS, K8s, Terraform at {name}."},
    {"platform": "X (Twitter)", "profile": f"https://x.com/{'{domain_slug}'}_careers",
     "name": f"{'{name}'} Careers", "role": "Corporate Account",
     "summary": "Open positions: Senior Cloud Security Engineer, Incident Responder, Red Team Lead."},
    {"platform": "X (Twitter)", "profile": f"https://x.com/{'{domain_slug}'}_status",
     "name": f"{'{name}'} Status", "role": "Service Status",
     "summary": "Recent posts: 'Investigating VPN connectivity issue', 'AWS us-east-1 incident affecting portal'."},
    {"platform": "LinkedIn", "profile": f"https://linkedin.com/in/alice-johnson-{'{hash}'}",
     "name": "Alice Johnson", "role": "Security Analyst (L3)",
     "summary": "Senior analyst at {name}. Detected and responded to 50+ incidents YTD."},
    {"platform": "Glassdoor", "profile": f"https://glassdoor.com/Reviews/{'{domain_slug}'}",
     "name": f"{'{name}'} Reviews", "role": "Employee Reviews",
     "summary": "3.8 rating. 'Good culture, understaffed SOC', 'legacy infrastructure slowing us down'."},
]

MOCK_DARKWEB_RESULTS = [
    {"source": "Ahmia (Tor)", "paste_url": f"http://ahmia7six6.onion/paste/{'{hash}'}",
     "title": "Leaked Database — {name} Users",
     "content": f"Excerpt: admin@{'{domain}'} / Password_S3ason@2026! / Role: Administrator",
     "credential_count": random.randint(500, 5000),
     "contains_credentials": True,
     "snippet": f"Database dump from {name} containing email:password pairs. Many appear to be admin/staff credentials."},
    {"source": "Ransomware Blog (Tor)", "paste_url": f"http://ransomblog.onion/post/{'{hash}'}",
     "title": f"{'{name}'} Added to Ransomware Leak Site",
     "content": f"{name} has been listed on the LockBit leak site. Threat actors claim 1.2TB of data exfiltrated.",
     "credential_count": 0,
     "contains_credentials": False,
     "snippet": f"Ransomware group claims breach of {name}. Deadline for ransom: 7 days from publication."},
    {"source": "Telegram Channel (Criminal)", "paste_url": f"https://t.me/leakdb/status/{'{hash}'}",
     "title": f"Credentials for {'{domain}'} VPN Access",
     "content": f"openvpn@{'{domain}'} / 2026_VPN_Access!@{'{hash}'[:8]}",
     "credential_count": random.randint(1, 50),
     "contains_credentials": True,
     "snippet": f"VPN credentials for {name} being traded in Telegram channel with 45K subscribers."},
    {"source": "Dark Web Forum (Tor)", "paste_url": f"http://breachforu.onion/thread/{'{hash}'}",
     "title": f"Discussion: Targeting {name} Infrastructure",
     "content": "Initial access broker offering RDP access to {name} for 3 BTC. Described as 'domain admin ready'.",
     "credential_count": 0,
     "contains_credentials": False,
     "snippet": f"Threat actors discussing attack plans against {name}. RDP access being sold on the forum."},
    {"source": "Pastebin (Dark Copy)", "paste_url": f"https://pastebin.com/raw/{'{hash}'}",
     "title": f"{name} Employee Credentials Dump",
     "content": f"hr@{'{domain}'} / HR_P@ss123! | it@{'{domain}'} / IT_Admin@2026!",
     "credential_count": random.randint(200, 2000),
     "contains_credentials": True,
     "snippet": f"Large credential dump for {name} employees. Emails and plaintext passwords."},
    {"source": "ZeroDay Forums (Tor)", "paste_url": f"http://0dayforum.onion/thread/{'{hash}'}",
     "title": f"{name} — Zero-Day Access",
     "content": f"Selling unpatched RCE in {name}'s custom web application. Price: $50K. Exploit works against all instances.",
     "credential_count": 0,
     "contains_credentials": False,
     "snippet": f"Zero-day exploit being advertised targeting a custom application used by {name}."},
]

# ═══════════════════════════════════════════════════════════════════════════════
# CrewAI Tools for each agent
# ═══════════════════════════════════════════════════════════════════════════════


@tool("Clear Web Dork Search")
def clear_web_dork(target: str) -> str:
    """Search public web via Google Dorks for exposed documents, financial records, and infrastructure of a target domain. Input: target company name or domain."""
    research_id = _current_research_id()
    company = _resolve_company(target)
    name = company["name"]
    domain = company["domain"]
    results = []
    for dork in MOCK_DORK_RESULTS:
        h = hashlib.md5(f"{name}{domain}{dork['title']}".encode()).hexdigest()[:8]
        results.append({
            "dork_title": dork["title"].format(name=name, domain=domain),
            "url": dork["url"].format(domain=domain),
            "snippet": dork["snippet"].format(name=name, domain=domain, company_keyword=name.split()[0].lower()[:8]),
        })
    _store_finding(research_id, "clear_web", {"results": results, "total": len(results)})
    return json.dumps({"agent": "clear_web", "findings": results, "total": len(results), "target": target}, indent=2)


@tool("Social Media Research")
def social_media_research(target: str) -> str:
    """Scan LinkedIn, X (Twitter), and Glassdoor for employee profiles, sentiment, and organizational structure. Input: target company name."""
    research_id = _current_research_id()
    company = _resolve_company(target)
    name = company["name"]
    domain = company["domain"]
    domain_slug = domain.split(".")[0]
    results = []
    for entry in MOCK_SOCIAL_RESULTS:
        h = hashlib.md5(f"{name}{entry['profile']}".encode()).hexdigest()[:8]
        results.append({
            "platform": entry["platform"],
            "profile_url": entry["profile"].format(hash=h),
            "name": entry["name"],
            "role": entry["role"],
            "summary": entry["summary"].format(name=name, hash=h, domain_slug=domain_slug),
        })
    _store_finding(research_id, "social_media", {"results": results, "total": len(results)})
    return json.dumps({"agent": "social_media", "findings": results, "total": len(results), "target": target}, indent=2)


@tool("Dark Web Intelligence")
def dark_web_intel(target: str) -> str:
    """Query Ahmia (Tor), ransomware blogs, Telegram criminal channels, and dark web forums for leaked credentials, database dumps, and ransomware mentions. Input: target company name or domain."""
    research_id = _current_research_id()
    company = _resolve_company(target)
    name = company["name"]
    domain = company["domain"]
    results = []
    for entry in MOCK_DARKWEB_RESULTS:
        h = hashlib.md5(f"{name}{entry['title']}".encode()).hexdigest()[:8]
        results.append({
            "source": entry["source"],
            "paste_url": entry["paste_url"].format(hash=h),
            "title": entry["title"].format(name=name, domain=domain, hash=h),
            "snippet": entry["snippet"].format(name=name, domain=domain, hash=h),
            "contains_credentials": entry["contains_credentials"],
            "credential_count": entry["credential_count"],
        })
    _store_finding(research_id, "dark_web", {"results": results, "total": len(results)})
    return json.dumps({"agent": "dark_web", "findings": results, "total": len(results), "target": target}, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# Research ID context (thread-local) — set before each CrewAI kickoff
# ═══════════════════════════════════════════════════════════════════════════════

_thread_local = threading.local()


def _current_research_id() -> str:
    return getattr(_thread_local, "research_id", "unknown")


def _set_research_id(research_id: str) -> None:
    _thread_local.research_id = research_id


# ═══════════════════════════════════════════════════════════════════════════════
# Resolve target name to company profile
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_company(target: str) -> dict[str, Any]:
    target_lower = target.lower().replace(" ", "").replace(".com", "").replace(".io", "")
    for key, company in MOCK_COMPANIES.items():
        if key in target_lower:
            return company
        if company["domain"].split(".")[0] in target_lower:
            return company
        if company["name"].lower().replace(" ", "") in target_lower:
            return company
    return {
        "name": target.title(),
        "domain": f"{target.lower().replace(' ', '')}.com",
        "industry": "technology",
        "employees": random.randint(100, 1000),
        "revenue_m": random.randint(10, 500),
        "hq": "Unknown",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CrewAI Agents
# ═══════════════════════════════════════════════════════════════════════════════

clear_web_agent = Agent(
    role="Clear Web OSINT Agent",
    goal=(
        "Use Google Dorks and public search engines to find exposed documents, "
        "financial filings, infrastructure details, and job postings about a target."
    ),
    backstory=(
        "You are an expert OSINT researcher specializing in open-source intelligence "
        "gathering from the public web. You craft Google Dork queries to uncover "
        "exposed documents, S3 buckets, Jenkins instances, Confluence pages, and "
        "SEC filings. You never miss a publicly exposed asset."
    ),
    verbose=True,
    allow_delegation=False,
    llm=fast_triage_llm,
    tools=[clear_web_dork],
)

social_media_agent = Agent(
    role="Social Media Intelligence Agent",
    goal=(
        "Scan LinkedIn, X (Twitter), and Glassdoor for employee profiles, "
        "organizational structure, sentiment analysis, and posted complaints "
        "that could indicate insider risk or technical debt."
    ),
    backstory=(
        "You are a social media intelligence specialist. You scrape LinkedIn for "
        "employee names, roles, and connections. You monitor X/Twitter for status "
        "updates and complaints. You use Glassdoor reviews to detect potential "
        "insider threats and organizational weaknesses."
    ),
    verbose=True,
    allow_delegation=False,
    llm=fast_triage_llm,
    tools=[social_media_research],
)

dark_web_agent = Agent(
    role="Dark Web Intelligence Agent",
    goal=(
        "Search Ahmia, Tor ransomware blogs, Telegram criminal channels, and "
        "dark web forums for leaked credentials, database dumps, IAB listings, "
        "and ransomware mentions related to the target."
    ),
    backstory=(
        "You are a dark web intelligence operative. You navigate Tor hidden services, "
        "monitor ransomware leak sites, infiltrate Telegram crime channels, and "
        "track credential dumps on paste sites. You find what the company doesn't "
        "know is already public."
    ),
    verbose=True,
    allow_delegation=False,
    llm=coder_llm,
    tools=[dark_web_intel],
)

reasoning_agent = Agent(
    role="OSINT Reasoning & Correlation Agent",
    goal=(
        "Collect all findings from Clear Web, Social Media, and Dark Web agents. "
        "Remove false positives (name collisions with other companies). Identify "
        "credential overlaps and shared infrastructure. Compile a final OSINT "
        "Intelligence Report with risk scoring and actionable recommendations."
    ),
    backstory=(
        "You are the lead intelligence analyst. You receive raw data from three "
        "specialized OSINT agents. Your job is to: (1) deduplicate and remove "
        "false positives caused by same-name companies or individuals, "
        "(2) correlate findings across sources (e.g., a leaked password on the "
        "dark web matches a LinkedIn employee name), (3) assign severity levels "
        "to each finding, and (4) compile the final OSINT Intelligence Report. "
        "Every false positive you miss wastes the SOC team's time."
    ),
    verbose=True,
    allow_delegation=False,
    llm=master_brain_llm,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Tasks
# ═══════════════════════════════════════════════════════════════════════════════

t_clear_web = Task(
    description=(
        "Use the Clear Web Dork Search tool to find public information about "
        "the target company or domain: {{target}}. "
        "Focus on exposed documents, financial filings, infrastructure, and job postings."
    ),
    expected_output="JSON list of dork findings with titles, URLs, and snippets.",
    agent=clear_web_agent,
    tools=[clear_web_dork],
)

t_social_media = Task(
    description=(
        "Use the Social Media Research tool to find employee profiles, org "
        "structure, sentiment, and complaints about {{target}}. "
        "Focus on LinkedIn, X/Twitter, and Glassdoor."
    ),
    expected_output="JSON list of social media findings with platform, profile URLs, and extracted intelligence.",
    agent=social_media_agent,
    tools=[social_media_research],
)

t_dark_web = Task(
    description=(
        "Use the Dark Web Intelligence tool to search for leaked credentials, "
        "database dumps, IAB listings, and ransomware mentions for {{target}}. "
        "Focus on Ahmia, ransomware blogs, Telegram, and dark web forums."
    ),
    expected_output="JSON list of dark web findings with source, URLs, credential info, and risk assessment.",
    agent=dark_web_agent,
    tools=[dark_web_intel],
)

t_reasoning = Task(
    description=(
        "You have received raw intelligence from three OSINT agents about {{target}}. "
        "Now perform the following:\n"
        "1. Read all findings from memory.\n"
        "2. Remove false positives (companies with similar names, known name collisions).\n"
        "3. Cross-correlate: e.g., if a leaked dark web credential matches a LinkedIn employee name, flag that as HIGH priority.\n"
        "4. Assign severity (CRITICAL / HIGH / MEDIUM / LOW) to each finding.\n"
        "5. Compile a final OSINT Intelligence Report as valid JSON with the structure:\n"
        "{\n"
        '  "target": "company name",\n'
        '  "target_domain": "domain.com",\n'
        '  "risk_score": 0-100,\n'
        '  "risk_level": "low|medium|high|critical",\n'
        '  "summary": "executive summary paragraph",\n'
        '  "sources_analyzed": 3,\n'
        '  "total_findings": number,\n'
        '  "false_positives_removed": number,\n'
        '  "credentials_exposed": number,\n'
        '  "credentials_at_risk": boolean,\n'
        '  "ransomware_mentions": boolean,\n'
        '  "zero_day_discussions": boolean,\n'
        '  "top_risks": [{"risk": "description", "severity": "CRITICAL|HIGH|MEDIUM|LOW", "source": "clear_web|social_media|dark_web"}],\n'
        '  "recommendations": ["action1", "action2"],\n'
        '  "dark_web_intel_summary": "what was found on dark web",\n'
        '  "clear_web_exposures": ["exposure1", "exposure2"],\n'
        '  "social_media_insights": ["insight1", "insight2"]\n'
        "}\n"
        "Output ONLY the JSON — no markdown, no explanation."
    ),
    expected_output="Valid JSON OSINT Intelligence Report.",
    agent=reasoning_agent,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Crew
# ═══════════════════════════════════════════════════════════════════════════════

osint_crew = Crew(
    agents=[clear_web_agent, social_media_agent, dark_web_agent, reasoning_agent],
    tasks=[t_clear_web, t_social_media, t_dark_web, t_reasoning],
    process=Process.sequential,
    verbose=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Public API — run the OSINT swarm
# ═══════════════════════════════════════════════════════════════════════════════

def run_deep_research(target_name: str, target_domain: str) -> dict[str, Any]:
    """
    Execute the full OSINT swarm pipeline:
      1. Generate a unique research ID.
      2. Run the 4-agent Crew sequentially.
      3. Parse the Reasoning Agent's JSON report.
      4. Store the report in the RAG vector store under "external_threat_intel".
      5. Return the final report.
    """
    research_id = f"OSINT-{hashlib.md5(f'{target_name}{target_domain}{datetime.now(timezone.utc).isoformat()}'.encode()).hexdigest()[:8].upper()}"
    _set_research_id(research_id)

    logger.info("OSINT Swarm: starting deep research '%s' — %s (%s)", research_id, target_name, target_domain)

    try:
        result = osint_crew.kickoff(inputs={
            "target": f"{target_name} ({target_domain})",
        })

        raw = result.raw if hasattr(result, "raw") else str(result)
        report = _parse_report(raw, target_name, target_domain)

    except Exception as exc:
        logger.exception("OSINT Swarm CrewAI failed: %s", exc)
        report = _generate_fallback_report(target_name, target_domain, str(exc))

    # Store findings and report
    _store_report(research_id, report)

    # Embed into RAG vector store
    try:
        from rag.vector_store import get_vector_store
        store = get_vector_store()
        doc_id = f"osint-{research_id.lower()}"
        content = json.dumps(report, indent=2)
        store.insert("external_threat_intel", doc_id, content, {
            "research_id": research_id,
            "target_name": target_name,
            "target_domain": target_domain,
            "risk_score": report.get("risk_score", 0),
            "risk_level": report.get("risk_level", "medium"),
            "credentials_exposed": report.get("credentials_exposed", 0),
            "ransomware_mentions": report.get("ransomware_mentions", False),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("OSINT Swarm: report '%s' stored in RAG external_threat_intel", doc_id)
    except Exception as exc:
        logger.warning("OSINT Swarm: RAG storage failed: %s", exc)

    report["research_id"] = research_id
    report["target_name"] = target_name
    report["target_domain"] = target_domain
    return report


def _parse_report(raw: str, target_name: str, target_domain: str) -> dict[str, Any]:
    """Extract JSON from the LLM output, handling markdown fences."""
    if not raw:
        return _generate_fallback_report(target_name, target_domain, "empty LLM output")
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        pass
    return _generate_fallback_report(target_name, target_domain, "parse error")


def _generate_fallback_report(target_name: str, target_domain: str, reason: str) -> dict[str, Any]:
    """Generate a mock OSINT report when CrewAI or parsing fails."""
    logger.warning("OSINT Swarm: using fallback report for %s (%s)", target_name, reason)
    company = _resolve_company(target_name)
    findings = _get_findings(_current_research_id()) if _current_research_id() != "unknown" else {}
    return {
        "target": company["name"],
        "target_domain": company["domain"],
        "risk_score": random.randint(40, 85),
        "risk_level": "medium",
        "summary": f"OSINT assessment for {company['name']}. "
                    f"Found exposed infrastructure, employee profiles, and potential dark web mentions. "
                    f"Fallback reason: {reason}",
        "sources_analyzed": 3,
        "total_findings": 12,
        "false_positives_removed": 2,
        "credentials_exposed": random.randint(50, 500),
        "credentials_at_risk": True,
        "ransomware_mentions": random.choice([True, False]),
        "zero_day_discussions": random.choice([True, False]),
        "top_risks": [
            {"risk": "Open S3 bucket with database backups exposed", "severity": "CRITICAL", "source": "clear_web"},
            {"risk": "VPN credentials found on Telegram criminal channel", "severity": "CRITICAL", "source": "dark_web"},
            {"risk": "SOC team reportedly understaffed (Glassdoor reviews)", "severity": "MEDIUM", "source": "social_media"},
        ],
        "recommendations": [
            "Immediately secure exposed S3 bucket and rotate all database credentials",
            "Enforce MFA on all VPN accounts and rotate existing credentials",
            "Conduct phishing simulation targeting employees whose credentials were found on dark web",
            "Review and restrict public-facing Confluence and Jenkins instances",
        ],
        "dark_web_intel_summary": "Multiple credential dumps and an IAB listing found. VPN credentials being traded on Telegram. Ransomware group may have exfiltrated data.",
        "clear_web_exposures": [
            f"Public Confluence wiki at https://confluence.{company['domain']} with network diagrams",
            f"Open S3 bucket at {company['domain']}-backup.s3.amazonaws.com containing DB backups",
            f"Jenkins CI at https://jenkins.{company['domain']} accessible without authentication",
        ],
        "social_media_insights": [
            f"SOC team lead (Jane Smith) publicly identified — potential phishing target",
            "Glassdoor reviews suggest understaffed security team",
            "Open roles for Senior Cloud Security Engineer indicate possible turnover",
        ],
    }


def get_research_status(research_id: str) -> dict[str, Any]:
    """Get the status of a research task."""
    return _get_research_status(research_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Dark Web Live Feed — mock real-time paste alerts
# ═══════════════════════════════════════════════════════════════════════════════

PASTE_TEMPLATES = [
    "🔴 New paste on Ahmia: {target_domain} user database — {count} credentials leaked",
    "🟠 Telegram channel 'LeakDB' posted {target_domain} VPN credentials ({count} entries)",
    "🔴 Ransomware blog: '{name}' listed — {count}GB data exfiltrated",
    "🟡 Dark web forum thread: 'Selling RDP access to {name} — domain admin'",
    "🟢 Pastebin: {target_domain} employee list published — {count} names with roles",
    "🔴 ZeroDay forum: {name} custom app exploit (RCE) for sale — ${price}K",
    "🟠 Telegram: {name} internal credentials being auctioned — starting at 0.5 BTC",
    "🟡 New Ahmia paste: {target_domain} — database_config.yml with passwords",
    "🔴 Ransomware group 'LockBit' claims {name} breach — negotiating ransom",
    "🟢 Pastebin: {target_domain} — AWS keys (AKIA*) found in public paste",
]


async def stream_dark_web_feeds(target_domain: str = "") -> list[dict[str, Any]]:
    """Generate a burst of mock dark web paste alerts for a given target domain."""
    name = target_domain.split(".")[0].title() if target_domain else "Unknown"
    count = random.randint(50, 5000)
    price = random.randint(10, 200)
    alerts = []
    for idx, template in enumerate(PASTE_TEMPLATES):
        alerts.append({
            "id": f"DW-{hashlib.md5(f'{target_domain}{idx}{datetime.now(timezone.utc).isoformat()}'.encode()).hexdigest()[:8].upper()}",
            "message": template.format(target_domain=target_domain, name=name, count=count, price=price),
            "source": template.split(":")[0].lstrip("🔴🟠🟡🟢"),
            "severity": "critical" if "🔴" in template else "high" if "🟠" in template else "medium" if "🟡" in template else "low",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    return alerts
