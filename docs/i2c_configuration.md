# I2C Configuration Guide

Comprehensive guide for configuring I2C on NVIDIA Jetson devices for ProjectJetson.

## Overview

ProjectJetson uses I2C bus 7 for communication with the OLED display and RGB controller. This guide covers enabling I2C, setting permissions, troubleshooting, and advanced configuration.

## Prerequisites

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade

# Install I2C tools
sudo apt-get install -y i2c-tools python3-smbus
```

## Enabling I2C

### Check Available I2C Buses

```bash
ls -l /dev/i2c-*
```

You should see multiple I2C devices. For this project, we use `/dev/i2c-7`.

### Verify I2C Bus 7 is Available

```bash
sudo i2cdetect -l
```

Look for:
```
i2c-7   i2c             Tegra I2C adapter                       I2C adapter
```

If I2C bus 7 is not listed, it may need to be enabled in the device tree.

## Setting I2C Permissions

By default, I2C devices require root access. To allow regular users:

### Add User to I2C Group

```bash
sudo groupadd -f i2c
sudo usermod -a -G i2c $USER
```

### Create Udev Rule

Create `/etc/udev/rules.d/99-i2c.rules`:

```bash
sudo nano /etc/udev/rules.d/99-i2c.rules
```

Add the following content:
```
KERNEL=="i2c-[0-9]*", GROUP="i2c", MODE="0660"
```

### Apply Changes

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Log Out and Back In

For group membership to take effect, log out and log back in, or reboot:
```bash
sudo reboot
```

### Verify Permissions

After reboot:
```bash
ls -l /dev/i2c-7
```

Should show:
```
crw-rw---- 1 root i2c 89, 7 Jan 22 12:00 /dev/i2c-7
```

## Testing I2C Communication

### Scan for Devices

```bash
sudo i2cdetect -y 7
```

This displays a grid showing detected I2C addresses. Example output:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- 0e --
10:          -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20:          -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30:          -- -- -- -- -- -- -- -- -- -- -- -- 3c -- -- --
...
```

Devices shown:
- `0e` (14 decimal) - RGB controller
- `3c` (60 decimal) - OLED display

### Read from I2C Device

```bash
# Read a byte from OLED at address 0x3c
sudo i2cget -y 7 0x3c 0x00
```

### Write to I2C Device

```bash
# Write a byte to RGB controller at address 0x0e
sudo i2cset -y 7 0x0e 0x00 0xFF
```

## Configuration for Python

### Install Python I2C Libraries

```bash
pip3 install smbus2 python-periphery
```

### Python I2C Example

```python
from smbus2 import SMBus

# Open I2C bus 7
bus = SMBus(7)

# Read from device at address 0x3c
data = bus.read_byte_data(0x3c, 0x00)
print(f"Read: {data}")

# Write to device at address 0x0e
bus.write_byte_data(0x0e, 0x00, 0xFF)

# Close bus
bus.close()
```

## Troubleshooting

### "Permission denied" Error

**Problem:** Cannot access I2C device without sudo.

**Solution:**
1. Add user to i2c group (see above)
2. Create udev rule (see above)
3. Log out and back in
4. Verify permissions: `ls -l /dev/i2c-7`

### "No such file or directory" Error

**Problem:** `/dev/i2c-7` doesn't exist.

**Solution:**
1. Check available buses: `ls -l /dev/i2c-*`
2. Use a different bus number if 7 is not available
3. Update configuration files to match available bus
4. Check device tree if bus should be enabled

### "Input/output error" When Scanning

**Problem:** `i2cdetect` returns I/O errors.

**Possible causes:**
1. **Incorrect wiring** - Check connections
2. **Wrong voltage** - Verify 3.3V vs 5V requirements
3. **Device not powered** - Check power supply
4. **Pull-up resistors missing** - Some devices need external pull-ups

**Solutions:**
```bash
# Try slower speed (100kHz)
sudo i2cdetect -y 7 -r

# Check if device responds at specific address
sudo i2cget -y 7 0x3c 0x00
```

### Multiple Devices on Same Address

**Problem:** Two devices have the same I2C address.

**Solutions:**
1. Use different I2C buses if available
2. Check if device has configurable address (solder jumpers)
3. Use I2C multiplexer to separate devices

