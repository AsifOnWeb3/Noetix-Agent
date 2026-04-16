# 🤖 NoetixAgent

> A powerful, self-improving personal AI agent for coding, automation, research, scheduling, and ethical security testing. Inspired by [OpenClaw](https://github.com/openclaw/openclaw) and [Hermes Agent](https://github.com/NousResearch/hermes-agent).

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![OpenRouter](https://img.shields.io/badge/Powered%20by-OpenRouter-orange)](https://openrouter.ai)

---

## ✨ Features

| Capability | Description |
|---|---|
| 🧠 **AI Agent Loop** | ReAct-style reasoning with tool use (OpenAI-compatible API) |
| 💻 **Coding** | Execute bash, run Python, git operations, code search, linting |
| 🔍 **Research** | Web search (DuckDuckGo, no API key), URL fetching, synthesis |
| 🕐 **Scheduling** | Built-in cron scheduler — recurring tasks in natural language |
| 🔐 **Security / Pentest** | nmap, whois, subdomain enum, CVE search, HTTP probing |
| 💬 **Messaging Gateway** | Telegram + Discord bot integration |
| 🧬 **Memory** | Persistent cross-session memory with keyword search |
| 🛠️ **Skills** | Modular skills system — add custom tools as Python files |
| 🔌 **Multi-provider** | OpenRouter (200+ models), OpenAI, Anthropic, Ollama, LM Studio |

---

## 🚀 Quick Start

### 1. Get a Free API Key

Get a free API key from [OpenRouter](https://openrouter.ai) — access 200+ models including free tiers (Qwen3, Llama, Gemma, etc).

### 2. Install & Run

```bash
# One-line installer (Linux / macOS / WSL2)
curl -fsSL https://raw.githubusercontent.com/AsifOnWeb3/noetix-agent/main/install.sh | bash

# Reload shell
source ~/.bashrc  # or source ~/.zshrc

# Set API key
export OPENROUTER_API_KEY=your_key_here

# Start the agent
noetix
```

---

## 📦 Installation Guide

### Windows (WSL2) — Recommended

> Native Windows not supported. Use WSL2 for full compatibility.

**Step 1 — Install WSL2:**
```powershell
# Run in PowerShell as Administrator
wsl --install
# Restart your PC, then open Ubuntu from Start Menu
```

**Step 2 — Inside WSL2 Ubuntu terminal:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python + Git
sudo apt install -y python3 python3-pip git curl

# Install uv (faster than pip)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Clone NoetixAgent
git clone https://github.com/AsifOnWeb3/noetix-agent.git
cd noetix-agent

# Install
uv pip install -e ".[all]"
# OR: pip3 install -e ".[all]"

# Copy config
mkdir -p ~/.noetix
cp config/config.example.yaml ~/.noetix/config.yaml

# Set API key (add to ~/.bashrc to persist)
echo 'export OPENROUTER_API_KEY=your_key_here' >> ~/.bashrc
source ~/.bashrc

# Run!
noetix
```

**Optional — Windows Terminal shortcut:**
```powershell
# In PowerShell, create a shortcut to open WSL + start noetix
wsl -e bash -c "noetix"
```

---

### Kali Linux

Kali is the ideal platform for NoetixAgent's security/pentest toolset — nmap, searchsploit, and whois are pre-installed.

```bash
# Step 1 — Update & install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip git curl nmap whois

# Step 2 — Install uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc  # Kali uses zsh by default

# Step 3 — Clone repo
git clone https://github.com/AsifOnWeb3/noetix-agent.git ~/noetix-agent
cd ~/noetix-agent

# Step 4 — Install
uv pip install -e ".[all]"
# If uv not available:
pip3 install -e ".[all]" --break-system-packages

# Step 5 — Configure
mkdir -p ~/.noetix
cp config/config.example.yaml ~/.noetix/config.yaml

# Step 6 — Set API key
echo 'export OPENROUTER_API_KEY=your_key_here' >> ~/.zshrc
source ~/.zshrc

# Step 7 — Run
noetix
```

**Kali Pentest Toolset** — switch to pentest mode in the agent:
```
> /toolset pentest
```
This enables: `nmap_scan`, `whois_lookup`, `subdomain_enum`, `http_probe`, `exploit_search`, `bash`.

> ⚠️ **Legal Warning:** Only use security tools on systems you own or have explicit written authorization to test. Unauthorized scanning is illegal.

**Optional — Install Exploit-DB for offline search:**
```bash
sudo apt install exploitdb
# Then searchsploit will work inside the agent
```

---

### macOS

```bash
# Step 1 — Install Homebrew (if not already)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Step 2 — Install dependencies
brew install python@3.12 git nmap

# Step 3 — Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc  # or ~/.bash_profile

# Step 4 — Clone repo
git clone https://github.com/AsifOnWeb3/noetix-agent.git ~/noetix-agent
cd ~/noetix-agent

# Step 5 — Install
uv pip install -e ".[all]"
# OR: pip3 install -e ".[all]"

# Step 6 — Configure
mkdir -p ~/.noetix
cp config/config.example.yaml ~/.noetix/config.yaml

# Step 7 — Set API key
echo 'export OPENROUTER_API_KEY=your_key_here' >> ~/.zshrc
source ~/.zshrc

# Step 8 — Run
noetix
```

**macOS nmap note:** nmap scans may require sudo:
```bash
sudo noetix  # for SYN scans
```

---

## ⚙️ Configuration

Config file location: `~/.noetix/config.yaml`

```yaml
# Model — OpenRouter free tier (no cost)
model: "openrouter:qwen/qwen3-coder:free"
provider: "openrouter"
api_key_env: "OPENROUTER_API_KEY"

# Other model options:
# model: "openrouter:meta-llama/llama-3.3-70b-instruct:free"
# model: "openrouter:google/gemma-3-27b-it:free"
# model: "ollama:qwen2.5-coder:7b"        # local Ollama
# model: "lmstudio:local-model"            # local LM Studio (port 1234)
# model: "openai:gpt-4o"                   # OpenAI
# model: "anthropic:claude-sonnet-4-5"     # Anthropic

max_tokens: 4096
temperature: 0.7

# Security — tools requiring confirmation before running
security:
  require_approval:
    - bash
    - nmap_scan
    - exploit_search

# Messaging gateway (optional)
gateway:
  telegram:
    enabled: false
    bot_token: "YOUR_BOT_TOKEN"
  discord:
    enabled: false
    token: "YOUR_DISCORD_TOKEN"
```

---

## 💻 Usage

### Interactive Mode (default)

```bash
noetix
```

```
NoetixAgent ready. Type 'exit' to quit, '/help' for commands.
Model: openrouter:qwen/qwen3-coder:free
Active toolset: default
──────────────────────────────────────────────────

> Write a Python script that monitors CPU usage every 5 seconds
> /toolset pentest
> Scan ports on 192.168.1.1 (my router)
> Search for recent CVEs in Apache 2.4
> Schedule a daily backup at 2am
> Research: what is the best local LLM for coding in 2025?
```

### Single Task Mode

```bash
noetix --task "List all Python files in ~/projects and summarize what each does"
noetix --task "Check if port 22 is open on localhost" --toolset pentest
noetix --task "Create a FastAPI project called my-api" --toolset coding
```

### Model Override

```bash
noetix --model "openrouter:meta-llama/llama-3.3-70b-instruct:free"
noetix --model "ollama:qwen2.5-coder:7b"
```

### Messaging Gateway

```bash
# Start Telegram + Discord gateway
noetix --gateway
```

### Slash Commands (inside interactive mode)

| Command | Description |
|---|---|
| `/toolset <name>` | Switch toolset: `coding`, `research`, `pentest`, `automation`, `full` |
| `/model <id>` | Change model on the fly |
| `/memory` | Show current memory context |
| `/tools` | List active tools |
| `/new` or `/clear` | Start fresh session |
| `/help` | Show all commands |
| `exit` | Quit |

---

## 🛠️ Toolsets

| Toolset | Tools Included |
|---|---|
| `default` | bash, file I/O, web search, memory |
| `coding` | bash, git, file I/O, code search, linter, Python runner |
| `research` | web search, URL fetch, file I/O, summarize |
| `pentest` | bash, nmap, whois, subdomain enum, HTTP probe, CVE/exploit search |
| `automation` | bash, HTTP requests, file I/O, cron scheduler |
| `full` | All tools enabled |

---

## 🧩 Adding Custom Tools

Create a `.py` file in `~/.noetix/skills/` or the `tools/` directory:

```python
from agent.toolregistry import noetix_tool

@noetix_tool(
    name="my_tool",
    description="What this tool does — be specific for the LLM.",
    parameters={
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "The input"},
        },
        "required": ["input"],
    },
    tags=["custom"],
)
def my_tool(input: str):
    return f"Processed: {input}"
```

Tools are auto-discovered on startup. Restart `noetix` to load new tools.

---

## 📡 Messaging Gateway Setup

### Telegram

1. Create a bot via [@BotFather](https://t.me/botfather) → get token
2. Add to `~/.noetix/config.yaml`:
```yaml
gateway:
  telegram:
    enabled: true
    bot_token: "123456:ABCDEF..."
    allowed_users: [123456789]  # your Telegram user ID
```
3. Run: `noetix --gateway`
4. Message your bot → it runs tasks and replies

### Discord

1. Create app at [discord.com/developers](https://discord.com/developers/applications)
2. Create bot → copy token → invite to server with `Send Messages` permission
3. Add to config:
```yaml
gateway:
  discord:
    enabled: true
    token: "YOUR_BOT_TOKEN"
    allowed_channels: [123456789]
```
4. In Discord: `!noetix <your task>`

---

## 🔄 Using Local Models

### Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull qwen2.5-coder:7b

# Configure NoetixAgent
# In ~/.noetix/config.yaml:
# model: "ollama:qwen2.5-coder:7b"
# base_url: "http://localhost:11434/v1"
# api_key_env: "OLLAMA_KEY"  # any value, Ollama doesn't need real key

export OLLAMA_KEY=ollama
noetix
```

### LM Studio

```bash
# Start LM Studio → load a model → start local server (port 1234)
# In config.yaml:
# model: "lmstudio:local-model"
# base_url: "http://localhost:1234/v1"

export LMSTUDIO_KEY=lmstudio
noetix
```

---

## 🏗️ Project Structure

```
noetix-agent/
├── agent/
│   ├── core.py          # Entry point + CLI
│   ├── loop.py          # ReAct agent loop
│   ├── config.py        # Config loader
│   ├── memory.py        # Persistent memory
│   └── toolregistry.py  # Tool auto-discovery + schemas
├── tools/
│   ├── core_tools.py    # bash, file I/O, web search, HTTP
│   ├── coding_tools.py  # git, linting, Python runner
│   └── security_tools.py # nmap, whois, CVE search
├── skills/
│   └── builtin_skills.py # code review, research, daily report
├── cron/
│   └── scheduler.py     # Cron job scheduler
├── gateway/
│   └── server.py        # Telegram + Discord gateway
├── config/
│   └── config.example.yaml
├── install.sh
├── pyproject.toml
└── README.md
```

---

## 🔒 Security Notes

- Security tools require user approval by default (configured in `security.require_approval`)
- Never run pentest tools on targets you don't own
- Store API keys in environment variables, never in config.yaml committed to git
- Add `~/.noetix/config.yaml` to `.gitignore` if you fork this repo

---

## 📋 Requirements

- Python 3.10+
- Git
- API key from [OpenRouter](https://openrouter.ai) (free tier available) OR any OpenAI-compatible endpoint

**Optional for full pentest toolset:**
- `nmap` — port scanning
- `whois` — domain lookup
- `searchsploit` (exploitdb) — offline exploit search

---

## 🤝 Acknowledgements

Architecture inspired by:
- [OpenClaw](https://github.com/openclaw/openclaw) — gateway pattern, multi-channel support, skills system
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) by NousResearch — agent loop, memory architecture, toolset system

---

## 📄 License

MIT — see [LICENSE](LICENSE)
