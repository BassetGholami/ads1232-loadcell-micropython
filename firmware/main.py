from machine import Pin
import time
import os

"""
Raspberry Pi Pico W (MicroPython) + ADS1232 load cell reader
- Reads raw 24-bit data from ADS1232
- 2-point calibration (empty + known weight)
- Prints weight in kg
"""

# ADS1232 digital pins (change GPIO numbers to match your wiring)
PDWN = Pin(22, Pin.OUT)   # Power-down / reset pin
DOUT = Pin(20, Pin.IN)    # Data output (goes LOW when data ready)
SCLK = Pin(21, Pin.OUT)   # Serial clock

CAL_FILE = "cal.txt"

def read_raw():
    # Wait until data is ready (DOUT goes low)
    while DOUT.value() == 1:
        pass

    raw = 0
    for _ in range(24):
        SCLK.value(1)
        raw = (raw << 1) | DOUT.value()
        SCLK.value(0)

    # Extra clock pulse (kept from original implementation)
    SCLK.value(1)
    SCLK.value(0)

    # Convert 24-bit two's complement to signed integer
    if raw & 0x800000:
        raw -= 1 << 24

    return raw

def reset_ads():
    # PDWN low -> reset/power-down, then high -> normal operation
    PDWN.value(0)
    time.sleep_ms(10)
    PDWN.value(1)
    time.sleep_ms(500)

def save_calibration(offset, scale):
    with open(CAL_FILE, "w") as f:
        f.write(f"{offset},{scale}")

def load_calibration():
    if CAL_FILE in os.listdir():
        with open(CAL_FILE) as f:
            data = f.read().strip().split(",")
            return float(data[0]), float(data[1])
    return None, None

def calibrate(known_weight_g=5000):
    print("Calibration started.")
    print("1) Make the load cell EMPTY ...")
    time.sleep(3)
    offset = sum(read_raw() for _ in range(10)) / 10
    print("Empty value (offset):", offset)

    print("2) Put the known weight on the load cell:", known_weight_g, "g")
    time.sleep(5)
    raw_weight = sum(read_raw() for _ in range(10)) / 10
    print("Raw value with weight:", raw_weight)

    delta = (raw_weight - offset)
    scale = abs(delta / known_weight_g) if delta != 0 else 1.0
    print("Calibration coefficient (scale):", scale)

    save_calibration(offset, scale)
    print("Calibration saved to", CAL_FILE)
    return offset, scale

def average_weight_g(offset, scale, samples=5):
    values = [read_raw() for _ in range(samples)]
    avg = sum(values) / len(values)
    return (avg - offset) / scale

reset_ads()

offset, scale = load_calibration()
if offset is None or scale is None:
    offset, scale = calibrate(known_weight_g=5000)

print("\nReading weight...")

while True:
    weight_g = average_weight_g(offset, scale, samples=5)
    weight_kg = weight_g / 1000.0
    print("Weight: {:.2f} kg".format(weight_kg))
    time.sleep(0.5)
