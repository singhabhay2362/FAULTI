import os
from ultralytics import YOLO

# STEP 1: Set working directory to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)
print("Current Working Directory ->", os.getcwd())

# STEP 2: Relative paths
weights_path = os.path.join("faults", "runs", "detect", "yolov8n-custom4", "weights", "best.pt")
data_yaml_path = os.path.join("dataset", "data.yaml")

print("Weights:", os.path.abspath(weights_path))
print("YAML:", os.path.abspath(data_yaml_path))

# STEP 3: Load model + Train
model = YOLO(weights_path)

model.train(
    data=data_yaml_path,
    epochs=10,
    imgsz=640,
    batch=4,
    workers=0,
    device="cpu",
    name="yolov8n-custom",
)
