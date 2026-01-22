# Hardware Setup Guide

Complete hardware setup instructions for ProjectJetson monitoring systems.

## Required Components

### For OLED Monitor
- 1x NVIDIA Jetson device (Orin Nano, Xavier NX, or compatible)
- 1x 128x64 I2C OLED display (SSD1306 compatible)
- 4x Female-to-Female jumper wires

### For RGB Light Bar
- 1x I2C RGB LED controller (CubeNano or compatible)
- 1x RGB LED strip or array
- Power supply for RGB LEDs (if external power required)
- 4x Female-to-Female jumper wires

## Wiring Diagrams

### OLED Display Connection

Connect the OLED display to the Jetson's I2C bus 7:

```
OLED Display          Jetson Pin
-----------          ----------
VCC      ----------> Pin 1 (3.3V)
GND      ----------> Pin 6 (GND)
SCL      ----------> Pin 28 (I2C_7_SCL)
SDA      ----------> Pin 27 (I2C_7_SDA)
```

### RGB Controller Connection

Connect the RGB controller to the same I2C bus:

```
RGB Controller        Jetson Pin
--------------       ----------
VCC      ----------> Pin 1 (3.3V) or Pin 2 (5V)*
GND      ----------> Pin 6 (GND)
SCL      ----------> Pin 28 (I2C_7_SCL)
SDA      ----------> Pin 27 (I2C_7_SDA)
```

*Check your RGB controller's voltage requirements (3.3V or 5V)

## Pin Layout Reference

Jetson Orin Nano 40-pin header (relevant pins):

```
     3.3V [ 1] [ 2] 5V
          [ 3] [ 4] 5V
          [ 5] [ 6] GND
          ...
I2C_7_SDA [27] [28] I2C_7_SCL
          ...
```

## I2C Address Configuration

### Default Addresses
- **OLED Display:** 0x3C (60 decimal)
- **RGB Controller:** 0x0E (14 decimal)

### Verifying I2C Devices

After connecting hardware, verify devices are detected:

```bash
sudo i2cdetect -y 7
```

Expected output:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- 0e --
10:          -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20:          -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30:          -- -- -- -- -- -- -- -- -- -- -- -- 3c -- -- --
40:          -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50:          -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60:          -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70:          -- -- -- -- -- -- -- --
```

You should see:
- `3c` - OLED display
- `0e` - RGB controller (if using CubeNano)

## Troubleshooting Hardware

### No I2C Devices Detected

1. **Check physical connections:**
   - Ensure wires are firmly seated
   - Verify correct pin numbers
   - Check for bent pins

2. **Verify I2C bus is enabled:**
   ```bash
   ls -l /dev/i2c-*
   ```
   You should see `/dev/i2c-7`

3. **Check for loose connections:**
   - Try different jumper wires
   - Ensure no corrosion on pins

### Wrong I2C Address Displayed

If devices show at different addresses:
1. Update configuration files to match detected addresses
2. Some OLED displays can be at 0x3D instead of 0x3C
3. Check device datasheet for address configuration options

### Device Detected But Not Working

1. **Check voltage levels:**
   - Verify 3.3V or 5V requirement
   - Measure voltage with multimeter

2. **Check I2C clock speed:**
   Some devices may require slower clock speeds. Configure in device tree if needed.

3. **Test with i2c-tools:**
   ```bash
   # Read from OLED (address 0x3c)
   sudo i2cget -y 7 0x3c 0x00

   # Write to RGB controller (address 0x0e)
   sudo i2cset -y 7 0x0e 0x00 0xFF
   ```

## Power Considerations

### OLED Display
- Typical power draw: 20-40 mA
- Can be powered directly from Jetson 3.3V pin
- No external power supply needed

### RGB Light Bar
- Power draw varies with:
  - Number of LEDs
  - Brightness level
  - Active effect

- **For small arrays (<10 LEDs):** Can use Jetson 5V pin
- **For larger arrays:** Use external power supply
  - Connect LED power to external supply
  - Connect grounds together (common ground)
  - I2C signals remain connected to Jetson

### External Power Supply Wiring

```
External PSU          RGB LEDs          Jetson
------------         ---------         ------
5V/12V    ---------> VCC
GND       ---------> GND    <--------- GND (Pin 6)
                     SCL    <--------- I2C_7_SCL (Pin 28)
                     SDA    <--------- I2C_7_SDA (Pin 27)
```

**Important:** Always connect grounds together when using external power!

## Cable Length Considerations

### I2C Signal Integrity
- **Maximum recommended length:** 1 meter (3 feet)
- **Longer cables may require:**
  - Pull-up resistors (2.2kΩ - 4.7kΩ)
  - Lower I2C clock speed
  - Shielded cables

### Reducing Interference
- Keep I2C wires away from power cables
- Use twisted pair for SDA/SCL
- Add 100nF capacitors near devices if experiencing issues

## Safety Notes

1. **Always power off Jetson before connecting/disconnecting I2C devices**
2. **Do not hot-plug I2C devices** - can damage I2C bus
3. **Check voltage requirements** before connecting
4. **Use proper current ratings** for RGB LED power supplies
5. **Avoid short circuits** - double-check wiring before powering on

## Testing Procedure

After wiring hardware:

1. **Visual inspection:**
   - Verify all connections
   - Check for shorts
   - Ensure proper polarity

2. **Power on Jetson**

3. **Detect I2C devices:**
   ```bash
   sudo i2cdetect -y 7
   ```

4. **Test OLED:**
   ```bash
   cd oled_monitor
   python3 oled_stats.py
   ```
   You should see stats displayed on the OLED

5. **Test RGB controller:**
   ```bash
   cd lightbar
   sudo systemctl start lightbar.service
   ```
   LEDs should light up with default effect

## Hardware Specifications

### Supported OLED Displays
- SSD1306 128x64 I2C
- SSD1305 128x64 I2C
- SH1106 128x64 I2C

### Supported RGB Controllers
- CubeNano I2C RGB controller
- Other I2C LED controllers (may require CubeNano.py modifications)

### Jetson Compatibility
- Jetson Orin Nano (tested)
- Jetson Xavier NX (compatible)
- Jetson Nano (compatible)
- Other Jetson devices with I2C support

## Reference Links

- [Jetson Orin Nano Pinout](https://jetsonhacks.com/nvidia-jetson-orin-nano-gpio-header-pinout/)
- [SSD1306 OLED Datasheet](https://cdn-shop.adafruit.com/datasheets/SSD1306.pdf)
- [I2C Bus Specification](https://www.nxp.com/docs/en/user-guide/UM10204.pdf)
