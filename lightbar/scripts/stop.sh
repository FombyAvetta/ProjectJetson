#!/bin/bash
# Light Bar Controller Shutdown Script
# Gracefully stops controller and web server with fade-out

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LIGHTBAR_DIR="$(dirname "$SCRIPT_DIR")"
PID_DIR="/var/run/lightbar"
WEB_PID_FILE="$PID_DIR/web.pid"
FADE_DURATION=2  # seconds

echo "=== Light Bar Controller Shutdown ==="
echo "$(date): Stopping Light Bar Controller..."

# Trigger graceful fade-out via control state
echo "Initiating fade-out..."
cd "$LIGHTBAR_DIR"
python3 << 'EOF'
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'core'))

try:
    from shared_state import update_control_state
    # Disable lights (will trigger fade-out if brightness > 0)
    update_control_state(enabled=False)
    print("✓ Fade-out triggered")
except Exception as e:
    print(f"WARNING: Could not trigger fade-out: {e}")
EOF

# Wait for fade-out to complete
sleep $FADE_DURATION

# Stop main controller process (it's the parent of this script when run by systemd)
# The controller will receive SIGTERM and shut down gracefully
echo "Stopping controller process..."

# Stop web server
if [ -f "$WEB_PID_FILE" ]; then
    WEB_PID=$(cat "$WEB_PID_FILE")
    if kill -0 $WEB_PID 2>/dev/null; then
        echo "Stopping web server (PID: $WEB_PID)..."
        kill -TERM $WEB_PID

        # Wait up to 5 seconds for graceful shutdown
        for i in {1..5}; do
            if ! kill -0 $WEB_PID 2>/dev/null; then
                break
            fi
            sleep 1
        done

        # Force kill if still running
        if kill -0 $WEB_PID 2>/dev/null; then
            echo "Force killing web server..."
            kill -9 $WEB_PID
        fi

        echo "✓ Web server stopped"
    fi
    rm -f "$WEB_PID_FILE"
fi

# Ensure lights are off using direct Python call
echo "Ensuring lights are off..."
python3 << 'EOF'
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'hardware'))

try:
    from CubeNano import CubeNano
    bot = CubeNano(i2c_bus=7, i2c_address=14)
    bot.turn_off()
    print("✓ Lights turned off")
except Exception as e:
    print(f"WARNING: Could not turn off lights: {e}")
EOF

# Preserve state file (don't delete)
echo "State file preserved"

echo "$(date): Shutdown complete"
echo ""
