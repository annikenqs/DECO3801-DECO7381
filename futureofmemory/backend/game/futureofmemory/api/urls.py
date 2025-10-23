from django.urls import path

from .views import (
    CurrentScenarioView, NextScenarioView, SessionView, ScenarioView,
    JoinSessionView, PlayerCountView, GameStateView,
    FactionVoteView, FactionResultView, VotingLogicView, PlayerVoteCheck,
)

urlpatterns = [
    
    # Session creation
    path("session/", SessionView.as_view(), name="session_create"),

    # Joining a session
    path("session/join/", JoinSessionView.as_view(), name="session_join"),

    # Voting for a faction
    path("session/<str:pin>/faction/vote/", FactionVoteView.as_view(), name="faction_vote"),

    # Retrieving faction results
    path("session/<str:pin>/faction/result/", FactionResultView.as_view(), name="faction_result"),

    # Retrieving the current scenario of a session
    path("session/<str:pin>/scenario/", ScenarioView.as_view(), name="session_scenario"),

    # Retrieving the number of players in a session
    path("session/<str:pin>/players/count/", PlayerCountView.as_view(), name="player_count"),

    # Retrieving the current game state of a session
    path("session/<str:pin>/state/", GameStateView.as_view(), name="game_state"),

    # Voting logic within a session
    path("session/<str:pin>/vote/", VotingLogicView.as_view(), name="session_vote"),

    # Checking a player's vote status
    path("session/<str:pin>/votes/status/", PlayerVoteCheck.as_view(), name="vote_check"),

    # Progressing to the next scenario in a session
    path("session/<str:pin>/next/", NextScenarioView.as_view(), name="session_next"),

    # Retrieving the next scenario in a session
    path("session/<str:pin>/scenario/next/", NextScenarioView.as_view(), name="session_scenario_next"),

    # Retrieving the current scenario in a session
    path("session/<str:pin>/scenario/current/", CurrentScenarioView.as_view(), name="session_scenario_current"),

]
