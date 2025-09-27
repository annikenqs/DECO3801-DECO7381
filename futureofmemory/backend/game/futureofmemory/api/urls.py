from django.urls import path
from .views import (
    SessionView,
    FactionView,
    ScenarioView,
    ChoiceView,
    # LobbyStatusView,
    # LobbyJoinView,
)

urlpatterns = [
    path("session/", SessionView.as_view(), name="create-session"),
    path("session/<str:pin>/faction/", FactionView.as_view(), name="faction"),
    path("session/<str:pin>/scenario/", ScenarioView.as_view(), name="scenario"),
    path("session/<str:pin>/choice/", ChoiceView.as_view(), name="choice"),
    # path("session/<str:pin>/status/", LobbyStatusView.as_view(), name="lobby-status"),
    # path("session/<str:pin>/join/", LobbyJoinView.as_view(), name="lobby-join"),
]