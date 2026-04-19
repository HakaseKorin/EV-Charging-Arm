# venv enviroment setup notes

when setting up virtual environment ensure that the environment has access to system site packages
picamera2 is easier installed on system rather that installed in the environment

when installing torch and torchvision, this version on the Raspberry pi 4 works with

torch=2.60 torchvision=0.21.0

when installing ultralytics onto a raspberry pi 4
the size of the file is typically too large for installation 

store the files in a larger partition of the drive

TMPDIR=/var/tmp/ pip install ultralytics --no-cache-dir

# using the python code

open up CLI
navigate to this folder

from root

cd EV-Charging-Arm
cd Hiwonder_Version
cd RPi
source env/bin/activate
python BLE_Server.py

# TODOS

connect RPi to ESP32 and communicate commands back and forth
    execution should come from the pi side first before claw moves

create function to tell user if car is aligned with claw

create gui
display the image after being analyzed by model

