#!/usr/bin/env python3
"""
Jetson OLED Monitor - Enhanced Version
Displays system statistics on SSD1306 OLED display with advanced features.

Features:
- CPU/Memory/IP/Uptime monitoring
- GPU monitoring via jtop
- Temperature monitoring with alerts
- Network traffic speeds
- Disk usage monitoring
- Docker container count
- Multi-screen rotation
- Boot splash screen
- Alert system for critical conditions
- Configuration file support
"""

import time
import json
import socket
import subprocess
import os
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont
import psutil

# Optional imports
try:
    from jtop import jtop
    JTOP_AVAILABLE = True
except ImportError:
    JTOP_AVAILABLE = False

# Shared state file for light bar synchronization
SHARED_STATE_FILE = '/tmp/jetson_state.json'



class Config:
    """Configuration manager"""

    DEFAULT_CONFIG = {
        "refresh_rate": 1,
        "i2c_bus": 7,
        "screen_rotation_interval": 5,
        "boot_splash_duration": 2,
        "features": {
            "show_gpu": True,
            "show_temperature": True,
            "show_network_speed": True,
            "show_disk_usage": True,
            "show_docker": True,
            "rotate_screens": True,
            "show_alerts": True,
            "boot_splash": True
        },
        "alerts": {
            "cpu_threshold": 90,
            "memory_threshold": 85,
            "temperature_threshold": 80,
            "disk_threshold": 90
        }
    }

    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self.load()

    def load(self):
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                loaded = json.load(f)
                # Merge with defaults
                config = self.DEFAULT_CONFIG.copy()
                config.update(loaded)
                if 'features' in loaded:
                    config['features'] = {**self.DEFAULT_CONFIG['features'], **loaded['features']}
                if 'alerts' in loaded:
                    config['alerts'] = {**self.DEFAULT_CONFIG['alerts'], **loaded['alerts']}
                return config
        except Exception as e:
            print(f"Config load error: {e}, using defaults")
            return self.DEFAULT_CONFIG.copy()

    def get(self, key, default=None):
        return self.config.get(key, default)

    def feature(self, name):
        return self.config.get('features', {}).get(name, False)

    def alert_threshold(self, name):
        return self.config.get('alerts', {}).get(name, 90)


class AlertManager:
    """Alert system for critical conditions"""

    def __init__(self, config):
        self.config = config
        self.alerts = []
        self.blink_state = False

    def check_conditions(self, stats):
        """Check for alert conditions"""
        self.alerts = []

        if stats.get('cpu', 0) > self.config.alert_threshold('cpu_threshold'):
            self.alerts.append("CPU!")
        if stats.get('mem_percent', 0) > self.config.alert_threshold('memory_threshold'):
            self.alerts.append("MEM!")
        if stats.get('cpu_temp', 0) > self.config.alert_threshold('temperature_threshold'):
            self.alerts.append("HOT!")
        if stats.get('disk_percent', 0) > self.config.alert_threshold('disk_threshold'):
            self.alerts.append("DISK!")

    def has_alerts(self):
        return len(self.alerts) > 0

    def get_alert_text(self):
        if self.alerts:
            return " ".join(self.alerts)
        return ""

    def toggle_blink(self):
        self.blink_state = not self.blink_state
        return self.blink_state


class NetworkMonitor:
    """Network traffic monitor"""

    def __init__(self):
        self.last_bytes_sent = 0
        self.last_bytes_recv = 0
        self.last_time = time.time()
        # Initialize with current values
        net = psutil.net_io_counters()
        self.last_bytes_sent = net.bytes_sent
        self.last_bytes_recv = net.bytes_recv

    def get_speed(self):
        """Get network speed in KB/s"""
        net = psutil.net_io_counters()
        current_time = time.time()
        time_delta = current_time - self.last_time

        if time_delta > 0:
            bytes_sent = net.bytes_sent - self.last_bytes_sent
            bytes_recv = net.bytes_recv - self.last_bytes_recv
            send_speed = (bytes_sent / time_delta) / 1024  # KB/s
            recv_speed = (bytes_recv / time_delta) / 1024  # KB/s
        else:
            send_speed = 0
            recv_speed = 0

        self.last_bytes_sent = net.bytes_sent
        self.last_bytes_recv = net.bytes_recv
        self.last_time = current_time

        return recv_speed, send_speed


