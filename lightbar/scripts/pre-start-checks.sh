#!/bin/bash
# Light Bar Pre-Start Validation Script
# Quick validation checks before systemd starts the service

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LIGHTBAR_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$LIGHTBAR_DIR/config.json"

# 1. Validate config.json syntax
if ! python3 -c "import json; json.load(open('$CONFIG_FILE'))" 2>/dev/null; then
    echo "ERROR: Invalid JSON in config file: $CONFIG_FILE"
    exit 1
fi

# 2. Check I2C device exists
if [ ! -e /dev/i2c-7 ]; then
    echo "ERROR: I2C device /dev/i2c-7 not found"
    exit 1
fi

# 3. Check minimum disk space (100MB)
AVAILABLE_MB=$(df /home | tail -1 | awk '{print int($4/1024)}')
if [ "$AVAILABLE_MB" -lt 100 ]; then
    echo "ERROR: Insufficient disk space. Available: ${AVAILABLE_MB}MB, Required: 100MB"
    exit 1
fi

# 4. Check Python and dependencies
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

# All checks passed
exit 0