### Device Detected But Code Doesn't Work

**Problem:** Device shows in i2cdetect but Python code fails.

**Solutions:**
1. **Verify address format:**
   - Some libraries use 7-bit (0x3c)
   - Some use 8-bit (0x78)
   - Convert if needed: 8-bit = 7-bit << 1

2. **Check for clock stretching:**
   - Some devices require clock stretching support
   - May need to slow down I2C speed

3. **Verify register addresses:**
   - Check device datasheet for correct register map
   - Some devices have different command formats

## Advanced Configuration

### Changing I2C Clock Speed

Default I2C speed is typically 100kHz or 400kHz. To change:

#### Temporary Change (Until Reboot)

Not directly supported on Jetson - requires device tree modification.

#### Permanent Change (Device Tree)

Requires recompiling device tree with modified clock-frequency property. Consult NVIDIA Jetson documentation for your specific model.

### Adding Pull-up Resistors

If experiencing communication issues with long cables:

1. **Calculate resistor value:**
   - Standard values: 2.2kΩ - 4.7kΩ
   - Lower resistance = stronger pull-up (better for long cables)
   - Higher resistance = lower power (better for short cables)

2. **Install resistors:**
   ```
   3.3V ----[Resistor]---- SDA
   3.3V ----[Resistor]---- SCL
   ```

3. **Test communication:**
   ```bash
   sudo i2cdetect -y 7
   ```

### Using Multiple I2C Buses

If you have multiple I2C devices with address conflicts:

1. **Check available buses:**
   ```bash
   sudo i2cdetect -l
   ```

2. **Update configuration files:**
   - OLED on bus 7: `"i2c_bus": 7`
   - RGB on bus 8: `"i2c": {"bus": 8}`

3. **Verify both buses:**
   ```bash
   sudo i2cdetect -y 7
   sudo i2cdetect -y 8
   ```

## I2C Best Practices

### Hardware
1. Use short cables (< 1 meter) when possible
2. Keep I2C wires away from power cables
3. Use twisted pair for SDA/SCL to reduce noise
4. Add 100nF capacitors near devices for noise filtering
5. Never hot-plug I2C devices - power off first

### Software
1. Always close I2C bus after use
2. Handle exceptions for I/O errors
3. Add timeouts to prevent hanging
4. Use appropriate clock speed for your devices
5. Test with i2c-tools before writing code

### Debugging
1. Start with i2cdetect to verify hardware
2. Use i2cget/i2cset to test basic communication
3. Check device datasheet for register map
4. Use oscilloscope for signal analysis if available
5. Check kernel logs: `dmesg | grep i2c`

## Configuration Files

### Lightbar I2C Configuration

Edit `lightbar/config.json`:
```json
{
  "i2c": {
    "bus": 7,
    "address": 14
  }
}
```

### OLED I2C Configuration

Edit `oled_monitor/config.json`:
```json
{
  "i2c_bus": 7
}
```

## System Information

### Check I2C Driver Status

```bash
lsmod | grep i2c
```

Should show i2c-core and related modules.

### Check Kernel Messages

```bash
dmesg | grep i2c
```

Look for any errors or warnings.

### Verify Device Tree

```bash
sudo fdtget /boot/dtb/kernel_tegra234-p3768-0000+p3767-0005-nv.dtb /i2c@3160000 status
```

Should return "okay" if enabled.

## Common I2C Addresses

For reference when working with I2C devices:

| Device Type | Common Addresses |
|-------------|------------------|
| OLED (SSD1306) | 0x3C, 0x3D |
| Temperature Sensors | 0x48, 0x49 |
| Real-Time Clocks | 0x68 |
| EEPROM | 0x50-0x57 |
| GPIO Expanders | 0x20-0x27 |
| PWM Controllers | 0x40 |

## References

- [I2C Bus Specification](https://www.nxp.com/docs/en/user-guide/UM10204.pdf)
- [Jetson Linux I2C Documentation](https://docs.nvidia.com/jetson/archives/r35.1/DeveloperGuide/text/HR/ConfiguringTheJetsonExpansionHeader.html)
- [Linux I2C Subsystem](https://www.kernel.org/doc/Documentation/i2c/)
- [i2c-tools Documentation](https://i2c.wiki.kernel.org/index.php/I2C_Tools)
