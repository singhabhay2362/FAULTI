from rest_framework import serializers
from .models import FaultRecord, TaskStatus

class FaultRecordSerializer(serializers.ModelSerializer):
    assigned_to = serializers.StringRelatedField()

    class Meta:
        model = FaultRecord
        fields = [
            "id",
            "image",
            "timestamp",
            "status",
            "assigned_to",
            "confirmed",       # Added for self-training
            "sent_to_service",  # Added for notifications
        ]


class TaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStatus
        fields = ["task_id", "name", "status", "result", "timestamp"]
