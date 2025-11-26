from django.urls import path
from . import views

app_name = "faults"

urlpatterns = [
    # ------------------------------
    # 📄 PAGE ROUTES
    # ------------------------------
    path("", views.dashboard, name="dashboard"),
    path("home/", views.home, name="home"),
    path("controls/", views.controls, name="controls"),
    path("task_status/", views.task_status, name="task_status"),

    # ------------------------------
    # ⚙️ TASK TRIGGER ROUTES
    # ------------------------------
    path("start_capture/", views.start_capture, name="start_capture"),
    path("start_detect/", views.start_detect, name="start_detect"),


    # ------------------------------
    # 🧠 API ENDPOINTS
    # ------------------------------
    # Fault-related APIs
    path("api/faults/", views.FaultListView.as_view(), name="fault_list"),
    path("api/faults/<int:pk>/confirm/", views.confirm_fault, name="confirm_fault"),


    # Task-related APIs
    path("api/tasks/", views.TaskStatusListView.as_view(), name="task_list"),
]
