from picamera2 import Picamera2
import time
import os
import random

photo_id = random.randint(10000000,99999999)

home_dir = os.environ["HOME"]
cam = Picamera2()
config = cam.create_still_configuration()
cam.configure(config)

cam.start()
time.sleep(2)
cam.capture_file(f"{home_dir}/EV-Charging-Arm/current{photo_id}.jpg")
print(f"Saved current{photo_id}.jpg")
