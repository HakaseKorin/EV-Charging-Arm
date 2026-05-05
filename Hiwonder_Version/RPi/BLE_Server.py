from bleak import BleakClient, BleakScanner
from camera_guide import Camera_Guide
from gui import ControllerGui
import RPi.GPIO as GPIO
import threading
import asyncio
import queue
import time
from soc import BatterySensor, SoCTracker, relay_on, relay_off

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID     = "12345678-1234-5678-1234-56789abcdef1"
DEVICE_NAME="ESP32_Server"

command_queue = queue.Queue()
status_queue = queue.Queue()
state_queue = queue.Queue()
observer_queue = queue.Queue()

gui = ControllerGui(command_queue,status_queue)

RELAY_PIN       = 17
STANDBY_PIN     = 25
DOCKING_PIN     = 27
CHARGING_PIN    = 22
CONNECTED_PIN   = 23

GPIO.setmode(GPIO.BCM)
GPIO.setup(STANDBY_PIN, GPIO.OUT)
GPIO.setup(DOCKING_PIN, GPIO.OUT)
GPIO.setup(CHARGING_PIN, GPIO.OUT)
GPIO.setup(CONNECTED_PIN, GPIO.OUT)

def charging_in_progress(tracker, current, status_queue):
    print("Now charging..")
    GPIO.output(CONNECTED_PIN,GPIO.HIGH)

    if tracker.soc_pct >= 99.9 and current < 0:
        status_queue.put("DISCONNECT")
def disconnect():
    print("Stopping charging squence..")
    GPIO.output(CONNECTED_PIN,GPIO.LOW)

def standby():
    print("Standby")
    GPIO.output(STANDBY_PIN,GPIO.HIGH)
    GPIO.output(DOCKING_PIN,GPIO.LOW)
    GPIO.output(CHARGING_PIN,GPIO.LOW)

def docking():
    print("Docking")
    GPIO.output(STANDBY_PIN,GPIO.LOW)
    GPIO.output(DOCKING_PIN,GPIO.HIGH)
    GPIO.output(CHARGING_PIN,GPIO.LOW)

def charging(tracker, current, status_queue):
    print("Charging")
    GPIO.output(STANDBY_PIN,GPIO.LOW)
    GPIO.output(DOCKING_PIN,GPIO.LOW)
    GPIO.output(CHARGING_PIN,GPIO.HIGH)

    charging_in_progress(tracker, current, status_queue)

def awaitingCommand(command, command_queue, state_queue):
    while True:
        #if command_queue.get() == "DISCONNECT":
        #    state_queue.put("DISCONNECT")
        #    break
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

async def remote_worker(command_queue, status_queue,state_queue,observer_queue):
    # should mirror main() but uses queue to coordinate everything.
    status_queue.put("SYSTEM_INITIALIZING")
    folder_path = "../../runs/detect"
    camera = Camera_Guide(r"daykit_socket_model.pt", folder_path)

    restart = True

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
            
            while restart:
                while True:
                    
                    # wait for command CAPTURE from gui
                    status_queue.put("SYSTEM_READY")
                    state_queue.put("STANDBY")
                    awaitingCommand("CAPTURE", command_queue, state_queue)
                    
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

                        #status_queue.put("SHOW_IMAGE")
                        break
                    if(horz_result == -1):
                        status_queue.put("NOT_ALIGNED")
                        status_queue.put("ADJUST_VEHICLE_FORWARD")
                    if(horz_result == 1):
                        status_queue.put("NOT_ALIGNED")
                        status_queue.put("ADJUST_VEHICLE_BACKWARD")

                    camera.take_photo()
                    camera.locate_socket()
                    #status_queue.put("SHOW_IMAGE")

                    awaitingCommand("RETRY", command_queue, state_queue)
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
                        state_queue.put("DOCKING")
                        break
                    if(vert_result > 0):
                        # adjust up
                        status_queue.put("STARTING_APPROACH")
                        status_queue.put("ADJUSTING_UPWARDS")
                    if(vert_result < 0):
                        # adjust down
                        status_queue.put("STARTING_APPROACH")
                        status_queue.put("ADJUSTING_DOWNWARDS")
                    data = str(vert_result).encode()
                    await client.write_gatt_char(CHAR_UUID, data, response=True)
                    state_queue.put("DOCKING")
                    break
                time.sleep(7)
                status_queue.put("DOCKING_COMPLETE")
                status_queue.put("CHARGING")
                awaitingCommand("DISCONNECT",command_queue, state_queue)
                message = "disconnect"
                data = message.encode()
                await client.write_gatt_char(CHAR_UUID, data, response=True)
                
                status_queue.put("DISCONNECTION_START")
                time.sleep(1)
                status_queue.put("ARM_RETRACTING")
                # Give command to approach
                state_queue.put("DOCKING")
                time.sleep(4)
                state_queue.put("STANDBY")
                status_queue.put("DISCONNECT_COMPLETE")
                awaitingCommand("FINISH",command_queue, state_queue)
               

    except Exception:
        print("Exception while connecting/connected", Exception)

def run_async(command_queue,status_queue,state_queue):
    asyncio.run(remote_worker(command_queue,status_queue, state_queue,observer_queue))

def state_worker(state_queue, observation_queue, status_queue):
    state_queue.put("STATE_QUEUE_START")
    observation_queue.put("OBSERVATION_START")

    battery_sensor = BatterySensor()
    soc_tracker = SoCTracker(battery_sensor)

    while True:
        while not state_queue.empty():
            msg = state_queue.get()
            print(msg)

            if msg == "STANDBY":
                standby()

            if msg == "DOCKING":
                docking()

            if msg == "CHARGING":
                relay_on()

                voltage, current_ma, power_mw = soc_tracker.update()
                is_charging = current_ma < -5.0
                is_idle     = abs(current_ma) <= 5.0
                state       = "CHARGING" if is_charging else ("IDLE" if is_idle else "DISCHARGING")
                # if charging
                if state == "CHARGING":
                    ttf = soc_tracker.time_to_full
                    observer_queue.put(f"SoC: {soc_tracker.soc_pct}%, ETA: {soc_tracker.fmt_minutes(ttf)}")
                    charging(soc_tracker, current_ma, status_queue)

            if msg == "DISCONNECT":
                relay_off()
                disconnect()
            time.sleep(1)

state_thread = threading.Thread(
    target=state_worker,
    args=(state_queue, observer_queue, status_queue),
    daemon=True
)

arm_thread = threading.Thread(
    target=run_async,
    args=(command_queue,status_queue,observer_queue),
    daemon=True
)

state_thread.start()
arm_thread.start()
gui.run()

#asyncio.run(main())