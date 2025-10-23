"""URL configurations for the Future of Memory game API."""
from django.urls import path

"""Import views for handling game API endpoints."""
from .views import (
    CurrentScenarioView, NextScenarioView, SessionView, ScenarioView,
    JoinSessionView, PlayerCountView, GameStateView,
    FactionVoteView, FactionResultView, VotingLogicView, PlayerVoteCheck,
)

urlpatterns = [
    
    # Endpoint for session creation
    path("session/", SessionView.as_view(), name="session_create"),

    # Endpoint for joining a session
    path("session/join/", JoinSessionView.as_view(), name="session_join"),

    # Endpoint for voting for a faction
    path("session/<str:pin>/faction/vote/", FactionVoteView.as_view(), name="faction_vote"),

    # Endpoint for retrieving faction results
    path("session/<str:pin>/faction/result/", FactionResultView.as_view(), name="faction_result"),

    # Endpoint for retrieving the current scenario of a session
    path("session/<str:pin>/scenario/", ScenarioView.as_view(), name="session_scenario"),

    # Endpoint for retrieving the number of players in a session
    path("session/<str:pin>/players/count/", PlayerCountView.as_view(), name="player_count"),

    # Endpoint for retrieving the current game state of a session
    path("session/<str:pin>/state/", GameStateView.as_view(), name="game_state"),

    # Endpoint for voting logic within a session
    path("session/<str:pin>/vote/", VotingLogicView.as_view(), name="session_vote"),

    # Endpoint for checking a player's vote status
    path("session/<str:pin>/votes/status/", PlayerVoteCheck.as_view(), name="vote_check"),

    # Endpoint for progressing to the next scenario in a session
    path("session/<str:pin>/next/", NextScenarioView.as_view(), name="session_next"),

    # Endpoint for retrieving the next scenario in a session
    path("session/<str:pin>/scenario/next/", NextScenarioView.as_view(), name="session_scenario_next"),

    # Endpoint for retrieving the current scenario in a session
    path("session/<str:pin>/scenario/current/", CurrentScenarioView.as_view(), name="session_scenario_current"),

]
