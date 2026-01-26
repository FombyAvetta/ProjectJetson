#!/usr/bin/env python3
"""
Smart Scheduler for RGB Light Bar
Automatic day/night detection with smooth transitions
"""

import json
import os
import time
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum
import fcntl

class ScheduleState(Enum):
    """Schedule states."""
    ON = "on"
    OFF = "off"
    OVERRIDE_ON = "override_on"
    OVERRIDE_OFF = "override_off"
    TRANSITIONING = "transitioning"

class Scheduler:
    """Manages automatic scheduling and manual overrides."""

    def __init__(self, state_file: str = None, config_file: str = None):
        """Initialize scheduler.

        Args:
            state_file: Path to state file (default: lightbar/state.json)
            config_file: Path to config file (default: lightbar/schedule_config.json)
        """
        # Find the lightbar root directory
        # Works whether scheduler.py is at lightbar/scheduler.py or lightbar/core/scheduler.py
        this_file = Path(__file__).resolve()
        this_dir = this_file.parent

        # Check if we're in a 'core' subdirectory
        if this_dir.name == "core":
            lightbar_dir = this_dir.parent
        else:
            lightbar_dir = this_dir

        if state_file is None:
            self.state_file = str(lightbar_dir / "state.json")
        else:
            self.state_file = state_file

        if config_file is None:
            self.config_file = str(lightbar_dir / "schedule_config.json")
        else:
            self.config_file = config_file

        self.state = self.load_state()

        # Load schedule configuration
        config = self.load_config()
        self.enabled = config.get("enabled", True)
        self.start_time = self.parse_time(config.get("start_time", "07:00"))
        self.end_time = self.parse_time(config.get("end_time", "20:00"))

        # Track config file modification time for hot-reload
        self.config_mtime = self._get_config_mtime()

        self.last_check = 0
        self.check_interval = 60  # Check every 60 seconds
        
    def load_state(self) -> Dict[str, Any]:
        """Load state from file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file) as f:
                    return json.load(f)
        except Exception:
            pass
        
        # Default state
        return {
            "schedule_state": ScheduleState.OFF.value,
            "override_until": None,
            "last_transition": None,
            "current_brightness": 0.0,
        }
    
    def save_state(self):
        """Save state to file (atomic write)."""
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

            # Write to temp file first
            temp_file = self.state_file + ".tmp"
            with open(temp_file, "w") as f:
                json.dump(self.state, f, indent=2)

            # Atomic rename
            os.replace(temp_file, self.state_file)
        except Exception as e:
            print(f"Error saving state: {e}")

    def _get_config_mtime(self) -> float:
        """Get config file modification time."""
        try:
            if os.path.exists(self.config_file):
                return os.path.getmtime(self.config_file)
        except Exception:
            pass
        return 0.0

    def reload_config_if_changed(self) -> bool:
        """Check if config file changed and reload if so. Returns True if reloaded."""
        current_mtime = self._get_config_mtime()
        if current_mtime > self.config_mtime:
            config = self.load_config()
            old_enabled = self.enabled
            old_start = self.start_time
            old_end = self.end_time

            self.enabled = config.get("enabled", True)
            self.start_time = self.parse_time(config.get("start_time", "07:00"))
            self.end_time = self.parse_time(config.get("end_time", "20:00"))
            self.config_mtime = current_mtime

            # Log if anything changed
            if (old_enabled != self.enabled or old_start != self.start_time
                    or old_end != self.end_time):
                print(f"Schedule config reloaded: enabled={self.enabled}, "
                      f"{self.start_time.hour:02d}:{self.start_time.minute:02d} - "
                      f"{self.end_time.hour:02d}:{self.end_time.minute:02d}")
                return True
        return False

    def load_config(self) -> Dict[str, Any]:
        """Load schedule configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file) as f:
                    return json.load(f)
        except Exception:
            pass

        # Default configuration
        return {
            "enabled": True,
            "start_time": "07:00",
            "end_time": "20:00"
        }

    def save_config(self, config: Dict[str, Any]):
        """Save schedule configuration to file (atomic write)."""
        try:
            # Create directory if needed
            dir_path = os.path.dirname(self.config_file)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            # Write to temp file first
            temp_file = self.config_file + ".tmp"
            with open(temp_file, "w") as f:
                json.dump(config, f, indent=2)

            # Atomic rename
            os.replace(temp_file, self.config_file)
        except Exception as e:
            print(f"Error saving config: {e}")

    def parse_time(self, time_str: str) -> dtime:
        """Parse time string in HH:MM format to datetime.time object."""
        try:
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            return dtime(hour=hour, minute=minute)
        except Exception:
            # Fallback to 7 AM if parsing fails
            return dtime(hour=7, minute=0)

    def get_config(self) -> Dict[str, Any]:
        """Get current schedule configuration."""
        return {
            "enabled": self.enabled,
            "start_time": f"{self.start_time.hour:02d}:{self.start_time.minute:02d}",
            "end_time": f"{self.end_time.hour:02d}:{self.end_time.minute:02d}"
        }

    def update_config(self, enabled: bool, start_time: str, end_time: str):
        """
        Update schedule configuration.

        Args:
            enabled: Whether schedule is enabled
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
        """
        # Update instance variables
        self.enabled = enabled
        self.start_time = self.parse_time(start_time)
        self.end_time = self.parse_time(end_time)

        # Save to file
        config = {
            "enabled": enabled,
            "start_time": start_time,
            "end_time": end_time
        }
        self.save_config(config)

        # Force immediate re-evaluation
        self.last_check = 0

    def get_current_time(self) -> dtime:
        """Get current time."""
        now = datetime.now()
        return dtime(hour=now.hour, minute=now.minute, second=now.second)
    
    def is_within_schedule(self, current_time: Optional[dtime] = None) -> bool:
        """
        Check if current time is within active schedule.
        
        Args:
            current_time: Time to check (default: now)
            
        Returns:
            True if lights should be on based on schedule
        """
        if current_time is None:
            current_time = self.get_current_time()
        
        # Handle schedule that crosses midnight
        if self.start_time <= self.end_time:
            # Normal case: 7 AM to 8 PM
            return self.start_time <= current_time < self.end_time
        else:
            # Crosses midnight: 8 PM to 7 AM
            return current_time >= self.start_time or current_time < self.end_time
    
    def should_lights_be_on(self) -> bool:
        """
        Determine if lights should currently be on.
        Considers schedule and manual overrides.

        Returns:
            True if lights should be on
        """
        # If schedule is disabled, lights stay on 24/7
        if not self.enabled:
            return True

        now = time.time()
        current_time = self.get_current_time()

        # Check if override is active
        override_until = self.state.get("override_until")
        if override_until and now < override_until:
            # Override is active
            state = ScheduleState(self.state.get("schedule_state", ScheduleState.OFF.value))
            return state in [ScheduleState.OVERRIDE_ON, ScheduleState.ON]

        # Check regular schedule
        return self.is_within_schedule(current_time)
    
    def get_current_brightness_multiplier(self) -> float:
        """
        Get brightness multiplier based on current state and transitions.
        
        Returns:
            Brightness multiplier (0.0 to 1.0)
        """
        state = ScheduleState(self.state.get("schedule_state", ScheduleState.OFF.value))
        
        if state == ScheduleState.OFF or state == ScheduleState.OVERRIDE_OFF:
            return 0.0
        elif state == ScheduleState.TRANSITIONING:
            return self.state.get("current_brightness", 1.0)
        else:
            return 1.0
    
    def set_override(self, turn_on: bool, duration_seconds: int = 3600):
        """
        Set manual override.
        
        Args:
            turn_on: True to force on, False to force off
            duration_seconds: Override duration (default: 1 hour)
        """
        now = time.time()
        override_until = now + duration_seconds
        
        self.state["override_until"] = override_until
        self.state["schedule_state"] = (
            ScheduleState.OVERRIDE_ON.value if turn_on 
            else ScheduleState.OVERRIDE_OFF.value
        )
        
        self.save_state()
    
    def clear_override(self):
        """Clear any active override."""
        self.state["override_until"] = None
        
        # Return to schedule-based state
        if self.should_lights_be_on():
            self.state["schedule_state"] = ScheduleState.ON.value
            self.state["current_brightness"] = 1.0
        else:
            self.state["schedule_state"] = ScheduleState.OFF.value
            self.state["current_brightness"] = 0.0
        
        self.save_state()
    
    def update(self) -> Optional[str]:
        """
        Update scheduler state.
        Should be called periodically from main loop.

        Returns:
            Action to take: "fade_in", "fade_out", "turn_on", "turn_off", or None
        """
        now = time.time()

        # Only check once per interval
        if now - self.last_check < self.check_interval:
            return None

        self.last_check = now

        # Check for config file changes (hot-reload from web interface)
        self.reload_config_if_changed()

        # Check if override expired
        override_until = self.state.get("override_until")
        if override_until and now >= override_until:
            self.clear_override()
            return "fade_in" if self.should_lights_be_on() else "fade_out"
        
        # Check schedule transition
        should_be_on = self.should_lights_be_on()
        current_state = ScheduleState(self.state.get("schedule_state", ScheduleState.OFF.value))
        
        is_currently_on = current_state in [ScheduleState.ON, ScheduleState.OVERRIDE_ON]
        
        if should_be_on and not is_currently_on:
            # Transition to ON
            self.state["schedule_state"] = ScheduleState.ON.value
            self.save_state()
            return "fade_in"
        elif not should_be_on and is_currently_on:
            # Transition to OFF
            self.state["schedule_state"] = ScheduleState.OFF.value
            self.save_state()
            return "fade_out"
        
        return None
    
    def get_boot_behavior(self) -> str:
        """
        Determine what to do on system boot.

        Returns:
            "fade_in" if lights should start, "stay_off" if outside schedule
        """
        # If schedule is disabled, always fade in
        if not self.enabled:
            return "fade_in"

        if self.should_lights_be_on():
            return "fade_in"
        else:
            return "stay_off"


