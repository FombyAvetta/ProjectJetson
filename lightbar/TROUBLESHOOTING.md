# Troubleshooting Guide

Common issues and solutions for the Jetson RGB Light Bar Controller.

## Table of Contents

- [Service Won't Start](#service-wont-start)
- [Lights Not Responding](#lights-not-responding)
- [Web Interface Not Accessible](#web-interface-not-accessible)
- [Effects Not Changing](#effects-not-changing)
- [Brightness Not Working](#brightness-not-working)
- [I2C Errors](#i2c-errors)
- [High CPU Usage](#high-cpu-usage)
- [Service Crashes](#service-crashes)
- [OLED Sync Issues](#oled-sync-issues)
- [Schedule Not Working](#schedule-not-working)

---

## Service Won't Start

### Symptoms
- `systemctl status lightbar` shows "failed" or "inactive (dead)"
- Service exits immediately after starting

### Diagnostic Steps

1. **Check service status**:
   ```bash
   sudo systemctl status lightbar
   ```

2. **View recent logs**:
   ```bash
   journalctl -u lightbar -n 50
   ```

3. **Run pre-start checks**:
   ```bash
   /home/john/lightbar/scripts/pre-start-checks.sh
   ```

### Common Causes & Solutions

#### Invalid config.json
**Symptom**: Pre-start check fails with "Invalid JSON"

**Solution**:
```bash
# Validate JSON syntax
python3 -c "import json; json.load(open('/home/john/lightbar/config.json'))"

# If invalid, restore from backup or fix syntax
# JSON must be valid: proper quotes, commas, brackets
```

#### I2C Device Not Found
**Symptom**: Pre-start check fails with "I2C device /dev/i2c-7 not found"

**Solution**:
```bash
# Check if I2C device exists
ls -l /dev/i2c-*

# Check I2C modules loaded
lsmod | grep i2c

# Load I2C dev module if needed
sudo modprobe i2c-dev
```

#### Permission Issues
**Symptom**: "Permission denied" on I2C device

**Solution**:
```bash
# Add user to i2c group
sudo usermod -a -G i2c john

# Log out and back in for group change to take effect
# Or run: newgrp i2c

# Check group membership
groups john
```

#### Missing Dependencies
**Symptom**: "ModuleNotFoundError: No module named 'flask'" or similar

**Solution**:
```bash
# Install Python dependencies
pip3 install flask flask-sock psutil --user

# Verify installation
python3 -c "import flask, psutil; print('OK')"
```

---

## Lights Not Responding

### Symptoms
- Service running but lights don't turn on
- No visible light changes when changing effects

### Diagnostic Steps

1. **Check if service is running**:
   ```bash
   ps aux | grep lightbar_controller
   ```

2. **Test I2C communication**:
   ```bash
   i2cdetect -y 7
   # Should show device at address 0x0E
   ```

3. **Check logs for I2C errors**:
   ```bash
   journalctl -u lightbar -n 100 | grep -i error
   ```

### Common Causes & Solutions

#### I2C Bus Busy
**Symptom**: I2C timeout errors in logs

**Solution**:
```bash
# Check if OLED is using the bus
ps aux | grep oled_stats

# Temporarily stop OLED to test
pkill -f oled_stats

# Test lights directly
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/john')
from CubeNano import CubeNano
bot = CubeNano(i2c_bus=7, i2c_address=14)
bot.set_all_RGB(255, 0, 0)  # Should show red
EOF
```

#### Lights Disabled
**Symptom**: Service running, no errors, but lights off

**Solution**:
```bash
# Check if lights are disabled
curl http://localhost:5001/api/status | python3 -m json.tool

# Enable lights
curl -X POST http://localhost:5001/api/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

#### Wrong I2C Address
**Symptom**: No errors but lights don't respond

**Solution**:
```bash
# Scan I2C bus for devices
i2cdetect -y 7

# If device is not at 0x0E, update config.json
# "address": XX (use decimal, not hex)
```

---

## Web Interface Not Accessible

### Symptoms
- Cannot access `http://<jetson-ip>:5001`
- Browser shows "Connection refused" or "Timeout"

### Diagnostic Steps

1. **Check if web server is running**:
   ```bash
   ps aux | grep server.py
   ```

2. **Check if port is listening**:
   ```bash
   netstat -tulpn | grep 5001
   # or
   ss -tulpn | grep 5001
   ```

3. **Test local access**:
   ```bash
   curl http://localhost:5001/api/status
   ```

### Common Causes & Solutions

#### Web Server Not Started
**Symptom**: No server.py process running

**Solution**:
```bash
# Restart the service
sudo systemctl restart lightbar

# Or start web server manually
cd /home/john/lightbar/web
python3 server.py --port 5001 &
```

#### Firewall Blocking
**Symptom**: Local access works, remote access fails

**Solution**:
```bash
# Check firewall rules
sudo iptables -L -n

# Allow port 5001 if needed
sudo iptables -A INPUT -p tcp --dport 5001 -j ACCEPT

# Or disable firewall temporarily to test
sudo ufw disable
```

#### Wrong IP Address
**Symptom**: Cannot access from network

**Solution**:
```bash
# Check Jetson's IP address
hostname -I

# Access using correct IP
# http://[JETSON_IP]:5001
```

---

## Effects Not Changing

### Symptoms
- Changing effect in web UI has no visible result
- All effects look the same

### Diagnostic Steps

1. **Check if commands are being written**:
   ```bash
   cat /tmp/lightbar_control.json
   # Should show current effect name
   ```

2. **Check controller logs**:
   ```bash
   journalctl -u lightbar -f
   # Should see "Changed effect to: XXX" messages
   ```

3. **Verify effect is registered**:
   ```bash
   curl http://localhost:5001/api/status | python3 -m json.tool | grep effect
   ```

### Common Causes & Solutions

#### Brightness Too Low
**Symptom**: Effects changing in logs but not visible

**Solution**:
```bash
# Increase brightness
curl -X POST http://localhost:5001/api/brightness \
  -H "Content-Type: application/json" \
  -d '{"brightness": 100}'
```

#### Demo Mode Active
**Symptom**: Effect changes but immediately reverts

**Solution**:
Wait 30 seconds for demo mode to complete, or restart service.

#### Effect Not Loaded
**Symptom**: Specific effect doesn't work

**Solution**:
```bash
# Check available effects
curl http://localhost:5001/api/status | python3 -m json.tool | grep available_effects

# Try a different effect
curl -X POST http://localhost:5001/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "system_pulse"}'
```

---

## Brightness Not Working

### Symptoms
- Brightness slider in UI doesn't affect light intensity
- Lights always at full brightness or off

### Diagnostic Steps

1. **Check brightness value**:
   ```bash
   curl http://localhost:5001/api/status | python3 -m json.tool | grep brightness
   ```

2. **Test brightness changes**:
   ```bash
   # Try different levels
   for level in 25 50 75 100; do
     curl -X POST http://localhost:5001/api/brightness \
       -H "Content-Type: application/json" \
       -d "{\"brightness\": $level}"
     sleep 3
   done
   ```

### Common Causes & Solutions

#### BrightnessWrapper Not Working
**Symptom**: Brightness changes logged but no visual change

**Solution**:
```bash
# Check controller logs for BrightnessWrapper debug messages
journalctl -u lightbar -n 200 | grep BrightnessWrapper

# Restart service
sudo systemctl restart lightbar
```

#### Lights Disabled
**Symptom**: Brightness set but lights still off

**Solution**:
```bash
# Ensure lights are enabled
curl -X POST http://localhost:5001/api/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

---

## I2C Errors

### Symptoms
- Logs show "I2C errors occurred (N since last log)"
- Occasional LED flicker or glitches

### Diagnostic Steps

1. **Check error rate**:
   ```bash
   journalctl -u lightbar -f | grep "I2C errors"
   # Note the frequency and count
   ```

2. **Check I2C bus usage**:
   ```bash
   i2cdetect -y 7
   # Should show devices at 0x0E (RGB) and 0x3C (OLED)
   ```

### Common Causes & Solutions

#### Shared Bus Contention
**Symptom**: 15-30 errors per minute (normal)

**This is expected behavior** due to bus sharing with OLED. No action needed.

**If errors are excessive (>50/minute)**:
```bash
# Stop OLED temporarily to test
sudo systemctl stop oled-stats  # or pkill -f oled_stats

# If errors stop, adjust I2C timing in CubeNano.py:
# Increase I2C_WRITE_DELAY and I2C_COMMAND_DELAY
```

#### Hardware Issues
**Symptom**: Constant I2C failures, lights non-functional

**Solution**:
```bash
# Check physical connections
# Verify I2C device
i2cdetect -y 7

# Try rebooting
sudo reboot
```

---

## High CPU Usage

### Symptoms
- Controller using >5% CPU
- System becomes sluggish

### Diagnostic Steps

1. **Check CPU usage**:
   ```bash
   top -p $(pgrep -f lightbar_controller)
   ```

2. **Check frame rate**:
   ```bash
   journalctl -u lightbar -n 50 | grep "Performance:"
   ```

### Common Causes & Solutions

#### Too High Frame Rate
**Symptom**: FPS higher than expected

**Solution**:
Edit `/home/john/lightbar/config.json`:
```json
{
  "performance": {
    "update_interval": 0.5,  // Increase to reduce FPS
    "target_fps": 2          // Lower target FPS
  }
}
```

Then restart: `sudo systemctl restart lightbar`

#### Effect Too Complex
**Symptom**: CPU spikes with certain effects

**Solution**:
Switch to a simpler effect like `system_pulse`:
```bash
curl -X POST http://localhost:5001/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "system_pulse"}'
```

---

## Service Crashes

### Symptoms
- Service stops unexpectedly
- `systemctl status lightbar` shows "failed"

### Diagnostic Steps

1. **Check crash logs**:
   ```bash
   journalctl -u lightbar -n 100 | grep -i error
   ```

2. **Check Python tracebacks**:
   ```bash
   journalctl -u lightbar -n 200 | grep -A 10 "Traceback"
   ```

3. **Check system logs**:
   ```bash
   dmesg | tail -50
   ```

### Common Causes & Solutions

#### Python Exception
**Symptom**: Traceback in logs

**Solution**:
```bash
# Restart service (systemd will auto-retry)
sudo systemctl restart lightbar

# If crash persists, check code for bugs
# Report issue with full traceback
```

#### Out of Memory
**Symptom**: "Killed" message in logs

**Solution**:
```bash
# Check memory limit
systemctl show lightbar | grep MemoryLimit

# Increase if needed (edit /etc/systemd/system/lightbar.service)
MemoryLimit=200M

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart lightbar
```

#### Systemd Rate Limiting
**Symptom**: Service won't restart after multiple crashes

**Solution**:
```bash
# Reset failed state
sudo systemctl reset-failed lightbar

# Start again
sudo systemctl start lightbar
```

---

## OLED Sync Issues

### Symptoms
- Logs show "OLED state is stale"
- Red pulsing error mode

### Diagnostic Steps

1. **Check OLED monitor status**:
   ```bash
   ps aux | grep oled_stats
   ```

2. **Check shared state file**:
   ```bash
   cat /tmp/jetson_state.json
   # Check timestamp is recent
   ```

### Common Causes & Solutions

#### OLED Monitor Not Running
**Symptom**: No oled_stats process

**Solution**:
```bash
# Start OLED monitor
cd /home/john/jetson_oled_monitor
python3 oled_stats.py &

# Or if it has a systemd service
sudo systemctl start oled-stats
```

#### Stale State File
**Symptom**: OLED running but state file old

**Solution**:
```bash
# Check OLED monitor logs
cat /tmp/oled_stats.log

# Restart OLED monitor
pkill -f oled_stats
cd /home/john/jetson_oled_monitor
python3 oled_stats.py &
```

#### OLED I2C Conflicts
**Symptom**: Both OLED and lights having I2C errors

**Solution**:
Increase I2C timing delays in both applications.

---

## Schedule Not Working

### Symptoms
- Lights don't turn on/off at scheduled times
- No fade transitions at 7 AM / 8 PM

### Diagnostic Steps

1. **Check system time**:
   ```bash
   date
   # Ensure time is correct
   ```

2. **Check schedule config**:
   ```bash
   python3 -c "import json; print(json.load(open('/home/john/lightbar/config.json'))['schedule'])"
   ```

3. **Check logs for schedule events**:
   ```bash
   journalctl -u lightbar -f | grep -i "fade"
   ```

### Common Causes & Solutions

#### Schedule Disabled
**Symptom**: No schedule activity

**Solution**:
Edit `/home/john/lightbar/config.json`:
```json
{
  "schedule": {
    "enabled": true,
    "start_hour": 7,
    "end_hour": 20
  }
}
```

Restart: `sudo systemctl restart lightbar`

#### Wrong Timezone
**Symptom**: Schedule activates at wrong time

**Solution**:
```bash
# Check timezone
timedatectl

# Set correct timezone if needed
sudo timedatectl set-timezone America/Denver
```

#### Manual Override Active
**Symptom**: Schedule not working

**Solution**:
Clear manual override by restarting service:
```bash
sudo systemctl restart lightbar
```

---

## Diagnostic Commands Reference

### Quick Health Check
```bash
# Service status
sudo systemctl status lightbar

# Processes running
ps aux | grep -E 'lightbar_controller|server.py'

# API status
curl http://localhost:5001/api/status

# I2C devices
i2cdetect -y 7

# Recent logs
journalctl -u lightbar -n 50
```

### Performance Check
```bash
# CPU usage
top -p $(pgrep -f lightbar_controller) -n 1

# Memory usage
ps aux | grep lightbar_controller | awk '{print $6/1024 " MB"}'

# Frame rate
journalctl -u lightbar -n 50 | grep "Performance:"
```

### Network Check
```bash
# Port listening
ss -tulpn | grep 5001

# Test API
curl -v http://localhost:5001/api/status

# Test from remote
curl -v http://<jetson-ip>:5001/api/status
```

---

## Recovery Procedures

### Complete Reset
```bash
# Stop service
sudo systemctl stop lightbar

# Clear state files
rm -f /tmp/lightbar_control.json
rm -f /tmp/lightbar/web.pid

# Restart service
sudo systemctl start lightbar
```

### Reinstall Service
```bash
# Stop and disable service
sudo systemctl stop lightbar
sudo systemctl disable lightbar

# Remove service file
sudo rm /etc/systemd/system/lightbar.service

# Reinstall
cd /home/john/lightbar/scripts
sudo ./install.sh

# Start service
sudo systemctl start lightbar
```

### Factory Reset Configuration
```bash
# Backup current config
cp /home/john/lightbar/config.json /home/john/lightbar/config.json.backup

# Restore default (if you have a default config file)
# Or manually edit config.json to restore defaults
```

---

## Getting Help

If issues persist:

1. **Collect diagnostic information**:
   ```bash
   # Save logs
   journalctl -u lightbar -n 500 > /tmp/lightbar_debug.log

   # Save system info
   uname -a > /tmp/system_info.txt
   cat /etc/os-release >> /tmp/system_info.txt

   # Save config
   cat /home/john/lightbar/config.json > /tmp/config_debug.json
   ```

2. **Check hardware**:
   ```bash
   i2cdetect -y 7
   ls -l /dev/i2c-*
   ```

3. **Test in isolation**:
   Stop all services and test hardware directly with Python.

4. **Provide details**:
   - Jetson model and JetPack version
   - Full error messages and tracebacks
   - Steps to reproduce the issue
   - Recent changes to the system
