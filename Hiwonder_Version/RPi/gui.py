import tkinter as tk

class ControllerGui:
    def __init__(self, command_queue, status_queue):
        # Creates main window
        self.__root = tk.Tk()
        self.__command_queue = command_queue
        self.__status_queue = status_queue
        self.__root.title("Robot Controllor GUI")
        self.__root.geometry("300x200")

        # Title Label
        self.__label = tk.Label(
            self.__root,
            text="Robot Controller",
            font=("Arial", 14)
        )
        self.__label.pack(pady=20)

        # Start Button
        self.__button = tk.Button(
            self.__root,
            text="Start",
            font=("Arial", 12),
            width=15,
            height=2,
            command=start_program
        )
        self.__button.pack(pady=10)
        self.__button.config(state="disabled")

        # Status label
        self.__status = tk.Label(
            self.__root,
            text="Waiting...",
            font=("Arial", 10)
        )
        self.__status.pack(pady=10)

    def run(self):
        self.__root.mainloop()

# Function that runs when the button is pressed
def start_program():
    status_label.config(text="Program Started")
    print("Program Started")


