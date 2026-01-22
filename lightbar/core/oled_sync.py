"""
OLED Synchronization Module
Monitors OLED display health and provides visual feedback for errors.
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

SHARED_STATE_FILE = "/tmp/jetson_state.json"
STALE_THRESHOLD = 5.0  # seconds - if state is older than this, OLED is considered down

class OLEDSync:
    """Monitors OLED health and provides system metrics."""

    def __init__(self):
        self.last_health_status = None
        self.last_check_time = 0
        self.check_interval = 5.0  # Check every 5 seconds
        self.oled_recovery_flash_until = 0  # Timestamp to show green flash until

    def check_oled_health(self) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check OLED health by reading shared state file.

        Returns:
            tuple: (is_healthy, state_data)
        """
        current_time = time.time()

        # Rate limit checks
        if current_time - self.last_check_time < self.check_interval:
            return self.last_health_status or (True, None)

        self.last_check_time = current_time

        try:
            state_file = Path(SHARED_STATE_FILE)
            if not state_file.exists():
                logger.warning("OLED shared state file does not exist")
                if self.last_health_status is None or self.last_health_status[0]:
                    logger.error("OLED monitor appears to be down - state file missing")
                    self.last_health_status = (False, None)
                return (False, None)

            # Read state file
            with open(state_file, 'r') as f:
                state = json.load(f)

            # Check if state is stale
            timestamp = state.get('timestamp', 0)
            age = current_time - timestamp

            if age > STALE_THRESHOLD:
                age_str = f"{age:.1f}s old"
                logger.warning(f"OLED state is stale ({age_str})")
                if self.last_health_status is None or self.last_health_status[0]:
                    logger.error(f"OLED monitor appears to be down - stale data ({age_str})")
                    self.last_health_status = (False, state)
                return (False, state)

            # OLED is healthy
            is_healthy = True
            was_healthy = self.last_health_status[0] if self.last_health_status else True

            if not was_healthy and is_healthy:
                # OLED just recovered!
                logger.info("✓ OLED monitor recovered!")
                self.oled_recovery_flash_until = current_time + 2.0  # Flash green for 2 seconds

            self.last_health_status = (is_healthy, state)
            return (is_healthy, state)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OLED state file: {e}")
            return (False, None)
        except Exception as e:
            logger.error(f"Error reading OLED state: {e}")
            return (False, None)

    def is_showing_recovery_flash(self) -> bool:
        """Check if we should show recovery flash (green)."""
        return time.time() < self.oled_recovery_flash_until

    def get_system_metrics(self) -> Optional[Dict[str, float]]:
        """
        Get system metrics from OLED shared state.

        Returns:
            dict with cpu_percent, ram_percent, temperature, or None if unavailable
        """
        is_healthy, state = self.check_oled_health()

        if not is_healthy or not state:
            return None

        return {
            'cpu_percent': state.get('cpu_percent', 0),
            'ram_percent': state.get('ram_percent', 0),
            'temperature': state.get('temperature', 0),
            'load_average': state.get('load_average', [0, 0, 0])
        }
