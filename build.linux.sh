#!/bin/bash
set -e

echo "=================================================="
echo "Plotune relay Extension Builder (Linux)"
echo "=================================================="

APP_NAME="plotune_relay_ext"
ARCHIVE_NAME="plotune-relay-ext-linux-x86_64.tar.gz"
DIST_DIR="dist"
HISTORY_DIR="$DIST_DIR/history"
VENV_DIR="..venv"

# Create virtual environment if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/python" -m ensurepip --upgrade
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
[ -f requirements.txt ] && pip install -r requirements.txt

# Ensure PyInstaller
python -c "import PyInstaller" 2>/dev/null || pip install pyinstaller

# Prepare history
mkdir -p "$HISTORY_DIR"

if [ -f "$DIST_DIR/$ARCHIVE_NAME" ]; then
    TS=$(date +"%Y%m%d_%H%M%S")
    echo "Archiving previous build: $TS"
    mv "$DIST_DIR/$ARCHIVE_NAME" "$HISTORY_DIR/${ARCHIVE_NAME}_$TS"
fi

# Build
echo "Building executable..."
pyinstaller \
  --name "$APP_NAME" \
  --onedir \
  --noconfirm \
  src/main.py

# Copy plugin.json (external, runtime-loaded)
echo "Copying plugin.json..."
cp src/plugin.json "$DIST_DIR/$APP_NAME/plugin.json"

# Package
echo "Creating tar.gz archive..."
cd "$DIST_DIR"
tar -czf "$ARCHIVE_NAME" "$APP_NAME"

sha256sum $ARCHIVE_NAME > $ARCHIVE_NAME.sha256

cd ..

echo "=================================================="
echo "Linux build completed successfully"
echo "=================================================="