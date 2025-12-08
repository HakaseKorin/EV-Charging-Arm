from ultralytics import YOLO

# Load trained model
model = YOLO(r"ev_socket_model.pt")

# Run inference with boxes automatically drawn & saved
results = model("test02.jpg", save=True, show=True, name="output")
