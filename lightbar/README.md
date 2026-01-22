# Jetson RGB Light Bar Controller

System-reactive RGB light bar controller for NVIDIA Jetson Orin Nano with Yahboom CUBE NANO case. Features 5 dynamic visual effects, web interface, automatic scheduling, and OLED synchronization.

## Features

- **5 System-Reactive Visual Effects**
  - `system_pulse` - Breathing effect with load-reactive colors (green → yellow → orange → red)
  - `load_rainbow` - Rainbow cycle with speed tied to CPU load
  - `random_sparkle` - Random LED sparkles, frequency increases with load
  - `thermal_gradient` - Temperature-based colors (blue → orange → red)
  - `load_bars` - CPU/RAM visualization with animated bars

- **Web Interface**
  - Modern dark-themed UI at `http://<jetson-ip>:5001`
  - Real-time system metrics display
  - Effect mode selection
  - Brightness control (0-100%)
  - Manual on/off toggle
  - Demo mode trigger

- **Smart Scheduling**
  - Automatic on/off based on time (7 AM - 8 PM by default)
  - Smooth fade-in/fade-out transitions
  - Manual override with duration options

- **OLED Synchronization**
  - Reads metrics from OLED display for efficiency
  - Detects OLED crashes and shows error mode (red pulse)
  - Green flash on OLED recovery

- **Enhanced Randomness**
  - Chaos factor scales with system load (1.0 - 5.0)
  - Effects become more dynamic under heavy load
  - Temperature bonus adds extra chaos above 70°C

- **Auto-Start Service**
  - Systemd integration for boot auto-start
  - Automatic crash recovery (10s delay)
  - Resource limits (5% CPU, 100MB RAM)
  - Graceful shutdown with fade-out

## Quick Start

### Installation

1. **Install the systemd service:**
   ```bash
   cd /home/john/lightbar/scripts
   sudo ./install.sh
   ```

2. **Start the service:**
   ```bash
   sudo systemctl start lightbar
   ```

3. **Enable auto-start on boot (if not already enabled):**
   ```bash
   sudo systemctl enable lightbar
   ```

4. **Access the web interface:**
   Open `http://<jetson-ip>:5001` in your browser

### Manual Start (Without Systemd)

```bash
cd /home/john/lightbar
./scripts/start.sh
```

## Usage

### Web Interface

Access the web UI at `http://<jetson-ip>:5001` to:
- View real-time CPU, RAM, temperature, and load metrics
- Select visual effects from the 5 available options
- Adjust brightness from 0-100%
- Toggle lights on/off
- Trigger demo mode (30-second cycle through all effects)

### API Endpoints

#### Get Status
```bash
curl http://<jetson-ip>:5001/api/status
```

#### Change Effect
```bash
curl -X POST http://<jetson-ip>:5001/api/mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "load_rainbow"}'
```

#### Set Brightness
```bash
curl -X POST http://<jetson-ip>:5001/api/brightness \
  -H "Content-Type: application/json" \
  -d '{"brightness": 75}'
```

#### Toggle On/Off
```bash
# Turn off
curl -X POST http://<jetson-ip>:5001/api/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'

# Turn on
curl -X POST http://<jetson-ip>:5001/api/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

#### Trigger Demo Mode
```bash
curl -X POST http://<jetson-ip>:5001/api/demo \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Service Management

```bash
# Start the service
sudo systemctl start lightbar

# Stop the service
sudo systemctl stop lightbar

# Restart the service
sudo systemctl restart lightbar

# Check service status
sudo systemctl status lightbar

# View live logs
journalctl -u lightbar -f

# Enable auto-start on boot
sudo systemctl enable lightbar

# Disable auto-start
sudo systemctl disable lightbar
```

## Configuration

Edit `/home/john/lightbar/config.json` to customize:

```json
{
  "i2c": {
    "bus": 7,
    "address": 14
  },
  "effects": {
    "available_effects": [
      "system_pulse",
      "load_rainbow",
      "random_sparkle",
      "thermal_gradient",
      "load_bars"
    ],
    "default_effect": "system_pulse"
  },
  "display": {
    "brightness_multiplier": 1.0
  },
  "schedule": {
    "enabled": true,
    "start_hour": 7,
    "end_hour": 20
  },
  "performance": {
    "update_interval": 0.5,
    "target_fps": 2
  }
}
```

After changing the config, restart the service:
```bash
sudo systemctl restart lightbar
```

## Effects Guide

### system_pulse
Breathing/pulsing effect where color and speed react to system load:
- **Low load**: Slow green pulse
- **Medium load**: Faster yellow/orange pulse
- **High load**: Rapid red pulse

