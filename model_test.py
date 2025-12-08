from ultralytics import YOLO

# Load trained model
model = YOLO(r"D:\CodeSpace\Python\ImageClassifier\runs\detect\ev_socket_detector3\weights\best.pt")

# Run inference with boxes automatically drawn & saved
results = model("test02.jpg", save=True, show=True, name="output")
