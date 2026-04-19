from typing import Tuple, Optional, Union
from picamera2 import Picamera2
from ultralytics import YOLO
import numpy as np 
import shutil
import time
import cv2
import os

class Camera_Guide():
    def __init__(self,model, path):
        self.__model = YOLO(model)
        self.__box_x = 0
        self.__box_y = 0
        self.__img_w = 0
        self.__img_h = 0
        self.__path = path

        self.__cam = Picamera2()
        self.__dir = os.environ["HOME"] 

        config = self.__cam.create_still_configuration()
        self.__cam.configure(config)


    def startup(self):
        img = cv2.imread("updated.jpg")
        h, w = img.shape[:2]
        
        self.set_image_dimensions(w,h)

    def show_image(self):
        img = cv2.imread("updated.jpg")
        cv2.imshow("Camera01", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def take_photo(self):
        self.__cam.start()

        print("Taking Picture..")
        time.sleep(1)
        self.__cam.capture_file(f"{self.__dir}/EV-Charging-Arm/Hiwonder_Version/RPi/current.jpg")

        print("Picture Saved..")

    def locate_socket(self):
        print("Locating Socket..")
        results = self.__model("current.jpg", save=True, name=".")

        for result in results:
            boxes = result.boxes
            if len(boxes) > 0:
                coords = boxes.xywh.tolist()
                cx = coords[0][0]
                cy = coords[0][1]
        
                self.set_bounding_box_center(cx, cy)

        img = cv2.imread(f"../../runs/detect/current.jpg")                     # BGR
        out = draw_crosshair_cv(img, center=None)         # center
        cv2.imwrite("updated.jpg", out)

        try:
            shutil.rmtree(self.__path)
            print(f"Folder '{self.__path}' and all its contents have been deleted.")
        except FileNotFoundError:
            print(f"The folder '{self.__path}' does not exist.")
        except PermissionError:
            print(f"Permission denied to delete '{self.__path}'.")
        except Exception as e:
            print(f"An error occurred: {e}")
        
        # Check to see if any objects are found
        if len(boxes) > 0:
            return True
        else:
            return False

    def check_horz(self):
        margins = self.__img_w // 20

        center_x = self.__img_w // 2
        result = abs(center_x - self.__box_x)

        print(f"margins x: {margins}")
        print(f"results x: {result}")
        
        if result > margins:
            # tell to adjust right
            if center_x > self.__box_x:
                return -1
            # adjust left
            else:
                return 1
        if result <= margins:
            return 0

    def check_vert(self):
        margins = self.__img_h // 20

        center_y = self.__img_h // 2
        result = abs(center_y - self.__box_y)

        print(f"margins x: {margins}")
        print(f"results x: {result}")
        
        if result > margins:
            # adjust up
            if center_y > self.__box_y:
                correction = result // margins
                return correction
            # adjust down
            else:
                correction = -1 * (result // margins)
                return correction
        if result <= margins:
            return 0

    def set_bounding_box_center(self,x,y):
        self.__box_x = x
        self.__box_y = y
    
    def get_box_x(self):
        return self.__box_x
    
    def get_box_y(self):
        return self.__box_y
    
    def set_image_dimensions(self,w,h):
        self.__img_w = w
        self.__img_h = h
    
    def get_image_w(self):
        return self.__img_w
    
    def get_image_h(self):
        return self.__img_h
    
Coord = Union[Tuple[int,int], Tuple[float,float]]

def draw_crosshair_cv(
    img: np.ndarray,
    center: Optional[Coord] = None,
    color: Tuple[int,int,int] = (255, 0, 0),
    size: int = 20,
    thickness: int = 2,
    relative: bool = False,
    return_img: bool = True
) -> np.ndarray:
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
    
if __name__ == "__main__":
    print("Running camera_guide as main")
    folder_path = "../../runs/detect"
    camera = Camera_Guide(r"ev_socket_model.pt", folder_path)

    camera.take_photo()
    if camera.locate_socket():
        camera.startup()
        print(camera.check_horz())
        print(camera.check_vert())