### load_rainbow
Rainbow color cycle where speed is tied to CPU usage:
- **Low load**: Smooth 3-second cycle
- **High load**: Rapid 0.5-second cycle

### random_sparkle
Random sparkles on individual LEDs:
- **Low load**: Occasional single sparkles
- **High load**: Many simultaneous sparkles
- **Colors**: Blue (cool), orange (warm), red/magenta (hot)

### thermal_gradient
Temperature-based colors with pulse speed tied to load:
- **<50°C**: Blue
- **50-70°C**: Orange
- **>70°C**: Red

### load_bars
Animated visualization of CPU and RAM usage:
- **CPU**: Cyan bars
- **RAM**: Magenta bars
- Scrolling effect with activity-based speed

## Demo Mode

Demo mode cycles through all 5 effects over 30 seconds (6 seconds each) while ramping randomness from 1.0 to 5.0:

- **Via Web UI**: Click the "Demo Mode" button
- **Via API**: `curl -X POST http://<jetson-ip>:5001/api/demo -H "Content-Type: application/json" -d '{}'`

After 30 seconds, the system returns to the previous effect.

## Scheduling

By default, lights are active from **7 AM to 8 PM** with smooth transitions:
- **7:00 AM**: 3-second fade-in
- **8:00 PM**: 2-second fade-out

### Boot Behavior
- **Boot during active hours**: 5-second fade-in
- **Boot outside hours**: Lights stay off

### Manual Override
Use the web interface or API to override the schedule temporarily.

## Performance

- **CPU Usage**: <1% (capped at 5%)
- **Memory Usage**: ~15MB (capped at 100MB)
- **Startup Time**: ~3 seconds
- **Frame Rate**: 2 FPS (stable)
- **API Response**: <100ms (typical)
- **Crash Recovery**: <15 seconds

## Logs

View logs using journalctl:

```bash
# Live logs
journalctl -u lightbar -f

# Last 50 lines
journalctl -u lightbar -n 50

# Logs since today
journalctl -u lightbar --since today

# Logs with errors only
journalctl -u lightbar -p err
```

Controller logs are also written to:
- `/tmp/lightbar_controller.log` (main controller)
- `/home/john/lightbar/logs/web.log` (web server)

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

Quick diagnostics:
```bash
# Check service status
sudo systemctl status lightbar

# Check if processes are running
ps aux | grep -E 'lightbar_controller|server.py'

# Check I2C device
ls -l /dev/i2c-7

# Test I2C communication
i2cdetect -y 7

# Check web interface
curl http://localhost:5001/api/status
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details about the system design, component interactions, and data flow.

## Files and Directories

```
/home/john/lightbar/
├── lightbar_controller.py   # Main controller
├── effects.py                # Effect implementations
├── scheduler.py              # Time-based scheduling
├── oled_sync.py              # OLED health monitoring
├── randomness.py             # Chaos factor calculations
├── brightness_wrapper.py     # Brightness control layer
├── shared_state.py           # IPC utilities
├── config.json               # Configuration file
├── lightbar.service          # Systemd service definition
├── web/                      # Web interface
│   ├── server.py             # Flask backend
│   └── static/
│       ├── index.html        # Web UI
│       ├── style.css         # Styling
│       └── app.js            # Client-side JavaScript
├── scripts/                  # Management scripts
│   ├── start.sh              # Startup script
│   ├── stop.sh               # Shutdown script
│   ├── pre-start-checks.sh   # Validation script
│   └── install.sh            # Installation script
├── tests/                    # Test suite
│   └── integration_tests.py  # Integration tests
└── logs/                     # Log directory
    └── web.log               # Web server logs
```

## Dependencies

- **Python 3.8+**
- **Flask** (`pip install flask flask-sock`)
- **psutil** (`pip install psutil`)
- **smbus2** (for I2C communication, usually pre-installed)
- **I2C device** at `/dev/i2c-7`

## Hardware Requirements

- NVIDIA Jetson Orin Nano
- Yahboom CUBE NANO case with integrated RGB light bar
- I2C RGB controller at bus 7, address 0x0E

## License

This project was developed with assistance from Claude Code.

## Support

For issues or questions:
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Review logs: `journalctl -u lightbar -n 100`
3. Test hardware: `i2cdetect -y 7`
4. Restart service: `sudo systemctl restart lightbar`

## Acknowledgments

Built for the NVIDIA Jetson Orin Nano platform with the Yahboom CUBE NANO case.
Developed with Claude Code (Anthropic).
