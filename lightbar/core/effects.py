#!/usr/bin/env python3
"""
System-Reactive RGB Light Bar Effects
Each effect scales with system load (0.0 = idle, 1.0 = maximum load)
"""

import sys
import os
# Add hardware directory to path for CubeNano import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'hardware'))

from CubeNano import CubeNano, hsv_to_rgb
import math
import time
import random
from typing import Dict, Any

class EffectEngine:
    """Base engine for managing RGB light effects with system load reactivity."""
    
    def __init__(self, bot: CubeNano):
        self.bot = bot
        self.frame_count = 0
        self.start_time = time.time()
        
    def get_elapsed(self) -> float:
        """Get elapsed time since effect started."""
        return time.time() - self.start_time
    
    def reset(self):
        """Reset effect state."""
        self.frame_count = 0
        self.start_time = time.time()


class SystemPulseEffect(EffectEngine):
    """
    Breathing/pulsing effect that changes color and speed based on load.
    Low load: slow green pulse
    High load: fast red pulse
    """
    
    def update(self, system_load: float, randomness: float = 1.0):
        """
        Update pulse effect.
        
        Args:
            system_load: 0.0-1.0 (0=idle, 1=max load)
            randomness: 1.0-5.0 (chaos multiplier)
        """
        # Speed increases with load (0.5-4.0 Hz)
        base_speed = 0.5 + (system_load * 3.5)
        speed = base_speed * randomness
        
        # Calculate pulse using sine wave
        t = self.get_elapsed()
        pulse = (math.sin(t * speed * 2 * math.pi) + 1) / 2  # 0.0 to 1.0
        
        # Add jitter at high randomness
        if randomness > 2.0:
            jitter = random.uniform(-0.1, 0.1) * (randomness - 2.0) / 3.0
            pulse = max(0, min(1, pulse + jitter))
        
        # Color transitions: green -> yellow -> orange -> red
        if system_load < 0.3:
            # Green zone
            hue = 0.33  # Green
        elif system_load < 0.6:
            # Yellow zone
            hue = 0.33 - ((system_load - 0.3) / 0.3) * 0.16  # Green to yellow
        elif system_load < 0.8:
            # Orange zone
            hue = 0.17 - ((system_load - 0.6) / 0.2) * 0.08  # Yellow to orange
        else:
            # Red zone
            hue = 0.0  # Red
        
        # Apply brightness pulse
        brightness = 0.3 + (pulse * 0.7)  # 30% to 100%
        r, g, b = hsv_to_rgb(hue, 1.0, brightness)
        
        self.bot.set_all_RGB(r, g, b)
        self.frame_count += 1


class LoadRainbowEffect(EffectEngine):
    """
    Rainbow cycle effect where speed increases with system load.
    Low load: 3-second smooth cycle
    High load: 0.5-second rapid cycle
    """
    
    def update(self, system_load: float, randomness: float = 1.0):
        """
        Update rainbow effect.
        
        Args:
            system_load: 0.0-1.0
            randomness: 1.0-5.0 (chaos multiplier)
        """
        # Cycle speed increases with load
        base_cycle_time = 3.0 - (system_load * 2.5)  # 3.0s to 0.5s
        cycle_time = base_cycle_time / randomness
        
        t = self.get_elapsed()
        
        # Calculate hue position (0.0 to 1.0, wrapping)
        hue = (t / cycle_time) % 1.0
        
        # Add chaos: random hue jumps at high randomness
        if randomness > 3.0 and random.random() < 0.1:
            hue = random.random()
        
        # Full saturation and brightness
        r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
        
        self.bot.set_all_RGB(r, g, b)
        self.frame_count += 1


