"""
Randomness Engine Module
Calculates chaos/randomness factor based on system load.
Higher system load = more chaotic visual effects.
"""

import logging

logger = logging.getLogger(__name__)


def calculate_randomness(cpu_percent: float, ram_percent: float, temperature: float) -> float:
    """
    Calculate randomness factor from 1.0 (calm) to 5.0 (maximum chaos).

    Formula:
    - CPU contributes 60% of load calculation
    - RAM contributes 40% of load calculation
    - Temperature above 70°C adds bonus chaos (up to +1.0)

    Args:
        cpu_percent: CPU usage (0-100)
        ram_percent: RAM usage (0-100)
        temperature: CPU temperature in Celsius

    Returns:
        float: Randomness factor from 1.0 to 5.0
    """
    # Normalize CPU and RAM to 0-1 range
    cpu_normalized = min(cpu_percent / 100.0, 1.0)
    ram_normalized = min(ram_percent / 100.0, 1.0)

    # Calculate base load (weighted: 60% CPU, 40% RAM)
    base_load = (cpu_normalized * 0.6) + (ram_normalized * 0.4)

    # Temperature bonus: adds chaos for temps above 70°C
    # Scales from 0.0 at 70°C to 1.0 at 85°C or higher
    temp_bonus = 0.0
    if temperature > 70:
        temp_bonus = min((temperature - 70) / 15.0, 1.0)

    # Base randomness: 1.0 (calm) to 4.0 (very chaotic)
    # Temperature bonus: 0.0 to 1.0 additional chaos
    # Total range: 1.0 to 5.0
    randomness = 1.0 + (base_load * 3.0) + temp_bonus

    # Clamp to 1.0-5.0 range
    randomness = max(1.0, min(5.0, randomness))

    return randomness


def apply_timing_jitter(base_speed: float, randomness: float) -> float:
    """
    Apply timing jitter to effect speed based on randomness.

    Args:
        base_speed: Base speed multiplier
        randomness: Randomness factor (1.0-5.0)

    Returns:
        float: Modified speed with jitter applied
    """
    import random

    # Jitter amount scales with randomness
    # At randomness=1.0: no jitter
    # At randomness=5.0: up to ±50% jitter
    jitter_amount = (randomness - 1.0) / 4.0 * 0.5  # 0.0 to 0.5

    # Apply random jitter
    jitter = 1.0 + random.uniform(-jitter_amount, jitter_amount)

    return base_speed * jitter


def get_led_count_for_randomness(base_count: int, randomness: float, max_leds: int = 6) -> int:
    """
    Calculate how many LEDs should be active based on randomness.

    Args:
        base_count: Minimum number of LEDs to light
        randomness: Randomness factor (1.0-5.0)
        max_leds: Maximum LEDs available

    Returns:
        int: Number of LEDs to activate
    """
    # At randomness=1.0: use base_count
    # At randomness=5.0: use up to max_leds
    scaling_factor = (randomness - 1.0) / 4.0  # 0.0 to 1.0

    additional_leds = int((max_leds - base_count) * scaling_factor)

    return min(base_count + additional_leds, max_leds)


def should_trigger_effect(base_probability: float, randomness: float) -> bool:
    """
    Determine if an effect should trigger based on probability and randomness.

    Args:
        base_probability: Base probability (0.0-1.0)
        randomness: Randomness factor (1.0-5.0)

    Returns:
        bool: True if effect should trigger
    """
    import random

    # Scale probability with randomness
    # At randomness=1.0: use base probability
    # At randomness=5.0: probability is doubled (more frequent)
    scaled_probability = base_probability * (1.0 + (randomness - 1.0) / 4.0)
    scaled_probability = min(scaled_probability, 1.0)

    return random.random() < scaled_probability


def get_transition_abruptness(randomness: float) -> float:
    """
    Get transition abruptness factor.

    Args:
        randomness: Randomness factor (1.0-5.0)

    Returns:
        float: Abruptness factor (1.0 = smooth, 5.0 = very abrupt)
    """
    # Higher randomness = more abrupt transitions
    return randomness
