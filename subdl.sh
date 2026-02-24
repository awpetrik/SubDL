#!/usr/bin/env bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SubDL — One-liner installer & runner
# Usage: curl -sSL https://raw.githubusercontent.com/awpetrik/SubDL/main/subdl.sh | bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REPO_RAW="https://raw.githubusercontent.com/awpetrik/SubDL/main"
INSTALL_DIR="$HOME/.subdl"
SCRIPT_NAME="subdl.py"
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

SYS_PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge "$MIN_PYTHON_MAJOR" ] 2>/dev/null && [ "$minor" -ge "$MIN_PYTHON_MINOR" ] 2>/dev/null; then
            SYS_PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$SYS_PYTHON" ]; then
    fail "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ tidak ditemukan.

  Install Python terlebih dahulu:
    Ubuntu/Debian : sudo apt install python3 python3-pip python3-venv
    Fedora        : sudo dnf install python3 python3-pip
    macOS         : brew install python3
    Arch          : sudo pacman -S python python-pip
    Windows       : https://python.org/downloads"
fi

ok "Python ditemukan: $SYS_PYTHON ($($SYS_PYTHON --version 2>&1))"

# PYTHON_CMD = the python we'll actually use to run subdl.py
# Starts as system python, may be upgraded to venv python
PYTHON_CMD="$SYS_PYTHON"

# ── Step 2: Create install directory ──
mkdir -p "$INSTALL_DIR"

# ── Step 3: Validate or create venv, install requests ──
VENV_DIR="$INSTALL_DIR/.venv"
INSTALLED=false

# Check if existing venv is healthy (has working python + pip)
_venv_healthy() {
    [ -x "$VENV_DIR/bin/python" ] && \
    [ -x "$VENV_DIR/bin/pip" ] && \
    "$VENV_DIR/bin/python" -c "print('ok')" &>/dev/null
}

# --- Check existing venv ---
if [ -d "$VENV_DIR" ]; then
    if _venv_healthy; then
        ok "Virtual environment OK."
        PYTHON_CMD="$VENV_DIR/bin/python"
        if "$PYTHON_CMD" -c "import requests" 2>/dev/null; then
            INSTALLED=true
            ok "Dependency sudah lengkap."
        else
            info "Menginstall requests ke venv..."
            if "$VENV_DIR/bin/pip" install requests 2>&1; then
                INSTALLED=true
                ok "Dependency 'requests' terinstall (venv)."
            fi
        fi
    else
        warn "Venv lama corrupt, menghapus dan buat ulang..."
        rm -rf "$VENV_DIR"
    fi
fi

# --- Create new venv if needed ---
if [ "$INSTALLED" = false ] && [ ! -d "$VENV_DIR" ]; then
    info "Membuat virtual environment..."
    if "$SYS_PYTHON" -m venv "$VENV_DIR" 2>&1; then
        if _venv_healthy; then
            ok "Virtual environment dibuat."
            PYTHON_CMD="$VENV_DIR/bin/python"
            info "Menginstall requests..."
            if "$VENV_DIR/bin/pip" install requests 2>&1; then
                INSTALLED=true
                ok "Dependency 'requests' terinstall (venv)."
            fi
        fi
    else
        warn "python3-venv tidak tersedia."
        # Clean up failed venv
        rm -rf "$VENV_DIR"
    fi
fi

# --- Try auto-install python3-venv via apt (passwordless sudo only) ---
if [ "$INSTALLED" = false ] && command -v apt-get &>/dev/null; then
    # Detect python version for correct package name (python3.12-venv vs python3-venv)
    PY_VER=$("$SYS_PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
    warn "Mencoba: sudo apt-get install python${PY_VER}-venv python3-venv..."
    if sudo -n apt-get install -y "python${PY_VER}-venv" python3-venv 2>/dev/null; then
        info "Retry membuat venv..."
        if "$SYS_PYTHON" -m venv "$VENV_DIR" 2>/dev/null && _venv_healthy; then
            PYTHON_CMD="$VENV_DIR/bin/python"
            "$VENV_DIR/bin/pip" install requests 2>&1 && INSTALLED=true && ok "Dependency 'requests' terinstall (venv setelah apt)."
        fi
    else
        info "sudo tanpa password tidak tersedia, skip auto-install venv."
    fi
fi

# --- Fallback: pip install --user (using SYSTEM python, not broken venv) ---
if [ "$INSTALLED" = false ]; then
    info "Mencoba: $SYS_PYTHON -m pip install --user requests..."
    if "$SYS_PYTHON" -m pip install --user requests 2>&1; then
        INSTALLED=true
        PYTHON_CMD="$SYS_PYTHON"
        ok "Dependency 'requests' terinstall (--user)."
    fi
fi

# --- Fallback: --break-system-packages (PEP 668) ---
if [ "$INSTALLED" = false ]; then
    info "Mencoba: $SYS_PYTHON -m pip install --break-system-packages requests..."
    if "$SYS_PYTHON" -m pip install --break-system-packages requests 2>&1; then
        INSTALLED=true
        PYTHON_CMD="$SYS_PYTHON"
        ok "Dependency 'requests' terinstall (--break-system-packages)."
    fi
fi

# --- Fallback: pip3 standalone ---
if [ "$INSTALLED" = false ] && command -v pip3 &>/dev/null; then
    info "Mencoba: pip3 install --user requests..."
    if pip3 install --user requests 2>&1; then
        INSTALLED=true
        PYTHON_CMD="$SYS_PYTHON"
        ok "Dependency 'requests' terinstall (pip3)."
    fi
fi

# --- Final verification ---
if [ "$INSTALLED" = false ]; then
    # Maybe requests was installed somewhere in the process
    if "$SYS_PYTHON" -c "import requests" 2>/dev/null; then
        INSTALLED=true
        PYTHON_CMD="$SYS_PYTHON"
        ok "Dependency tersedia."
    fi
fi

if [ "$INSTALLED" = false ]; then
    fail "Gagal install dependency 'requests'.

  Coba manual:
    sudo apt install python3-pip python3.12-venv
    python3 -m venv ~/.subdl/.venv
    ~/.subdl/.venv/bin/pip install requests

  Atau:
    pip3 install --user requests"
fi

# ── Step 4: Download subdl.py ──
info "Mendownload SubDL..."

DOWNLOAD_CMD=""
if command -v curl &>/dev/null; then
    DOWNLOAD_CMD="curl -sSL"
elif command -v wget &>/dev/null; then
    DOWNLOAD_CMD="wget -qO-"
else
    fail "curl atau wget tidak ditemukan."
fi

if ! $DOWNLOAD_CMD "$REPO_RAW/$SCRIPT_NAME" > "$INSTALL_DIR/$SCRIPT_NAME"; then
    fail "Gagal download $SCRIPT_NAME dari GitHub."
fi

chmod +x "$INSTALL_DIR/$SCRIPT_NAME"
ok "SubDL terinstall di: $INSTALL_DIR/$SCRIPT_NAME"

# ── Step 5: Create launcher ──
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

# ── Step 6: Done ──
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

# ── Step 7: Run immediately ──
echo "🚀 Menjalankan SubDL..."
echo ""
exec "$PYTHON_CMD" "$INSTALL_DIR/$SCRIPT_NAME" "$@" < /dev/tty
