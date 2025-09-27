import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from game.futureofmemory.services.query_service import run_rag
from game.futureofmemory.services.firebase_service import (
    create_session, get_session_by_pin, add_scenario, update_scenarios, 
    update_year, update_faction, join_session, get_player_count, update_game_state
)


class SessionView(APIView):
    def post(self, request):
        """
        Create a new game session in Firebase.
        The creator provides a nickname and becomes the host.
        """
        try:
            data = request.data
            nickname = data.get("nickname")
            if not nickname:
                return Response({"error": "Nickname is required."}, status=status.HTTP_400_BAD_REQUEST)

            faction = data.get("faction", "Unknown")
            year = data.get("year", 2075)

            session = create_session(faction=faction, year=year)
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
            nickname = data.get("nickname")

            if not pin:
                return Response(
                    {"error": "PIN is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not nickname:
                return Response(
                    {"error": "Nickname is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Join the session
            session = join_session(pin, nickname)
            
            # Debug: Check what type session is
            if not isinstance(session, dict):
                return Response(
                    {"error": f"Unexpected return type from join_session: {type(session)}, value: {session}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response({
                "success": True,
                "pin": pin,
                "nickname": nickname,
                "numberOfPlayers": session.get("numberOfPlayers", [])
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
            
            if session.get("state") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            # Call RAG to generate a scenario
            result = run_rag(
                question="Generate a scenario",
                role="scenario",
                year=session["year"]
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
            
            if session.get("state") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            # Update last scenario's chosen choice
            scenarios = session.get("scenarios", [])
            for s in scenarios:
                if s["id"] == scenario_id:
                    s["chosen"] = choice_id
            update_scenarios(pin, scenarios)
            
            # Calculate new year
            new_year = session["year"] + 1

            # Generate new scenario
            result = run_rag(
                question="Generate next scenario",
                role="scenario",
                year=new_year,
                scenario=scenarios[-1]["text"],
                choices=scenarios[-1]["choices"],
                choice_id=choice_id
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
        Updates the game state, typically to start the game.
        """
        try:
            data = request.data
            new_state = data.get("state")

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
