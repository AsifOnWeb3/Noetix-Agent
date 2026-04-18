#!/usr/bin/env bash
# NoetixAgent Installer
# Supports: Linux (Ubuntu/Debian/Kali), macOS, Windows WSL2

set -e

REPO_URL="https://github.com/AsifOnWeb3/Noetix-Agent"
INSTALL_DIR="$HOME/.noetix"
CONFIG_DIR="$HOME/.noetix"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[NoetixAgent]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
fi
info "Detected OS: $OS"

# Check Python
if ! command -v python3 &>/dev/null; then
    err "Python 3.10+ required. Install from https://python.org"
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python version: $PY_VER"

# Check pip / uv
if command -v uv &>/dev/null; then
    PM="uv pip"
    info "Using uv for installation"
elif command -v pip3 &>/dev/null; then
    PM="pip3"
else
    err "pip3 or uv required. Install: python3 -m ensurepip"
fi

# Clone or update repo
if [ -d "$HOME/noetix-agent/.git" ]; then
    info "Updating existing installation..."
    cd "$HOME/noetix-agent"
    git pull
else
    info "Cloning NoetixAgent..."
    git clone "$REPO_URL" "$HOME/noetix-agent"
    cd "$HOME/noetix-agent"
fi

# Install package
info "Installing dependencies..."
if [[ "$PM" == "uv pip" ]]; then
    uv pip install -e ".[all]"
else
    pip3 install -e ".[all]" --break-system-packages 2>/dev/null || pip3 install -e ".[all]"
fi

# Setup config
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    cp config/config.example.yaml "$CONFIG_DIR/config.yaml"
    info "Config created at $CONFIG_DIR/config.yaml"
fi

# Add to PATH
SHELL_RC="$HOME/.bashrc"
[[ "$SHELL" == *"zsh"* ]] && SHELL_RC="$HOME/.zshrc"

if ! grep -q "noetix" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# NoetixAgent" >> "$SHELL_RC"
    echo "export PATH=\"\$PATH:\$HOME/.local/bin\"" >> "$SHELL_RC"
fi

info "Installation complete!"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "  1. Set your API key:"
echo "     export OPENROUTER_API_KEY=your_key_here"
echo "     (add to ~/.bashrc or ~/.zshrc)"
echo ""
echo "  2. Edit config (optional):"
echo "     nano ~/.noetix/config.yaml"
echo ""
echo "  3. Start the agent:"
echo "     noetix"
echo ""
echo -e "${YELLOW}Get a free API key at: https://openrouter.ai${NC}"
