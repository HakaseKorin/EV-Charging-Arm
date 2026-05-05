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

RELAY_ON = GPIO.HIGH
RELAY_OFF = GPIO.LOW

# ---------------- GPIO SETUP ----------------
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

# Set relay once
GPIO.output(RELAY_PIN, RELAY_ON)

# ---------------- INA219 SETUP ----------------
i2c = busio.I2C(board.SCL, board.SDA)
ina219 = INA219(i2c)

# ---------------- VOLTAGE -> SOC ----------------
def voltage_to_soc(voltage):
    curve = [
        (12.60, 100), (12.45, 95), (12.30, 90), (12.15, 85),
        (12.00, 80), (11.85, 70), (11.70, 60), (11.55, 50),
        (11.40, 40), (11.25, 30), (11.10, 20), (10.95, 15),
        (10.80, 10), (10.50, 5), (9.60, 0),
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

# ---------------- ETA FORMAT ----------------
def format_eta(hours):
    if hours is None or hours == float("inf"):
        return "N/A"
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m}m"

# ---------------- MAIN LOOP ----------------
last_time = time.time()
soc = 100.0

try:
    while True:
        voltage = ina219.bus_voltage
        current_mA = ina219.current
        current_A = current_mA / 1000.0
        power = ina219.power

        now = time.time()
        dt_hours = (now - last_time) / 3600.0
        last_time = now

        # --- Coulomb counting ---
        soc -= (current_A * dt_hours / BATTERY_CAPACITY_AH) * 100

        # --- Voltage correction (always allowed now) ---
        soc = voltage_to_soc(voltage)

        soc = max(0, min(100, soc))

        # ---------------- ETA CALCULATION ----------------
        if current_A > 0:
            # Discharging
            eta_hours = (soc / 100.0) * BATTERY_CAPACITY_AH / current_A if current_A != 0 else float("inf")
            mode = "Discharging"
        elif current_A < 0:
            # Charging
            eta_hours = ((100 - soc) / 100.0) * BATTERY_CAPACITY_AH / abs(current_A)
            mode = "Charging"
        else:
            eta_hours = float("inf")
            mode = "Idle"

        # --- Low voltage safety ---
        if voltage < MIN_VOLTAGE:
            print("⚠️ Low battery! Turning relay OFF.")
            GPIO.output(RELAY_PIN, RELAY_OFF)

        # --- Output ---
        print(f"Voltage: {voltage:.2f} V")
        print(f"Current: {current_mA:.2f} mA")
        print(f"Power:   {power:.2f} mW")
        print(f"SoC:     {soc:.1f}%")
        print(f"Mode:    {mode}")
        print(f"ETA:     {format_eta(eta_hours)}")
        print("-" * 40)

        time.sleep(1)

except KeyboardInterrupt:
    print("Stopping...")

finally:
    GPIO.cleanup()