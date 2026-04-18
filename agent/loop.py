"""
NoetixAgent Loop — ReAct-style agent loop with tool use.
Inspired by Hermes Agent's architecture + OpenClaw's session model.
"""

import json
import logging
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime

from openai import OpenAI

from agent.config import AgentConfig
from agent.memory import MemoryManager
from agent.toolregistry import ToolRegistry

logger = logging.getLogger("noetix.loop")

SYSTEM_PROMPT = """You are NoetixAgent — a highly capable personal AI assistant with deep expertise in:
- Software development & coding (Python, JS/TS, Kotlin, Bash, and more)
- Automation & system orchestration
- Security research & ethical penetration testing
- Web research & data synthesis
- Task scheduling & workflow management

You have access to tools. Use them proactively to complete tasks thoroughly.
Always think step by step. For complex tasks, break them into subtasks.
When doing security/pentest work, always operate ethically and only on authorized targets.

Current time: {datetime}
Workspace: {workspace}

Memory context:
{memory_context}
"""


class AgentLoop:
    def __init__(self, config: AgentConfig, memory: MemoryManager, tools: ToolRegistry):
        self.config = config
        self.memory = memory
        self.tools = tools
        self.history: List[Dict[str, Any]] = []
        self.client = OpenAI(
            api_key=config.get_api_key(),
            base_url=config.provider_base_url(),
        )
        logging.basicConfig(level=getattr(logging, config.log_level))

    def _system_prompt(self) -> str:
        mem_ctx = self.memory.get_context(max_entries=10)
        return SYSTEM_PROMPT.format(
            datetime=datetime.now().strftime("%Y-%m-%d %H:%M"),
            workspace=str(self.config.workspace_dir),
            memory_context=mem_ctx or "(no prior memories)",
        )

    def _tool_schemas(self) -> List[Dict]:
        return self.tools.get_schemas()

    def run_task(self, task: str, max_iterations: int = 20) -> str:
        """Run single task, return final response."""
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": task},
        ]
        return self._run_loop(messages, max_iterations)

    def _run_loop(self, messages: List[Dict], max_iterations: int) -> str:
        for iteration in range(max_iterations):
            try:
                response = self.client.chat.completions.create(
                    model=self._resolve_model(),
                    messages=messages,
                    tools=self._tool_schemas() or None,
                    max_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                )
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return f"Error: {e}"

            msg = response.choices[0].message

            # No tool calls → done
            if not msg.tool_calls:
                content = msg.content or ""
                self.memory.add(content, tags=["response"])
                return content

            # Execute tool calls
            messages.append(msg.model_dump(exclude_none=True))
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                logger.info(f"[Tool] {tool_name}({args})")

                # Security: approval gate
                if tool_name in self.config.security.get("require_approval", []):
                    if not self._request_approval(tool_name, args):
                        result = "User denied tool execution."
                    else:
                        result = self.tools.call(tool_name, args)
                else:
                    result = self.tools.call(tool_name, args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })

        return "Max iterations reached. Task may be incomplete."

    def _resolve_model(self) -> str:
        """Strip provider prefix if needed."""
        model = self.config.model
        if ":" in model and not model.startswith("openai:") and not model.startswith("anthropic:"):
            # openrouter format: keep as-is
            parts = model.split(":", 1)
            if parts[0] in ["openrouter", "ollama", "lmstudio"]:
                return parts[1]
        return model

    def _request_approval(self, tool_name: str, args: Dict) -> bool:
        print(f"\n[APPROVAL REQUIRED] Tool: {tool_name}")
        print(f"Arguments: {json.dumps(args, indent=2)}")
        ans = input("Allow? (y/N): ").strip().lower()
        return ans == "y"

    def interactive(self):
        """Interactive REPL."""
        print("NoetixAgent ready. Type 'exit' to quit, '/help' for commands.")
        print(f"Model: {self.config.model}")
        print(f"Active toolset: {self.config.active_toolset}")
        print("-" * 50)

        self.history = []

        while True:
            try:
                user_input = input("\n> ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye.")
                break

            if not user_input:
                continue

            # Slash commands
            if user_input == "exit":
                break
            elif user_input == "/help":
                self._print_help()
                continue
            elif user_input.startswith("/model "):
                self.config.model = user_input[7:].strip()
                print(f"Model set to: {self.config.model}")
                continue
            elif user_input.startswith("/toolset "):
                profile = user_input[9:].strip()
                self.tools.apply_profile(profile)
                self.config.active_toolset = profile
                print(f"Toolset: {profile}")
                continue
            elif user_input == "/memory":
                print(self.memory.get_context(max_entries=20) or "(empty)")
                continue
            elif user_input == "/clear":
                self.history.clear()
                print("History cleared.")
                continue
            elif user_input == "/tools":
                for t in self.tools.list_active():
                    print(f"  - {t}")
                continue
            elif user_input == "/new":
                self.history.clear()
                print("New session started.")
                continue

            # Build messages with history
            messages = [{"role": "system", "content": self._system_prompt()}]
            messages.extend(self.history)
            messages.append({"role": "user", "content": user_input})

            result = self._run_loop(messages, max_iterations=20)
            print(f"\n{result}")

            # Update history
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": result})

            # Keep history bounded
            if len(self.history) > 40:
                self.history = self.history[-40:]

    def _print_help(self):
        print("""
Commands:
  /model <provider:model>  — switch model
  /toolset <name>          — coding|research|pentest|automation|full
  /memory                  — show memory
  /tools                   — list active tools
  /clear                   — clear history
  /new                     — new session
  exit                     — quit
        """)
