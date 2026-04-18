from ultralytics import YOLO
from picamera2 import Picamera2
from PIL import Image
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
img = Image.open("current.jpg")

for result in results:
    # Access the Boxes object
    boxes = result.boxes
    
    # Check if any objects were detected
    if len(boxes) > 0:
        print(True)
    else:
        print(False)


input("Press enter to exit")
