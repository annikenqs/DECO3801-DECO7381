from django.urls import path
from .views import (
    CurrentScenarioView, NextScenarioView, SessionView, ScenarioView,
    JoinSessionView, PlayerCountView, GameStateView,
    FactionVoteView, FactionResultView, VotingLogicView, PlayerVoteCheck,
)

urlpatterns = [
    path("session/", SessionView.as_view(), name="session_create"),
    path("session/join/", JoinSessionView.as_view(), name="session_join"),
    path("session/<str:pin>/faction/vote/", FactionVoteView.as_view(), name="faction_vote"),
    path("session/<str:pin>/faction/result/", FactionResultView.as_view(), name="faction_result"),
    path("session/<str:pin>/scenario/", ScenarioView.as_view(), name="session_scenario"),
    path("session/<str:pin>/players/count/", PlayerCountView.as_view(), name="player_count"),
    path("session/<str:pin>/state/", GameStateView.as_view(), name="game_state"),
    path("session/<str:pin>/vote/", VotingLogicView.as_view(), name="session_vote"),
    path("session/<str:pin>/votes/status/", PlayerVoteCheck.as_view(), name="vote_check"),
    path("session/<str:pin>/next/", NextScenarioView.as_view(), name="session_next"),
    path("session/<str:pin>/scenario/current/", CurrentScenarioView.as_view(), name="session_scenario_current"),

]
