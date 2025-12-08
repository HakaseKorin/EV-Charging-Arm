from picamera2 import Picamera2
import os
import time

home_dir = os.environ["HOME"]
cam = Picamera2()
config = cam.create_still_configuration()
cam.configure(config)

cam.start()
time.sleep(2)
cam.capture_file(f"{home_dir}/EV-Charging-Arm/current.jpg")
print("Saved current.jpg")