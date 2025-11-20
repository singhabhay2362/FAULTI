from django.contrib import admin

# Register your models here.

from .models import FaultRecord, TaskStatus

@admin.register(FaultRecord)
class FaultRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "timestamp", "status", "assigned_to")
    list_filter = ("status", "timestamp")
    search_fields = ("id", "assigned_to__username")

@admin.register(TaskStatus)
class TaskStatusAdmin(admin.ModelAdmin):
    list_display = ("task_id", "name", "status", "timestamp")
    list_filter = ("status", "timestamp")
    search_fields = ("task_id", "name")
