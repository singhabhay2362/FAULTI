from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from faults.models import FaultRecord, TaskStatus
import subprocess
import os

# 🔔 Notify Fault Task
@shared_task
def notify_fault(fault_id, feedback_required=False):
    """
    Send notification when new fault is detected.
    Also create TaskStatus entry.
    If feedback_required=True, frontend JS will show popup.
    """
    try:
        fault = FaultRecord.objects.get(id=fault_id)

        # ✅ Always create TaskStatus entry
        TaskStatus.objects.create(
            fault=fault,
            task_id=f"task-{fault.id}",
            name=fault.fault_name or f"Unnamed Fault #{fault.id}",
            status=fault.status,
        )

        # ✅ Extra metadata: mark feedback flag (can be exposed in API)
        if feedback_required:
            fault.status = "needs_feedback"
            fault.save()

        # ✅ Example Email Notification (optional)
        send_mail(
            subject="⚠ New Railway Fault Detected",
            message=f"A new fault has been detected!\n\nFault ID: {fault.id}\nStatus: {fault.status}\nFeedback Required: {feedback_required}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=["admin@example.com"],  # update email list
            fail_silently=True,
        )

        print(
            f"[NOTIFY] Fault {fault.id} notified. "
            f"Feedback Required: {feedback_required}"
        )

    except FaultRecord.DoesNotExist:
        print(f"[ERROR] Fault with ID {fault_id} not found")


# -------------------------------------------------
# NEW TASKS FOR BUTTONS
# -------------------------------------------------

BASE_DIR = settings.BASE_DIR  # Django project root

@shared_task
def run_capture_video():
    """
    Run capture_video.py in a separate process
    """
    script_path = os.path.join(BASE_DIR, "faults", "capture_video.py")
    if os.path.exists(script_path):
        print("[TASK] Running capture_video.py ...")
        subprocess.Popen(["python", script_path])
        return "Capture video started"
    else:
        print("[ERROR] capture_video.py not found")
        return "Error: capture_video.py not found"


@shared_task
def run_detect_faults():
    """
    Run detect_faults.py in a separate process
    """
    script_path = os.path.join(BASE_DIR, "faults", "detect_faults.py")
    if os.path.exists(script_path):
        print("[TASK] Running detect_faults.py ...")
        subprocess.Popen(["python", script_path])
        return "Fault detection started"
    else:
        print("[ERROR] detect_faults.py not found")
        return "Error: detect_faults.py not found"


@shared_task
def run_train_faults():
    """
    Run train_faults.py in a separate process
    """
    script_path = os.path.join(BASE_DIR, "faults", "train_faults.py")
    if os.path.exists(script_path):
        print("[TASK] Running train_faults.py ...")
        subprocess.Popen(["python", script_path])
        return "Training started"
    else:
        print("[ERROR] train_faults.py not found")
        return "Error: train_faults.py not found"