class ScreenManager:
    """Multi-screen rotation manager"""

    def __init__(self, interval=5):
        self.current_screen = 0
        self.last_switch = time.time()
        self.interval = interval
        self.num_screens = 3

    def should_switch(self):
        """Check if it's time to switch screens"""
        if time.time() - self.last_switch >= self.interval:
            self.last_switch = time.time()
            self.current_screen = (self.current_screen + 1) % self.num_screens
            return True
        return False

    def get_screen(self):
        return self.current_screen


class OLEDMonitor:
    """Main OLED monitor class"""

    def __init__(self):
        self.config = Config()
        self.device = self.find_display()
        self.font = self.load_font()
        self.alerts = AlertManager(self.config)
        self.network = NetworkMonitor()
        self.screens = ScreenManager(self.config.get('screen_rotation_interval', 5))

        # Initialize CPU measurement
        psutil.cpu_percent(interval=None)

        # Show boot splash if enabled
        if self.config.feature('boot_splash'):
            self.show_splash()

    def find_display(self):
        """Find and initialize OLED display"""
        buses_to_try = [self.config.get('i2c_bus', 7), 7, 1, 0, 2, 4, 5]

        for bus in buses_to_try:
            try:
                serial = i2c(port=bus, address=0x3C)
                device = ssd1306(serial, width=128, height=32)
                print(f"Found OLED display on I2C bus {bus}")
                return device
            except Exception:
                continue

        raise RuntimeError("Could not find OLED display on any I2C bus")

    def load_font(self):
        """Load display font"""
        try:
            return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 9)
        except IOError:
            return ImageFont.load_default()

    def show_splash(self):
        """Display boot splash screen"""
        image = Image.new('1', (self.device.width, self.device.height), 0)
        draw = ImageDraw.Draw(image)

        draw.text((10, 2), "JETSON ORIN NANO", font=self.font, fill=255)
        draw.text((30, 14), "Starting...", font=self.font, fill=255)

        self.device.display(image)
        time.sleep(self.config.get('boot_splash_duration', 2))

    def get_cpu_usage(self):
        """Get CPU usage percentage"""
        return psutil.cpu_percent(interval=None)

    def get_memory_stats(self):
        """Get memory statistics"""
        mem = psutil.virtual_memory()
        used_gb = mem.used / (1024 ** 3)
        total_gb = mem.total / (1024 ** 3)
        return used_gb, total_gb, mem.percent

    def get_ip_address(self):
        """Get primary IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "No IP"

    def get_uptime(self):
        """Get system uptime"""
        uptime_seconds = time.time() - psutil.boot_time()
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)

        if days > 0:
            return f"{days}d{hours}h"
        else:
            return f"{hours}h{minutes}m"

    def get_temperatures(self):
        """Get CPU and GPU temperatures"""
        cpu_temp = 0
        gpu_temp = 0

        # Read CPU temperature from thermal zones
        try:
            for i in range(10):
                path = f'/sys/class/thermal/thermal_zone{i}/temp'
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        temp = int(f.read().strip()) / 1000
                        if temp > cpu_temp:
                            cpu_temp = temp
        except Exception:
            pass

        # Try jtop for GPU temp
        if JTOP_AVAILABLE and self.config.feature('show_gpu'):
            try:
                with jtop() as jetson:
                    if jetson.ok():
                        gpu_temp = jetson.stats.get('Temp GPU', cpu_temp)
            except Exception:
                gpu_temp = cpu_temp
        else:
            gpu_temp = cpu_temp

        return cpu_temp, gpu_temp

    def get_gpu_usage(self):
        """Get GPU usage percentage"""
        if not JTOP_AVAILABLE or not self.config.feature('show_gpu'):
            return 0

        try:
            with jtop() as jetson:
                if jetson.ok():
                    return jetson.stats.get('GPU', 0)
        except Exception:
            pass
        return 0

    def get_disk_usage(self):
        """Get disk usage"""
        try:
            disk = psutil.disk_usage('/')
            used_gb = disk.used / (1024 ** 3)
            total_gb = disk.total / (1024 ** 3)
            return used_gb, total_gb, disk.percent
        except Exception:
            return 0, 0, 0

    def get_docker_count(self):
        """Get count of running Docker containers"""
        if not self.config.feature('show_docker'):
            return 0

        try:
            result = subprocess.run(
                ['docker', 'ps', '-q'],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.stdout.strip():
                return len(result.stdout.strip().split('\n'))
            return 0
        except Exception:
            return 0

    def get_all_stats(self):
        """Gather all system statistics"""
        cpu = self.get_cpu_usage()
        mem_used, mem_total, mem_percent = self.get_memory_stats()
        ip = self.get_ip_address()
        uptime = self.get_uptime()
        cpu_temp, gpu_temp = self.get_temperatures()
        gpu = self.get_gpu_usage()
        disk_used, disk_total, disk_percent = self.get_disk_usage()
        rx_speed, tx_speed = self.network.get_speed()
        docker_count = self.get_docker_count()

        return {
            'cpu': cpu,
            'mem_used': mem_used,
            'mem_total': mem_total,
            'mem_percent': mem_percent,
            'ip': ip,
            'uptime': uptime,
            'cpu_temp': cpu_temp,
            'gpu_temp': gpu_temp,
            'gpu': gpu,
            'disk_used': disk_used,
            'disk_total': disk_total,
            'disk_percent': disk_percent,
            'rx_speed': rx_speed,
            'tx_speed': tx_speed,
            'docker': docker_count,
            'time': time.strftime("%H:%M:%S")
        }


    def write_shared_state(self, stats):
        """Write shared state file for light bar synchronization."""
        try:
            # Extract load average
            load_avg = os.getloadavg()
            
            # Create shared state
            state = {
                'timestamp': time.time(),
                'cpu_percent': stats['cpu'],
                'ram_percent': stats['mem_percent'],
                'temperature': stats['cpu_temp'],
                'load_average': list(load_avg),
                'health': 'ok'
            }
            
            # Write atomically using temp file + rename
            temp_file = SHARED_STATE_FILE + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2)
            os.replace(temp_file, SHARED_STATE_FILE)
        except Exception as e:
            # Don't crash if shared state write fails
            pass

    def render_screen_main(self, draw, stats):
        """Screen 1: Main system stats"""
        # Line 1: CPU, GPU, Temp
        if self.config.feature('show_gpu') and JTOP_AVAILABLE:
            line1 = f"C:{stats['cpu']:2.0f}% G:{stats['gpu']:2.0f}% {stats['cpu_temp']:.0f}C"
        else:
            line1 = f"CPU:{stats['cpu']:3.0f}%  {stats['cpu_temp']:.0f}C"
        draw.text((0, 0), line1, font=self.font, fill=255)

        # Line 2: Memory
        line2 = f"MEM:{stats['mem_used']:.1f}/{stats['mem_total']:.1f}GB"
        draw.text((0, 11), line2, font=self.font, fill=255)

        # Line 3: Time and IP
        line3 = f"{stats['time']} {stats['ip']}"
        draw.text((0, 22), line3, font=self.font, fill=255)

    def render_screen_network(self, draw, stats):
        """Screen 2: Network and storage stats"""
        # Line 1: Network speeds
        if stats['rx_speed'] > 1024:
            rx = f"{stats['rx_speed']/1024:.1f}M"
        else:
            rx = f"{stats['rx_speed']:.0f}K"
        if stats['tx_speed'] > 1024:
            tx = f"{stats['tx_speed']/1024:.1f}M"
        else:
            tx = f"{stats['tx_speed']:.0f}K"
        line1 = f"NET: D:{rx} U:{tx}"
        draw.text((0, 0), line1, font=self.font, fill=255)

        # Line 2: Disk usage
        line2 = f"DISK:{stats['disk_percent']:.0f}% {stats['disk_used']:.0f}/{stats['disk_total']:.0f}G"
        draw.text((0, 11), line2, font=self.font, fill=255)

        # Line 3: Docker and uptime
        if self.config.feature('show_docker') and stats['docker'] > 0:
            line3 = f"UP:{stats['uptime']} Docker:{stats['docker']}"
        else:
            line3 = f"UP:{stats['uptime']} {stats['ip']}"
        draw.text((0, 22), line3, font=self.font, fill=255)

    def render_screen_thermal(self, draw, stats):
        """Screen 3: Thermal and performance"""
        # Line 1: Temperatures
        line1 = f"CPU:{stats['cpu_temp']:.0f}C GPU:{stats['gpu_temp']:.0f}C"
        draw.text((0, 0), line1, font=self.font, fill=255)

        # Line 2: CPU and GPU usage
        line2 = f"CPU:{stats['cpu']:.0f}% GPU:{stats['gpu']:.0f}% MEM:{stats['mem_percent']:.0f}%"
        draw.text((0, 11), line2, font=self.font, fill=255)

        # Line 3: Time and uptime
        line3 = f"{stats['time']}  UP:{stats['uptime']}"
        draw.text((0, 22), line3, font=self.font, fill=255)

    def render_alerts(self, draw, stats):
        """Render alert screen if alerts active"""
        alert_text = self.alerts.get_alert_text()

        # Blinking alert header
        if self.alerts.toggle_blink():
            draw.text((0, 0), f"!! {alert_text} !!", font=self.font, fill=255)
        else:
            draw.rectangle((0, 0, 127, 10), fill=255)
            draw.text((0, 0), f"!! {alert_text} !!", font=self.font, fill=0)

        # Show critical stats
        line2 = f"C:{stats['cpu']:.0f}% M:{stats['mem_percent']:.0f}% {stats['cpu_temp']:.0f}C"
        draw.text((0, 11), line2, font=self.font, fill=255)

        line3 = f"{stats['time']} {stats['ip']}"
        draw.text((0, 22), line3, font=self.font, fill=255)

    def render(self, stats):
        """Render stats to display"""
        image = Image.new('1', (self.device.width, self.device.height), 0)
        draw = ImageDraw.Draw(image)

        # Check for alerts
        if self.config.feature('show_alerts'):
            self.alerts.check_conditions(stats)

        # Render appropriate screen
        if self.alerts.has_alerts() and self.config.feature('show_alerts'):
            self.render_alerts(draw, stats)
        elif self.config.feature('rotate_screens'):
            self.screens.should_switch()
            screen = self.screens.get_screen()
            if screen == 0:
                self.render_screen_main(draw, stats)
            elif screen == 1:
                self.render_screen_network(draw, stats)
            else:
                self.render_screen_thermal(draw, stats)
        else:
            self.render_screen_main(draw, stats)

        self.device.display(image)

    def run(self):
        """Main loop"""
        print("Starting enhanced OLED monitor. Press Ctrl+C to exit.")
        print(f"Features enabled: GPU={self.config.feature('show_gpu')}, "
              f"Temp={self.config.feature('show_temperature')}, "
              f"Network={self.config.feature('show_network_speed')}, "
              f"Disk={self.config.feature('show_disk_usage')}, "
              f"Docker={self.config.feature('show_docker')}, "
              f"Rotate={self.config.feature('rotate_screens')}, "
              f"Alerts={self.config.feature('show_alerts')}")

        try:
            while True:
                stats = self.get_all_stats()
                self.write_shared_state(stats)
                self.render(stats)
                time.sleep(self.config.get('refresh_rate', 1))
        except KeyboardInterrupt:
            print("\nExiting...")
            self.cleanup()

    def cleanup(self):
        """Clean up on exit"""
        self.device.clear()
        print("Display cleared. Goodbye!")


if __name__ == '__main__':
    monitor = OLEDMonitor()
    monitor.run()
