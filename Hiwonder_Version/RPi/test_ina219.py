import time
import board
import busio
import RPi.GPIO as GPIO
from adafruit_ina219 import INA219

# ---- GPIO SETUP ----
RELAY_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

# ---- INA219 SETUP ----
i2c = busio.I2C(board.SCL, board.SDA)
ina219 = INA219(i2c)

def read_sensor():
    print(f"Voltage: {ina219.bus_voltage:.3f} V")
    print(f"Current: {ina219.current:.3f} mA")
    print(f"Power:   {ina219.power:.3f} mW")
    print("-" * 30)

try:
    while True:
        print("Relay ON")
        GPIO.output(RELAY_PIN, GPIO.HIGH)  # may be LOW depending on module
        time.sleep(2)

        read_sensor()

        print("Relay OFF")
        GPIO.output(RELAY_PIN, GPIO.LOW)
        time.sleep(2)

except KeyboardInterrupt:
    print("Exiting...")

finally:
    GPIO.cleanup()