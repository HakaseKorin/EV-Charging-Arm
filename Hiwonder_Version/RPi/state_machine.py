import serial
import time

ser = serial.Serial('/dev/serial0', 9600, timeout=1)
time.sleep(2)

# Standby
print("Standby")
ser.write(b"STATE:1\n")
time.sleep(3)

# Docking
print("Docking")
ser.write(b"STATE:2\n")
time.sleep(5)

# Charging
print("Charging")
ser.write(b"STATE:3\n")
time.sleep(5)