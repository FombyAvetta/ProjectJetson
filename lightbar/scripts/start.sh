#!/bin/bash
# Light Bar Controller Startup Script
# Performs pre-flight checks and starts controller with web server

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LIGHTBAR_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$LIGHTBAR_DIR/config.json"
LOG_DIR="$LIGHTBAR_DIR/logs"
PID_DIR="/tmp/lightbar"
WEB_PID_FILE="$PID_DIR/web.pid"
CONTROLLER_LOG="/tmp/lightbar_controller.log"
WEB_LOG="$LOG_DIR/web.log"

echo "=== Light Bar Controller Startup ==="
echo "$(date): Starting Light Bar Controller..."

# Pre-flight checks
echo "Running pre-flight checks..."

# 1. Check if lightbar directory exists
if [ ! -d "$LIGHTBAR_DIR" ]; then
    echo "ERROR: Light bar directory not found: $LIGHTBAR_DIR"
    exit 1
fi

# 2. Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Config file not found: $CONFIG_FILE"
    exit 1
fi

# 3. Validate config.json syntax
if ! python3 -c "import json; json.load(open('$CONFIG_FILE'))" 2>/dev/null; then
    echo "ERROR: Invalid JSON in config file: $CONFIG_FILE"
    exit 1
fi
echo "✓ Config file valid"

# 4. Check I2C device exists
if [ ! -e /dev/i2c-7 ]; then
    echo "ERROR: I2C device /dev/i2c-7 not found"
    exit 1
fi
echo "✓ I2C device found"

# 5. Check I2C permissions
if ! timeout 2 i2cdetect -y 7 &>/dev/null; then
    echo "WARNING: Cannot access I2C bus 7 (permission issue or bus busy)"
fi

# 6. Check disk space (need at least 100MB free)
AVAILABLE_MB=$(df /home | tail -1 | awk '{print int($4/1024)}')
if [ "$AVAILABLE_MB" -lt 100 ]; then
    echo "ERROR: Insufficient disk space. Available: ${AVAILABLE_MB}MB, Required: 100MB"
    exit 1
fi
echo "✓ Sufficient disk space (${AVAILABLE_MB}MB available)"

# 7. Create necessary directories
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"
# chown not needed "$PID_DIR"
echo "✓ Directories created"

# 8. Check Python dependencies
if ! python3 -c "import flask" 2>/dev/null; then
    echo "ERROR: Flask not installed"
    exit 1
fi
if ! python3 -c "import psutil" 2>/dev/null; then
    echo "ERROR: psutil not installed"
    exit 1
fi
echo "✓ Python dependencies available"

echo "All pre-flight checks passed!"
echo ""

# Start web server in background
echo "Starting web server..."
cd "$LIGHTBAR_DIR/web"
python3 server.py --port 5001 > "$WEB_LOG" 2>&1 &
WEB_PID=$!
echo $WEB_PID > "$WEB_PID_FILE"
echo "✓ Web server started (PID: $WEB_PID)"

# Wait for web server to initialize
sleep 2

# Check if web server is still running
if ! kill -0 $WEB_PID 2>/dev/null; then
    echo "ERROR: Web server failed to start"
    cat "$WEB_LOG"
    exit 1
fi

# Start main controller in foreground
echo "Starting main controller..."
cd "$LIGHTBAR_DIR"
exec python3 lightbar_controller.py
