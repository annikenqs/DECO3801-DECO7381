from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ..services.query_service import run_rag
from ..services.firebase_service import (
    create_session, get_session, add_scenario, update_scenarios,
    update_year, update_faction, get_lobby_status, join_lobby, generate_pin,
)


class SessionView(APIView):
    def post(self, request):
        """
        Create a new game session in Firebase using a 6-digit PIN.
        """
        try:
            data = request.data
            pin = data.get("pin") or generate_pin()   
            faction = data.get("faction", "Unknown")
            year = data.get("year", 2075)

            session = create_session(pin, faction, year, status="lobby", numberOfPlayers=0)
            return Response(session, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

            session = get_session(pin)
            if not session:
                return Response({"error": "Game not found"}, status=status.HTTP_404_NOT_FOUND)

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
            session = get_session(pin)
            if not session:
                return Response({"error": "Game not found"}, status=status.HTTP_404_NOT_FOUND)

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
                "id": len(session["scenarios"]) + 1,
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

            session = get_session(pin)
            if not session:
                return Response({"error": "Game not found"}, status=status.HTTP_404_NOT_FOUND)

            # Update last scenario's chosen choice
            scenarios = session["scenarios"]
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


class LobbyStatusView(APIView):
    def get(self, request, pin):
        result = get_lobby_status(pin)
        if not result:
            return Response({"ok": False, "msg": "Invalid PIN"}, status=404)

class LobbyJoinView(APIView):
    def post(self, request, pin):
        result = join_lobby(pin)
        if "error" in result:
            return Response({"ok": False, "msg": result["error"]}, status=400)
        return Response({"ok": True, **result})