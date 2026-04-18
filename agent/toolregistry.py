"""
NoetixAgent ToolRegistry — dynamic tool discovery + OpenAI function schema generation.
"""

import importlib
import inspect
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger("noetix.tools")


class Tool:
    def __init__(self, name: str, fn: Callable, description: str, parameters: Dict, tags: List[str] = None):
        self.name = name
        self.fn = fn
        self.description = description
        self.parameters = parameters
        self.tags = tags or []
        self.enabled = True

    def schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

    def call(self, args: Dict) -> Any:
        try:
            return self.fn(**args)
        except Exception as e:
            return f"Tool error ({self.name}): {e}"


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._profiles: Dict[str, List[str]] = {
            "coding": ["bash", "read_file", "write_file", "git_cmd", "code_search"],
            "research": ["search_web", "fetch_url", "read_file", "write_file"],
            "pentest": ["bash", "nmap_scan", "whois_lookup", "subdomain_enum", "http_probe", "exploit_search"],
            "automation": ["bash", "http_request", "read_file", "write_file", "file_watch"],
            "full": None,  # all tools
        }
        self._active_tags: Optional[List[str]] = None  # None = all

    def register(self, tool: Tool):
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def auto_discover(self, directory: Path):
        """Scan directory for Python files with @noetix_tool decorated functions."""
        if not directory.exists():
            return
        for pyfile in directory.glob("*.py"):
            if pyfile.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(pyfile.stem, pyfile)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if callable(attr) and hasattr(attr, "_noetix_tool"):
                        self.register(attr._noetix_tool)
            except Exception as e:
                logger.warning(f"Failed to load {pyfile}: {e}")

    def apply_profile(self, profile: str):
        """Enable only tools matching profile."""
        allowed = self._profiles.get(profile)
        if allowed is None:
            # 'full' — enable all
            for t in self._tools.values():
                t.enabled = True
            self._active_tags = None
        else:
            for name, t in self._tools.items():
                t.enabled = name in allowed
            self._active_tags = allowed

    def call(self, name: str, args: Dict) -> Any:
        tool = self._tools.get(name)
        if not tool:
            return f"Unknown tool: {name}"
        if not tool.enabled:
            return f"Tool {name} is not enabled in current toolset."
        return tool.call(args)

    def get_schemas(self) -> List[Dict]:
        return [t.schema() for t in self._tools.values() if t.enabled]

    def list_active(self) -> List[str]:
        return [name for name, t in self._tools.items() if t.enabled]

    def list_all(self) -> List[str]:
        return list(self._tools.keys())


def noetix_tool(name: str, description: str, parameters: Dict, tags: List[str] = None):
    """Decorator to register a function as a NoetixAgent tool."""
    def decorator(fn: Callable) -> Callable:
        tool = Tool(name=name, fn=fn, description=description, parameters=parameters, tags=tags or [])
        fn._noetix_tool = tool
        return fn
    return decorator