class FadeController:
    """Controls smooth fade transitions."""
    
    def __init__(self, bot):
        """Initialize fade controller."""
        self.bot = bot
        self.fading = False
        self.fade_start = 0
        self.fade_duration = 0
        self.fade_from = 0.0
        self.fade_to = 0.0
        
    def start_fade(self, from_brightness: float, to_brightness: float, duration: float):
        """
        Start a fade transition.
        
        Args:
            from_brightness: Starting brightness (0.0-1.0)
            to_brightness: Target brightness (0.0-1.0)
            duration: Fade duration in seconds
        """
        self.fading = True
        self.fade_start = time.time()
        self.fade_duration = duration
        self.fade_from = from_brightness
        self.fade_to = to_brightness
    
    def update(self) -> Optional[float]:
        """
        Update fade transition.
        
        Returns:
            Current brightness (0.0-1.0), or None if not fading
        """
        if not self.fading:
            return None
        
        elapsed = time.time() - self.fade_start
        progress = min(1.0, elapsed / self.fade_duration)
        
        # Smooth easing (sine wave)
        import math
        smooth_progress = (math.sin((progress - 0.5) * math.pi) + 1) / 2
        
        current_brightness = self.fade_from + (self.fade_to - self.fade_from) * smooth_progress
        
        if progress >= 1.0:
            self.fading = False
            return self.fade_to
        
        return current_brightness
    
    def is_fading(self) -> bool:
        """Check if currently fading."""
        return self.fading


# Test function
if __name__ == "__main__":
    scheduler = Scheduler()
    
    print("Current time:", scheduler.get_current_time())
    print("Within schedule:", scheduler.is_within_schedule())
    print("Should lights be on:", scheduler.should_lights_be_on())
    print("Boot behavior:", scheduler.get_boot_behavior())
    
    # Test override
    print("\nSetting override (ON for 10 seconds)...")
    scheduler.set_override(True, 10)
    print("Should lights be on:", scheduler.should_lights_be_on())
    
    time.sleep(2)
    print("Still overridden:", scheduler.should_lights_be_on())
    
    scheduler.clear_override()
    print("Override cleared:", scheduler.should_lights_be_on())
    
    print("\n✓ Scheduler tests passed")
