import board
import busio
from adafruit_ina219 import INA219

# Initialize I2C
i2c = busio.I2C(board.SCL, board.SDA)

# Create INA219 object
ina219 = INA219(i2c)

# Read values
print("Bus Voltage: {:.3f} V".format(ina219.bus_voltage))
print("Current: {:.3f} mA".format(ina219.current))
print("Power: {:.3f} mW".format(ina219.power))