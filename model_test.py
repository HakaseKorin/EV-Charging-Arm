from ultralytics import YOLO
from picamera2 import Picamera2
import os
import time

home_dir = os.environ["HOME"]
cam = Picamera2()
config = cam.create_still_configuration()
cam.configure(config)

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
