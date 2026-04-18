from typing import Tuple, Optional, Union
from picamera2 import Picamera2 
from ultralytics import YOLO 
from PIL import Image
import numpy as np
import shutil
import time
import cv2
import os

home_dir = os.environ["HOME"]

cam = Picamera2()
config = cam.create_still_configuration()
cam.configure(config)

Coord = Union[Tuple[int,int], Tuple[float,float]]
folder_path = "../../runs/detect"

def draw_crosshair_cv(
    img: np.ndarray,
    center: Optional[Coord] = None,
    color: Tuple[int,int,int] = (255, 0, 0),
    size: int = 20,
    thickness: int = 2,
    relative: bool = False,
    return_img: bool = True
) -> np.ndarray:
    """
    Draws a crosshair on an OpenCV image (numpy BGR array).

    - img: input image as numpy array (BGR). Will not be modified unless you reassign the return.
    - center: (x, y). If None, default is image center.
              If relative=True, provide floats in [0,1] meaning fraction of width/height.
    - color: BGR tuple (default green).
    - size: half-length of each crosshair arm in pixels.
    - thickness: line thickness.
    - relative: whether center is relative (fractions) or absolute (pixels).
    - return_img: whether to return the modified image.

    Returns the modified image (copy).
    """
    if img is None:
        raise ValueError("img must be a numpy array (loaded with cv2.imread or created).")
    h, w = img.shape[:2]
    out = img.copy()

    if center is None:
        cx, cy = w // 2, h // 2
    else:
        cx, cy = center
        if relative:
            # allow floats in [0,1]
            cx = int(round(cx * w))
            cy = int(round(cy * h))
        else:
            cx = int(round(cx))
            cy = int(round(cy))

     # horizontal line
    x1, x2 = max(0, cx - size), min(w - 1, cx + size)
    cv2.line(out, (x1, cy), (x2, cy), color, thickness, lineType=cv2.LINE_AA)

    # vertical line
    y1, y2 = max(0, cy - size), min(h - 1, cy + size)
    cv2.line(out, (cx, y1), (cx, y2), color, thickness, lineType=cv2.LINE_AA)

    # optional small center dot for precision (thin filled circle)
    cv2.circle(out, (cx, cy), max(1, thickness), color, -1, lineType=cv2.LINE_AA)

    if return_img:
        return out


cam.start()

print("Taking Picture..")
time.sleep(2)
cam.capture_file(f"{home_dir}/EV-Charging-Arm/Hiwonder_Version/RPi/current.jpg")
print("Saved Picture")

# Load trained model
model = YOLO(r"ev_socket_model.pt")
print("Finding Socket..")

# Run inference with boxes automatically drawn & saved
results = model("current.jpg", save=True, name=".")
#img = Image.open("current.jpg")

for result in results:
    # Access the Boxes object
    boxes = result.boxes
    
    # Check if any objects were detected
    if len(boxes) > 0:
        print(True)
    else:
        print(False)

img = cv2.imread(f"{folder_path}/current.jpg")                     # BGR
out = draw_crosshair_cv(img, center=None)         # center
cv2.imwrite("updated.jpg", out)

try:
    shutil.rmtree(folder_path)
    print(f"Folder '{folder_path}' and all its contents have been deleted.")
except FileNotFoundError:
    print(f"The folder '{folder_path}' does not exist.")
except PermissionError:
    print(f"Permission denied to delete '{folder_path}'.")
except Exception as e:
    print(f"An error occurred: {e}")

input("Press enter to exit")
