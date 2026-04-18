"""
Core tools: bash execution, file I/O, web search, HTTP.
"""

import subprocess
import os
import requests
from pathlib import Path
from agent.toolregistry import noetix_tool


@noetix_tool(
    name="bash",
    description="Execute a bash/shell command. Use for system tasks, scripts, automation, compilation, running code, etc.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to run"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)", "default": 30},
            "cwd": {"type": "string", "description": "Working directory (optional)"},
        },
        "required": ["command"],
    },
    tags=["core", "coding", "automation", "pentest"],
)
def bash(command: str, timeout: int = 30, cwd: str = None):
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or os.getcwd(),
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        if result.returncode != 0 and not output:
            return f"Exit {result.returncode}: {error}"
        return output + ("\n" + error if error else "")
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"


@noetix_tool(
    name="read_file",
    description="Read contents of a file from disk.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to read"},
            "max_bytes": {"type": "integer", "description": "Max bytes to read (default 50000)"},
        },
        "required": ["path"],
    },
    tags=["core", "coding", "research"],
)
def read_file(path: str, max_bytes: int = 50000):
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"File not found: {path}"
        content = p.read_bytes()[:max_bytes]
        return content.decode("utf-8", errors="replace")
    except Exception as e:
        return f"Error reading {path}: {e}"


@noetix_tool(
    name="write_file",
    description="Write or append content to a file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to write"},
            "content": {"type": "string", "description": "Content to write"},
            "mode": {"type": "string", "enum": ["write", "append"], "default": "write"},
        },
        "required": ["path", "content"],
    },
    tags=["core", "coding", "automation"],
)
def write_file(path: str, content: str, mode: str = "write"):
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        flag = "w" if mode == "write" else "a"
        p.write_text(content) if flag == "w" else p.open("a").write(content)
        return f"Written {len(content)} chars to {path}"
    except Exception as e:
        return f"Error writing {path}: {e}"


@noetix_tool(
    name="fetch_url",
    description="Fetch content from a URL. For research, scraping, API calls.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
            "headers": {"type": "object", "description": "HTTP headers (optional)"},
            "body": {"type": "string", "description": "Request body (for POST/PUT)"},
            "timeout": {"type": "integer", "default": 15},
        },
        "required": ["url"],
    },
    tags=["core", "research", "automation", "pentest"],
)
def fetch_url(url: str, method: str = "GET", headers: dict = None, body: str = None, timeout: int = 15):
    try:
        resp = requests.request(
            method=method,
            url=url,
            headers=headers or {},
            data=body,
            timeout=timeout,
        )
        return f"HTTP {resp.status_code}\n{resp.text[:10000]}"
    except Exception as e:
        return f"Request error: {e}"


@noetix_tool(
    name="search_web",
    description="Search the web using DuckDuckGo (no API key required).",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
    tags=["research", "core"],
)
def search_web(query: str, max_results: int = 5):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        lines = []
        for r in results:
            lines.append(f"**{r.get('title', '')}**\n{r.get('href', '')}\n{r.get('body', '')}\n")
        return "\n".join(lines)
    except ImportError:
        # Fallback: use requests to scrape DDG HTML
        try:
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            return resp.text[:5000]
        except Exception as e:
            return f"Search error: {e}"


@noetix_tool(
    name="list_dir",
    description="List files and directories at a path.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path"},
            "recursive": {"type": "boolean", "default": False},
        },
        "required": ["path"],
    },
    tags=["core", "coding"],
)
def list_dir(path: str, recursive: bool = False):
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return f"Path not found: {path}"
        if recursive:
            items = sorted(str(x.relative_to(p)) for x in p.rglob("*") if not x.name.startswith("."))
        else:
            items = sorted(x.name + ("/" if x.is_dir() else "") for x in p.iterdir())
        return "\n".join(items) or "(empty)"
    except Exception as e:
        return f"Error: {e}"
