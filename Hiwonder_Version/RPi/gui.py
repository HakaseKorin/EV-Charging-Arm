import tkinter as tk
from time import sleep
from PIL import Image, ImageTk

class ControllerGui:
    def __init__(self, main_queue):
        # Creates main window
        self.__root = tk.Tk()
        self.__main_queue = main_queue
        #self.__command_queue = command_queue
        #self.__status_queue = status_queue
        self.__root.title("Robot Controllor GUI")
        self.__root.geometry("300x200")
        self.__img =  Image.open("no_display.png")
        self.__img.resize((50,50))
        self.__tkimage = ImageTk.PhotoImage(self.__img)

        # Title Label
        self.__label = tk.Label(
            self.__root,
            text="Robot Controller",
            font=("Arial", 14)
        )
        self.__label.pack(pady=20)

        #self.__image = tk.Label(
        #    self.__root,
        #    image = self.__tkimage
        #)
        #self.__image.image = self.__tkimage
        #self.__image.pack()

        # Start Button
        self.__button = tk.Button(
            self.__root,
            text="Start",
            font=("Arial", 12),
            width=15,
            height=2,
        )
        self.__button.pack(pady=10)
        self.__button.config(state="disabled")

        # Status label
        self.__status = tk.Label(
            self.__root,
            text="STANDBY",
            font=("Arial", 10)
        )
        self.__status.pack(pady=10)

        self.update_gui()
    
    def resize(self, event):
        return
        new_width = int(event.width * 0.5)
        new_height = int(event.height * 0.5)

        img_copy = self.__img.copy()
        img_copy.thumbnail((new_width,new_height))

        self.__tkimage = ImageTk.PhotoImage(img_copy)
        self.__image.config(image=self.__tkimage)
        self.__image.image = self.__tkimage

    def update_image(self, img_dir):
        return
        self.__img = Image.open(img_dir)
        self.__img.resize((200,200))
        self.__tkimage = ImageTk.PhotoImage(self.__img)

        self.__image.config(
            image = self.__tkimage
        )
        self.__image.pack()
    
    def start_program(self):
        #self.__command_queue.put("CAPTURE")
        self.__main_queue.put(("command","CAPTURE"))
        #self.__status_queue.put(". . .")
        self.__main_queue.put(("status",". . ."))

    def retry(self):
        #self.__command_queue.put("RETRY")
        self.__main_queue.put(("command","RETRY"))
        #self.__status_queue.put(". . .")
        self.__main_queue.put(("status",". . ."))

    def quit(self):
        #self.__command_queue.put("QUIT")
        self.__main_queue.put(("command","QUIT"))

    def disconnect(self):
        #self.__command_queue.put("DISCONNECT")
        self.__main_queue.put(("command","DISCONNECT"))
        #self.__status_queue.put(". . .")
        self.__main_queue.put(("status",". . ."))

    def finish(self):
        #self.__command_queue.put("FINISH")
        self.__main_queue.put(("command","FINISH"))

    def update_gui(self):
        while not self.__main_queue.empty():
        #while True:
            msg,data = self.__main_queue.get()
            if msg == "status":
                self.__status.config(text=data)
            elif msg == "command":
                print(data)
                
                # initialization complete step
                if data == "SYSTEM_READY":
                    # enable start button set command to capture.
                    self.__button.config(
                        state="active",
                        text="continue",
                        # capture command
                        command=self.start_program)

                if data == "NOT_FOUND" or data == "NOT_ALIGNED":
                    self.__button.config(
                        text="Retry",
                        state="active",
                        command=self.retry
                    )

                if data == "DOCKING_COMPLETE":
                    self.__button.config(
                        # disconnect command
                        text="Disconnect",
                        state="active",
                        command=self.disconnect
                    )
                if data == ". . .":
                    self.__button.config(
                        state="disabled"
                    )
                if data == "DISCONNECT_COMPLETE":
                    self.__button.config(
                        state="active",
                        text="Restart",
                        command=self.finish
                    )
                if data == "SHOW_IMAGE":
                    self.update_image("updated.jpg")

        self.__root.after(100,self.update_gui)
            
    def run(self):
        self.__root.mainloop()