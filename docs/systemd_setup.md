# Systemd Service Setup Guide

Guide for installing and managing ProjectJetson services with systemd.

## Overview

Both the RGB light bar and OLED monitor run as systemd services, providing:
- Automatic startup on boot
- Process monitoring and restart on failure
- Centralized logging with journald
- Service dependency management
- Clean shutdown procedures

## Service Files

### RGB Light Bar Service

File: `lightbar/lightbar.service`

```ini
[Unit]
Description=RGB Light Bar Controller
After=network.target

[Service]
Type=simple
User=john
WorkingDirectory=/home/john/lightbar
ExecStart=/usr/bin/python3 /home/john/lightbar/lightbar_controller.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### OLED Monitor Service

File: `oled_monitor/oled-stats.service`

```ini
[Unit]
Description=Jetson OLED Stats Monitor
After=network.target

[Service]
Type=simple
User=john
WorkingDirectory=/home/john/jetson_oled_monitor
ExecStart=/usr/bin/python3 /home/john/jetson_oled_monitor/oled_stats.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Installation Instructions

### RGB Light Bar

1. **Edit service file paths:**
   ```bash
   cd lightbar
   nano lightbar.service
   ```

   Update these fields:
   - `User=` - Your username
   - `WorkingDirectory=` - Full path to lightbar directory
   - `ExecStart=` - Full path to Python and script

2. **Copy service file:**
   ```bash
   sudo cp lightbar.service /etc/systemd/system/
   ```

3. **Set permissions:**
   ```bash
   sudo chmod 644 /etc/systemd/system/lightbar.service
   ```

4. **Reload systemd:**
   ```bash
   sudo systemctl daemon-reload
   ```

5. **Enable service:**
   ```bash
   sudo systemctl enable lightbar.service
   ```

6. **Start service:**
   ```bash
   sudo systemctl start lightbar.service
   ```

### OLED Monitor

Follow the same steps, replacing "lightbar" with "oled-stats":

```bash
cd oled_monitor
# Edit oled-stats.service with your paths
sudo cp oled-stats.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/oled-stats.service
sudo systemctl daemon-reload
sudo systemctl enable oled-stats.service
sudo systemctl start oled-stats.service
```

## Service Management

### Starting and Stopping

```bash
# Start service
sudo systemctl start lightbar.service

# Stop service
sudo systemctl stop lightbar.service

# Restart service
sudo systemctl restart lightbar.service

# Reload configuration (if service supports it)
sudo systemctl reload lightbar.service
```

### Enable and Disable

```bash
# Enable service (start on boot)
sudo systemctl enable lightbar.service

# Disable service (don't start on boot)
sudo systemctl disable lightbar.service

# Check if service is enabled
systemctl is-enabled lightbar.service
```

### Checking Status

```bash
# Full status information
sudo systemctl status lightbar.service

# Check if service is running
systemctl is-active lightbar.service

# Check if service failed
systemctl is-failed lightbar.service
```

## Viewing Logs

### Using journalctl

```bash
# View all logs for service
journalctl -u lightbar.service

# Follow logs in real-time
journalctl -u lightbar.service -f

# Show last 100 lines
journalctl -u lightbar.service -n 100

# Show logs since last boot
journalctl -u lightbar.service -b

# Show logs from last hour
journalctl -u lightbar.service --since "1 hour ago"

# Show logs from date range
journalctl -u lightbar.service --since "2024-01-20" --until "2024-01-21"

# Show logs with priority (error and above)
journalctl -u lightbar.service -p err
```

### Log Priority Levels

- 0: emerg (emergency)
- 1: alert
- 2: crit (critical)
- 3: err (error)
- 4: warning
- 5: notice
- 6: info
- 7: debug

## Troubleshooting

### Service Won't Start

1. **Check service status:**
   ```bash
   sudo systemctl status lightbar.service
   ```

2. **View detailed logs:**
   ```bash
   journalctl -u lightbar.service -n 50
   ```

3. **Check file permissions:**
   ```bash
   ls -l /home/john/lightbar/lightbar_controller.py
   ```
   Should be readable by the user specified in service file.

4. **Verify Python path:**
   ```bash
   which python3
   ```
   Update `ExecStart=` if path differs.

5. **Test script manually:**
   ```bash
   cd /home/john/lightbar
   python3 lightbar_controller.py
   ```

### Service Keeps Restarting

1. **Check for errors in logs:**
   ```bash
   journalctl -u lightbar.service -f
   ```

2. **Common issues:**
   - Missing dependencies: `pip3 install -r requirements.txt`
   - Configuration errors: Validate `config.json`
   - I2C permissions: Check `/dev/i2c-*` permissions
   - Hardware not connected: Verify I2C devices

