import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from game.futureofmemory.services.query_service import run_rag
from game.futureofmemory.services.firebase_service import (
    create_session, get_session_by_pin, add_scenario, update_scenarios, 
    update_year, join_session, get_player_count, update_game_state, allocate_pin,
    vote_for_faction, finalize_faction_vote, get_faction_votes
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
    Allows a player to join an existing session using PIN and nickname.
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
    def post(self, request, pin):
        try:
            print(f"[ScenarioView] Generating scenario for PIN: {pin}")
            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            print(f"[ScenarioView] Session found. Year: {session['year']}, Faction: {session['faction']}")
            
            # Call RAG to generate a scenario
            print("[ScenarioView] Calling RAG...")
            result = run_rag(
                question="Generate a scenario",
                year=session["year"],
                faction=session["faction"] 
            )
            print(f"[ScenarioView] RAG completed")
            
            scenario_data = result.get("scenario", {})
            scenario_text = scenario_data.get("scenario_text", "No scenario generated")
            raw_choices = scenario_data.get("choices", [])
            
            # Convert choices format: {"id": 1, "text": "..."} -> {"id": "A", "text": "...", "label": "A: ..."}
            letter_map = {1: "A", 2: "B", 3: "C"}
            choices = []
            for choice in raw_choices[:3]:
                choice_id = choice.get("id", 1)
                choice_text = choice.get("text", f"Option {choice_id}")
                letter = letter_map.get(choice_id, "A")
                choices.append({
                    "id": letter,
                    "text": choice_text,
                    "label": f"{letter}: {choice_text}"
                })

            # Store scenario in Firebase
            scenario = {
                "id": len(session.get("scenarios", [])) + 1,
                "text": scenario_text,
                "choices": choices,
                "chosen": None,
                "year": session["year"]
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
            
            # Calculate new year
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
            raw_choices = scenario_data.get("choices", [])
            
            # Convert choices format
            letter_map = {1: "A", 2: "B", 3: "C"}
            choices = []
            for choice in raw_choices[:3]:
                choice_id = choice.get("id", 1)
                choice_text = choice.get("text", f"Option {choice_id}")
                letter = letter_map.get(choice_id, "A")
                choices.append({
                    "id": letter,
                    "text": choice_text,
                    "label": f"{letter}: {choice_text}"
                })

            new_scenario = {
                "id": len(scenarios) + 1,
                "text": scenario_text,
                "choices": choices,
                "chosen": None,
                "year": new_year
            }
            add_scenario(pin, new_scenario)
            
            update_year(pin, new_year)

            return Response(new_scenario, status=status.HTTP_200_OK)

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
