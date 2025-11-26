from .train_faults import notify_new_labels_for_training, get_detection_model
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

# perceptual hashing
from PIL import Image
import imagehash

# -----------------------------
# Perceptual hash function
# -----------------------------
def compute_phash(filepath):
    try:
        return imagehash.phash(Image.open(filepath))
    except:
        return None




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




# -----------------------------
# CONFIRM FAULT (YES / NO)
# -----------------------------
@api_view(["POST"])
def confirm_fault(request, pk):

    fault = get_object_or_404(FaultRecord, pk=pk)
    action = request.data.get("action")

    dataset_images = os.path.join(settings.BASE_DIR, "dataset", "train", "images")
    dataset_labels = os.path.join(settings.BASE_DIR, "dataset", "train", "labels")
    os.makedirs(dataset_images, exist_ok=True)
    os.makedirs(dataset_labels, exist_ok=True)

    # target image
    target_path = os.path.join(settings.MEDIA_ROOT, str(fault.image))
    if not os.path.exists(target_path):
        fault.delete()
        return Response({"error": "Image missing"}, status=404)

    # compute perceptual hash
    target_phash = compute_phash(target_path)
    if target_phash is None:
        return Response({"error": "Hash error"}, status=500)

    # threshold for similarity (0-64)
    SIMILARITY_THRESHOLD = 8

    duplicate_records = []

    # scan all records for visual duplicates
    for rec in FaultRecord.objects.all():
        img_path = os.path.join(settings.MEDIA_ROOT, str(rec.image))

        if os.path.exists(img_path):
            ph = compute_phash(img_path)
            if ph is not None:
                diff = target_phash - ph  # Hamming distance
                if diff <= SIMILARITY_THRESHOLD:
                    duplicate_records.append(rec)

    if not duplicate_records:
        return Response({"error": "No visually similar images found"}, status=404)

    copied_ids = []
    copied_count = 0

    # copy matching images
    for rec in duplicate_records:
        src = os.path.join(settings.MEDIA_ROOT, str(rec.image))
        dst = os.path.join(dataset_images, os.path.basename(src))

        shutil.copy(src, dst)
        copied_ids.append(rec.id)
        copied_count += 1

        if action == "no":
            txt = os.path.splitext(os.path.basename(src))[0] + ".txt"
            open(os.path.join(dataset_labels, txt), "w").close()

    # delete all duplicates from DB
    FaultRecord.objects.filter(id__in=copied_ids).delete()

    # YES → annotation
    if action == "yes":
        classes_txt = os.path.join(dataset_labels, "classes.txt")

        # Run labelImg and wait for user to finish labeling
        process = subprocess.Popen(["labelImg", dataset_images, classes_txt], shell=True)
        process.wait()  # ⚠️ wait until annotation window is closed

        # Now update YAML after labeling is done
        update_yaml_after_labeling()
        notify_new_labels_for_training()

        return Response({
            "message": f"{copied_count} visually similar images sent for annotation.",
            "count": copied_count,
            "copied_ids": copied_ids
        })

    # NO → auto training
    if action == "no":
        notify_new_labels_for_training()

        return Response({
            "message": f"{copied_count} visually similar images auto-labeled as background.",
            "count": copied_count,
            "copied_ids": copied_ids
        })

    return Response({"error": "Invalid action"}, status=400)