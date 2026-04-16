"""
Coding tools: git, code search, linting, language runners.
"""

import subprocess
import os
from pathlib import Path
from agent.toolregistry import noetix_tool


@noetix_tool(
    name="git_cmd",
    description="Run git commands (status, diff, log, commit, etc.).",
    parameters={
        "type": "object",
        "properties": {
            "args": {"type": "string", "description": "Git arguments (e.g. 'status', 'log --oneline -10', 'diff HEAD')"},
            "cwd": {"type": "string", "description": "Repository directory"},
        },
        "required": ["args"],
    },
    tags=["coding"],
)
def git_cmd(args: str, cwd: str = None):
    try:
        result = subprocess.run(
            f"git {args}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd or os.getcwd(),
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Git error: {e}"


@noetix_tool(
    name="code_search",
    description="Search for patterns in code files (like grep for code).",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Search pattern (regex or text)"},
            "path": {"type": "string", "description": "Directory or file to search"},
            "file_type": {"type": "string", "description": "File extension filter (e.g. '.py', '.js')"},
            "case_sensitive": {"type": "boolean", "default": False},
        },
        "required": ["pattern", "path"],
    },
    tags=["coding"],
)
def code_search(pattern: str, path: str, file_type: str = None, case_sensitive: bool = False):
    try:
        flags = "" if case_sensitive else "-i"
        include = f"--include='*{file_type}'" if file_type else ""
        cmd = f"grep -r {flags} {include} -n '{pattern}' {path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return result.stdout[:5000] or "(no matches)"
    except Exception as e:
        return f"Search error: {e}"


@noetix_tool(
    name="run_python",
    description="Run Python code snippet and return output.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"},
            "timeout": {"type": "integer", "default": 30},
        },
        "required": ["code"],
    },
    tags=["coding"],
)
def run_python(code: str, timeout: int = 30):
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        f.flush()
        try:
            result = subprocess.run(
                f"python3 {f.name}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout + (("\n" + result.stderr) if result.stderr else "")
        except subprocess.TimeoutExpired:
            return f"Timed out after {timeout}s"
        except Exception as e:
            return f"Error: {e}"
        finally:
            os.unlink(f.name)


@noetix_tool(
    name="lint_code",
    description="Lint Python code with ruff or pylint. Returns warnings/errors.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File or directory to lint"},
            "linter": {"type": "string", "enum": ["ruff", "pylint", "auto"], "default": "auto"},
        },
        "required": ["path"],
    },
    tags=["coding"],
)
def lint_code(path: str, linter: str = "auto"):
    # Try ruff first (faster), fallback pylint
    tools = ["ruff", "pylint"] if linter == "auto" else [linter]
    for tool in tools:
        result = subprocess.run(f"{tool} {path}", shell=True, capture_output=True, text=True, timeout=20)
        if result.returncode != 127:  # 127 = not found
            return result.stdout + result.stderr
    return "No linter found. Install ruff: pip install ruff"


@noetix_tool(
    name="create_project",
    description="Scaffold a new project (Python, Node.js, or shell script).",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Project name"},
            "type": {"type": "string", "enum": ["python", "node", "shell"], "description": "Project type"},
            "path": {"type": "string", "description": "Where to create the project"},
        },
        "required": ["name", "type"],
    },
    tags=["coding", "automation"],
)
def create_project(name: str, type: str, path: str = "."):
    base = Path(path).expanduser() / name
    base.mkdir(parents=True, exist_ok=True)

    if type == "python":
        (base / "main.py").write_text('"""Main entry point."""\n\ndef main():\n    print("Hello from " + __name__)\n\nif __name__ == "__main__":\n    main()\n')
        (base / "requirements.txt").write_text("# Add dependencies here\n")
        (base / "README.md").write_text(f"# {name}\n\n## Install\n\n```bash\npip install -r requirements.txt\n```\n")
        (base / ".gitignore").write_text("__pycache__/\n*.pyc\n.env\nvenv/\n")
    elif type == "node":
        import json as json_lib
        pkg = {"name": name, "version": "1.0.0", "main": "index.js", "scripts": {"start": "node index.js"}}
        (base / "package.json").write_text(json_lib.dumps(pkg, indent=2))
        (base / "index.js").write_text("// Entry point\nconsole.log('Hello from ' + require('./package.json').name);\n")
        (base / ".gitignore").write_text("node_modules/\n.env\n")
    elif type == "shell":
        script = base / "run.sh"
        script.write_text(f"#!/bin/bash\n# {name}\nset -e\n\necho 'Starting {name}'\n")
        script.chmod(0o755)

    return f"Project '{name}' ({type}) created at {base}"
