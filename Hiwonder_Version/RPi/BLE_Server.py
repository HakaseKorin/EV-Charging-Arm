from bleak import BleakClient, BleakScanner
from camera_guide import Camera_Guide
from gui import ControllerGui
import RPi.GPIO as GPIO
import threading
import asyncio
import queue
import time

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID     = "12345678-1234-5678-1234-56789abcdef1"
DEVICE_NAME="ESP32_Server"

command_queue = queue.Queue()
status_queue = queue.Queue()

gui = ControllerGui(command_queue,status_queue)

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

def awaitingCommand(command, command_queue):
    while True:
        if command_queue.get() == command:
            break

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
    camera = Camera_Guide(r"daykit_socket_model.pt", folder_path)

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
                    input("Press Enter to try again..")
                if(horz_result == 1):
                    print("Please adjust your vehicle left")
                    input("Press Enter to try again..")
                camera.take_photo()
                camera.locate_socket()
            while True:
                
                # Tells arm that vehicle is aligned within bounds
                message = "aligned"
                data = message.encode()
                await client.write_gatt_char(CHAR_UUID, data, response=True)
                time.sleep(5)

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
            time.sleep(7)
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

async def remote_worker(command_queue, status_queue):
    # should mirror main() but uses queue to coordinate everything.
    status_queue.put("SYSTEM_INITIALIZING")
    folder_path = "../../runs/detect"
    camera = Camera_Guide(r"ev_socket_model.pt", folder_path)

    status_queue.put("CONNECTING_TO_DEVICE")
    await scan_and_connect()

    disconnect_event = asyncio.Event()

    try: 
        cmd = command_queue.get_nowait()
    except:
        cmd = None

    # do all the back and forth in here..
    try:
        async with BleakClient(
            device, disconnected_callback=lambda c: disconnect_event.set()
        ) as client:
            while True:
                
                # wait for command CAPTURE from gui
                status_queue.put("SYSTEM_READY")
                awaitingCommand("CAPTURE", command_queue)
                
                standby()
                camera.take_photo()
                
                # Locate Socket
                status_queue.put("FINDING_TARGET")
                if camera.locate_socket():
                    break
                status_queue.put("NO_TARGET_FOUND")
                time.sleep(5)
            
            camera.startup()

            while True:
                # Horizontal alignment
                horz_result = camera.check_horz()
                if(horz_result == 0):
                    status_queue.put("CAUTION_STAND_CLEAR_OF_ARM")
                    time.sleep(1)

                    #camera.show_image()
                    break
                if(horz_result == -1):
                    status_queue.put("NOT_ALIGNED")
                    status_queue.put("ADJUST_VEHICLE_FORWARD")
                if(horz_result == 1):
                    status_queue.put("NOT_ALIGNED")
                    status_queue.put("ADJUST_VEHICLE_BACKWARD")

                camera.take_photo()
                camera.locate_socket()

                awaitingCommand("RETRY", command_queue)
            while True:
                
                # Tells arm that vehicle is aligned within bounds
                message = "aligned"
                data = message.encode()
                await client.write_gatt_char(CHAR_UUID, data, response=True)
                time.sleep(5)

                # Vertical alignment
                vert_result = camera.check_vert()
                if(vert_result == 0):
                    print("Arm within tolerances, beginning approach..")
                    status_queue.put("STARTING_APPROACH")
                    docking()
                    time.sleep(1)
                    break
                if(vert_result < 0):
                    # adjust up
                    status_queue.put("STARTING_APPROACH")
                    status_queue.put("ADJUSTING UPWARDS")
                if(vert_result > 0):
                    # adjust down
                    status_queue.put("STARTING_APPROACH")
                    status_queue.put("ADJUSTING BACKWARDS")
                data = str(vert_result).encode()
                await client.write_gatt_char(CHAR_UUID, data, response=True)
                docking()
                time.sleep(1)
                break
            time.sleep(7)
            status_queue.put("DOCKING_COMPLETE")
            charging()
            awaitingCommand("DISCONNECT",command_queue)
            message = "disconnect"
            data = message.encode()
            await client.write_gatt_char(CHAR_UUID, data, response=True)
            
            status_queue.put("DISCONNECTION_START")
            time.sleep(1)

            status_queue.put("ARM_RETRACTING")
            # Give command to approach
            disconnect()
            docking()
            time.sleep(4)
            standby()
            status_queue.put("DISCONNECT_COMPLETE")
            awaitingCommand("FINISH",command_queue)
               

    except Exception:
        print("Exception while connecting/connected", Exception)

def run_async(command_queue,status_queue):
    asyncio.run(remote_worker(command_queue,status_queue))

arm_thread = threading.Thread(
    target=run_async,
    args=(command_queue,status_queue),
    daemon=True
)

arm_thread.start()
gui.run()

#asyncio.run(main())