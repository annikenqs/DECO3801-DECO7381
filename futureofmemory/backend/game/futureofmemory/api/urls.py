
from django.urls import path
from .views import (
    SessionView, ScenarioView, ChoiceView, FactionView,
    JoinSessionView, PlayerCountView, GameStateView,
    FactionVoteView, FactionResultView
)

urlpatterns = [
    path("session/", SessionView.as_view(), name="session_create"),
    path("session/join/", JoinSessionView.as_view(), name="session_join"),
    path("session/<str:pin>/", FactionView.as_view(), name="session_details"), # Can be used for GET details
    path("session/<str:pin>/faction/", FactionView.as_view(), name="session_faction"),
    path("session/<str:pin>/faction/vote/", FactionVoteView.as_view(), name="faction_vote"),
    path("session/<str:pin>/faction/result/", FactionResultView.as_view(), name="faction_result"),
    path("session/<str:pin>/scenario/", ScenarioView.as_view(), name="session_scenario"),
    path("session/<str:pin>/choice/", ChoiceView.as_view(), name="session_choice"),
    path("session/<str:pin>/players/count/", PlayerCountView.as_view(), name="player_count"),
    path("session/<str:pin>/state/", GameStateView.as_view(), name="game_state"),
]
