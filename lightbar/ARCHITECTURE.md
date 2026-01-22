# Light Bar System Architecture

Technical documentation for the Jetson RGB Light Bar Controller system.

## System Overview

The light bar controller is a multi-process system with three main components:
1. **Main Controller** - Collects metrics, manages effects, and drives RGB hardware
2. **Web Server** - Provides REST API and WebSocket interface
3. **OLED Monitor** - Separate service that shares system metrics

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACES                          │
├─────────────────────────────────────────────────────────────┤
│  Web Browser          API Clients         Systemd            │
│  (Port 5001)          (REST/curl)         (systemctl)        │
└────────┬──────────────────┬────────────────────┬────────────┘
         │                  │                    │
         v                  v                    v
┌─────────────────────────────────────────────────────────────┐
│                     WEB SERVER (Flask)                       │
│  • REST API (/api/*)                                         │
│  • WebSocket (/ws/updates)                                   │
│  • Static file serving                                       │
│  • JSON request/response handling                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          │ (Shared State File)
                          │ /tmp/lightbar_control.json
                          │
                          v
┌─────────────────────────────────────────────────────────────┐
│              MAIN CONTROLLER (lightbar_controller.py)        │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │   Scheduler    │  │    OLED      │  │   Effects       │ │
│  │   Module       │  │    Sync      │  │   Engine        │ │
│  │ (Time-based)   │  │  (Health)    │  │  (5 effects)    │ │
│  └────────────────┘  └──────────────┘  └─────────────────┘ │
│  ┌────────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │  Randomness    │  │  Brightness  │  │   System        │ │
│  │   Engine       │  │   Wrapper    │  │   Metrics       │ │
│  │ (Chaos 1-5)    │  │ (Multiplier) │  │  (psutil)       │ │
│  └────────────────┘  └──────────────┘  └─────────────────┘ │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ (I2C Bus 7)
                     │
                     v
┌─────────────────────────────────────────────────────────────┐
│                RGB HARDWARE (0x0E)                           │
│  • 14 individual LEDs                                        │
│  • RGB color control                                         │
│  • Per-LED or all-LED control                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│        OLED MONITOR (oled_stats.py) - Separate Process      │
│  Writes to: /tmp/jetson_state.json                          │
│  • CPU, RAM, Temperature, Load metrics                       │
│  • Updated every 1 second                                    │
│  • Shared with light bar controller                          │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. System Metrics Collection

```
┌─────────────────┐
│ OLED Monitor    │ Writes metrics every 1s
│ (oled_stats.py) ├────────────────────────┐
└─────────────────┘                        │
                                           v
                                  /tmp/jetson_state.json
                                           │
                                           │ Read every 500ms
                                           │
┌──────────────────┐                      v
│ Main Controller  │────────────> collect_system_metrics()
│                  │                      │
│  If OLED data    │<─────────────────────┘
│  unavailable:    │
│  • Direct psutil │
│  • Temp sensor   │
│  • Load average  │
└──────────────────┘
```

### 2. Effect Rendering Loop

```
Main Loop (2 FPS):
  1. Check scheduler (fade-in/fade-out)
  2. Check web control commands (every 500ms)
  3. Collect system metrics (every 500ms)
  4. Check OLED health
  5. Update demo mode (if active)
  6. Calculate randomness (1.0-5.0)
  7. Update current effect
  8. Apply brightness multiplier
  9. Send RGB commands to I2C
  10. Sleep to maintain target FPS
```

### 3. Web Interface Communication

```
Browser Request
    │
    v
Flask REST API
    │
    ├─> Read current state
    │   └─> Return JSON response
    │
    └─> Write command
        │
        v
  /tmp/lightbar_control.json
        │
        │ Checked every 500ms
        v
  Main Controller
        │
        └─> Apply changes
```

## Threading Model

### Main Controller (Single Thread)
- Runs synchronously in a single event loop
- No threading for core logic
- Signal handlers for graceful shutdown (SIGTERM, SIGINT)

### Web Server (Multi-Threaded)
- Flask with Werkzeug WSGI server
- One thread per HTTP request
- WebSocket connections handled by flask-sock
- Thread-safe state access via locks

### IPC Mechanism
- File-based communication (not threading)
- Atomic writes using temp file + rename
- Controller polls control file every 500ms
- Web server writes commands immediately

## Module Descriptions

### lightbar_controller.py
**Purpose**: Main orchestrator and hardware driver

**Key Classes**:
- `LightBarController` - Main controller class

**Key Methods**:
- `run()` - Main event loop
- `collect_system_metrics()` - Gather CPU, RAM, temp, load
- `update_effect()` - Render current visual effect
- `calculate_randomness()` - Compute chaos factor (1.0-5.0)
- `check_control_commands()` - Read web interface commands
- `handle_oled_health()` - Monitor OLED status

**Update Rate**: 2 FPS (500ms interval)

### effects.py
**Purpose**: Visual effect implementations

**Base Class**: `EffectEngine`
- `update(system_load, randomness)` - Render one frame
- `reset()` - Reset effect state
- `get_elapsed()` - Get time since effect started

**Effect Classes**:
1. `SystemPulseEffect` - Breathing with load-reactive colors
2. `LoadRainbowEffect` - Rainbow cycle, speed tied to load
3. `RandomSparkleEffect` - Random sparkles, frequency tied to load
4. `ThermalGradientEffect` - Temperature-based colors
5. `LoadBarsEffect` - CPU/RAM bar visualization

**Randomness Integration**:
- Speed jitter increases with randomness
- More simultaneous LEDs at high randomness
- Faster/more abrupt transitions
- Overlapping patterns

### scheduler.py
**Purpose**: Time-based on/off control

**Key Classes**:
- `Scheduler` - Determines if lights should be on
- `FadeController` - Manages smooth brightness transitions

**Features**:
- Active hours: 7 AM - 8 PM (configurable)
- Boot behavior based on current time
- Fade-in (3s) and fade-out (2s) transitions
- Manual override support

### oled_sync.py
**Purpose**: Monitor OLED display health

**Key Class**: `OLEDSync`

**Features**:
- Reads `/tmp/jetson_state.json` every 5 seconds
- Detects stale data (>5 seconds old) as failure
- Tracks recovery transitions
- Provides green flash indication on recovery

**Error Modes**:
- **OLED Down**: Red pulsing effect
- **OLED Recovered**: 2-second green flash
- **OLED Healthy**: Normal operation

### randomness.py
**Purpose**: Calculate chaos factor from system load

**Key Function**: `calculate_randomness(cpu, ram, temp)`

**Formula**:
```python
base_load = (cpu * 0.6) + (ram * 0.4)
base_randomness = 1.0 + (base_load * 3.0)

if temp > 70:
    temp_bonus = min(1.0, (temp - 70) / 15.0)
    base_randomness += temp_bonus

return clamp(base_randomness, 1.0, 5.0)
```

**Range**: 1.0 (calm) to 5.0 (maximum chaos)

### brightness_wrapper.py
**Purpose**: Apply brightness multiplier to all RGB commands

**Key Class**: `BrightnessWrapper`

**Wrapping**:
- Intercepts all `set_all_RGB()` and `set_RGB()` calls
- Scales RGB values by `brightness_multiplier` (0.0-1.0)
- Forwards scaled values to hardware
- Transparent to effects (effects use 0-255 range)

### shared_state.py
**Purpose**: Inter-process communication utilities

**Key Functions**:
- `read_control_state()` - Read `/tmp/lightbar_control.json`
- `update_control_state(**kwargs)` - Write control commands

**Control File Schema**:
```json
{
  "effect": "system_pulse",
  "brightness": 100,
  "enabled": true,
  "override": null,
  "demo_mode": false,
  "timestamp": 1234567890.123
}
```

**Atomic Writes**: temp file + `os.replace()` for safety

### web/server.py
**Purpose**: REST API and WebSocket server

**Endpoints**:
- `GET /api/status` - Current system state
- `POST /api/mode` - Change effect
- `POST /api/brightness` - Set brightness (0-100)
- `POST /api/toggle` - Enable/disable lights
- `POST /api/demo` - Trigger demo mode
- `WebSocket /ws/updates` - Real-time metrics stream

**Update Rate**: WebSocket pushes every 1 second

## I2C Communication

### Hardware Details
- **Bus**: 7 (`/dev/i2c-7`)
- **Address**: 0x0E (14 decimal)
- **Shared with**: OLED display (0x3C)

### Timing
- **Write delay**: 25ms between register writes
- **Command delay**: 30ms after commands
- **Retry logic**: 3 attempts with delays

### Error Handling
- I2C timeouts are common (shared bus)
- Errors logged but don't crash controller
- Retry logic prevents intermittent failures
- Typical error rate: 15-20 per minute (acceptable)

### Register Map
- `REG_LED_SELECT` (0x00) - Select which LED(s)
- `REG_RED` (0x01) - Red value (0-255)
- `REG_GREEN` (0x02) - Green value (0-255)
- `REG_BLUE` (0x03) - Blue value (0-255)
- `LED_ALL` (0xFF) - Select all LEDs

## Performance Characteristics

### CPU Usage
- **Idle**: 0.3-0.5%
- **Active effects**: 0.8-1.2%
- **Limit**: 5% (systemd CPUQuota)

### Memory Usage
- **Startup**: ~15MB
- **Running**: ~15-20MB
- **Limit**: 100MB (systemd MemoryLimit)

### Frame Rate
- **Target**: 2 FPS
- **Actual**: 2.0 FPS (stable)
- **Update interval**: 500ms

### API Response Time
- **Typical**: 10-50ms
- **First request**: 100-500ms (warmup)
- **Target**: <100ms (for subsequent requests)

### Startup Time
- **Pre-flight checks**: ~1s
- **Web server start**: ~1s
- **Controller init**: ~1s
- **Total**: ~3s

## State Management

### State Files

**1. Control State** (`/tmp/lightbar_control.json`)
- Written by: Web server
- Read by: Main controller
- Update frequency: On user command
- Purpose: IPC from web UI to controller

**2. OLED State** (`/tmp/jetson_state.json`)
- Written by: OLED monitor
- Read by: Main controller
- Update frequency: Every 1 second
- Purpose: Share system metrics

**3. Web PID** (`/tmp/lightbar/web.pid`)
- Written by: Start script
- Read by: Stop script
- Purpose: Track web server process ID

### In-Memory State

**Controller State**:
- Current effect name
- Current effect object
- Brightness multiplier
- System metrics cache
- Frame counter
- Scheduler state
- OLED health status
- Demo mode status

**Web Server State**:
- Current UI state (brightness, effect, enabled)
- Active WebSocket connections
- State lock for thread safety

## Configuration System

### config.json Schema
```json
{
  "i2c": {
    "bus": 7,
    "address": 14
  },
  "effects": {
    "available_effects": ["system_pulse", "load_rainbow", ...],
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
  },
  "thermal": {
    "sensor_path": "/sys/class/thermal/thermal_zone0/temp"
  }
}
```

### Configuration Loading
- Read at controller startup
- JSON validation during pre-start checks
- Restart required for changes to take effect
- Invalid config prevents service start

## Security Considerations

### Systemd Hardening
- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolated /tmp directory
- `User=john` - Runs as non-root user
- Resource limits prevent DoS

### I2C Permissions
- User added to `i2c` group
- Udev rules for device access
- No root required for I2C operations

### Web Interface
- Local network only (no external exposure)
- No authentication (trusted LAN)
- Input validation on all endpoints
- JSON schema enforcement

## Error Handling Strategy

### Hardware Errors (I2C)
- Retry logic (3 attempts)
- Log errors but continue operation
- Don't crash on timeout
- Acceptable error rate: ~20/minute

### OLED Errors
- Detect stale metrics (>5s old)
- Switch to direct metric collection
- Visual feedback (red pulse)
- Automatic recovery detection

### Web Server Errors
- JSON error responses
- HTTP status codes (400, 500)
- Exception logging
- Graceful degradation

### Service Errors
- Systemd auto-restart (10s delay)
- Rate limiting (5 attempts per 5 min)
- Graceful shutdown on signals
- State preservation

## Monitoring and Observability

### Logging
- Main controller: journalctl + `/tmp/lightbar_controller.log`
- Web server: journalctl + `/home/john/lightbar/logs/web.log`
- Log levels: INFO, WARNING, ERROR
- Performance stats logged every 10 seconds

### Metrics Available
- CPU percentage
- RAM percentage
- Temperature (°C)
- System load average
- Frame rate (FPS)
- I2C error count

### Health Checks
- OLED state freshness (<5s)
- I2C device availability
- Web server responsiveness
- Process existence

## Future Enhancements

Potential improvements not yet implemented:
- Persistent configuration via web UI
- User-defined custom effects
- MQTT integration for home automation
- Historical metrics logging
- Alerting on high temperature
- Mobile-responsive web UI improvements
- Authentication for web interface
- Multiple schedules (weekday/weekend)

## Development Notes

### Adding New Effects

1. Create new class in `effects.py` inheriting from `EffectEngine`
2. Implement `update(system_load, randomness)` method
3. Add effect name to `available_effects` in config.json
4. Add creation logic to `create_effect()` function
5. Test effect in isolation before deploying

### Modifying I2C Timing

If experiencing I2C errors, adjust timing in `CubeNano.py`:
```python
I2C_WRITE_DELAY = 0.025    # Increase for fewer errors
I2C_COMMAND_DELAY = 0.030  # Increase for fewer errors
```

### Debugging Tips
- Enable DEBUG logging: `self.logger.setLevel(logging.DEBUG)`
- Monitor I2C bus: `i2cdetect -y 7`
- Check process status: `ps aux | grep lightbar`
- View real-time logs: `journalctl -u lightbar -f`
- Test API: `curl -v http://localhost:5001/api/status`

## References

- **Yahboom CUBE NANO**: https://github.com/YahboomTechnology/Jetson-CUBE-case
- **Jetson GPIO**: https://github.com/NVIDIA/jetson-gpio
- **Flask Documentation**: https://flask.palletsprojects.com/
- **systemd Service Management**: `man systemd.service`
