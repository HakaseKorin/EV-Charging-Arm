import board
import busio
from gpiozero import OutputDevice
from adafruit_ina219 import INA219
import time

# Initialize I2C
i2c = busio.I2C(board.SCL, board.SDA)

# -------------------------
# Charging safety limits
# -------------------------
MAX_BATTERY_VOLTAGE = 12.60   # 3S Li-ion full charge
MAX_CURRENT_A = 2.0           # adjust for your charger/battery
MIN_BATTERY_VOLTAGE = 9.0     # fault threshold

# relay setup
RELAY_PIN = 17
# Change this if your relay is active LOW
RELAY_ACTIVE_HIGH = True

relay = OutputDevice(
    RELAY_PIN,
    active_high=RELAY_ACTIVE_HIGH,
    initial_value=False
)

# -------------------------
# INA219 setup
# -------------------------
i2c = busio.I2C(board.SCL, board.SDA)
ina219 = INA219(i2c)

# Create INA219 object
ina219 = INA219(i2c)

def set_relay(on: bool):
    if on:
        relay.on()
    else:
        relay.off()

def relay_state_text():
    return "ON" if relay.value else "OFF"

def read_sensor():
    bus_voltage = ina219.bus_voltage      # volts
    current = ina219.current / 1000.0     # mA to A
    power = ina219.power / 1000.0         # mW to W
    return bus_voltage, current, power

def should_charge(voltage, current):
    if voltage >= MAX_BATTERY_VOLTAGE:
        return False

    if voltage <= MIN_BATTERY_VOLTAGE:
        return False

    if abs(current) > MAX_CURRENT_A:
        return False

    return True

try:
    print("INA219 + Relay Charger Monitor Started")
    print("Press CTRL+C to stop")

    while True:
        voltage, current, power = read_sensor()

        charge_allowed = should_charge(voltage, current)
        set_relay(charge_allowed)

        print(
            f"Voltage: {voltage:.2f} V | "
            f"Current: {current:.3f} A | "
            f"Power: {power:.2f} W | "
            f"Relay: {relay_state_text()}"
        )

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nStopping system...")

finally:
    set_relay(False)
    relay.close()
    print("Relay OFF. Shutdown complete.")

# Read values
print("Bus Voltage: {:.3f} V".format(ina219.bus_voltage))
print("Current: {:.3f} mA".format(ina219.current))
print("Power: {:.3f} mW".format(ina219.power))