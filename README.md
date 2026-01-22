# ProjectJetson

A comprehensive system monitoring and visualization suite for NVIDIA Jetson Orin Nano, featuring an OLED stats display and reactive RGB light bar controller.

## Noteworthy
This was created using Claude Code

## Overview

ProjectJetson provides real-time hardware monitoring with visual feedback through two integrated systems:

1. **OLED Monitor** - Multi-screen stats display showing CPU, GPU, memory, temperature, network, and Docker container status
2. **RGB Light Bar** - System-reactive light effects that respond to CPU load, temperature, and system health

Both systems work independently but share state information for synchronized health monitoring and visual indicators.

## Features

### RGB Light Bar Controller
- **5 System-Reactive Effects:**
  - System Pulse: Breathing effect based on CPU load
  - Load Rainbow: Color spectrum shifts with system load
  - Random Sparkle: Chaotic pixel patterns influenced by system activity
  - Thermal Gradient: Heat-map visualization of CPU temperature
  - Load Bars: Segmented bar graph showing load distribution

- **Smart Scheduling:** Automatic on/off with smooth fade transitions (7 AM - 8 PM by default)
- **Web Interface:** Remote control and monitoring via Flask + WebSocket
- **OLED Synchronization:** Monitors OLED health and displays alerts
- **Systemd Integration:** Runs as a reliable background service

### OLED Monitor
- **Multi-Screen Display:** Rotating views of system stats
- **Real-Time Metrics:**
  - CPU usage per core with frequency
  - GPU usage and temperature
  - Memory and swap utilization
  - Network speed (upload/download)
  - Disk usage
  - Docker container status
  - System temperature and alerts

- **Shared State Support:** Publishes health status for lightbar integration
- **Configurable Alerts:** Threshold-based warnings for CPU, memory, temperature
- **Boot Splash:** Custom startup animation

## Hardware Requirements

- **Device:** NVIDIA Jetson Orin Nano (or compatible Jetson device)
- **OLED Display:** 128x64 I2C OLED (SSD1306 compatible)
- **RGB Light Bar:** I2C RGB LED controller (CubeNano or compatible)
- **I2C Bus:** Bus 7 (configurable)

### Wiring
- OLED: Connect to I2C bus 7 (default address: 0x3C)
- RGB Controller: Connect to I2C bus 7 (default address: 0x0E)

See [docs/hardware_setup.md](docs/hardware_setup.md) for detailed wiring diagrams and configuration.

## Quick Start

### Prerequisites
```bash
# Enable I2C
sudo apt-get update
sudo apt-get install -y i2c-tools python3-pip

# Verify I2C devices
i2cdetect -y 7
```

### Installation

#### RGB Light Bar
```bash
cd lightbar
pip3 install -r requirements.txt
cp config.json.example config.json
# Edit config.json for your setup
chmod +x scripts/*.sh
./scripts/install.sh
```

#### OLED Monitor
```bash
cd oled_monitor
pip3 install -r requirements.txt
cp config.json.example config.json
# Edit config.json for your setup
sudo cp oled-stats.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable oled-stats.service
sudo systemctl start oled-stats.service
```

### Usage

#### Light Bar Web Interface
Access the web interface at `http://<jetson-ip>:5000`

#### Manual Control
```bash
# Start lightbar
sudo systemctl start lightbar.service

# Check status
sudo systemctl status lightbar.service

# View logs
journalctl -u lightbar.service -f

# Stop lightbar
sudo systemctl stop lightbar.service
```

#### OLED Monitor
```bash
# Check status
sudo systemctl status oled-stats.service

# View logs
journalctl -u oled-stats.service -f
```

## Configuration

### Light Bar Configuration
Edit `lightbar/config.json`:
- **I2C Settings:** Bus number and device address
- **Performance:** Update interval and target FPS
- **Effects:** Default effect and available options
- **Schedule:** Operating hours and fade transitions
- **Thresholds:** CPU load levels for effect intensity
- **OLED Sync:** State file location and timeout settings

See [lightbar/README.md](lightbar/README.md) for detailed configuration options.

### OLED Configuration
Edit `oled_monitor/config.json`:
- **Display Settings:** Refresh rate, I2C bus, rotation interval
- **Features:** Enable/disable individual display screens
- **Alerts:** Threshold values for warnings

See [oled_monitor/README.md](oled_monitor/README.md) for detailed configuration options.

## Documentation

- **[RGB Light Bar Documentation](lightbar/README.md)** - Complete guide to the light bar system
- **[Architecture Overview](lightbar/ARCHITECTURE.md)** - Technical implementation details
- **[Troubleshooting Guide](lightbar/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Hardware Setup](docs/hardware_setup.md)** - Wiring diagrams and hardware configuration
- **[I2C Configuration](docs/i2c_configuration.md)** - I2C bus setup and troubleshooting
- **[Systemd Setup](docs/systemd_setup.md)** - Service installation and management

## Project Structure

```
ProjectJetson/
├── lightbar/                 # RGB Light Bar System
│   ├── core/                # Core Python modules
│   ├── hardware/            # Hardware interface (CubeNano.py)
│   ├── web/                 # Flask web interface
│   ├── scripts/             # Management scripts
│   └── tests/               # Test suite
│
├── oled_monitor/            # OLED Display System
│   └── oled_stats.py       # Main monitor script
│
└── docs/                    # Additional documentation
```

## Testing

Run integration tests:
```bash
cd lightbar
python3 tests/integration_tests.py
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome. Please open an issue to discuss proposed changes before submitting pull requests.

## Credits

Developed for NVIDIA Jetson Orin Nano. Tested and production-ready.

## Support

For issues, questions, or feature requests, please open an issue on GitHub.
