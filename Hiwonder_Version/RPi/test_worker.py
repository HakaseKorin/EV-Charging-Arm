from gui import ControllerGui
import queue
import threading
import time
import random

command_queue = queue.Queue()
status_queue = queue.Queue()

gui = ControllerGui(command_queue, status_queue)

def awaitingCommand(command, command_queue):
    while True:
        if command_queue.get() == command:
            break

def random_event(status_queue):
    match random.randint(1,3):
        case 1:
            status_queue.put("NOT_FOUND")
            print("not found")
        case 2:
            status_queue.put("NOT_ALIGNED")
            print("not aligned")
        case 3:
            status_queue.put("TARGET_FOUND")
            print("target found")
        case _:
            pass

def thread_worker(command_queue, status_queue):
    status_queue.put("SYSTEM_INITIALIZING")
    print("system initializing")

    status_queue.put("SYSTEM_READY")
    print("system ready")
    time.sleep(1)

    awaitingCommand("CAPTURE", command_queue)
    status_queue.put("IMAGE_CAPTURED")
    time.sleep(2)
    status_queue.put("FINDING_TARGET")
    time.sleep(3)

    random_event(status_queue)

    while True:
        status = status_queue.get()
        status_queue.put(status)
        match status:
            case "NOT_FOUND":
                awaitingCommand("RETRY",command_queue)
                random_event(status_queue)
            case "NOT_ALIGNED":
                awaitingCommand("RETRY",command_queue)
                random_event(status_queue)
            case "TARGET_FOUND":
                break
            case _: # unkown command
                pass
    status_queue.put("VEHICLE_ALIGNED")
    time.sleep(2)
    status_queue.put("STARTING_APPROACH")
    time.sleep(7)
    status_queue.put("DOCKING_COMPLETE")
    
    awaitingCommand("DISCONNECT", command_queue)
    status_queue.put("DISCONNECTION_START")
    time.sleep(1)
    status_queue.put("ARM_RETRACTED")
    time.sleep(3)
    status_queue.put("DISCONNECT_COMPLETE")
    time.sleep(10)

worker_thread = threading.Thread(
    target=thread_worker,
    args=(command_queue,status_queue),
    daemon=True
)

worker_thread.start()
gui.run()
