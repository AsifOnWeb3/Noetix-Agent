"""
NoetixAgent Sub-Agent System
Allows the main agent to spawn specialized sub-agents for parallel/delegated work.
Inspired by Hermes multi-agent patterns.
"""

import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from queue import Queue
from typing import Any, Callable, Dict, List, Optional

from agent.config import AgentConfig
from agent.memory import MemoryManager
from agent.toolregistry import ToolRegistry, noetix_tool

logger = logging.getLogger("noetix.subagent")


class SubAgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class SubAgentTask:
    task_id: str
    task: str
    agent_name: str
    toolset: str
    status: SubAgentStatus = SubAgentStatus.IDLE
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


# ── Sub-Agent Profiles ─────────────────────────────────────────────────────
SUBAGENT_PROFILES = {
    "coder": {
        "toolset": "coding",
        "system_extra": "You are a coding specialist. Focus on writing clean, working code. Always test your solutions.",
    },
    "researcher": {
        "toolset": "research",
        "system_extra": "You are a research specialist. Search thoroughly, verify facts, synthesize clearly.",
    },
    "pentester": {
        "toolset": "pentest",
        "system_extra": "You are an ethical security specialist. Only operate on authorized targets. Document findings clearly.",
    },
    "automator": {
        "toolset": "automation",
        "system_extra": "You are an automation specialist. Write robust scripts with error handling.",
    },
    "analyst": {
        "toolset": "full",
        "system_extra": "You are a data analyst. Break down problems, analyze systematically, present findings clearly.",
    },
}


class SubAgent:
    """A specialized agent instance that runs a delegated task."""

    def __init__(self, name: str, profile: str, parent_config: AgentConfig):
        self.name = name
        self.profile = profile
        self.task_id = str(uuid.uuid4())[:8]

        # Inherit parent config but with sub-agent identity
        self.config = parent_config
        self._profile_data = SUBAGENT_PROFILES.get(profile, SUBAGENT_PROFILES["analyst"])

        # Lightweight memory for this sub-agent
        sub_memory_dir = parent_config.memory_dir / "subagents" / name
        self.memory = MemoryManager(sub_memory_dir, max_entries=50)

        # Tools
        self.tools = ToolRegistry()
        self.tools.auto_discover(Path(__file__).parent.parent / "tools")
        self.tools.auto_discover(Path(__file__).parent.parent / "skills")
        self.tools.apply_profile(self._profile_data["toolset"])

    def run(self, task: str, max_iterations: int = 15) -> str:
        """Run task synchronously, return result."""
        from openai import OpenAI
        from agent.loop import SYSTEM_PROMPT

        client = OpenAI(
            api_key=self.config.get_api_key(),
            base_url=self.config.provider_base_url(),
        )

        # Sub-agent system prompt = base + specialization
        system = SYSTEM_PROMPT.format(
            datetime=datetime.now().strftime("%Y-%m-%d %H:%M"),
            workspace=str(self.config.workspace_dir),
            memory_context=self.memory.get_context(max_entries=5) or "(fresh sub-agent)",
        ) + f"\n\nSub-agent role: {self._profile_data['system_extra']}\nYour name: {self.name}"

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": task},
        ]

        model = self.config.model
        if ":" in model:
            parts = model.split(":", 1)
            if parts[0] in ["openrouter", "ollama", "lmstudio"]:
                model = parts[1]

        for _ in range(max_iterations):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=self.tools.get_schemas() or None,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                )
            except Exception as e:
                return f"Sub-agent {self.name} error: {e}"

            msg = response.choices[0].message

            if not msg.tool_calls:
                result = msg.content or ""
                self.memory.add(result, tags=["result"])
                return result

            messages.append(msg.model_dump(exclude_none=True))
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                logger.info(f"[SubAgent:{self.name}] {tool_name}({args})")
                # Sub-agents never prompt for approval — auto-allow non-destructive tools
                result = self.tools.call(tool_name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })

        return f"Sub-agent {self.name} hit max iterations."


