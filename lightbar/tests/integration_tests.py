#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite
Tests all major functionality of the light bar system
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:5001"
TESTS_PASSED = 0
TESTS_FAILED = 0

def test(name, func):
    """Run a test and track results."""
    global TESTS_PASSED, TESTS_FAILED
    try:
        print(f"Testing: {name}...", end=" ")
        func()
        print("✓ PASS")
        TESTS_PASSED += 1
        return True
    except AssertionError as e:
        print(f"✗ FAIL: {e}")
        TESTS_FAILED += 1
        return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        TESTS_FAILED += 1
        return False

# ===== API TESTS =====

def test_api_status():
    """Test GET /api/status endpoint."""
    r = requests.get(f"{BASE_URL}/api/status", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert data["success"] == True, "success should be True"
    assert "metrics" in data["data"], "Missing metrics"
    assert "effect" in data["data"], "Missing effect"
    assert "brightness" in data["data"], "Missing brightness"

def test_api_change_effect():
    """Test POST /api/mode endpoint."""
    r = requests.post(
        f"{BASE_URL}/api/mode",
        json={"mode": "load_rainbow"},
        headers={"Content-Type": "application/json"},
        timeout=5
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert data["success"] == True, "success should be True"
    assert data["effect"] == "load_rainbow", f"Expected load_rainbow, got {data['effect']}"

def test_api_set_brightness():
    """Test POST /api/brightness endpoint."""
    r = requests.post(
        f"{BASE_URL}/api/brightness",
        json={"brightness": 75},
        headers={"Content-Type": "application/json"},
        timeout=5
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert data["success"] == True, "success should be True"
    assert data["brightness"] == 75, f"Expected 75, got {data['brightness']}"

def test_api_toggle_off():
    """Test POST /api/toggle (disable)."""
    r = requests.post(
        f"{BASE_URL}/api/toggle",
        json={"enabled": False},
        headers={"Content-Type": "application/json"},
        timeout=5
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert data["success"] == True, "success should be True"
    assert data["enabled"] == False, "Expected enabled=False"

def test_api_toggle_on():
    """Test POST /api/toggle (enable)."""
    r = requests.post(
        f"{BASE_URL}/api/toggle",
        json={"enabled": True},
        headers={"Content-Type": "application/json"},
        timeout=5
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert data["success"] == True, "success should be True"
    assert data["enabled"] == True, "Expected enabled=True"

def test_api_demo_mode():
    """Test POST /api/demo endpoint."""
    r = requests.post(
        f"{BASE_URL}/api/demo",
        json={},
        headers={"Content-Type": "application/json"},
        timeout=5
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    data = r.json()
    assert data["success"] == True, "success should be True"

# ===== EFFECT TESTS =====

def test_all_effects():
    """Test cycling through all 5 effects."""
    effects = ["system_pulse", "load_rainbow", "random_sparkle", "thermal_gradient", "load_bars"]
    for effect in effects:
        r = requests.post(
            f"{BASE_URL}/api/mode",
            json={"mode": effect},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        assert r.status_code == 200, f"Failed to set effect {effect}"
        data = r.json()
        assert data["effect"] == effect, f"Effect mismatch for {effect}"
        time.sleep(2)  # Let effect run for 2 seconds

# ===== BRIGHTNESS TESTS =====

def test_brightness_range():
    """Test brightness at various levels."""
    levels = [10, 25, 50, 75, 100]
    for level in levels:
        r = requests.post(
            f"{BASE_URL}/api/brightness",
            json={"brightness": level},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        assert r.status_code == 200, f"Failed to set brightness {level}"
        data = r.json()
        assert data["brightness"] == level, f"Brightness mismatch: expected {level}, got {data['brightness']}"
        time.sleep(1)

# ===== PERFORMANCE TESTS =====

def test_api_response_time():
    """Test API response time is under 100ms."""
    start = time.time()
    r = requests.get(f"{BASE_URL}/api/status", timeout=5)
    elapsed = (time.time() - start) * 1000  # Convert to ms
    assert elapsed < 100, f"Response time {elapsed:.1f}ms exceeds 100ms limit"

def test_metrics_update():
    """Test that metrics are being updated."""
    r1 = requests.get(f"{BASE_URL}/api/status", timeout=5)
    time.sleep(2)
    r2 = requests.get(f"{BASE_URL}/api/status", timeout=5)

    data1 = r1.json()["data"]["metrics"]
    data2 = r2.json()["data"]["metrics"]

    # At least one metric should have changed
    changed = (
        data1["cpu_percent"] != data2["cpu_percent"] or
        data1["ram_percent"] != data2["ram_percent"] or
        data1["temperature"] != data2["temperature"]
    )
    assert changed, "Metrics not updating"

# ===== MAIN TEST RUNNER =====

def main():
    """Run all integration tests."""
    global TESTS_PASSED, TESTS_FAILED

    print("=" * 60)
    print("LIGHT BAR INTEGRATION TEST SUITE")
    print("=" * 60)
    print()

    print("=== API ENDPOINT TESTS ===")
    test("API Status Endpoint", test_api_status)
    test("API Change Effect", test_api_change_effect)
    test("API Set Brightness", test_api_set_brightness)
    test("API Toggle Off", test_api_toggle_off)
    test("API Toggle On", test_api_toggle_on)
    test("API Demo Mode", test_api_demo_mode)
    print()

    print("=== EFFECT TESTS ===")
    test("All 5 Effects Cycle", test_all_effects)
    print()

    print("=== BRIGHTNESS TESTS ===")
    test("Brightness Range (10-100%)", test_brightness_range)
    print()

    print("=== PERFORMANCE TESTS ===")
    test("API Response Time <100ms", test_api_response_time)
    test("Metrics Update", test_metrics_update)
    print()

    print("=" * 60)
    print(f"RESULTS: {TESTS_PASSED} passed, {TESTS_FAILED} failed")
    print("=" * 60)

    return 0 if TESTS_FAILED == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
