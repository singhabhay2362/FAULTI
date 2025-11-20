from .detect_faults import run_fault_detection
import threading
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.http import require_POST
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import FaultRecord, TaskStatus
from .serializers import FaultRecordSerializer, TaskStatusSerializer
from django.conf import settings
import os
import yaml
import subprocess
import shutil
import hashlib
import sys
import time

# ------------------------------
# Helper: Compute hash (for duplicate detection)
# ------------------------------
def compute_file_hash(filepath):
    """Return SHA256 hash of a file."""
    hash_func = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


# ------------------------------
# Helper: Append classes + update data.yaml
# ------------------------------
def update_yaml_after_labeling():
    base_dir = settings.BASE_DIR  # do NOT add "dataset" here
    dataset_dir = os.path.join(base_dir, "dataset")

    yaml_path = os.path.join(dataset_dir, "data.yaml")
    classes_path = os.path.join(dataset_dir, "train", "labels", "classes.txt")

    time.sleep(1)

    if not os.path.exists(classes_path):
        print("⚠️ classes.txt not found!")
        return

    with open(classes_path, "r", encoding="utf-8") as f:
        classes = [line.strip() for line in f if line.strip()]

    yaml_data = {
        "train": "train/images",
        "val": "val/images",
        "nc": len(classes),
        "names": classes
    }

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(yaml_data, f, sort_keys=False)

    print("✅ data.yaml updated (relative paths)")


# ------------------------------
# HOME & CONTROL VIEWS
# ------------------------------
def home(request):
    return render(request, "home.html")


def controls(request):
    return render(request, "controls.html")


# ------------------------------
# TASK TRIGGERS
# ------------------------------
@require_POST
def start_capture(request):
    try:
        script_path = os.path.join(settings.BASE_DIR, "faults", "capture_video.py")
        subprocess.Popen(["python", script_path])
        messages.success(request, "Video capture started ✅")
    except Exception as e:
        messages.error(request, f"Failed to start capture: {e}")
    return redirect(reverse("faults:controls"))


@require_POST
def start_detect(request):
    video_file = request.FILES.get("video_file")
    video_path = None

    if video_file:
        upload_dir = os.path.join(settings.BASE_DIR, "faults", "video_feed")
        os.makedirs(upload_dir, exist_ok=True)
        video_path = os.path.join(upload_dir, video_file.name)
        with open(video_path, "wb") as f:
            for chunk in video_file.chunks():
                f.write(chunk)

    try:
        threading.Thread(target=run_fault_detection, args=(video_path,), daemon=True).start()
        messages.success(request, "Fault detection started ✅")
    except Exception as e:
        messages.error(request, f"Failed to start detection: {e}")

    return redirect(reverse("faults:controls"))


@require_POST
def start_train(request):
    try:
        script_path = os.path.join(settings.BASE_DIR, "faults", "train_faults.py")
        subprocess.Popen([sys.executable, script_path])
        messages.success(request, "Training started ✅")
    except Exception as e:
        messages.error(request, f"Failed to start training: {e}")
    return redirect(reverse("faults:controls"))


