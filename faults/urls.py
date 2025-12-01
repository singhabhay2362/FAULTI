from django.urls import path
from . import views
from .views import annotate_view, save_labels, add_new_class



app_name = "faults"

urlpatterns = [
    # ------------------------------
    # 📄 PAGE ROUTES
    # ------------------------------
    path("", views.dashboard, name="dashboard"),
    path("home/", views.home, name="home"),
    path("controls/", views.controls, name="controls"),
    path("task_status/", views.task_status, name="task_status"),

    path("annotate/", views.annotate_view, name="annotate"),
    path("save_labels/", views.save_labels, name="save_labels"),
    path("add-class/", add_new_class, name="add_class"),


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
