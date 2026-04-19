from bleak import BleakClient, BleakScanner
from typing import Tuple, Optional, Union
from picamera2 import Picamera2 
from ultralytics import YOLO 
from PIL import Image
import numpy as np
import asyncio
import shutil
import time
import cv2
import os
import time

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID     = "12345678-1234-5678-1234-56789abcdef1"
DEVICE_NAME="ESP32_Server"

home_dir = os.environ["HOME"]

cam = Picamera2()
config = cam.create_still_configuration()
cam.configure(config)

Coord = Union[Tuple[int,int], Tuple[float,float]]
folder_path = "../../runs/detect"
model = YOLO(r"ev_socket_model.pt")

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


async def scan_and_connect():
    global device
    
    retries = 0
    while True:
        print(f"Scanning for device {DEVICE_NAME}")
        device = await BleakScanner.find_device_by_name(DEVICE_NAME)

        # Breaks out of loop once a connection is found
        if device is not None:
            print(f"Connected to {DEVICE_NAME} at...",device.address)
            break
        
        print("No device found.. Now attemping to reconnect.. (30s)")
        
        # Do use asyncio.sleep() in an asyncio program.
        await asyncio.sleep(30)
        retries += 1
        #TODO: change to properly end program
        if retries>10: return

# returns -1 to adjust left, 1 to adjust right, 0 for no change
def check_horz(box_x, cam_x):
    img = cv2.imread("update.jpg")
    h, w = img.shape[:2]
    margins = int(w*.05)

    # finding center
    result = cam_x - box_x
    
    if abs(result) > margins:
        # tell to adjust left
        return -1
    if abs(result) < margins:
        # tell to adjust right
        return 1
    # no change needed
    return 0;

# returns -1 to adjust left, 1 to adjust right, 0 for no change
def check_vert(box_y, cam_y):
    img = cv2.imread("update.jpg")
    h, w = img.shape[:2]
    margins = int(h*.05)

    # finding center
    result = cam_y - box_y
    
    if abs(result) > margins:
        # tell to adjust left
        return -1
    if abs(result) < margins:
        # tell to adjust right
        return 1
    # no change needed
    return 0;


def take_photo():
    cx = 0 
    cy = 0
    w = 0
    h = 0

    cam.start()

    print("Taking Picture..")
    time.sleep(1)

    cam.capture_file(f"{home_dir}/EV-Charging-Arm/Hiwonder_Version/RPi/current.jpg")
    print("Saved Picture")
    time.sleep(1)

    print("Finding Socket..")
    # Run inference with boxes automatically drawn & saved
    results = model("current.jpg", save=True, name=".")
    #img = Image.open("current.jpg")

    for result in results:
        # Access the Boxes object
        boxes = result.boxes
        cx, cy, w, h = boxes.xywh

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
    
        # Check if any objects were detected
    if len(boxes) > 0:
        return True
    else:
        return False


async def main():
    await scan_and_connect()

    disconnect_event = asyncio.Event()

    ser = serial.Serial("/dev/serial0",9600,timeout=1)
    time.sleep(2)

    # do all the back and forth in here..
    try:
        async with BleakClient(
            device, disconnected_callback=lambda c: disconnect_event.set()
        ) as client:
            while True:
                
                #waiting for press to start
                input("Press Enter to Begin")

                # take first photo
                if take_photo():
                    # send commands to realign robot arm head and thrust forward
                    pass
                else:
                    # send Error code and end
                    return

                if ser.in_waiting:
                    data = ser.readline().decode(errors="ignore").strip()
                    if data:
                        print("Received:", data)

                        if len(data) > 1:
                            commands = list(data)
                            for _ in commands:
                                msg = _
                                data = msg.encode()
                                await client.write_gatt_char(CHAR_UUID, data, response=True)
                                print("Sent:", msg)
                        else:
                            msg = data
                            data = msg.encode()
                            await client.write_gatt_char(CHAR_UUID, data, response=True)
                            print("Sent:", msg)
                        data = None # resets to none to wait for new input

    except Exception:
        print("Exception while connecting/connected", Exception)


take_photo()
input("Press enter to exit")
