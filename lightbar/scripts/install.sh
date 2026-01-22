#!/bin/bash
# Light Bar Controller Installation Script
# Sets up systemd service and configures permissions

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LIGHTBAR_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="lightbar.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_FILE"

echo "=== Light Bar Controller Installation ==="
echo ""

# 1. Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run with sudo"
    echo "Usage: sudo ./install.sh"
    exit 1
fi

# 2. Set up directory structure
echo "Setting up directory structure..."
mkdir -p "$LIGHTBAR_DIR/logs"
mkdir -p "$LIGHTBAR_DIR/scripts"
mkdir -p /tmp/lightbar
chown john:john /tmp/lightbar
echo "✓ Directories created"

# 3. Configure I2C permissions
echo "Configuring I2C permissions..."

# Add user to i2c group
if ! groups john | grep -q i2c; then
    usermod -a -G i2c john
    echo "✓ User 'john' added to i2c group"
else
    echo "✓ User 'john' already in i2c group"
fi

# Create udev rule for I2C device
UDEV_RULE="/etc/udev/rules.d/99-i2c.rules"
if [ ! -f "$UDEV_RULE" ]; then
    echo 'SUBSYSTEM=="i2c-dev", GROUP="i2c", MODE="0660"' > "$UDEV_RULE"
    udevadm control --reload-rules
    udevadm trigger
    echo "✓ I2C udev rules created"
else
    echo "✓ I2C udev rules already exist"
fi

# 4. Install Python dependencies
echo "Checking Python dependencies..."

MISSING_DEPS=0

if ! sudo -u john python3 -c "import flask" 2>/dev/null; then
    echo "Installing Flask..."
    sudo -u john pip3 install flask flask-sock --user
    MISSING_DEPS=1
fi

if ! sudo -u john python3 -c "import psutil" 2>/dev/null; then
    echo "Installing psutil..."
    sudo -u john pip3 install psutil --user
    MISSING_DEPS=1
fi

if [ $MISSING_DEPS -eq 0 ]; then
    echo "✓ All Python dependencies already installed"
else
    echo "✓ Python dependencies installed"
fi

# 5. Install systemd service
echo "Installing systemd service..."

if [ ! -f "$LIGHTBAR_DIR/$SERVICE_FILE" ]; then
    echo "ERROR: Service file not found: $LIGHTBAR_DIR/$SERVICE_FILE"
    echo "Please ensure lightbar.service is in $LIGHTBAR_DIR"
    exit 1
fi

# Copy service file
cp "$LIGHTBAR_DIR/$SERVICE_FILE" "$SERVICE_PATH"
chmod 644 "$SERVICE_PATH"
echo "✓ Service file installed to $SERVICE_PATH"

# 6. Make scripts executable
echo "Making scripts executable..."
chmod +x "$LIGHTBAR_DIR/scripts/"*.sh
echo "✓ Scripts are executable"

# 7. Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload
echo "✓ Systemd reloaded"

# 8. Enable service
echo "Enabling lightbar service..."
systemctl enable lightbar.service
echo "✓ Service enabled (will start on boot)"

echo ""
echo "=== Installation Complete! ==="
echo ""
echo "Service Status: $(systemctl is-enabled lightbar.service)"
echo ""
echo "Available commands:"
echo "  sudo systemctl start lightbar    - Start the service"
echo "  sudo systemctl stop lightbar     - Stop the service"
echo "  sudo systemctl restart lightbar  - Restart the service"
echo "  sudo systemctl status lightbar   - Check service status"
echo "  journalctl -u lightbar -f        - View live logs"
echo ""
echo "NOTE: You may need to log out and back in for I2C group changes to take effect."
echo ""