# ------------------------------
# DASHBOARD & STATUS
# ------------------------------
def dashboard(request):
    all_faults = FaultRecord.objects.filter(confirmed=False).order_by("-timestamp")
    all_tasks = TaskStatus.objects.select_related("fault").all().order_by("-timestamp")

    # Load known fault class names from classes.txt
    classes_file = os.path.join(settings.BASE_DIR, "dataset", "train", "labels", "classes.txt")
    known_classes = []
    if os.path.exists(classes_file):
        with open(classes_file, "r") as f:
            known_classes = [line.strip() for line in f if line.strip()]

    valid_faults = []
    for fault in all_faults:
        if fault.image:
            file_path = os.path.join(settings.MEDIA_ROOT, str(fault.image))
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                fault_name = os.path.splitext(filename)[0]

                # Try to find any known class name inside filename
                detected_class = None
                for cls in known_classes:
                    if cls.lower() in fault_name.lower():
                        detected_class = cls
                        break

                # If no match found, fallback to cleaned filename
                if not detected_class:
                    # Remove numbers and extra underscores
                    fault_name_cleaned = "".join([ch for ch in fault_name if not ch.isdigit()])
                    parts = fault_name_cleaned.split("_")
                    detected_class = parts[-1] if len(parts) > 0 else "Unknown"

                fault.display_name = detected_class
                valid_faults.append(fault)

    # Count stats
    total_count = len(valid_faults)
    pending_count = len([f for f in valid_faults if f.status == "pending"])
    assigned_count = len([f for f in valid_faults if f.status == "assigned"])
    resolved_count = len([f for f in valid_faults if f.status == "resolved"])

    # Paginate
    fault_paginator = Paginator(valid_faults, 20)
    faults = fault_paginator.get_page(request.GET.get("fault_page"))

    task_paginator = Paginator(all_tasks, 10)
    tasks = task_paginator.get_page(request.GET.get("task_page"))

    return render(request, "dashboard.html", {
        "faults": faults,
        "tasks": tasks,
        "total_count": total_count,
        "pending_count": pending_count,
        "assigned_count": assigned_count,
        "resolved_count": resolved_count,
    })



def task_status(request):
    all_tasks = TaskStatus.objects.select_related("fault").all().order_by("-timestamp")
    valid_tasks = []

    for task in all_tasks:
        if task.fault and task.fault.image:
            file_path = os.path.join(settings.MEDIA_ROOT, str(task.fault.image))
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                fault_name = os.path.splitext(filename)[0]
                if "_" in fault_name:
                    parts = fault_name.split("_")
                    fault_name = "_".join(parts[:2]) if len(parts) >= 2 else parts[0]
                task.display_name = fault_name
                valid_tasks.append(task)
        else:
            task.display_name = "Unknown"
            valid_tasks.append(task)

    paginator = Paginator(valid_tasks, 10)
    tasks = paginator.get_page(request.GET.get("task_page"))
    return render(request, "task_status.html", {"tasks": tasks})

# ------------------------------
# API VIEWS
# ------------------------------
class FaultListView(generics.ListAPIView):
    queryset = FaultRecord.objects.all().order_by("-timestamp")
    serializer_class = FaultRecordSerializer


class TaskStatusListView(generics.ListAPIView):
    queryset = TaskStatus.objects.select_related("fault").all().order_by("-timestamp")
    serializer_class = TaskStatusSerializer


# ------------------------------
# ASSIGN FAULT (assigns a fault to engineer)
# ------------------------------
@api_view(["POST"])
def assign_fault(request, pk):
    fault = get_object_or_404(FaultRecord, pk=pk)
    assigned_to = request.data.get("assigned_to", "Engineer")

    fault.status = "assigned"
    fault.assigned_to = assigned_to if hasattr(fault, "assigned_to") else None
    fault.save()

    TaskStatus.objects.create(
        fault=fault,
        status="assigned",
        message=f"Fault assigned to {assigned_to}"
    )

    return Response({
        "message": f"✅ Fault {fault.id} assigned to {assigned_to}"
    })


# ------------------------------
# FEEDBACK FAULT (user feedback for a fault)
# ------------------------------
@api_view(["POST"])
def feedback_fault(request, pk):
    fault = get_object_or_404(FaultRecord, pk=pk)
    feedback = request.data.get("feedback")

    if not feedback:
        return Response({"error": "Feedback message is required."}, status=400)

    # Add task status entry
    TaskStatus.objects.create(
        fault=fault,
        status="feedback",
        message=feedback
    )

    # Mark fault as resolved
    fault.status = "resolved"
    fault.save()

    return Response({
        "message": f"✅ Feedback submitted successfully for fault ID {pk}",
        "feedback": feedback
    })

