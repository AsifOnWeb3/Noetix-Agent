"""
NoetixAgent Configuration — supports YAML config + env overrides.
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


DEFAULT_CONFIG = {
    "model": "openrouter:qwen/qwen3-coder:free",
    "provider": "openrouter",
    "api_key_env": "OPENROUTER_API_KEY",
    "base_url": "https://openrouter.ai/api/v1",
    "max_tokens": 4096,
    "temperature": 0.7,
    "memory_dir": "~/.noetix/memory",
    "skills_dir": "~/.noetix/skills",
    "workspace_dir": "~/.noetix/workspace",
    "log_level": "INFO",
    "toolsets": {
        "default": ["bash", "read_file", "write_file", "search_web", "memory"],
        "coding": ["bash", "read_file", "write_file", "git", "code_search", "linter"],
        "research": ["search_web", "fetch_url", "read_file", "write_file", "summarize"],
        "pentest": ["bash", "nmap_scan", "whois", "subdomain_enum", "http_probe", "exploit_search"],
        "automation": ["bash", "cron", "webhook", "file_watch", "http_request", "notify"],
        "full": ["*"],
    },
    "gateway": {
        "enabled": False,
        "port": 8765,
        "telegram": {"enabled": False, "bot_token": ""},
        "discord": {"enabled": False, "token": ""},
    },
    "memory": {
        "max_entries": 500,
        "auto_save": True,
        "search_enabled": True,
    },
    "security": {
        "require_approval": ["bash", "nmap_scan", "exploit_search"],
        "sandbox_mode": False,
        "allowed_domains": [],
    },
}


@dataclass
class AgentConfig:
    model: str = "openrouter:qwen/qwen3-coder:free"
    provider: str = "openrouter"
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    max_tokens: int = 4096
    temperature: float = 0.7
    memory_dir: Path = field(default_factory=lambda: Path.home() / ".noetix" / "memory")
    skills_dir: Path = field(default_factory=lambda: Path.home() / ".noetix" / "skills")
    workspace_dir: Path = field(default_factory=lambda: Path.home() / ".noetix" / "workspace")
    log_level: str = "INFO"
    toolsets: Dict[str, List[str]] = field(default_factory=lambda: DEFAULT_CONFIG["toolsets"])
    gateway: Dict[str, Any] = field(default_factory=lambda: DEFAULT_CONFIG["gateway"])
    memory_cfg: Dict[str, Any] = field(default_factory=lambda: DEFAULT_CONFIG["memory"])
    security: Dict[str, Any] = field(default_factory=lambda: DEFAULT_CONFIG["security"])
    active_toolset: str = "default"
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: str) -> "AgentConfig":
        path = Path(config_path).expanduser()
        data = dict(DEFAULT_CONFIG)

        if path.exists():
            with open(path) as f:
                user_cfg = yaml.safe_load(f) or {}
            data = cls._deep_merge(data, user_cfg)

        # Env overrides
        env_map = {
            "NOETIX_MODEL": "model",
            "NOETIX_PROVIDER": "provider",
            "NOETIX_BASE_URL": "base_url",
            "NOETIX_LOG_LEVEL": "log_level",
        }
        for env_key, cfg_key in env_map.items():
            if val := os.getenv(env_key):
                data[cfg_key] = val

        # Resolve API key from env
        api_key_env = data.get("api_key_env", "OPENROUTER_API_KEY")
        api_key = os.getenv(api_key_env) or os.getenv("NOETIX_API_KEY") or ""

        cfg = cls(
            model=data["model"],
            provider=data["provider"],
            api_key=api_key,
            base_url=data["base_url"],
            max_tokens=data["max_tokens"],
            temperature=data["temperature"],
            memory_dir=Path(data["memory_dir"]).expanduser(),
            skills_dir=Path(data["skills_dir"]).expanduser(),
            workspace_dir=Path(data["workspace_dir"]).expanduser(),
            log_level=data["log_level"],
            toolsets=data["toolsets"],
            gateway=data["gateway"],
            memory_cfg=data["memory"],
            security=data["security"],
            raw=data,
        )
        # Create dirs
        for d in [cfg.memory_dir, cfg.skills_dir, cfg.workspace_dir]:
            d.mkdir(parents=True, exist_ok=True)
        return cfg

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        result = dict(base)
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(result.get(k), dict):
                result[k] = AgentConfig._deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    def get_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        # Try common env names
        for env in ["OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "NOETIX_API_KEY"]:
            if val := os.getenv(env):
                return val
        raise ValueError("No API key found. Set OPENROUTER_API_KEY or NOETIX_API_KEY env var.")

    def provider_base_url(self) -> str:
        provider_urls = {
            "openrouter": "https://openrouter.ai/api/v1",
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com",
            "ollama": "http://localhost:11434/v1",
            "lmstudio": "http://localhost:1234/v1",
        }
        return self.base_url or provider_urls.get(self.provider, self.base_url)
