# OLED Monitor

Real-time system monitoring display for NVIDIA Jetson devices using a 128x64 I2C OLED screen.

## Features

- **Multi-Screen Display:** Rotating views of different system metrics
- **Real-Time Stats:**
  - CPU usage per core with frequencies
  - GPU usage and temperature
  - Memory and swap utilization
  - Network speed (upload/download)
  - Disk usage by partition
  - Docker container status
  - System temperature monitoring

- **Alert System:** Visual warnings when thresholds are exceeded
- **Shared State:** Publishes health status for integration with other systems (e.g., RGB light bar)
- **Boot Splash:** Custom startup animation
- **Configurable:** JSON-based configuration for all features and thresholds

## Hardware Requirements

- NVIDIA Jetson device (Orin Nano, Xavier NX, or compatible)
- 128x64 I2C OLED display (SSD1306 compatible)
- I2C connection on bus 7 (configurable)

## Installation

1. Install dependencies:
```bash
pip3 install -r requirements.txt
```

2. Create configuration file:
```bash
cp config.json.example config.json
```

3. Edit configuration as needed:
```bash
nano config.json
```

4. Install systemd service:
```bash
sudo cp oled-stats.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable oled-stats.service
sudo systemctl start oled-stats.service
```

## Configuration

Edit `config.json` to customize behavior:

```json
{
    "refresh_rate": 1,
    "i2c_bus": 7,
    "screen_rotation_interval": 5,
    "boot_splash_duration": 2,
    "features": {
        "show_gpu": true,
        "show_temperature": true,
        "show_network_speed": true,
        "show_disk_usage": true,
        "show_docker": true,
        "rotate_screens": true,
        "show_alerts": true,
        "boot_splash": true
    },
    "alerts": {
        "cpu_threshold": 90,
        "memory_threshold": 85,
        "temperature_threshold": 80,
        "disk_threshold": 90
    }
}
```

### Configuration Options

- **refresh_rate:** Display update frequency in seconds (default: 1)
- **i2c_bus:** I2C bus number for OLED (default: 7)
- **screen_rotation_interval:** Seconds between screen changes (default: 5)
- **boot_splash_duration:** Duration of startup animation in seconds (default: 2)

### Features
- **show_gpu:** Display GPU usage and temperature
- **show_temperature:** Show system temperature sensors
- **show_network_speed:** Display network upload/download speeds
- **show_disk_usage:** Show disk usage by partition
- **show_docker:** Display Docker container status
- **rotate_screens:** Auto-rotate between different views
- **show_alerts:** Display visual warnings when thresholds exceeded
- **boot_splash:** Show startup animation on launch

### Alert Thresholds
- **cpu_threshold:** CPU usage percentage to trigger alert (default: 90)
- **memory_threshold:** Memory usage percentage to trigger alert (default: 85)
- **temperature_threshold:** Temperature in Celsius to trigger alert (default: 80)
- **disk_threshold:** Disk usage percentage to trigger alert (default: 90)

## Usage

### Start/Stop Service
```bash
# Start
sudo systemctl start oled-stats.service

# Stop
sudo systemctl stop oled-stats.service

# Restart
sudo systemctl restart oled-stats.service

# Check status
sudo systemctl status oled-stats.service
```

### View Logs
```bash
# Real-time logs
journalctl -u oled-stats.service -f

# Recent logs
journalctl -u oled-stats.service -n 100
```

### Manual Run (for testing)
```bash
python3 oled_stats.py
```

## Shared State Integration

The OLED monitor publishes its health status to `/tmp/jetson_state.json` for integration with other systems:

```json
{
    "oled_healthy": true,
    "timestamp": 1234567890.123,
    "cpu_percent": 45.2,
    "temperature": 55.3,
    "memory_percent": 62.1
}
```

Other systems (like the RGB light bar) can read this file to:
- Monitor OLED health status
- Display alerts if OLED becomes unresponsive
- Synchronize effects based on system metrics

## Troubleshooting

### OLED Not Displaying
1. Check I2C connection:
```bash
i2cdetect -y 7
```
You should see a device at address 0x3C (or your configured address).

2. Verify I2C permissions:
```bash
sudo usermod -a -G i2c $USER
```
Log out and back in for group changes to take effect.

3. Check service status:
```bash
sudo systemctl status oled-stats.service
journalctl -u oled-stats.service -n 50
```

### Display Flickering
- Increase `refresh_rate` in config.json (e.g., from 1 to 2 seconds)
- Check I2C signal quality and cable length

### Missing Metrics
- GPU stats require proper NVIDIA drivers
- Docker stats require Docker to be installed and running
- Network stats require active network interfaces

### Service Won't Start
1. Check Python dependencies:
```bash
pip3 list | grep -E "luma|psutil|Pillow"
```

2. Verify configuration file:
```bash
python3 -m json.tool config.json
```

3. Check permissions:
```bash
ls -l /dev/i2c-*
```

## Performance Notes

- The OLED monitor uses minimal CPU (typically <2%)
- Memory footprint is approximately 50-80 MB
- I2C communication is non-blocking
- Display refresh can be adjusted for performance

## License

MIT License - See main repository LICENSE file for details
