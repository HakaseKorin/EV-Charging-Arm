import asyncio
from bleak import BleakClient, BleakScanner
import time
from camera_guide import Camera_Guide

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID     = "12345678-1234-5678-1234-56789abcdef1"
DEVICE_NAME="ESP32_Server"

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
                camera.take_photo()
                # Locate Socket
                if camera.locate_socket():
                    break
                print("No viable target located, please try again..")
                time.sleep(5)
            
            camera.start()

            while True:
                # Horizontal alignment
                horz_result = camera.check_horz()
                if(horz_result == 0):
                    break
                if(horz_result == -1):
                    print("Please adjust your vehicle right")
                    input("Press Enter to try again..")
                if(horz_result == 1):
                    print("Please adjust your vehicle left")
                    input("Press Enter to try again..")
            while True:
                # Vertical alignment
                vert_result = camera.check_vert()
                if(vert_result == 0):
                    break
                if(vert_result == -1):
                    # adjust up
                    message = "adjust_up"
                    data = message.encode()
                    await client.write_gatt_char(CHAR_UUID, data, response=True)
                    print("Adjusting arm upwards..")
                    break
                if(vert_result == 1):
                    # adjust down
                    message = "adjust_down"
                    data = message.encode()
                    await client.write_gatt_char(CHAR_UUID, data, response=True)
                    print("Adjusting arm downwards..")
                    break
            # Give command to approach
            print("Device is now connected..")
            input("Press Enter to End Simulation")
               

    except Exception:
        print("Exception while connecting/connected", Exception)

asyncio.run(main())