from bleak import BleakClient, BleakScanner
from camera_guide import Camera_Guide
import RPi.GPIO as GPIO
import asyncio
import time

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID     = "12345678-1234-5678-1234-56789abcdef1"
DEVICE_NAME="ESP32_Server"

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.setup(27, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)

def charging_in_progress():
    print("Now charging..")
    time.sleep(3)
    GPIO.output(23,GPIO.HIGH)

def disconnect():
    print("Stopping charging squence..")
    GPIO.output(23,GPIO.LOW)

def standby():
    print("Standby")
    GPIO.output(17,GPIO.HIGH)
    GPIO.output(27,GPIO.LOW)
    GPIO.output(22,GPIO.LOW)
    time.sleep(2)

def docking():
    print("Docking")
    GPIO.output(17,GPIO.LOW)
    GPIO.output(27,GPIO.HIGH)
    GPIO.output(22,GPIO.LOW)
    time.sleep(2)

def charging():
    print("Charging")
    GPIO.output(17,GPIO.LOW)
    GPIO.output(27,GPIO.LOW)
    GPIO.output(22,GPIO.HIGH)
    time.sleep(2)

    charging_in_progress()

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

async def main():
    folder_path = "../../runs/detect"
    camera = Camera_Guide(r"ev_socket_model.pt", folder_path)

    await scan_and_connect()

    disconnect_event = asyncio.Event()

    time.sleep(2)

    # do all the back and forth in here..
    try:
        async with BleakClient(
            device, disconnected_callback=lambda c: disconnect_event.set()
        ) as client:
            while True:
                input("System Ready, Press Enter to continue..")
                standby()
                camera.take_photo()
                # Locate Socket
                if camera.locate_socket():
                    break
                print("No viable target located, please try again..")
                time.sleep(5)
            
            camera.startup()

            while True:
                # Horizontal alignment
                horz_result = camera.check_horz()
                if(horz_result == 0):
                    print("Please do not move vehicle while arm is in motion..")
                    time.sleep(1)

                    #camera.show_image()
                    break
                if(horz_result == -1):
                    print("Please adjust your vehicle right")
                    camera.take_photo()
                    camera.locate_socket()
                    input("Press Enter to try again..")
                if(horz_result == 1):
                    print("Please adjust your vehicle left")
                    camera.take_photo()
                    camera.locate_socket()
                    input("Press Enter to try again..")
            while True:
                # Vertical alignment
                vert_result = camera.check_vert()
                if(vert_result == 0):
                    print("Arm within tolerances, beginning approach..")
                    docking()
                    time.sleep(1)
                    break
                if(vert_result < 0):
                    # adjust up
                    data = str(vert_result).encode()
                    await client.write_gatt_char(CHAR_UUID, data, response=True)
                    print("Adjusting arm upwards..")
                    docking()
                    time.sleep(1)
                    break
                if(vert_result > 0):
                    # adjust down
                    data = str(vert_result).encode()
                    await client.write_gatt_char(CHAR_UUID, data, response=True)
                    print("Adjusting arm downwards..")
                    docking()
                    time.sleep(1)
                    break
            time.sleep(5)
            print("Device is now connected..")
            charging()
            input("Press Enter to Disconnect..")
            message = "disconnect"
            data = message.encode()
            await client.write_gatt_char(CHAR_UUID, data, response=True)
            # Give command to approach
            disconnect()
            docking()
            time.sleep(4)
            standby()
            input("Press Enter to End Simulation")
               

    except Exception:
        print("Exception while connecting/connected", Exception)

asyncio.run(main())