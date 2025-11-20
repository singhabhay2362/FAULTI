from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import FaultRecord, TaskStatus


@receiver(post_save, sender=FaultRecord)
def create_task_for_fault(sender, instance, created, **kwargs):
    """
    Auto-create a TaskStatus when a new FaultRecord is created.
    """
    if created:
        TaskStatus.objects.create(
            fault=instance,
            task_id=f"task-{instance.id}",   # Auto-generate task id
            name=instance.fault_name or f"Fault #{instance.id}",
            status=instance.status
        )
