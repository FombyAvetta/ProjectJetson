#!/usr/bin/env python3
"""
Custom CubeNano RGB Light Controller
Based on Yahboom CUBE NANO I2C Protocol
I2C Address: 0x0E, Bus: 7
"""

import smbus2
import time
from typing import Tuple

class CubeNano:
    """Control interface for Yahboom CUBE NANO case RGB light bar."""
    
    # I2C Registers
    REG_LED_SELECT = 0x00      # Select LED (0-13, or 255 for all)
    REG_RED = 0x01             # Red brightness (0-255)
    REG_GREEN = 0x02           # Green brightness (0-255)
    REG_BLUE = 0x03            # Blue brightness (0-255)
    REG_EFFECT = 0x04          # RGB effect mode (0-6)
    REG_SPEED = 0x05           # Effect speed (1-3)
    REG_COLOR = 0x06           # Effect color preset (0-6)
    REG_OFF = 0x07             # Turn off RGB
    REG_FAN = 0x08             # Fan control (0=on, 1=off)
    
    # Effect modes
    EFFECT_OFF = 0
    EFFECT_BREATHING = 1
    EFFECT_MARQUEE = 2
    EFFECT_RAINBOW = 3
    EFFECT_COLORFUL = 4
    EFFECT_RUNNING = 5
    EFFECT_CYCLE_BREATHING = 6
    
    # Speed settings
    SPEED_LOW = 1
    SPEED_MEDIUM = 2
    SPEED_HIGH = 3
    
    # Color presets
    COLOR_RED = 0
    COLOR_GREEN = 1
    COLOR_BLUE = 2
    COLOR_YELLOW = 3
    COLOR_PURPLE = 4
    COLOR_CYAN = 5
    COLOR_WHITE = 6
    
    # LED IDs
    LED_ALL = 255
    LED_COUNT = 14  # LEDs 0-13
    
    # Timing constants
    I2C_WRITE_DELAY = 0.025    # 10ms delay between I2C writes
    I2C_COMMAND_DELAY = 0.030  # 20ms delay after complete commands
    
    def __init__(self, i2c_bus: int = 7, i2c_address: int = 0x0E):
        """
        Initialize CubeNano controller.
        
        Args:
            i2c_bus: I2C bus number (default 7 for /dev/i2c-7)
            i2c_address: I2C device address (default 0x0E)
        """
        self.i2c_bus = i2c_bus
        self.i2c_address = i2c_address
        self.bus = None
        self._init_i2c()
        
    def _init_i2c(self):
        """Initialize I2C bus connection."""
        try:
            self.bus = smbus2.SMBus(self.i2c_bus)
            time.sleep(0.05)  # Initial settling time
        except Exception as e:
            raise RuntimeError(f"Failed to initialize I2C bus {self.i2c_bus}: {e}")
    
    def _write_register(self, register: int, value: int, retry_count: int = 3):
        """
        Write a value to an I2C register with retry logic.
        
        Args:
            register: Register address
            value: Value to write (0-255)
            retry_count: Number of retries on failure
        """
        for attempt in range(retry_count):
            try:
                self.bus.write_byte_data(self.i2c_address, register, value)
                time.sleep(self.I2C_WRITE_DELAY)
                return
            except (OSError, TimeoutError) as e:
                if attempt == retry_count - 1:
                    # Final attempt failed
                    raise RuntimeError(f"I2C write failed after {retry_count} attempts: {e}")
                # Wait longer before retry
                time.sleep(0.05)
    
    def set_RGB(self, led_id: int, red: int, green: int, blue: int):
        """
        Set RGB color for specific LED or all LEDs.
        
        Args:
            led_id: LED index (0-13) or 255 for all LEDs
            red: Red brightness (0-255)
            green: Green brightness (0-255)
            blue: Blue brightness (0-255)
        """
        if led_id != self.LED_ALL and not (0 <= led_id < self.LED_COUNT):
            raise ValueError(f"Invalid LED ID: {led_id}")
        
        red = max(0, min(255, int(red)))
        green = max(0, min(255, int(green)))
        blue = max(0, min(255, int(blue)))
        
        self._write_register(self.REG_LED_SELECT, led_id)
        self._write_register(self.REG_RED, red)
        self._write_register(self.REG_GREEN, green)
        self._write_register(self.REG_BLUE, blue)
        time.sleep(self.I2C_COMMAND_DELAY)  # Extra delay after complete command
    
    def set_all_RGB(self, red: int, green: int, blue: int):
        """
        Set RGB color for all LEDs.
        
        Args:
            red: Red brightness (0-255)
            green: Green brightness (0-255)
            blue: Blue brightness (0-255)
        """
        self.set_RGB(self.LED_ALL, red, green, blue)
    
    def set_effect(self, effect: int, speed: int = SPEED_MEDIUM, color: int = COLOR_WHITE):
        """
        Set built-in RGB effect.
        
        Args:
            effect: Effect mode (0-6)
            speed: Effect speed (1-3)
            color: Color preset (0-6)
        """
        if not (0 <= effect <= 6):
            raise ValueError(f"Invalid effect: {effect}")
        if not (1 <= speed <= 3):
            raise ValueError(f"Invalid speed: {speed}")
        if not (0 <= color <= 6):
            raise ValueError(f"Invalid color: {color}")
        
        self._write_register(self.REG_EFFECT, effect)
        self._write_register(self.REG_SPEED, speed)
        self._write_register(self.REG_COLOR, color)
        time.sleep(self.I2C_COMMAND_DELAY)
    
    def turn_off(self):
        """Turn off all RGB lights."""
        self._write_register(self.REG_OFF, 0)
        time.sleep(self.I2C_COMMAND_DELAY)
    
    def set_fan(self, enabled: bool):
        """
        Control the cooling fan.
        
        Args:
            enabled: True to turn on fan, False to turn off
        """
        self._write_register(self.REG_FAN, 0 if enabled else 1)
        time.sleep(self.I2C_COMMAND_DELAY)
    
    def close(self):
        """Close I2C bus connection."""
        if self.bus:
            try:
                self.bus.close()
            except:
                pass
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

# Convenience functions for common colors
def rgb_from_hex(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """
    Convert HSV color to RGB.
    
    Args:
        h: Hue (0.0-1.0)
        s: Saturation (0.0-1.0)
        v: Value/Brightness (0.0-1.0)
    
    Returns:
        RGB tuple (0-255, 0-255, 0-255)
    """
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)

if __name__ == '__main__':
    # Simple test
    print("CubeNano Library - Testing RGB lights")
    try:
        with CubeNano(i2c_bus=7) as bot:
            print("✓ I2C connection established")
            
            # Test: Red
            print("Setting RED...")
            bot.set_all_RGB(255, 0, 0)
            time.sleep(1)
            
            # Test: Green
            print("Setting GREEN...")
            bot.set_all_RGB(0, 255, 0)
            time.sleep(1)
            
            # Test: Blue
            print("Setting BLUE...")
            bot.set_all_RGB(0, 0, 255)
            time.sleep(1)
            
            # Test: Turn off
            print("Turning OFF...")
            bot.turn_off()
            
            print("✓ All tests passed!")
    except Exception as e:
        print(f"✗ Error: {e}")
