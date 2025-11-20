import cv2
import os
from datetime import datetime
import threading

# Folder to save videos
save_dir = "video_feed"
os.makedirs(save_dir, exist_ok=True)

# Open webcam
cap = cv2.VideoCapture(0)
fourcc = cv2.VideoWriter_fourcc(*"XVID")

# Generate filename
filename = os.path.join(save_dir, datetime.now().strftime("%Y%m%d_%H%M%S") + ".avi")
out = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))

print(f"[INFO] Recording started. File: {filename}")
print("[INFO] Press ENTER to stop recording anytime...")

# Flag to stop recording
stop_recording = False

# Function to wait for user input
def wait_for_stop():
    global stop_recording
    input()  # waits until user presses Enter
    stop_recording = True

# Start the input thread
thread = threading.Thread(target=wait_for_stop)
thread.daemon = True
thread.start()

# Main recording loop
while True:
    ret, frame = cap.read()
    if not ret:
        break
    out.write(frame)
    if stop_recording:
        break

cap.release()
out.release()
cv2.destroyAllWindows()
print(f"[INFO] Recording stopped. Video saved at: {filename}")
