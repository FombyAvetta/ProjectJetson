#!/usr/bin/env python3
"""
Brightness wrapper for CubeNano bot
Intercepts RGB commands and applies brightness multiplier
"""

class BrightnessWrapper:
    """Wraps CubeNano to apply brightness to all RGB commands."""
    
    def __init__(self, bot, controller):
        """
        Initialize wrapper.
        
        Args:
            bot: CubeNano instance
            controller: Controller instance (for brightness_multiplier)
        """
        self.bot = bot
        self.controller = controller
        self.debug_count = 0
    
    def set_RGB(self, led_id, red, green, blue):
        """Apply brightness and set RGB."""
        brightness = self.controller.brightness_multiplier
        r = int(red * brightness)
        g = int(green * brightness)
        b = int(blue * brightness)
        self.bot.set_RGB(led_id, r, g, b)
    
    def set_all_RGB(self, red, green, blue):
        """Apply brightness and set all RGB."""
        brightness = self.controller.brightness_multiplier
        r = int(red * brightness)
        g = int(green * brightness)
        b = int(blue * brightness)
        
        # Debug: log occasionally
        self.debug_count += 1
        if self.debug_count % 100 == 0:
            print(f"[BrightnessWrapper] brightness={brightness:.2f}, in=({red},{green},{blue}), out=({r},{g},{b})")
        
        self.bot.set_all_RGB(r, g, b)
    
    def turn_off(self):
        """Turn off lights."""
        self.bot.turn_off()
    
    def set_effect(self, *args, **kwargs):
        """Pass through to bot."""
        return self.bot.set_effect(*args, **kwargs)
    
    def set_fan(self, *args, **kwargs):
        """Pass through to bot."""
        return self.bot.set_fan(*args, **kwargs)
    
    def close(self):
        """Pass through to bot."""
        return self.bot.close()