3. **Disable auto-restart temporarily:**
   Edit service file and comment out:
   ```ini
   # Restart=always
   ```
   Then:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart lightbar.service
   ```

### Permission Denied Errors

1. **For I2C access:**
   ```bash
   sudo usermod -a -G i2c john
   sudo reboot
   ```

2. **For file access:**
   Check ownership of working directory:
   ```bash
   ls -la /home/john/lightbar
   chown -R john:john /home/john/lightbar
   ```

### Service Status Shows "Failed"

1. **Reset failed state:**
   ```bash
   sudo systemctl reset-failed lightbar.service
   ```

2. **Start service again:**
   ```bash
   sudo systemctl start lightbar.service
   ```

## Advanced Configuration

### Service Dependencies

If OLED monitor should start before lightbar:

Edit `lightbar.service`:
```ini
[Unit]
Description=RGB Light Bar Controller
After=network.target oled-stats.service
Wants=oled-stats.service
```

### Resource Limits

Limit CPU and memory usage:

```ini
[Service]
CPUQuota=50%
MemoryLimit=500M
```

### Environment Variables

Pass environment variables to service:

```ini
[Service]
Environment="PYTHONUNBUFFERED=1"
Environment="CONFIG_PATH=/etc/lightbar/config.json"
```

### Restart Policy

Customize restart behavior:

```ini
[Service]
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=5
```

This allows 5 restart attempts within 300 seconds.

### Logging Configuration

Customize log handling:

```ini
[Service]
StandardOutput=journal
StandardError=journal
SyslogIdentifier=lightbar
```

## Service Templates

### Service with Pre-Start Checks

```ini
[Unit]
Description=RGB Light Bar Controller
After=network.target

[Service]
Type=simple
User=john
WorkingDirectory=/home/john/lightbar
ExecStartPre=/home/john/lightbar/scripts/pre-start-checks.sh
ExecStart=/usr/bin/python3 /home/john/lightbar/lightbar_controller.py
ExecStop=/home/john/lightbar/scripts/stop.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Service with Virtual Environment

```ini
[Service]
Type=simple
User=john
WorkingDirectory=/home/john/lightbar
ExecStart=/home/john/lightbar/venv/bin/python3 /home/john/lightbar/lightbar_controller.py
```

## Systemd Timer (Alternative to Cron)

For periodic tasks instead of continuous running:

Create `lightbar-timer.service`:
```ini
[Unit]
Description=RGB Light Bar Periodic Update

[Service]
Type=oneshot
User=john
WorkingDirectory=/home/john/lightbar
ExecStart=/usr/bin/python3 /home/john/lightbar/update_status.py
```

Create `lightbar-timer.timer`:
```ini
[Unit]
Description=Run RGB Light Bar Update Every 5 Minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

Enable timer:
```bash
sudo systemctl enable lightbar-timer.timer
sudo systemctl start lightbar-timer.timer
```

## Best Practices

### 1. Use Non-Root User
Run services as non-root user when possible. Use `User=` directive.

### 2. Specify Working Directory
Always set `WorkingDirectory=` to avoid path issues.

### 3. Enable Logging
Use `StandardOutput=journal` and `StandardError=journal` for centralized logging.

### 4. Set Restart Policy
Use `Restart=always` or `Restart=on-failure` for reliability.

### 5. Add Dependencies
Use `After=` and `Wants=` to specify service dependencies.

### 6. Test Before Enabling
Always test service manually before enabling auto-start:
```bash
sudo systemctl start lightbar.service
sudo systemctl status lightbar.service
# If working correctly:
sudo systemctl enable lightbar.service
```

### 7. Document Custom Changes
Add comments to service files explaining customizations.

### 8. Version Control Service Files
Keep service files in your repository for easy deployment.

## Monitoring Service Health

### Create Status Check Script

`check_services.sh`:
```bash
#!/bin/bash

services=("lightbar.service" "oled-stats.service")

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        echo "✓ $service is running"
    else
        echo "✗ $service is NOT running"
        journalctl -u "$service" -n 20 --no-pager
    fi
done
```

### Run on Cron

```bash
# Add to crontab
crontab -e

# Check every 5 minutes
*/5 * * * * /home/john/check_services.sh >> /home/john/service_health.log
```

## Uninstalling Services

```bash
# Stop service
sudo systemctl stop lightbar.service

# Disable service
sudo systemctl disable lightbar.service

# Remove service file
sudo rm /etc/systemd/system/lightbar.service

# Reload systemd
sudo systemctl daemon-reload

# Reset any failed states
sudo systemctl reset-failed
```

## References

- [systemd.service Manual](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [systemd.unit Manual](https://www.freedesktop.org/software/systemd/man/systemd.unit.html)
- [journalctl Manual](https://www.freedesktop.org/software/systemd/man/journalctl.html)
- [Understanding Systemd Units](https://www.digitalocean.com/community/tutorials/understanding-systemd-units-and-unit-files)
