import serial # pip install pyserial
import time

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
time.sleep(2)

def send(cmd, value):
    msg = f"<{cmd}|{value}>"
    ser.write(msg.encode())
    print("Sent:", msg)

def read_messages():
    while ser.in_waiting:
        line = ser.readline().decode().strip()
        print("Arduino:", line)

# Example: Turn LED into BLINK mode
send("SET_MODE", "BLINK")

time.sleep(1)

# Then print logs for 10 seconds
start = time.time()
while time.time() - start < 10:
    read_messages()
    time.sleep(0.1)

# Example: Turn LED OFF again
send("SET_MODE", "OFF")