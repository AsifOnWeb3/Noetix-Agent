"""
NoetixAgent Core — Agent loop inspired by OpenClaw + Hermes patterns.
Supports: coding, automation, research, scheduling, pentesting/security tasks.
"""

import os
import json
import datetime
import importlib
from pathlib import Path
from typing import Optional

from agent.memory import MemoryManager
from agent.toolregistry import ToolRegistry
from agent.loop import AgentLoop
from agent.config import AgentConfig


def create_agent(config_path: Optional[str] = None) -> "AgentLoop":
    config = AgentConfig.load(config_path or str(Path.home() / ".noetix" / "config.yaml"))
    memory = MemoryManager(config.memory_dir)
    tools = ToolRegistry()
    tools.auto_discover(Path(__file__).parent.parent / "tools")
    tools.auto_discover(Path(__file__).parent.parent / "skills")
    return AgentLoop(config=config, memory=memory, tools=tools)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="NoetixAgent — Your personal AI agent")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--task", help="Single task (non-interactive)")
    parser.add_argument("--model", help="Override model (provider:model-id)")
    parser.add_argument("--toolset", help="Toolset profile: coding|research|pentest|automation|full")
    parser.add_argument("--schedule", help="Schedule task with cron expression")
    parser.add_argument("--gateway", action="store_true", help="Start messaging gateway")
    args = parser.parse_args()

    agent = create_agent(args.config)

    if args.model:
        agent.config.model = args.model

    if args.toolset:
        agent.tools.apply_profile(args.toolset)

    if args.gateway:
        from gateway.server import GatewayServer
        GatewayServer(agent).start()
        return

    if args.task:
        result = agent.run_task(args.task)
        print(result)
        return

    # Interactive CLI
    agent.interactive()


if __name__ == "__main__":
    main()