class RandomSparkleEffect(EffectEngine):
    """
    Random LED sparkles with frequency tied to load.
    Low load: occasional single sparkles
    High load: many simultaneous sparkles
    """
    
    def __init__(self, bot: CubeNano):
        super().__init__(bot)
        self.led_states = [0.0] * 14  # Brightness for each LED
        self.led_colors = [(0, 0, 0)] * 14
        
    def update(self, system_load: float, randomness: float = 1.0):
        """
        Update sparkle effect.
        
        Args:
            system_load: 0.0-1.0
            randomness: 1.0-5.0 (chaos multiplier)
        """
        # Decay existing sparkles
        decay_rate = 0.85
        for i in range(14):
            self.led_states[i] *= decay_rate
        
        # Spawn new sparkles based on load
        base_spawn_chance = 0.05 + (system_load * 0.3)  # 5% to 35%
        spawn_chance = base_spawn_chance * randomness
        
        for i in range(14):
            if random.random() < spawn_chance:
                # Spawn sparkle
                self.led_states[i] = 1.0
                
                # Color based on load
                if system_load < 0.4:
                    # Cool colors (blue, cyan)
                    hue = random.uniform(0.5, 0.66)
                elif system_load < 0.7:
                    # Warm colors (yellow, orange)
                    hue = random.uniform(0.08, 0.17)
                else:
                    # Hot colors (red, magenta)
                    hue = random.choice([random.uniform(0.0, 0.08), random.uniform(0.8, 1.0)])
                
                r, g, b = hsv_to_rgb(hue, 1.0, 1.0)
                self.led_colors[i] = (r, g, b)
        
        # Update all LEDs
        for i in range(14):
            brightness = self.led_states[i]
            if brightness > 0.01:
                r, g, b = self.led_colors[i]
                r = int(r * brightness)
                g = int(g * brightness)
                b = int(b * brightness)
                self.bot.set_RGB(i, r, g, b)
            else:
                self.bot.set_RGB(i, 0, 0, 0)
        
        self.frame_count += 1
        
    def reset(self):
        """Reset sparkle states."""
        super().reset()
        self.led_states = [0.0] * 14
        self.led_colors = [(0, 0, 0)] * 14


class ThermalGradientEffect(EffectEngine):
    """
    Temperature-based color gradient with pulse speed tied to load.
    Cool: blue (<50°C)
    Warm: orange (50-70°C)
    Hot: red (>70°C)
    Pulse speed increases with system load.
    """
    
    def update(self, system_load: float, temp_celsius: float = 50.0, randomness: float = 1.0):
        """
        Update thermal gradient effect.
        
        Args:
            system_load: 0.0-1.0
            temp_celsius: Current temperature in Celsius
            randomness: 1.0-5.0 (chaos multiplier)
        """
        # Determine color based on temperature
        if temp_celsius < 50:
            # Cool (blue)
            hue = 0.6
            temp_factor = temp_celsius / 50.0
        elif temp_celsius < 70:
            # Warm (blue to orange)
            temp_factor = (temp_celsius - 50) / 20.0
            hue = 0.6 - (temp_factor * 0.5)  # Blue to orange
        else:
            # Hot (orange to red)
            temp_factor = min(1.0, (temp_celsius - 70) / 20.0)
            hue = 0.1 - (temp_factor * 0.1)  # Orange to red
        
        # Pulse speed increases with load
        base_speed = 0.5 + (system_load * 2.5)
        speed = base_speed * randomness
        
        t = self.get_elapsed()
        pulse = (math.sin(t * speed * 2 * math.pi) + 1) / 2
        
        # Brightness varies with pulse
        brightness = 0.4 + (pulse * 0.6)
        
        r, g, b = hsv_to_rgb(hue, 1.0, brightness)
        self.bot.set_all_RGB(r, g, b)
        self.frame_count += 1


