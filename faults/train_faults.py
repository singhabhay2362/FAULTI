import os
import threading
from django.conf import settings
from ultralytics import YOLO

# ----------------------------------------
# CONFIG
# ----------------------------------------
DATA_YAML = os.path.join(settings.BASE_DIR, "dataset", "data.yaml")
BEST_PT = os.path.join(
    settings.BASE_DIR,
    "faults", "runs", "detect", "yolov8n-custom4", "weights", "best.pt"
)

AUTO_TRAIN_THRESHOLD = 1  # Train ONLY when total labels >= 1


class YoloTrainingManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.is_training = False
        self.model = self._load_model()

    # ----------------------------------------
    # Load latest model once
    # ----------------------------------------
    def _load_model(self):
        print(f"[AutoTrain] Loading model: {BEST_PT}")
        return YOLO(BEST_PT)

    # ----------------------------------------
    # Always get latest model for detection
    # ----------------------------------------
    def get_model(self):
        with self.lock:
            return self.model

    # ----------------------------------------
    # Count REAL label files and trigger training
    # ----------------------------------------
    def check_label_threshold(self):
        labels_dir = os.path.join(settings.BASE_DIR, "dataset", "train", "labels")
        os.makedirs(labels_dir, exist_ok=True)

        label_files = [f for f in os.listdir(labels_dir) if f.endswith(".txt")]
        total_labels = len(label_files)

        print(f"[AutoTrain] Label Count Now: {total_labels}")

        if total_labels >= AUTO_TRAIN_THRESHOLD and not self.is_training:
            print("🚀 Label threshold reached — starting training!")
            self.is_training = True
            threading.Thread(target=self._run_train, daemon=True).start()

    # ----------------------------------------
    # Silent background YOLO training
    # ----------------------------------------
    def _run_train(self):
        try:
            print("🔧 Auto-Training started silently…")

            model = YOLO(BEST_PT)

            model.train(
                data=DATA_YAML,
                project=os.path.join(settings.BASE_DIR, "faults", "runs", "detect"),
                name="yolov8n-custom4",
                exist_ok=True,
                epochs=30,
                imgsz=640,
                batch=8,
                device=0 if os.name != "nt" else "cpu"  # GPU if Linux
            )

            print("🎯 Training complete — Reloading updated weights!")
            with self.lock:
                self.model = YOLO(BEST_PT)

        except Exception as e:
            print(f"❌ TRAINING ERROR: {e}")

        finally:
            self.is_training = False
            print("⏳ Training done — waiting for more labels…")


# ---------------------------------------------------
# 🔥 Global Instance — Used in views & detection
# ---------------------------------------------------
training_manager = YoloTrainingManager()


def get_detection_model():
    return training_manager.get_model()


def notify_new_labels_for_training():
    """Call this whenever new label (.txt) files added or removed"""
    training_manager.check_label_threshold()