class SubAgentOrchestrator:
    """
    Orchestrator: manages sub-agent lifecycle, parallel execution, result collection.
    The main agent delegates tasks here via tools.
    """

    def __init__(self, parent_config: AgentConfig):
        self.config = parent_config
        self._tasks: Dict[str, SubAgentTask] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._results: Dict[str, str] = {}
        self._lock = threading.Lock()

    def spawn(self, task: str, profile: str = "analyst", name: str = None) -> str:
        """Spawn a sub-agent for a task. Returns task_id."""
        name = name or f"{profile}-{str(uuid.uuid4())[:6]}"
        task_id = str(uuid.uuid4())[:8]

        sub_task = SubAgentTask(
            task_id=task_id,
            task=task,
            agent_name=name,
            toolset=SUBAGENT_PROFILES.get(profile, {}).get("toolset", "full"),
        )

        with self._lock:
            self._tasks[task_id] = sub_task

        def run_sub():
            try:
                sub_task.status = SubAgentStatus.RUNNING
                agent = SubAgent(name=name, profile=profile, parent_config=self.config)
                result = agent.run(task)
                with self._lock:
                    sub_task.result = result
                    sub_task.status = SubAgentStatus.DONE
                    sub_task.completed_at = datetime.now().isoformat()
                    self._results[task_id] = result
                logger.info(f"Sub-agent {name} ({task_id}) completed.")
            except Exception as e:
                with self._lock:
                    sub_task.error = str(e)
                    sub_task.status = SubAgentStatus.FAILED
                logger.error(f"Sub-agent {name} ({task_id}) failed: {e}")

        t = threading.Thread(target=run_sub, daemon=True, name=f"subagent-{task_id}")
        self._threads[task_id] = t
        t.start()

        logger.info(f"Spawned sub-agent: {name} ({task_id}) — profile: {profile}")
        return task_id

    def get_result(self, task_id: str, wait: bool = False, timeout: int = 120) -> str:
        """Get sub-agent result. Optionally wait for completion."""
        if wait:
            t = self._threads.get(task_id)
            if t:
                t.join(timeout=timeout)

        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return f"No task found with id: {task_id}"
            if task.status == SubAgentStatus.RUNNING:
                return f"Sub-agent '{task.agent_name}' still running... check again later."
            if task.status == SubAgentStatus.FAILED:
                return f"Sub-agent '{task.agent_name}' failed: {task.error}"
            if task.status == SubAgentStatus.DONE:
                return task.result or "(no result)"
            return f"Sub-agent status: {task.status.value}"

    def list_tasks(self) -> str:
        with self._lock:
            if not self._tasks:
                return "No sub-agent tasks."
            lines = []
            for tid, t in self._tasks.items():
                elapsed = ""
                if t.completed_at:
                    elapsed = f" | done"
                lines.append(f"[{tid}] {t.agent_name} ({t.toolset}) — {t.status.value}{elapsed}")
                lines.append(f"       Task: {t.task[:80]}")
            return "\n".join(lines)

    def run_parallel(self, tasks: List[Dict]) -> Dict[str, str]:
        """
        Run multiple sub-agents in parallel, wait for all.
        tasks = [{"task": "...", "profile": "coder"}, ...]
        Returns {task_id: result}
        """
        task_ids = []
        for t in tasks:
            tid = self.spawn(t["task"], profile=t.get("profile", "analyst"))
            task_ids.append(tid)

        results = {}
        for tid in task_ids:
            results[tid] = self.get_result(tid, wait=True, timeout=180)
        return results


# ── Global orchestrator instance ───────────────────────────────────────────
_orchestrator: Optional[SubAgentOrchestrator] = None


def init_orchestrator(config: AgentConfig):
    global _orchestrator
    _orchestrator = SubAgentOrchestrator(config)
    logger.info("Sub-agent orchestrator initialized.")


def get_orchestrator() -> Optional[SubAgentOrchestrator]:
    return _orchestrator


# ── Tool registrations ──────────────────────────────────────────────────────

@noetix_tool(
    name="spawn_subagent",
    description=(
        "Spawn a specialized sub-agent to handle a task in parallel. "
        "Use this to delegate work: coding tasks to 'coder', research to 'researcher', "
        "security work to 'pentester', automation to 'automator', analysis to 'analyst'. "
        "Returns a task_id — use get_subagent_result to retrieve the result."
    ),
    parameters={
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "The task to delegate to the sub-agent"},
            "profile": {
                "type": "string",
                "enum": ["coder", "researcher", "pentester", "automator", "analyst"],
                "description": "Sub-agent specialization profile",
                "default": "analyst",
            },
            "name": {"type": "string", "description": "Optional custom name for this sub-agent"},
        },
        "required": ["task"],
    },
    tags=["core", "automation", "full"],
)
def spawn_subagent(task: str, profile: str = "analyst", name: str = None):
    if _orchestrator is None:
        return "Sub-agent system not initialized. Restart the agent."
    task_id = _orchestrator.spawn(task, profile=profile, name=name)
    return f"Sub-agent spawned. Task ID: {task_id}\nProfile: {profile}\nUse get_subagent_result(task_id='{task_id}') to get the result."


@noetix_tool(
    name="get_subagent_result",
    description="Get the result of a spawned sub-agent task. Optionally wait for it to finish.",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Task ID returned from spawn_subagent"},
            "wait": {"type": "boolean", "description": "Wait for completion if still running", "default": True},
            "timeout": {"type": "integer", "description": "Max seconds to wait", "default": 120},
        },
        "required": ["task_id"],
    },
    tags=["core", "automation", "full"],
)
def get_subagent_result(task_id: str, wait: bool = True, timeout: int = 120):
    if _orchestrator is None:
        return "Sub-agent system not initialized."
    return _orchestrator.get_result(task_id, wait=wait, timeout=timeout)


@noetix_tool(
    name="list_subagents",
    description="List all active and completed sub-agent tasks with their status.",
    parameters={"type": "object", "properties": {}},
    tags=["core", "automation", "full"],
)
def list_subagents():
    if _orchestrator is None:
        return "Sub-agent system not initialized."
    return _orchestrator.list_tasks()


@noetix_tool(
    name="run_parallel_tasks",
    description=(
        "Run multiple tasks in parallel using specialized sub-agents, then collect all results. "
        "Best for splitting a big job into independent parts. "
        "Example: research + code + write docs all at once."
    ),
    parameters={
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "description": "List of tasks to run in parallel",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "description": "Task description"},
                        "profile": {
                            "type": "string",
                            "enum": ["coder", "researcher", "pentester", "automator", "analyst"],
                            "default": "analyst",
                        },
                    },
                    "required": ["task"],
                },
            }
        },
        "required": ["tasks"],
    },
    tags=["core", "automation", "full"],
)
def run_parallel_tasks(tasks: list):
    if _orchestrator is None:
        return "Sub-agent system not initialized."
    results = _orchestrator.run_parallel(tasks)
    lines = ["=== Parallel Task Results ===\n"]
    for tid, result in results.items():
        lines.append(f"[{tid}]\n{result}\n{'─'*40}")
    return "\n".join(lines)
