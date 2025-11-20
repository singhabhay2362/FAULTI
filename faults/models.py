from django.db import models
from django.contrib.auth.models import User

class FaultRecord(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("assigned", "Assigned"),
        ("resolved", "Resolved"),
    ]

    # Save all images directly inside MEDIA_ROOT (fault_images/)
    image = models.ImageField(upload_to="", blank=True, null=True)

    fault_name = models.CharField(max_length=255, blank=True, null=True)  # Fault type/name
    class_index = models.IntegerField(blank=True, null=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # For YES/NO confirmation
    confirmed = models.BooleanField(default=False)   # True: confirmed fault, False: NO fault
    duplicate_images_removed = models.BooleanField(default=False)  # True if similar images removed
    sent_to_service = models.BooleanField(default=False)  # Alert sent via WhatsApp/Email

    def __str__(self):
        return f"Fault #{self.id} - {self.status}"


class TaskStatus(models.Model):
    fault = models.ForeignKey(FaultRecord, on_delete=models.CASCADE, null=True, blank=True)

    task_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=FaultRecord.STATUS_CHOICES, default="pending")
    result = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']  # Latest first

    def __str__(self):
        return f"Task {self.task_id} for Fault #{self.fault.id if self.fault else 'N/A'} - {self.status}"