class LoadBarsEffect(EffectEngine):
    """
    CPU/RAM visualization as animated bars.
    CPU = cyan, RAM = magenta
    Scrolling effect tied to activity level.
    """
    
    def __init__(self, bot: CubeNano):
        super().__init__(bot)
        self.scroll_position = 0
        
    def update(self, cpu_percent: float, ram_percent: float, randomness: float = 1.0):
        """
        Update load bars effect.
        
        Args:
            cpu_percent: CPU usage 0-100
            ram_percent: RAM usage 0-100
            randomness: 1.0-5.0 (chaos multiplier)
        """
        # Calculate how many LEDs to light for each metric (0-7 LEDs each)
        cpu_leds = int((cpu_percent / 100.0) * 7)
        ram_leds = int((ram_percent / 100.0) * 7)
        
        # Scroll speed based on activity
        avg_load = (cpu_percent + ram_percent) / 200.0  # 0.0-1.0
        base_scroll_speed = 0.5 + (avg_load * 2.0)
        scroll_speed = base_scroll_speed * randomness
        
        # Update scroll position
        t = self.get_elapsed()
        self.scroll_position = int(t * scroll_speed * 10) % 14
        
        # Build LED array
        for i in range(14):
            # Determine if this LED should show CPU or RAM
            offset_pos = (i - self.scroll_position) % 14
            
            if offset_pos < 7:
                # CPU section (cyan)
                if offset_pos < cpu_leds:
                    # Brightness gradient
                    brightness = 1.0 - (offset_pos / 7.0) * 0.5
                    r, g, b = hsv_to_rgb(0.5, 1.0, brightness)  # Cyan
                    self.bot.set_RGB(i, r, g, b)
                else:
                    self.bot.set_RGB(i, 0, 0, 0)
            else:
                # RAM section (magenta)
                ram_pos = offset_pos - 7
                if ram_pos < ram_leds:
                    brightness = 1.0 - (ram_pos / 7.0) * 0.5
                    r, g, b = hsv_to_rgb(0.83, 1.0, brightness)  # Magenta
                    self.bot.set_RGB(i, r, g, b)
                else:
                    self.bot.set_RGB(i, 0, 0, 0)
        
        self.frame_count += 1
    
    def reset(self):
        """Reset scroll position."""
        super().reset()
        self.scroll_position = 0


# Effect registry
EFFECTS = {
    "system_pulse": SystemPulseEffect,
    "load_rainbow": LoadRainbowEffect,
    "random_sparkle": RandomSparkleEffect,
    "thermal_gradient": ThermalGradientEffect,
    "load_bars": LoadBarsEffect,
}


def create_effect(effect_name: str, bot: CubeNano) -> EffectEngine:
    """
    Create an effect instance.
    
    Args:
        effect_name: Name of the effect
        bot: CubeNano controller instance
        
    Returns:
        Effect instance
    """
    if effect_name not in EFFECTS:
        raise ValueError(f"Unknown effect: {effect_name}. Available: {list(EFFECTS.keys())}")
    
    return EFFECTS[effect_name](bot)


if __name__ == "__main__":
    """Test all effects."""
    print("Testing all effects...")
    
    with CubeNano(i2c_bus=7) as bot:
        # Test system_pulse
        print("\n1. System Pulse (low load)")
        effect = SystemPulseEffect(bot)
        for _ in range(30):
            effect.update(0.2)
            time.sleep(0.05)
        
        print("2. System Pulse (high load)")
        effect.reset()
        for _ in range(30):
            effect.update(0.9)
            time.sleep(0.05)
        
        # Test load_rainbow
        print("3. Load Rainbow (slow)")
        effect = LoadRainbowEffect(bot)
        for _ in range(40):
            effect.update(0.1)
            time.sleep(0.05)
        
        # Test random_sparkle
        print("4. Random Sparkle")
        effect = RandomSparkleEffect(bot)
        for _ in range(60):
            effect.update(0.5)
            time.sleep(0.05)
        
        # Test thermal_gradient
        print("5. Thermal Gradient")
        effect = ThermalGradientEffect(bot)
        for i in range(40):
            temp = 40 + (i * 1.5)  # Simulate temperature rise
            effect.update(0.5, temp)
            time.sleep(0.05)
        
        # Test load_bars
        print("6. Load Bars")
        effect = LoadBarsEffect(bot)
        for i in range(60):
            cpu = 20 + (i % 40) * 2
            ram = 40 + (i % 30) * 1.5
            effect.update(cpu, ram)
            time.sleep(0.05)
        
        bot.turn_off()
        print("\n✓ All effects tested successfully!")
