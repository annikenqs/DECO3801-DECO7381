import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import random

from game.futureofmemory.services.query_service import run_rag
from game.futureofmemory.services.firebase_service import (
    create_session, get_session_by_pin, add_scenario, update_scenarios, 
    update_year, update_faction, join_session, get_player_count, update_game_state, allocate_pin,
    increment_choice_vote, pick_winner_from_choices
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


class FactionView(APIView):
    def post(self, request, pin):
        """
        Set the faction for an existing session.
        """
        try:
            data = request.data
            faction = data.get("faction")

            if faction not in ["rightists", "resourceists", "responsibilists"]:
                return Response(
                    {"error": "Invalid faction"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

            update_faction(pin, faction)

            return Response({"faction": faction}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class ScenarioView(APIView):
    def post(self, request, pin):
        """
        Generate the first scenario and save it in Firebase.
        """
        try:
            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            # Call RAG to generate a scenario
            result = run_rag(
                question="Generate a scenario",
                year=session["year"],
                faction=session["faction"] 
            )
            
            scenario_data = result.get("scenario", {})
            scenario_text = scenario_data.get("scenario_text", "No scenario generated")
            choices = scenario_data.get("choices", [])

            # Store scenario in Firebase
            scenario = {
                "id": len(session.get("scenarios", [])) + 1,
                "text": scenario_text,
                "choices": choices,
                "chosen": None
            }
            add_scenario(pin, scenario)

            return Response(scenario, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChoiceView(APIView):
    def patch(self, request, pin):
        """
        Mark a choice as chosen, then generate the next scenario.
        """
        try:
            data = request.data
            choice_id = data.get("choiceId")
            scenario_id = data.get("scenarioId")

            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            # Update last scenario's chosen choice
            scenarios = session.get("scenarios", [])
            for s in scenarios:
                if s["id"] == scenario_id:
                    s["chosen"] = choice_id
            update_scenarios(pin, scenarios)

            # calculate new year
            new_year = session["year"] + 1
            
            chosen_choice_text = None
            for c in scenarios[-1]["choices"]:
                if c["id"] == choice_id:
                    chosen_choice_text = c["text"]

            # Generate new scenario
            result = run_rag(
                question="Generate next scenario",
                year=new_year,
                scenario=scenarios[-1]["text"],
                chosen_choice=chosen_choice_text,
                faction=session["faction"]
            )

            scenario_data = result.get("scenario", {})
            scenario_text = scenario_data.get("scenario_text", "No scenario generated")
            choices = scenario_data.get("choices", [])

            new_scenario = {
                "id": len(scenarios) + 1,
                "text": scenario_text,
                "choices": choices,
                "chosen": None
            }
            add_scenario(pin, new_scenario)
            
            update_year(pin, new_year)

            return Response(new_scenario, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
            choices = vote_result["choices"]

            # 2) Check totals
            number_of_players = int(session.get("numberofplayers", 0))
            total_votes = sum(tally.values())

            if number_of_players == 0 or total_votes < number_of_players:
                # Just return the updated tally we already have
                return Response({
                    "pin": pin,
                    "scenarioId": scenario_id,
                    "finalized": False,
                    "total_votes": total_votes,
                    "number_of_players": number_of_players,
                    "tally": tally,
                }, status=status.HTTP_200_OK)

            # 3) Everyone voted -> pick winner from choices we already have
            winner = max(
                choices,
                key=lambda ch: (int(ch.get("votes", 0)), -int(ch.get("id", 0)))
            )

            # 4) Persist chosen (need current scenarios list)
            refreshed  = get_session_by_pin(pin)
            scenarios  = refreshed.get("scenarios", [])
            current    = next((s for s in scenarios if s.get("id") == scenario_id), None)
            if not current:
                return Response({"error": "Scenario not found"}, status=status.HTTP_404_NOT_FOUND)

            current["chosen"] = winner["id"]
            for i, s in enumerate(scenarios):
                if s.get("id") == scenario_id:
                    scenarios[i] = current
                    break
            
            update_scenarios(pin, scenarios)
            
            # --- AUTO-ADVANCE: generate the next scenario as soon as voting finalises ---
            new_year = refreshed["year"] + 1

            # Text of the winning choice from the current, finalised scenario
            chosen_choice_text = next(
                (c.get("text") for c in current.get("choices", []) if int(c.get("id")) == int(winner["id"])),
                None
            )

            # Generate the next scenario (same flow as ChoiceView)
            result = run_rag(
                question="Generate next scenario",
                year=new_year,
                scenario=current.get("text"),
                chosen_choice=chosen_choice_text,
                faction=refreshed.get("faction"),
            )

            scenario_data = result.get("scenario", {})
            scenario_text = scenario_data.get("scenario_text", "No scenario generated")
            choices = scenario_data.get("choices", [])

            new_scenario = {
                "id": len(scenarios) + 1,
                "text": scenario_text,
                "choices": choices,
                "chosen": None,
            }
            add_scenario(pin, new_scenario)
            update_year(pin, new_year)


            return Response({
                "pin": pin,
                "scenarioId": scenario_id,
                "finalized": True,
                "winnerId": winner["id"],
                "winnerText": winner.get("text"),
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
            finalize = request.query_params.get("finalize", "false").lower() == "true"

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

            # Not everyone voted (or unknown player count) -> just report status
            if number_of_players == 0 or total_votes < number_of_players:
                return Response({
                    "pin": pin,
                    "scenarioId": scenario_id,
                    "finalized": False,
                    "total_votes": total_votes,
                    "number_of_players": number_of_players,
                    "tally": tally
                }, status=status.HTTP_200_OK)

            # Everyone has voted: compute winner (highest votes; tie -> lowest id)
            winner = pick_winner_from_choices(current["choices"])  # uses your helper in firebase_service.py

            if not finalize:
                # Just report who would win; do NOT mutate
                return Response({
                    "pin": pin,
                    "scenarioId": scenario_id,
                    "finalized": True,
                    "winnerId": winner["id"],
                    "winnerText": winner.get("text"),
                    "tally": tally
                }, status=status.HTTP_200_OK)

            # finalize==true -> persist chosen
            current["chosen"] = winner["id"]
            for i, s in enumerate(scenarios):
                if s.get("id") == scenario_id:
                    scenarios[i] = current
                    break
            
            update_scenarios(pin, scenarios)

            return Response({
                "pin": pin,
                "scenarioId": scenario_id,
                "persisted": True,
                "winnerId": winner["id"],
                "winnerText": winner.get("text"),
                "tally": tally
            }, status=status.HTTP_200_OK)

        except (TypeError, ValueError):
            return Response({"error": "scenarioId must be provided as an integer"}, status=status.HTTP_400_BAD_REQUEST)
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
