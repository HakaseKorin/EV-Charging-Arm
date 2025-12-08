from ultralytics import YOLO
import os

home_dir = os.environ["HOME"]

# Load trained model
model = YOLO(r"ev_socket_model.pt")

# Run inference with boxes automatically drawn & saved
results = model("test02.jpg", name=f"{home_dir}/EV-Charging-Arm")
