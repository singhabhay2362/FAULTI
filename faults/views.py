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
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse
import os
import yaml
import subprocess
import shutil
import hashlib
import sys
import time
import json

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


# ---------------------- CUSTOM PATH -------------------------
# Yaha apna dataset folder access ho raha hai
DATASET_DIR = os.path.join(settings.BASE_DIR, "dataset", "train", "images")
LABELS_DIR = os.path.join(settings.BASE_DIR, "dataset", "train", "labels")

os.makedirs(LABELS_DIR, exist_ok=True)


def get_image_list():
    return sorted([f for f in os.listdir(DATASET_DIR) if f.lower().endswith((".jpg", ".png", ".jpeg"))])

# -----------------------------
# Add Class API (NEW)
# -----------------------------
@csrf_exempt
def add_new_class(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = json.loads(request.body.decode("utf-8"))
    new_class = data.get("class_name", "").strip()

    if not new_class:
        return JsonResponse({"error": "Empty class name"}, status=400)

    classes_file = os.path.join(LABELS_DIR, "classes.txt")

    # Load existing classes
    with open(classes_file, "r") as f:
        classes = [line.strip() for line in f.readlines()]

    if new_class in classes:
        return JsonResponse({"status": "exists", "classes": classes})

    # Append new class
    with open(classes_file, "a") as f:
        f.write(new_class + "\n")

    # Update data.yaml
    update_yaml_after_labeling()

    classes.append(new_class)

    return JsonResponse({"status": "added", "classes": classes})

# -----------------------------
# Annotate View (Updated)
# -----------------------------
def annotate_view(request):
    images_dir = os.path.join(settings.BASE_DIR, "dataset/train/images")
    labels_dir = os.path.join(settings.BASE_DIR, "dataset/train/labels")

    images = sorted(os.listdir(images_dir), key=lambda x: os.path.getmtime(os.path.join(images_dir, x)), reverse=True)

    total = len(images)
    idx = int(request.GET.get("idx", 0))

    if total == 0:
        return render(request, "annotate.html", {"no_images": True})

    image_name = images[idx]
    image_url = settings.DATASET_URL + f"train/images/{image_name}"

    # ---- Load existing YOLO labels ----
    label_file = os.path.splitext(image_name)[0] + ".txt"
    label_path = os.path.join(labels_dir, label_file)

    existing_boxes = []

    if os.path.exists(label_path):
        with open(label_path, "r") as f:
            for line in f.readlines():
                cls, xc, yc, w, h = map(float, line.split())
                existing_boxes.append({
                    "cls": int(cls),
                    "x_center": xc,
                    "y_center": yc,
                    "width": w,
                    "height": h
                })

    # ---- Load classes dynamically from file ----
    classes_path = os.path.join(settings.BASE_DIR, "dataset", "train", "labels", "classes.txt")

    labels_list = []
    if os.path.exists(classes_path):
        with open(classes_path, "r") as f:
            labels_list = [line.strip() for line in f.readlines()]

    context = {
        "image_name": image_name,
        "image_url": image_url,
        "idx": idx,
        "total": total,
        "labels": labels_list,
        "existing_boxes": json.dumps(existing_boxes),
        "no_images": False
    }

    return render(request, "annotate.html", context)


@csrf_exempt
def save_labels(request):
    """Save YOLO style annotations (.txt)"""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)

    data = json.loads(request.body.decode("utf-8"))
    image_name = data["image_name"]
    boxes = data["boxes"]

    label_path = os.path.join(LABELS_DIR, os.path.splitext(image_name)[0] + ".txt")

    with open(label_path, "w") as f:
        for b in boxes:
            f.write(f"{b['cls']} {b['x_center']} {b['y_center']} {b['width']} {b['height']}\n")

    notify_new_labels_for_training()

    return JsonResponse({"status": "saved"})


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
        #classes_txt = os.path.join(dataset_labels, "classes.txt")

        # Run labelImg and wait for user to finish labeling
        #process = subprocess.Popen(["labelImg", dataset_images, classes_txt], shell=True)
        #process.wait()  # ⚠️ wait until annotation window is closed

        # Now update YAML after labeling is done
        #update_yaml_after_labeling()

        #notify_new_labels_for_training()
        return Response({
            "message": f"{copied_count} visually similar images sent for annotation.",
            "count": copied_count,
            "copied_ids": copied_ids,
            "redirect": "/annotate/?idx=0"
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