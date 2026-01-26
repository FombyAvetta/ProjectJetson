#\!/usr/bin/env python3
"""
Jetson RGB Light Bar Controller
System-reactive lighting with OLED synchronization
"""

import sys
import os
# Add parent directory to path for CubeNano import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hardware'))

import json
import logging
import math
import psutil
import time
import signal
from pathlib import Path
from typing import Dict, Any, Optional

from CubeNano import CubeNano
from effects import create_effect, EffectEngine
from oled_sync import OLEDSync
from brightness_wrapper import BrightnessWrapper
from scheduler import Scheduler, FadeController

class LightBarController:
    """Main controller for RGB light bar with system-reactive effects."""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize controller."""
        self.config_path = config_path
        self.config = self.load_config()
        self.setup_logging()
        
        self.logger.info("Initializing Light Bar Controller...")
        
        # Initialize hardware
        self.raw_bot = CubeNano(
            i2c_bus=self.config["i2c"]["bus"],
            i2c_address=self.config["i2c"]["address"]
        )
        # Wrap bot to apply brightness automatically
        self.bot = BrightnessWrapper(self.raw_bot, self)
        
        # State
        self.running = False
        self.current_effect_name = self.config["effects"]["default_effect"]
        self.current_effect: Optional[EffectEngine] = None
        self.brightness_multiplier = self.config["display"]["brightness_multiplier"]
        
        # Demo mode
        self.demo_mode_active = False
        self.demo_mode_start_time = 0
        self.demo_mode_previous_effect = None
        self.demo_mode_effects = ["system_pulse", "load_rainbow", "random_sparkle", "thermal_gradient", "load_bars"]
        self.demo_mode_duration = 30.0  # seconds
        
        # Metrics
        self.system_metrics = {
            "cpu_percent": 0.0,
            "ram_percent": 0.0,
            "temperature": 50.0,
            "load_average": 0.0,
            "system_load": 0.0,  # Normalized 0.0-1.0
        }
        
        # Performance tracking
        self.frame_count = 0
        self.start_time = time.time()
        self.last_metrics_update = 0
        
        # Scheduler and fade control
        self.scheduler = Scheduler()
        self.fade_controller = FadeController(self.bot)
        
        # OLED synchronization
        self.oled_sync = OLEDSync()
        self.oled_error_mode_active = False
        
        # Check boot behavior
        boot_behavior = self.scheduler.get_boot_behavior()
        if boot_behavior == "fade_in":
            self.logger.info("Boot within schedule - will fade in")
        else:
            self.logger.info("Boot outside schedule - staying off")
            self.brightness_multiplier = 0.0
        self.error_count = 0
        self.last_error_log = 0
        self.last_control_check = 0
        self.control_check_interval = 0.5
        
        self.logger.info("✓ Controller initialized")
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            print("Using default configuration")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "i2c": {"bus": 7, "address": 14},
            "performance": {"update_interval": 0.1, "target_fps": 10},
            "effects": {
                "default_effect": "system_pulse",
                "available_effects": ["system_pulse", "load_rainbow", 
                                      "random_sparkle", "thermal_gradient", "load_bars"]
            },
            "display": {"brightness": 100, "brightness_multiplier": 1.0},
            "thresholds": {"low_load": 30, "medium_load": 60, "high_load": 80},
            "logging": {
                "level": "INFO",
                "file": "./logs/lightbar.log"
            },
            "thermal": {
                "sensor_path": "/sys/class/thermal/thermal_zone0/temp"
            }
        }
    
    def setup_logging(self):
        """Configure logging."""
        log_config = self.config.get("logging", {})
        log_file = log_config.get("file", "./logs/lightbar.log")
        log_level = log_config.get("level", "INFO")
        
        # Create log directory
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Configure logger
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("LightBarController")
    
    def collect_system_metrics(self):
        """Collect current system metrics (prefer OLED data when available)."""
        try:
            # Try to get metrics from OLED shared state first
            oled_metrics = self.oled_sync.get_system_metrics()
            
            if oled_metrics:
                # Use OLED data (fresher and avoids redundant syscalls)
                self.system_metrics["cpu_percent"] = oled_metrics["cpu_percent"]
                self.system_metrics["ram_percent"] = oled_metrics["ram_percent"]
                self.system_metrics["temperature"] = oled_metrics["temperature"]
                self.system_metrics["load_average"] = oled_metrics["load_average"][0]
            else:
                # Fallback to direct collection if OLED unavailable
                self.system_metrics["cpu_percent"] = psutil.cpu_percent(interval=None)
                
                mem = psutil.virtual_memory()
                self.system_metrics["ram_percent"] = mem.percent
                
                load_avg = os.getloadavg()[0]
                self.system_metrics["load_average"] = load_avg
                
                try:
                    temp_path = self.config["thermal"]["sensor_path"]
                    with open(temp_path) as f:
                        temp_millidegrees = int(f.read().strip())
                        self.system_metrics["temperature"] = temp_millidegrees / 1000.0
                except:
                    self.system_metrics["temperature"] = 50.0
            
            # Calculate normalized system load (0.0 to 1.0)
            cpu_norm = self.system_metrics["cpu_percent"] / 100.0
            ram_norm = self.system_metrics["ram_percent"] / 100.0
            load_avg = self.system_metrics["load_average"]
            cpu_count = psutil.cpu_count()
            load_norm = min(1.0, load_avg / cpu_count)
            
            system_load = (cpu_norm * 0.6) + (ram_norm * 0.3) + (load_norm * 0.1)
            self.system_metrics["system_load"] = min(1.0, max(0.0, system_load))
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")

    def handle_oled_health(self):
        """Check OLED health and provide visual feedback."""
        is_healthy, state = self.oled_sync.check_oled_health()

        # Check if showing recovery flash (green)
        if self.oled_sync.is_showing_recovery_flash():
            # Green flash for recovery
            self.bot.set_all_RGB(0, 255, 0)
            self.oled_error_mode_active = False
            return

        # Check if OLED is down
        if not is_healthy:
            if not self.oled_error_mode_active:
                self.logger.error("OLED monitor down - activating error mode")
                self.oled_error_mode_active = True

            # Red pulse error mode
            pulse = (math.sin(time.time() * 2.0) + 1) / 2  # 0.0 to 1.0
            brightness = int(128 + pulse * 127)  # 128 to 255
            self.bot.set_all_RGB(brightness, 0, 0)
            return

        # OLED is healthy, clear error mode
        if self.oled_error_mode_active:
            self.oled_error_mode_active = False

            
    
    def calculate_randomness(self) -> float:
        """
        Calculate randomness factor based on system load.
        Returns 1.0 to 5.0 (higher = more chaotic)
        """
        cpu = self.system_metrics["cpu_percent"]
        ram = self.system_metrics["ram_percent"]
        temp = self.system_metrics["temperature"]
        
        # Base randomness from CPU (60%) and RAM (40%)
        base_randomness = 1.0 + ((cpu * 0.6 + ram * 0.4) / 100.0) * 3.0
        
        # Temperature bonus (above 70°C adds chaos)
        if temp > 70:
            temp_bonus = min(1.0, (temp - 70) / 20.0)
            base_randomness += temp_bonus
        
        return min(5.0, base_randomness)

    def start_demo_mode(self):
        """Start demo mode - cycles through all effects with ramping randomness."""
        if self.demo_mode_active:
            self.logger.warning("Demo mode already active")
            return False

        self.logger.info("Starting demo mode (30 seconds)")
        self.demo_mode_active = True
        self.demo_mode_start_time = time.time()
        self.demo_mode_previous_effect = self.current_effect_name

        # Start with first effect
        self.set_effect(self.demo_mode_effects[0])

        return True

    def update_demo_mode(self):
        """Update demo mode - handle effect transitions and randomness ramping."""
        if not self.demo_mode_active:
            return

        elapsed = time.time() - self.demo_mode_start_time

        # Check if demo mode should end
        if elapsed >= self.demo_mode_duration:
            self.end_demo_mode()
            return

        # Calculate which effect should be active
        # 30 seconds / 5 effects = 6 seconds per effect
        effect_duration = self.demo_mode_duration / len(self.demo_mode_effects)
        effect_index = int(elapsed / effect_duration)
        effect_index = min(effect_index, len(self.demo_mode_effects) - 1)

        # Switch effect if needed
        target_effect = self.demo_mode_effects[effect_index]
        if target_effect != self.current_effect_name:
            self.logger.info(f"Demo mode: switching to {target_effect}")
            self.set_effect(target_effect)

    def end_demo_mode(self):
        """End demo mode and return to previous effect."""
        self.logger.info("Demo mode complete - returning to previous effect")
        self.demo_mode_active = False

        # Return to previous effect
        if self.demo_mode_previous_effect:
            self.set_effect(self.demo_mode_previous_effect)

        self.demo_mode_previous_effect = None

    def calculate_randomness_override(self) -> Optional[float]:
        """Calculate randomness override for demo mode."""
        if not self.demo_mode_active:
            return None

        elapsed = time.time() - self.demo_mode_start_time
        progress = elapsed / self.demo_mode_duration  # 0.0 to 1.0

        # Ramp randomness from 1.0 to 5.0 over the demo
        randomness = 1.0 + (progress * 4.0)
        return min(5.0, randomness)

    
    def set_effect(self, effect_name: str):
        """Change current effect."""
        if effect_name not in self.config["effects"]["available_effects"]:
            self.logger.warning(f"Unknown effect: {effect_name}")
            return False
        
        try:
            self.current_effect_name = effect_name
            self.current_effect = create_effect(effect_name, self.bot)
            self.logger.info(f"Changed effect to: {effect_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error setting effect: {e}")
            return False
    
    def set_brightness(self, brightness: float):
        """
        Set brightness multiplier.
        
        Args:
            brightness: 0.0 to 1.0
        """
        self.brightness_multiplier = max(0.0, min(1.0, brightness))
        self.logger.info(f"Brightness set to: {self.brightness_multiplier:.0%}")
    
    def update_effect(self):
        """Update current effect with latest metrics."""
        if not self.current_effect:
            return
        
        # Skip updates if lights are disabled
        if self.brightness_multiplier <= 0:
            return
        
        try:
            randomness = self.calculate_randomness()
            
            # Call appropriate update method based on effect type
            if self.current_effect_name == "thermal_gradient":
                self.current_effect.update(
                    self.system_metrics["system_load"],
                    self.system_metrics["temperature"],
                    randomness
                )
            elif self.current_effect_name == "load_bars":
                self.current_effect.update(
                    self.system_metrics["cpu_percent"],
                    self.system_metrics["ram_percent"],
                    randomness
                )
            else:
                self.current_effect.update(
                    self.system_metrics["system_load"],
                    randomness
                )
                
        except Exception as e:
            self.error_count += 1
            # Only log errors once per minute to avoid spam
            now = time.time()
            if now - self.last_error_log > 60:
                self.logger.warning(
                    f"I2C errors occurred ({self.error_count} since last log). "
                    "This is normal due to shared I2C bus with OLED display."
                )
                self.error_count = 0
                self.last_error_log = now
    
    def check_control_commands(self):
        """Check and apply commands from web interface."""
        try:
            from shared_state import read_control_state, update_control_state
            control = read_control_state()
            
            # Apply enable/disable FIRST
            enabled = control.get("enabled", True)
            if not enabled:
                # Disable lights
                if self.brightness_multiplier > 0:
                    self.brightness_multiplier = 0
                    self.bot.turn_off()
                    self.logger.info("Lights disabled via web interface")
            else:
                # Only apply changes if enabled
                
                # Apply effect change
                if control.get("effect") != self.current_effect_name:
                    new_effect = control["effect"]
                    if new_effect in self.config["effects"]["available_effects"]:
                        self.set_effect(new_effect)
                
                # Apply brightness change (only when enabled and not fading)
                if not self.fade_controller.is_fading():
                    new_brightness = control.get("brightness", 100) / 100.0
                    if abs(new_brightness - self.brightness_multiplier) > 0.01:
                        # If currently at 0 (was disabled), restore brightness
                        if self.brightness_multiplier == 0:
                            self.logger.info(f"Lights enabled via web interface at {int(new_brightness * 100)}%")
                        else:
                            self.logger.info(f"Brightness changed to {int(new_brightness * 100)}%")
                        self.brightness_multiplier = new_brightness
            
            # Check demo mode
            if control.get("demo_mode", False):
                update_control_state(demo_mode=False)  # Clear flag
                self.start_demo_mode()
                
        except Exception as e:
            self.logger.error(f"Error checking control commands: {e}")
    

    def run(self):
        """Main control loop."""
        self.running = True
        self.logger.info("Starting main control loop...")
        
        # Initialize effect
        self.set_effect(self.current_effect_name)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        target_interval = self.config["performance"]["update_interval"]
        
        try:
            while self.running:
                loop_start = time.time()
                
                
                # Check scheduler for transitions
                action = self.scheduler.update()
                if action == "fade_in":
                    self.logger.info("Starting fade in (3 seconds)")
                    self.fade_controller.start_fade(0.0, 1.0, 3.0)
                elif action == "fade_out":
                    self.logger.info("Starting fade out (2 seconds)")
                    self.fade_controller.start_fade(1.0, 0.0, 2.0)

                # Update fade controller and apply brightness
                fade_brightness = self.fade_controller.update()
                if fade_brightness is not None:
                    self.brightness_multiplier = fade_brightness

                # Check web control commands
                if loop_start - self.last_control_check > self.control_check_interval:
                    self.check_control_commands()
                    self.last_control_check = loop_start

                # Collect metrics periodically (every 500ms)
                if loop_start - self.last_metrics_update > 0.5:
                    self.collect_system_metrics()
                    self.last_metrics_update = loop_start

                # Update demo mode (handles effect transitions)
                self.update_demo_mode()
                
                # Update effect
                self.update_effect()
                
                # Frame counting
                self.frame_count += 1
                
                # Log performance stats every 10 seconds
                if self.frame_count % 100 == 0:
                    elapsed = time.time() - self.start_time
                    fps = self.frame_count / elapsed
                    self.logger.debug(
                        f"Performance: {fps:.1f} FPS | "
                        f"CPU: {self.system_metrics['cpu_percent']:.1f}% | "
                        f"RAM: {self.system_metrics['ram_percent']:.1f}% | "
                        f"Temp: {self.system_metrics['temperature']:.1f}°C | "
                        f"Load: {self.system_metrics['system_load']:.2f}"
                    )
                
                # Sleep to maintain target FPS
                loop_duration = time.time() - loop_start
                sleep_time = max(0, target_interval - loop_duration)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        finally:
            self.shutdown()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def shutdown(self):
        """Graceful shutdown."""
        self.logger.info("Shutting down...")
        
        try:
            # Turn off lights
            self.raw_bot.turn_off()
            self.raw_bot.close()
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        
        # Final stats
        elapsed = time.time() - self.start_time
        fps = self.frame_count / elapsed if elapsed > 0 else 0
        self.logger.info(f"Final stats: {self.frame_count} frames in {elapsed:.1f}s ({fps:.1f} FPS)")
        self.logger.info("Shutdown complete")


def main():
    """Entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Jetson RGB Light Bar Controller")
    parser.add_argument("--config", default="config.json",
                        help="Path to configuration file")
    parser.add_argument("--effect", help="Override default effect")
    parser.add_argument("--test", action="store_true", 
                        help="Run for 30 seconds and exit")
    
    args = parser.parse_args()
    
    # Create controller
    controller = LightBarController(config_path=args.config)
    
    # Override effect if specified
    if args.effect:
        controller.set_effect(args.effect)
    
    # Test mode
    if args.test:
        print("Running in test mode (30 seconds)...")
        controller.running = True
        controller.set_effect(controller.current_effect_name)
        
        for _ in range(300):  # 30 seconds at 10 FPS
            controller.collect_system_metrics()
            controller.update_effect()
            time.sleep(0.1)
        
        controller.shutdown()
        print("✓ Test complete")
        return 0
    
    # Normal operation
    try:
        controller.run()
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        controller.shutdown()
        return 0
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

