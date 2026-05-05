import time
import board
import busio
import RPi.GPIO as GPIO
from adafruit_ina219 import INA219

# ---------------- CONFIG ----------------
RELAY_PIN = 17

BATTERY_CAPACITY_AH = 2.6
MAX_VOLTAGE = 12.60
MIN_VOLTAGE = 9.60

# ---------------- GPIO SETUP ----------------
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

# ---------------- INA219 SETUP ----------------
i2c = busio.I2C(board.SCL, board.SDA)
ina219 = INA219(i2c)

# ---------------- VOLTAGE -> SOC ----------------
def voltage_to_soc(voltage):
    curve = [
        (12.60, 100),
        (12.45, 95),
        (12.30, 90),
        (12.15, 85),
        (12.00, 80),
        (11.85, 70),
        (11.70, 60),
        (11.55, 50),
        (11.40, 40),
        (11.25, 30),
        (11.10, 20),
        (10.95, 15),
        (10.80, 10),
        (10.50, 5),
        (9.60, 0),
    ]

    if voltage >= curve[0][0]:
        return 100.0
    if voltage <= curve[-1][0]:
        return 0.0

    for i in range(len(curve) - 1):
        v1, soc1 = curve[i]
        v2, soc2 = curve[i + 1]

        if v2 <= voltage <= v1:
            return soc2 + (soc1 - soc2) * (voltage - v2) / (v1 - v2)

    return 0.0

# ---------------- MAIN LOOP ----------------
last_time = time.time()
soc = 100.0  # start assumption

print("Relay ON")
GPIO.output(RELAY_PIN, GPIO.HIGH)  # flip if inverted

try:
    while True:
        # --- Toggle relay ---

        time.sleep(2)

        # --- Read INA219 ---
        voltage = ina219.bus_voltage
        current_mA = ina219.current
        current_A = current_mA / 1000.0
        power = ina219.power

        soc = voltage_to_soc(voltage)

        # Clamp
        soc = max(0, min(100, soc))

        # --- Print data ---
        print(f"Voltage: {voltage:.2f} V")
        print(f"Current: {current_mA:.2f} mA")
        print(f"Power:   {power:.2f} mW")
        print(f"SoC:     {soc:.1f}%")
        print("-" * 40)

        time.sleep(2)

except KeyboardInterrupt:
    print("Stopping...")

finally:
    print("Relay OFF")
    GPIO.output(RELAY_PIN, GPIO.LOW)
    GPIO.cleanup()