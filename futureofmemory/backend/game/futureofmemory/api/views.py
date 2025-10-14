import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import random

from game.futureofmemory.services.query_service import run_rag
from game.futureofmemory.services.firebase_service import (
    create_session, get_session_by_pin, add_scenario, update_scenarios, 
    update_year, join_session, get_player_count, update_game_state, allocate_pin,
    vote_for_faction, finalize_faction_vote, get_faction_votes,
    increment_choice_vote, pick_winner_from_choices, add_first_scenario_if_absent, add_next_scenario_if_absent 
)
        
class SessionView(APIView):
    def post(self, request):
        """
        Create a new game session in Firebase.
        """
        try:
            data = request.data
            faction = data.get("faction", "Unknown")
            year = data.get("year", 2075)

            # pin options
            pin = data.get("pin") or allocate_pin()

            session = create_session(faction, year, "lobby", pin, numberofplayers=0)

            return Response(session, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class JoinSessionView(APIView):
    """
    POST /api/join/
    Allows a player to join an existing session using PIN
    """
    def post(self, request):
        try:
            data = request.data
            pin = data.get("pin")

            if not pin:
                return Response(
                    {"error": "PIN is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Join the session
            session = join_session(pin)
            
            # Debug: Check what type session is
            if not isinstance(session, dict):
                return Response(
                    {"error": f"Unexpected return type from join_session: {type(session)}, value: {session}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response({
                "success": True,
                "pin": pin,
                "numberofplayers": session.get("numberofplayers", [])
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Exception type: {type(e)}, message: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FactionVoteView(APIView):
    """
    POST /api/session/{pin}/faction/vote/
    Allows a player to vote for a faction.
    """
    def post(self, request, pin):
        try:
            data = request.data
            faction = data.get("faction")

            if not faction:
                return Response(
                    {"error": "Faction is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if faction not in ["rightists", "resourceists", "responsibilists"]:
                return Response(
                    {"error": "Invalid faction"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

            # Record the vote
            result = vote_for_faction(pin, faction)

            return Response({
                "success": True,
                "faction": faction,
                "factionVotes": result["factionVotes"],
                "allVoted": result["allVoted"]
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FactionResultView(APIView):
    """
    GET /api/session/{pin}/faction/result/
    Gets the current voting status or finalizes the vote if all players have voted.
    """
    def get(self, request, pin):
        try:
            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

            # Get current vote status
            vote_status = get_faction_votes(pin)
            
            print(f"[FactionResultView] PIN: {pin}")
            print(f"[FactionResultView] Vote status: {vote_status}")
            print(f"[FactionResultView] All voted: {vote_status['allVoted']}")
            print(f"[FactionResultView] Current faction: {vote_status['faction']}")

            # If all players have voted and faction hasn't been finalized, finalize it
            if vote_status["allVoted"] and not vote_status["faction"]:
                print(f"[FactionResultView] Finalizing faction vote...")
                result = finalize_faction_vote(pin)
                print(f"[FactionResultView] Finalized faction: {result['faction']}")
                return Response({
                    "finalized": True,
                    "faction": result["faction"],
                    "factionVotes": result["factionVotes"],
                    "wasTie": result["wasTie"],
                    "totalPlayers": vote_status["totalPlayers"],
                    "votedPlayers": vote_status["votedPlayers"]
                }, status=status.HTTP_200_OK)
            
            # Return current status
            print(f"[FactionResultView] Returning current status (not finalizing)")
            return Response({
                "finalized": vote_status["allVoted"],
                "faction": vote_status["faction"],
                "factionVotes": vote_status["factionVotes"],
                "totalPlayers": vote_status["totalPlayers"],
                "votedPlayers": vote_status["votedPlayers"],
                "allVoted": vote_status["allVoted"]
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ScenarioView(APIView):
    """
    POST /api/session/{pin}/scenario/
    Returns the current scenario if one exists, or generates a new scenario candidate
    for the given session. Ensures only one scenario is created.
    """
    def post(self, request, pin):
        try:
            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)
            if not session.get("faction"):
                return Response({"error": "Faction not finalized yet."}, status=status.HTTP_409_CONFLICT)

            scenarios = session.get("scenarios", [])
            if scenarios:
                # Prefer the first scenario that is NOT finalized; otherwise return the last one.
                open_one = next((s for s in scenarios if s.get("chosen") is None), None)
                return Response(open_one or scenarios[-1], status=status.HTTP_200_OK)

            # Otherwise generate a candidate (may be thrown away if another request wins the race)
            try:
                rag_result = run_rag(
                    question="Generate a scenario",
                    year=session["year"],
                    faction=session["faction"]
                )
            except Exception as e:
                print(f"[ScenarioView] RAG ERROR: {type(e).__name__}: {e}")
                rag_result = None

            scenario_data = {}
            if isinstance(rag_result, dict):
                scenario_data = rag_result.get("scenario") or rag_result

            candidate = {
                "text": (
                    scenario_data.get("scenario_text")
                    or scenario_data.get("text")
                    or "No scenario generated (fallback)"
                ),
                "choices": scenario_data.get("choices") or [],
                "year": session["year"],
                "citations": scenario_data.get("citations", []),
            }

            # Atomic create-if-absent (or return existing)
            persisted = add_first_scenario_if_absent(pin, candidate)

            return Response(persisted, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"[ScenarioView] UNEXPECTED ERROR: {type(e).__name__}: {e}")
            return Response({"error": "Scenario generation failed", "details": str(e)},
                            status=status.HTTP_502_BAD_GATEWAY)

class NextScenarioView(APIView):
    """
    POST /api/session/{pin}/scenario/next/
    Generates and returns the next scenario in the session, based on the previous
    scenario’s chosen outcome. Ensures only one new scenario is appended.
    """
    def post(self, request, pin):
        try:
            data = request.data or {}
            prev_id = int(data.get("previousScenarioId", 0))

            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            scenarios = session.get("scenarios", [])
            if not scenarios:
                return Response({"error": "No previous scenario exists. Call /scenario/ first."},
                                status=status.HTTP_409_CONFLICT)

            # Use prev_id if provided, otherwise last
            prev = next((s for s in scenarios if int(s.get("id", 0)) == int(prev_id)), scenarios[-1])
            if prev.get("chosen") is None:
                return Response({"error": "Previous scenario not finalized (no winner)."},
                                status=status.HTTP_409_CONFLICT)

            expected_new_id = max(int(s.get("id", 0)) for s in scenarios) + 1

            chosen_text = next((c.get("text") for c in prev.get("choices", [])
                                if int(c.get("id")) == int(prev["chosen"])), None)
            new_year = int(session.get("year", 2075)) + 1

            # Generate candidate OUTSIDE the transaction (may be called twice; write is protected)
            try:
                rag_result = run_rag(
                    question="Generate next scenario",
                    year=new_year,
                    scenario=prev.get("text"),
                    chosen_choice=chosen_text,
                    faction=session.get("faction"),
                )
            except Exception as e:
                print(f"[NextScenarioView] RAG ERROR: {type(e).__name__}: {e}")
                rag_result = None

            scenario_data = {}
            if isinstance(rag_result, dict):
                scenario_data = rag_result.get("scenario") or rag_result

            candidate = {
                "text": (
                    scenario_data.get("scenario_text")
                    or scenario_data.get("text")
                    or "No scenario generated (fallback)"
                ),
                "choices": scenario_data.get("choices") or [],
                "year": session["year"],
                "citations": scenario_data.get("citations", []),
            }

            # Atomic: append or return existing
            persisted = add_next_scenario_if_absent(pin, expected_new_id, candidate, new_year)
            return Response(persisted, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"[NextScenarioView] UNEXPECTED ERROR: {type(e).__name__}: {e}")
            return Response({"error": "Next scenario generation failed", "details": str(e)},
                            status=status.HTTP_502_BAD_GATEWAY)

class CurrentScenarioView(APIView):
    """
    GET /api/session/{pin}/scenario/current/
    Fetches the current scenario for the session. Returns 404 if no scenario exists yet.
    """
    def get(self, request, pin):
        session = get_session_by_pin(pin)
        if not session:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

        scenarios = session.get("scenarios", [])
        if not scenarios:
            # 404 when nothing exists yet
            return Response({"detail": "No scenario yet"}, status=status.HTTP_404_NOT_FOUND)

        return Response(scenarios[0], status=status.HTTP_200_OK)
        
class VotingLogicView(APIView):
    def patch(self, request, pin):
        try:
            data = request.data
            scenario_id = data.get("scenarioId")
            choice_id   = data.get("choiceId")

            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            # 1) Increment this vote (transaction-safe)
            vote_result = increment_choice_vote(pin, scenario_id, choice_id)
            tally   = {k: int(v) for k, v in vote_result["votes"].items()}

            # 2) Check totals
            number_of_players = int(session.get("numberofplayers", 0))
            total_votes = sum(tally.values())

            return Response({
                    "pin": pin,
                    "scenarioId": scenario_id,
                    "finalized": False,
                    "total_votes": total_votes,
                    "number_of_players": number_of_players,
                    "tally": tally,
                }, status=status.HTTP_200_OK)
        
        except (TypeError, ValueError):
            return Response({"error": "scenarioId and choiceId must be integers"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




# endpoint 1: takes care of voting (based on choice id, it updates number in firebase)

# endpoint 2: checks how many players have voted so far, and check it against the number of players
# returns the choiceID of the picked choice

class PlayerVoteCheck(APIView):
    def get(self, request, pin):
        """
        Check how many players have voted vs total players.
        Query: ?scenarioId=<int>&finalize=true|false
        - If finalize=true and everyone voted: persist chosen (winner) and return winnerId.
        - Otherwise just return the current tally and progress.
        """
        try:
            scenario_id = int(request.query_params.get("scenarioId"))
        except (TypeError, ValueError):
            return Response({"error": "scenarioId must be provided as an integer"},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            scenarios = session.get("scenarios", [])
            current = next((s for s in scenarios if s.get("id") == scenario_id), None)
            if not current:
                return Response({"error": "Scenario not found"}, status=status.HTTP_404_NOT_FOUND)

            number_of_players = int(session.get("numberofplayers", 0))
            tally = {str(ch["id"]): int(ch.get("votes", 0)) for ch in current.get("choices", [])}
            total_votes = sum(tally.values())

            # If already finalised, return the winner
            if current.get("chosen") is not None:
                chosen_id = int(current["chosen"])
                chosen_text = next((c.get("text") for c in current.get("choices", []) 
                    if int(c.get("id")) == chosen_id), None)
                return Response({
                    "pin": pin,
                    "scenarioId": scenario_id,
                    "persisted": True,
                    "winnerId": chosen_id,
                    "winnerText": chosen_text,
                    "tally": tally,
                    "total_votes": total_votes,
                    "number_of_players": number_of_players,
                }, status=status.HTTP_200_OK)

            # if everyone hasn't voted yet: return what we've got so far
            if number_of_players == 0 or total_votes < number_of_players:
                return Response({
                    "pin": pin,
                    "scenarioId": scenario_id,
                    "persisted": False,
                    "ready_to_finalize": (number_of_players > 0 and total_votes == number_of_players),
                    "tally": tally,
                    "total_votes": total_votes,
                    "number_of_players": number_of_players,
                }, status=status.HTTP_200_OK)
            
            # just in case there's too many votes
            if total_votes > number_of_players:
                return Response({
                    "pin": pin,
                    "scenarioId": scenario_id,
                    "persisted": False,
                    "oversubscribed": True,
                    "tally": tally,
                    "total_votes": total_votes,
                    "number_of_players": number_of_players,
                }, status=status.HTTP_200_OK)
            else:
                # Everyone has voted -> pick winner and persist (single-shot)
                winner = pick_winner_from_choices(current["choices"])  # deterministic tie-breaker recommended
                current["chosen"] = winner["id"]

                for i, s in enumerate(scenarios):
                    if s.get("id") == scenario_id:
                        scenarios[i] = current
                        break

                update_scenarios(pin, scenarios)  # persist

                return Response({
                    "pin": pin,
                    "scenarioId": scenario_id,
                    "persisted": True,
                    "winnerId": winner["id"],
                    "winnerText": winner.get("text"),
                    "tally": tally,
                    "total_votes": total_votes,
                    "number_of_players": number_of_players,
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class PlayerCountView(APIView):
    def get(self, request, pin):
        """
        Gets the number of players in a session.
        """
        try:
            count = get_player_count(pin)
            return Response({"pin": pin, "player_count": count}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GameStateView(APIView):
    def get(self, request, pin):
        """
        Returns the current game status (e.g. lobby, in-progress, finished).
        """
        try:
            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"status": session.get("status", "lobby")}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def patch(self, request, pin):
        """
        Updates the game status, typically to start the game.
        """
        try:
            data = request.data
            new_state = data.get("status")

            if not new_state:
                return Response({"error": "State is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Optional: Add logic to ensure only the host can change the state
            # For now, anyone can change it.

            result = update_game_state(pin, new_state)
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
