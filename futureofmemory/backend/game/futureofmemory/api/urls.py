from django.urls import path
from .views import SessionView, ScenarioView, ChoiceView

urlpatterns = [
    path("session/", SessionView.as_view(), name="session"),
    path("session/<str:session_id>/scenario/", ScenarioView.as_view(), name="scenario"),
    path("session/<str:session_id>/choice/", ChoiceView.as_view(), name="choice"),
]
