"""
Security & Pentest tools — ethical hacking only.
All tools require explicit user approval (configured in security.require_approval).
"""

import subprocess
import socket
import re
import requests
from agent.toolregistry import noetix_tool

DISCLAIMER = "[ETHICAL USE ONLY] Ensure you have authorization before scanning any target.\n\n"


@noetix_tool(
    name="nmap_scan",
    description="Run nmap port scan on a target host. REQUIRES authorization. Ethical use only.",
    parameters={
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "IP address or hostname to scan"},
            "ports": {"type": "string", "description": "Port range (e.g. '1-1000', '22,80,443', 'top100')", "default": "top100"},
            "scan_type": {"type": "string", "enum": ["syn", "connect", "udp", "version"], "default": "connect"},
            "extra_flags": {"type": "string", "description": "Additional nmap flags", "default": ""},
        },
        "required": ["target"],
    },
    tags=["pentest", "security"],
)
def nmap_scan(target: str, ports: str = "top100", scan_type: str = "connect", extra_flags: str = ""):
    type_flags = {"syn": "-sS", "connect": "-sT", "udp": "-sU", "version": "-sV"}
    scan_flag = type_flags.get(scan_type, "-sT")
    port_flag = f"--top-ports 100" if ports == "top100" else f"-p {ports}"
    cmd = f"nmap {scan_flag} {port_flag} {extra_flags} {target}"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return DISCLAIMER + (result.stdout or result.stderr)
    except subprocess.TimeoutExpired:
        return "Scan timed out after 120s"
    except Exception as e:
        return f"nmap error: {e}"


@noetix_tool(
    name="whois_lookup",
    description="WHOIS lookup for domain or IP. Useful for recon.",
    parameters={
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "Domain or IP address"},
        },
        "required": ["target"],
    },
    tags=["pentest", "security", "research"],
)
def whois_lookup(target: str):
    try:
        result = subprocess.run(f"whois {target}", shell=True, capture_output=True, text=True, timeout=15)
        return result.stdout[:5000] or result.stderr
    except Exception as e:
        return f"whois error: {e}"


@noetix_tool(
    name="subdomain_enum",
    description="Enumerate subdomains of a domain using passive methods (crt.sh, DNS brute).",
    parameters={
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Target domain (e.g. example.com)"},
            "method": {"type": "string", "enum": ["crtsh", "dns_brute", "both"], "default": "crtsh"},
        },
        "required": ["domain"],
    },
    tags=["pentest", "security"],
)
def subdomain_enum(domain: str, method: str = "crtsh"):
    results = []

    if method in ("crtsh", "both"):
        try:
            resp = requests.get(
                f"https://crt.sh/?q=%.{domain}&output=json",
                timeout=15,
                headers={"User-Agent": "NoetixAgent/1.0"},
            )
            entries = resp.json()
            subs = set()
            for e in entries:
                name = e.get("name_value", "")
                for s in name.split("\n"):
                    s = s.strip().lstrip("*.")
                    if s.endswith(domain):
                        subs.add(s)
            results.extend(sorted(subs))
        except Exception as e:
            results.append(f"crt.sh error: {e}")

    if method in ("dns_brute", "both"):
        common = ["www", "mail", "ftp", "api", "dev", "staging", "admin", "vpn", "portal", "app"]
        for sub in common:
            try:
                host = f"{sub}.{domain}"
                socket.gethostbyname(host)
                results.append(host)
            except:
                pass

    return DISCLAIMER + "\n".join(results) if results else "No subdomains found."


@noetix_tool(
    name="http_probe",
    description="Probe an HTTP/HTTPS target for headers, tech stack, and basic info.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target URL"},
            "follow_redirects": {"type": "boolean", "default": True},
        },
        "required": ["url"],
    },
    tags=["pentest", "security"],
)
def http_probe(url: str, follow_redirects: bool = True):
    try:
        resp = requests.get(
            url,
            timeout=10,
            allow_redirects=follow_redirects,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        headers = dict(resp.headers)
        tech = []
        server = headers.get("Server", "")
        powered_by = headers.get("X-Powered-By", "")
        if server:
            tech.append(f"Server: {server}")
        if powered_by:
            tech.append(f"X-Powered-By: {powered_by}")

        return DISCLAIMER + f"""URL: {resp.url}
Status: {resp.status_code}
Tech: {', '.join(tech) or 'unknown'}
Content-Type: {headers.get('Content-Type', '')}
Security Headers:
  - X-Frame-Options: {headers.get('X-Frame-Options', 'MISSING')}
  - X-XSS-Protection: {headers.get('X-XSS-Protection', 'MISSING')}
  - Content-Security-Policy: {headers.get('Content-Security-Policy', 'MISSING')[:100]}
  - Strict-Transport-Security: {headers.get('Strict-Transport-Security', 'MISSING')}
  - X-Content-Type-Options: {headers.get('X-Content-Type-Options', 'MISSING')}
Body preview: {resp.text[:500]}"""
    except Exception as e:
        return f"Probe error: {e}"


@noetix_tool(
    name="exploit_search",
    description="Search Exploit-DB and CVE databases for known vulnerabilities.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term (e.g. 'Apache 2.4', 'CVE-2021-44228')"},
        },
        "required": ["query"],
    },
    tags=["pentest", "security"],
)
def exploit_search(query: str):
    results = []

    # Try searchsploit (Kali tool)
    try:
        r = subprocess.run(f"searchsploit {query}", shell=True, capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout:
            results.append("=== Exploit-DB (searchsploit) ===\n" + r.stdout[:3000])
    except:
        pass

    # Fallback: query nvd.nist.gov
    if not results:
        try:
            resp = requests.get(
                "https://services.nvd.nist.gov/rest/json/cves/2.0",
                params={"keywordSearch": query, "resultsPerPage": 5},
                timeout=10,
            )
            data = resp.json()
            vulns = data.get("vulnerabilities", [])
            if vulns:
                lines = [f"=== NVD CVE Results for '{query}' ==="]
                for v in vulns:
                    cve = v.get("cve", {})
                    cve_id = cve.get("id", "")
                    desc = cve.get("descriptions", [{}])[0].get("value", "")[:200]
                    lines.append(f"\n{cve_id}: {desc}")
                results.append("\n".join(lines))
        except Exception as e:
            results.append(f"NVD search error: {e}")

    return DISCLAIMER + ("\n\n".join(results) if results else "No exploits found.")