# ------------------------------
# ✅ CONFIRM FAULT (YES / NO full logic)
# ------------------------------
@api_view(["POST"])
def confirm_fault(request, pk):
    import time

    fault = get_object_or_404(FaultRecord, pk=pk)
    action = request.data.get("action")

    dataset_images = os.path.join(settings.BASE_DIR, "dataset", "train", "images")
    dataset_labels = os.path.join(settings.BASE_DIR, "dataset", "train", "labels")
    os.makedirs(dataset_images, exist_ok=True)
    os.makedirs(dataset_labels, exist_ok=True)

    # 🧠 Step 1: Compute hash of target image
    target_path = os.path.join(settings.MEDIA_ROOT, str(fault.image))
    if not os.path.exists(target_path):
        return Response({"error": "Target image not found"}, status=404)
    target_hash = compute_file_hash(target_path)

    # 🧠 Step 2: Collect all duplicates (across ALL pages)
    duplicate_records = []
    all_records = FaultRecord.objects.all()
    print(f"🔍 Scanning {len(all_records)} total records for duplicates...")

    for record in all_records:
        if record.image:
            path = os.path.join(settings.MEDIA_ROOT, str(record.image))
            if os.path.exists(path):
                try:
                    record_hash = compute_file_hash(path)
                    if record_hash == target_hash:
                        duplicate_records.append(record)
                except Exception as e:
                    print(f"⚠️ Error hashing record {record.id}: {e}")

    print(f"✅ Found {len(duplicate_records)} duplicate images (including clicked one).")

    # CASE: YES → Copy duplicates → Delete → Launch LabelImg
    if action == "yes":
        copied_ids = []
        for rec in duplicate_records:
            src = os.path.join(settings.MEDIA_ROOT, str(rec.image))
            if os.path.exists(src):
                dest = os.path.join(dataset_images, os.path.basename(src))
                shutil.copy(src, dest)
                copied_ids.append(rec.id)
                print(f"📸 Copied (YES): {os.path.basename(src)}")

        # Delete from dashboard immediately
        FaultRecord.objects.filter(id__in=copied_ids).delete()
        print(f"🗑️ Deleted {len(copied_ids)} duplicates from dashboard (YES case).")

        # Slight delay to sync DB
        time.sleep(0.5)

        # Launch LabelImg and update YAML after you close it
        try:
            classes_txt = os.path.join(settings.BASE_DIR, "dataset", "train", "labels", "classes.txt")
            subprocess.run(["labelImg", dataset_images, classes_txt], shell=True)  # waits until LabelImg closes
            update_yaml_after_labeling()  # updates YAML afterward
        except Exception as e:
            print(f"⚠️ LabelImg error: {e}")

        return Response({
            "message": f"✅ {len(copied_ids)} duplicate images copied, deleted, and ready for annotation.",
            "deleted_ids": copied_ids
        })

    #  CASE: NO → Copy duplicates → Create blank labels → Delete
    elif action == "no":
        deleted_ids = []
        for rec in duplicate_records:
            src = os.path.join(settings.MEDIA_ROOT, str(rec.image))
            if os.path.exists(src):
                # Copy image to train/images
                dest_img = os.path.join(dataset_images, os.path.basename(src))
                shutil.copy(src, dest_img)

                # Create blank label file in train/labels
                txt_file = os.path.splitext(os.path.basename(src))[0] + ".txt"
                txt_path = os.path.join(dataset_labels, txt_file)
                open(txt_path, "w").close()

                deleted_ids.append(rec.id)
                print(f"🚫 Copied (NO): {os.path.basename(src)} and blank label created.")

        # ✅ Delete from DB immediately
        FaultRecord.objects.filter(id__in=deleted_ids).delete()
        print(f"🗑️ Deleted {len(deleted_ids)} duplicates from dashboard (NO case).")

        time.sleep(0.5)

        return Response({
            "message": f"🚫 {len(deleted_ids)} duplicate images copied with blank labels and deleted from dashboard.",
            "deleted_ids": deleted_ids
        })

    return Response({"error": "Invalid action"}, status=400)


