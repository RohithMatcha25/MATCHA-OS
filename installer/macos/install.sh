#!/bin/bash
# MATCHA OS — macOS Installer

set -e

echo "╔══════════════════════════════════════╗"
echo "║       MATCHA OS — macOS Installer    ║"
echo "╚══════════════════════════════════════╝"

INSTALL_DIR="$HOME/.matcha-os"

# Check Homebrew
if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Check Python
if ! command -v python3 &>/dev/null; then
    brew install python@3.12
fi

# Download MATCHA
echo "Downloading MATCHA OS..."
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR" && git pull --quiet 2>/dev/null || true
else
    git clone --quiet https://github.com/RohithMatcha25/matcha-os "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --quiet -r requirements.txt

# Create macOS app launcher
cat > "$HOME/Desktop/MATCHA OS.command" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
venv/bin/python main.py &
sleep 2
open http://localhost:8080
EOF
chmod +x "$HOME/Desktop/MATCHA OS.command"

echo ""
echo "✅ MATCHA OS installed!"
echo "Double-click 'MATCHA OS' on your Desktop to launch."
echo ""
