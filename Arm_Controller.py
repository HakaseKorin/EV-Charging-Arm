from ultralytics import YOLO
from picamera2 import Picamera2
import os
import serial # pip install pyserial
import time

home_dir = os.environ["HOME"]
cam = Picamera2()
config = cam.create_still_configuration()
cam.configure(config)

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
time.sleep(2)

input_buffer = ""
reading_frame = False

def send(cmd, value):
    msg = f"<{cmd}|{value}>"
    ser.write(msg.encode())
    print("Sent:", msg)

def read_messages():
    while ser.in_waiting:
        line = ser.readline().decode().strip()
        print("Arduino:", line)

def read_serial():
    global input_buffer, reading_frame

    while ser.in_waiting > 0:
        c = ser.read().decode(errors='ignore')

        if c == '<':
            input_buffer = ""
            reading_frame = True

        elif c == '>':
            reading_frame = False
            process_message(input_buffer)

        else:
            if reading_frame:
                input_buffer += c

def process_message(msg):
    if '|' not in msg:
        print("Invalid frame:", msg)
        return

    command, value = msg.split('|', 1)  # split only at first '|'

    print("Command:", command)
    print("Value:  ", value)

    # Example: respond back to Arduino
    send(f"ACK {command}", value)

def scan():
    cam.start()
    print("Taking Picture..")
    time.sleep(2)
    cam.capture_file(f"{home_dir}/EV-Charging-Arm/current.jpg")
    print("Saved Picture")

    # Load trained model
    model = YOLO(r"ev_socket_model.pt")
    print("Finding Socket..")

    # Run inference with boxes automatically drawn & saved
    results = model("current.jpg", save=True, name=".")

    for result in results:
        # Access the Boxes object
        boxes = result.boxes
    
        # Check if any objects were detected
        if len(boxes) > 0:
            return "TRUE"
        else:
            return "FALSE"

while True:
    user_input = input("Command: ").strip()

    if user_input.lower() == "exit":
        print("Exiting...")
        break

    # Parse simple commands like: MOVE FORWARD, STATE RESET, STATE SCAN, ROTATE 10/-10, X 10/-10, Y 10/-10, CLAW OPEN/CLOSE
    try:
        parts = user_input.split()
        cmd = parts[0]
        value = " ".join(parts[1:]) if len(parts) > 1 else ""
        if value == "SCAN":
            cmd == "SCAN"
            value = scan()
        send(cmd, value)
    except Exception as e:
        print("Error parsing command:", e)

    # Read Arduino messages after each command
    time.sleep(0.1)
    read_messages()
