#!/usr/bin/env python3
"""
Flask Web Server for RGB Light Bar Control
REST API + WebSocket for real-time updates
"""

import sys
import os
# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'hardware'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, jsonify, request, send_from_directory
from flask_sock import Sock
import json
import psutil
import time
import threading
import logging

# Import controller components
from scheduler import Scheduler
from shared_state import update_control_state, read_control_state

app = Flask(__name__, static_folder="static", static_url_path="")
sock = Sock(app)

# Global state (will be updated by controller)
current_state = {
    "effect": "system_pulse",
    "brightness": 100,
    "enabled": True,
    "schedule_active": True,
    "metrics": {
        "cpu_percent": 0.0,
        "ram_percent": 0.0,
        "temperature": 50.0,
        "system_load": 0.0,
    },
    "available_effects": [
        "system_pulse",
        "load_rainbow",
        "random_sparkle",
        "thermal_gradient",
        "load_bars"
    ]
}

# Thread lock for state updates
state_lock = threading.Lock()

# Scheduler instance
scheduler = Scheduler()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebServer")

def update_metrics():
    """Update system metrics (background thread)."""
    while True:
        try:
            with state_lock:
                current_state["metrics"]["cpu_percent"] = psutil.cpu_percent(interval=0.5)
                mem = psutil.virtual_memory()
                current_state["metrics"]["ram_percent"] = mem.percent
                
                # Temperature
                try:
                    with open("/sys/class/thermal/thermal_zone0/temp") as f:
                        temp_millidegrees = int(f.read().strip())
                        current_state["metrics"]["temperature"] = temp_millidegrees / 1000.0
                except:
                    pass
                
                # Calculate system load
                cpu_norm = current_state["metrics"]["cpu_percent"] / 100.0
                ram_norm = current_state["metrics"]["ram_percent"] / 100.0
                load_avg = os.getloadavg()[0]
                cpu_count = psutil.cpu_count()
                load_norm = min(1.0, load_avg / cpu_count)
                
                system_load = (cpu_norm * 0.6) + (ram_norm * 0.3) + (load_norm * 0.1)
                current_state["metrics"]["system_load"] = min(1.0, max(0.0, system_load))
        
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
        
        time.sleep(1.0)

# Start metrics thread
metrics_thread = threading.Thread(target=update_metrics, daemon=True)
metrics_thread.start()

# ===== REST API ENDPOINTS =====

@app.route("/")
def index():
    """Serve main page."""
    return send_from_directory("static", "index.html")

@app.route("/api/status")
def api_status():
    """Get current system status."""
    with state_lock:
        return jsonify({
            "success": True,
            "data": current_state
        })

@app.route("/api/mode", methods=["POST"])
def api_set_mode():
    """Change effect mode."""
    try:
        data = request.get_json()
        mode = data.get("mode")
        
        if mode not in current_state["available_effects"]:
            return jsonify({"success": False, "error": "Invalid effect mode"}), 400
        
        with state_lock:
            current_state["effect"] = mode
        
        # Update shared state for controller
        update_control_state(effect=mode)
        logger.info(f"Effect changed to: {mode}")
        
        return jsonify({"success": True, "effect": mode})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/brightness", methods=["POST"])
def api_set_brightness():
    """Set brightness level."""
    try:
        data = request.get_json()
        brightness = data.get("brightness", 100)
        
        # Validate brightness
        brightness = max(0, min(100, int(brightness)))
        
        with state_lock:
            current_state["brightness"] = brightness
        
        # Update shared state for controller
        update_control_state(brightness=brightness)
        logger.info(f"Brightness set to: {brightness}%")
        
        return jsonify({"success": True, "brightness": brightness})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/toggle", methods=["POST"])
def api_toggle():
    """Toggle lights on/off."""
    try:
        data = request.get_json()
        enabled = data.get("enabled", True)
        
        with state_lock:
            current_state["enabled"] = enabled
        
        # Update shared state for controller
        update_control_state(enabled=enabled)
        logger.info(f"Lights {'enabled' if enabled else 'disabled'}")
        
        return jsonify({"success": True, "enabled": enabled})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/override", methods=["POST"])
def api_override():
    """Set manual override."""
    try:
        data = request.get_json()
        turn_on = data.get("turn_on", True)
        duration = data.get("duration", 3600)  # Default 1 hour
        
        scheduler.set_override(turn_on, duration)
        
        logger.info(f"Override set: {ON if turn_on else OFF} for {duration}s")
        
        return jsonify({
            "success": True,
            "override": "on" if turn_on else "off",
            "duration": duration
        })
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/override/clear", methods=["POST"])
def api_clear_override():
    """Clear manual override."""
    try:
        scheduler.clear_override()
        logger.info("Override cleared")
        
        return jsonify({"success": True})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/effects")
def api_list_effects():
    """List available effects."""
    with state_lock:
        return jsonify({
            "success": True,
            "effects": current_state["available_effects"]
        })

@app.route("/api/demo", methods=["POST"])
def api_demo_mode():
    """Trigger demo mode."""
    try:
        # Signal controller to start demo mode
        update_control_state(demo_mode=True)
        logger.info("Demo mode triggered")
        
        return jsonify({"success": True, "message": "Demo mode started"})
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ===== WEBSOCKET ENDPOINT =====

@sock.route("/ws/updates")
def websocket_updates(ws):
    """WebSocket for real-time metrics updates."""
    logger.info("WebSocket client connected")
    
    try:
        while True:
            # Send current state every second
            with state_lock:
                data = {
                    "metrics": current_state["metrics"],
                    "effect": current_state["effect"],
                    "brightness": current_state["brightness"],
                    "enabled": current_state["enabled"],
                    "timestamp": time.time()
                }
            
            ws.send(json.dumps(data))
            time.sleep(1.0)
    
    except Exception as e:
        logger.info(f"WebSocket client disconnected: {e}")

# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error"}), 500

# ===== MAIN =====

def main():
    """Start web server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Light Bar Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", default=5000, type=int, help="Port to bind to")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    logger.info(f"Starting web server on {args.host}:{args.port}")
    logger.info(f"Access web interface at http://<jetson-ip>:{args.port}")
    
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        threaded=True
    )

if __name__ == "__main__":
    main()
