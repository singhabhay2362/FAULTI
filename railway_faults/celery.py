import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "railway_faults.settings")

app = Celery("railway_faults")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
