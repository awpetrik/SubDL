#!/usr/bin/env bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SubDL — One-liner installer & runner
# Usage: curl -sSL https://raw.githubusercontent.com/awpetrik/SubDL/main/subdl.sh | bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/awpetrik/SubDL/main"
INSTALL_DIR="$HOME/.subdl"
SCRIPT_NAME="subdl.py"
REQUIREMENTS="requests"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=9

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}ℹ ${NC} $*"; }
ok()    { echo -e "${GREEN}✅${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠ ${NC} $*"; }
fail()  { echo -e "${RED}❌${NC} $*"; exit 1; }

echo ""
echo "┌─────────────────────────────────────────────┐"
echo "│  🎬 SubSource Sub Downloader by awpetrik    │"
echo "│  Download subtitle Indonesia secara instan  │"
echo "│     https://github.com/awpetrik/SubDL       │"
echo "└─────────────────────────────────────────────┘"
echo ""

# ── Step 1: Check Python ──
info "Mengecek Python..."

PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        # Check version
        version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge "$MIN_PYTHON_MAJOR" ] && [ "$minor" -ge "$MIN_PYTHON_MINOR" ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    fail "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ tidak ditemukan.

  Install Python terlebih dahulu:
    Ubuntu/Debian : sudo apt install python3 python3-pip python3-venv
    Fedora        : sudo dnf install python3 python3-pip
    macOS         : brew install python3
    Arch          : sudo pacman -S python python-pip
    Windows       : https://python.org/downloads"
fi

ok "Python ditemukan: $PYTHON_CMD ($("$PYTHON_CMD" --version 2>&1))"

# ── Step 2: Create install directory ──
mkdir -p "$INSTALL_DIR"

# ── Step 3: Setup virtual environment ──
VENV_DIR="$INSTALL_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    info "Membuat virtual environment..."
    "$PYTHON_CMD" -m venv "$VENV_DIR" 2>/dev/null || {
        warn "python3-venv tidak tersedia. Mencoba install tanpa venv..."
        VENV_DIR=""
    }
fi

if [ -n "$VENV_DIR" ] && [ -d "$VENV_DIR" ]; then
    # Use venv python
    PYTHON_CMD="$VENV_DIR/bin/python"
    PIP_CMD="$VENV_DIR/bin/pip"
    ok "Virtual environment siap."
else
    # Fallback: use system pip
    PIP_CMD="$PYTHON_CMD -m pip"
fi

# ── Step 4: Install dependencies ──
info "Mengecek dependencies..."

if ! "$PYTHON_CMD" -c "import requests" &>/dev/null; then
    info "Menginstall requests..."
    $PIP_CMD install --quiet "$REQUIREMENTS" 2>/dev/null || {
        # Try with --user flag if venv failed
        "$PYTHON_CMD" -m pip install --quiet --user "$REQUIREMENTS" 2>/dev/null || {
            fail "Gagal install dependency 'requests'.
  Coba manual: pip3 install requests"
        }
    }
    ok "Dependency 'requests' terinstall."
else
    ok "Dependency sudah lengkap."
fi

# ── Step 5: Download subdl.py ──
info "Mendownload SubDL..."

DOWNLOAD_CMD=""
if command -v curl &>/dev/null; then
    DOWNLOAD_CMD="curl -sSL"
elif command -v wget &>/dev/null; then
    DOWNLOAD_CMD="wget -qO-"
else
    fail "curl atau wget tidak ditemukan. Install salah satu terlebih dahulu."
fi

$DOWNLOAD_CMD "$REPO_RAW/$SCRIPT_NAME" > "$INSTALL_DIR/$SCRIPT_NAME" || {
    fail "Gagal download $SCRIPT_NAME dari GitHub."
}

chmod +x "$INSTALL_DIR/$SCRIPT_NAME"
ok "SubDL terinstall di: $INSTALL_DIR/$SCRIPT_NAME"

# ── Step 6: Create launcher alias ──
LAUNCHER="$INSTALL_DIR/subdl"
cat > "$LAUNCHER" << 'LAUNCHER_EOF'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
if [ -x "$VENV_PYTHON" ]; then
    exec "$VENV_PYTHON" "$SCRIPT_DIR/subdl.py" "$@"
else
    exec python3 "$SCRIPT_DIR/subdl.py" "$@"
fi
LAUNCHER_EOF
chmod +x "$LAUNCHER"

# ── Step 7: Add to PATH (suggest) ──
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ok "Instalasi selesai!"
echo ""
echo "  Jalankan sekarang:"
echo "    $LAUNCHER"
echo ""
echo "  Atau tambahkan ke PATH agar bisa dipanggil dari mana saja:"
echo "    echo 'export PATH=\"\$HOME/.subdl:\$PATH\"' >> ~/.bashrc"
echo "    source ~/.bashrc"
echo "    subdl   # langsung bisa!"
echo ""
echo "  Jangan lupa set API key:"
echo "    export SUBSOURCE_API_KEY=your_key_here"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Step 8: Run immediately ──
echo "🚀 Menjalankan SubDL..."
echo ""
exec "$PYTHON_CMD" "$INSTALL_DIR/$SCRIPT_NAME" "$@"
