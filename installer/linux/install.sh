#!/bin/bash
# MATCHA OS — Linux Installer
# Run: curl -sSL https://install.matchaos.com | bash
# Or: ./install.sh

set -e

GREEN='\033[0;32m'
BLACK='\033[0;30m'
NC='\033[0m'
BOLD='\033[1m'

echo ""
echo "╔══════════════════════════════════════╗"
echo "║          MATCHA OS Installer         ║"
echo "║    Your AI. Your machine. Just ask.  ║"
echo "╚══════════════════════════════════════╝"
echo ""

INSTALL_DIR="$HOME/.matcha-os"
PYTHON_MIN="3.10"

# Check Python
echo "Checking Python..."
if ! command -v python3 &>/dev/null; then
    echo "Python3 not found. Installing..."
    sudo apt-get install -y python3 python3-pip python3-venv 2>/dev/null || \
    sudo dnf install -y python3 python3-pip 2>/dev/null || \
    echo "Please install Python 3.10+ manually."
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python $PYTHON_VERSION found."

# Download MATCHA OS
echo "Downloading MATCHA OS..."
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR" && git pull --quiet 2>/dev/null || true
else
    git clone --quiet https://github.com/RohithMatcha25/matcha-os "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Create virtualenv
echo "Setting up environment..."
python3 -m venv venv
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Create desktop entry (Linux)
if [ -d "$HOME/.local/share/applications" ]; then
    cat > "$HOME/.local/share/applications/matcha-os.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=MATCHA OS
Comment=Your AI operating system
Exec=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py
Icon=$INSTALL_DIR/interface/assets/matcha-icon.png
Terminal=false
Categories=Utility;AI;
StartupNotify=true
EOF
    echo "Desktop entry created."
fi

# Create CLI shortcut
sudo ln -sf "$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py" /usr/local/bin/matcha 2>/dev/null || \
cat > "$HOME/.local/bin/matcha" << 'EOF'
#!/bin/bash
cd "$HOME/.matcha-os" && venv/bin/python main.py
EOF
chmod +x "$HOME/.local/bin/matcha" 2>/dev/null || true

# Autostart (optional)
read -p "Launch MATCHA OS on startup? [y/N] " autostart
if [[ "$autostart" =~ ^[Yy]$ ]]; then
    mkdir -p "$HOME/.config/autostart"
    cp "$HOME/.local/share/applications/matcha-os.desktop" "$HOME/.config/autostart/" 2>/dev/null || true
    echo "Autostart enabled."
fi

echo ""
echo "✅ MATCHA OS installed successfully!"
echo ""
echo "To launch: cd $INSTALL_DIR && venv/bin/python main.py"
echo "Then open: http://localhost:8080"
echo ""
echo "Or run: matcha"
echo ""
