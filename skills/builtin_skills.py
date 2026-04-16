"""
NoetixAgent Skills — reusable skill templates.
Skills are named task templates the agent can invoke.
"""

from agent.toolregistry import noetix_tool


@noetix_tool(
    name="code_review",
    description="Perform a thorough code review on a file or directory.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File or directory path to review"},
            "focus": {"type": "string", "description": "Focus area: security|performance|style|all", "default": "all"},
        },
        "required": ["path"],
    },
    tags=["coding", "security"],
)
def code_review(path: str, focus: str = "all"):
    import subprocess
    from pathlib import Path
    p = Path(path).expanduser()
    if not p.exists():
        return f"Path not found: {path}"
    # Read file(s)
    if p.is_file():
        content = p.read_text(errors="replace")[:10000]
        return f"[Code Review Request]\nPath: {path}\nFocus: {focus}\n\nContent:\n{content}\n\n[Agent will analyze this]"
    else:
        files = list(p.rglob("*.py"))[:10]
        summary = f"[Code Review: {path}]\nFiles found: {len(files)}\nFocus: {focus}\n\nFiles:\n"
        for f in files:
            summary += f"- {f.relative_to(p)}\n"
        return summary


@noetix_tool(
    name="research_topic",
    description="Deep research on a topic: search, fetch sources, and synthesize.",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Research topic"},
            "depth": {"type": "string", "enum": ["quick", "deep"], "default": "quick"},
            "output_file": {"type": "string", "description": "Optional file to save research to"},
        },
        "required": ["topic"],
    },
    tags=["research"],
)
def research_topic(topic: str, depth: str = "quick", output_file: str = None):
    return f"[Research Task]\nTopic: {topic}\nDepth: {depth}\nOutput: {output_file or 'none'}\n\nAgent will search and synthesize."


@noetix_tool(
    name="daily_report",
    description="Generate a daily summary report (system status, tasks, news).",
    parameters={
        "type": "object",
        "properties": {
            "sections": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Sections to include: system|tasks|news|weather",
                "default": ["system", "tasks"],
            }
        },
    },
    tags=["automation"],
)
def daily_report(sections: list = None):
    sections = sections or ["system", "tasks"]
    report = f"[Daily Report — {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}]\n"
    if "system" in sections:
        import subprocess
        uptime = subprocess.run("uptime", shell=True, capture_output=True, text=True).stdout.strip()
        report += f"\nSystem: {uptime}"
    if "tasks" in sections:
        report += "\nTasks: Check scheduled jobs with list_scheduled tool."
    return report
