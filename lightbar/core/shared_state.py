#!/usr/bin/env python3
"""
Shared state file for web server <-> controller communication
"""

import json
import os
import fcntl
import time
from typing import Dict, Any

CONTROL_FILE = "/tmp/lightbar_control.json"

def write_control_state(state: Dict[str, Any]):
    """
    Write control state atomically.
    
    Args:
        state: Control state dictionary
    """
    try:
        # Add timestamp
        state["timestamp"] = time.time()
        
        # Write to temp file
        temp_file = CONTROL_FILE + ".tmp"
        with open(temp_file, "w") as f:
            json.dump(state, f, indent=2)
        
        # Atomic rename
        os.replace(temp_file, CONTROL_FILE)
        
    except Exception as e:
        print(f"Error writing control state: {e}")

def read_control_state() -> Dict[str, Any]:
    """
    Read control state.
    
    Returns:
        Control state dictionary or defaults
    """
    try:
        if os.path.exists(CONTROL_FILE):
            with open(CONTROL_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    
    # Return defaults
    return {
        "effect": "system_pulse",
        "brightness": 100,
        "enabled": True,
        "override": None,
        "demo_mode": False,
        "timestamp": 0
    }

def update_control_state(**kwargs):
    """
    Update specific control state fields.
    
    Args:
        **kwargs: Fields to update
    """
    state = read_control_state()
    state.update(kwargs)
    write_control_state(state)
