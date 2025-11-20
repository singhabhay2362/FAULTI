import os
import sys
import django
import cv2
from datetime import datetime
from ultralytics import YOLO
from concurrent.futures import ThreadPoolExecutor
import threading

# ------------------------------
# Add project root to path
# ------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# ------------------------------
# Setup Django environment
# ------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "railway_faults.settings")
django.setup()

from django.conf import settings
from faults.models import FaultRecord
from faults.tasks import notify_fault

# ------------------------------
# Load YOLO model
# ------------------------------
MODEL_PATH = os.path.join(settings.BASE_DIR, "faults", "runs", "detect", "yolov8n-custom4", "weights", "best.pt")
model = YOLO(MODEL_PATH)

# ------------------------------
# Video directory (fallback)
# ------------------------------
video_dir = os.path.join(settings.BASE_DIR, "faults", "video_feed")

def get_latest_video(folder):
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith((".mp4", ".avi", ".mov"))]
    if not files:
        print("[ERROR] No video file found in video_feed/")
        return None
    return max(files, key=os.path.getmtime)

# ------------------------------
# Save faults & notify
# ------------------------------
output_dir = str(settings.MEDIA_ROOT).rstrip()
os.makedirs(output_dir, exist_ok=True)
executor = ThreadPoolExecutor(max_workers=2)

def draw_bounding_boxes(frame, results):
    """Draw bounding boxes and labels on detected frame."""
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            label = f"{model.names.get(cls, 'Unknown')} ({conf:.2f})"
            color = (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return frame

def save_fault_and_notify(frame, label, conf, timestamp):
    try:
        filename = f"{label}_{timestamp}.jpg"
        local_path = os.path.join(output_dir, filename)
        cv2.imwrite(local_path, frame)

        record = FaultRecord.objects.create(
            image=filename,
            status="pending",
            confirmed=False,
            sent_to_service=False
        )

        try:
            notify_fault.delay(record.id, feedback_required=True)
        except Exception as e:
            print(f"[WARNING] Could not send async notification: {e}")

        print(f"[INFO] Fault saved: {filename} | Confidence: {conf:.2f}")

    except Exception as e:
        print(f"[ERROR] Failed to save fault: {e}")

# ------------------------------
# Main fault detection
# ------------------------------
def run_fault_detection(video_file=None):
    if not video_file or not os.path.exists(video_file):
        video_file = get_latest_video(video_dir)
        if not video_file:
            print("[WARNING] No video available. Falling back to webcam.")
            video_file = 0

    cap = cv2.VideoCapture(video_file)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[INFO] End of video OR Camera not returning frames")
                break

            results = model(frame, conf=0.5, iou=0.5)
            annotated_frame = draw_bounding_boxes(frame.copy(), results)

            for r in results:
                for box in r.boxes:
                    cls = int(box.cls[0])
                    label = model.names.get(cls, "Unknown")
                    conf = float(box.conf[0])
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    executor.submit(save_fault_and_notify, annotated_frame.copy(), label, conf, timestamp)

    except KeyboardInterrupt:
        print("[INFO] Interrupted by user")

    finally:
        cap.release()
        executor.shutdown(wait=True)
        print("[INFO] Detection complete, resources released.")

# ------------------------------
# Run script directly
# ------------------------------
if __name__ == "__main__":
    video_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_fault_detection(video_arg)
