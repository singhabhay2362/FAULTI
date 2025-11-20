from django.test import TestCase

# Create your tests here.
from django.contrib.auth.models import User
from .models import FaultRecord, TaskStatus

class FaultRecordModelTest(TestCase):
    def test_create_fault(self):
        fault = FaultRecord.objects.create(status="pending")
        self.assertEqual(fault.status, "pending")
        self.assertIsNotNone(fault.timestamp)

class TaskStatusModelTest(TestCase):
    def test_create_task_status(self):
        task = TaskStatus.objects.create(
            task_id="12345",
            name="send_alert",
            status="SUCCESS",
            result="Test successful"
        )
        self.assertEqual(task.status, "SUCCESS")

class DashboardViewTest(TestCase):
    def test_dashboard_view(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fault Detection")
