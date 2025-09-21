from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from game.futureofmemory.services.query_service import run_rag


class ScenarioView(APIView):
    def post(self, request):
        try:
            data = request.data
            result = run_rag(
                question=data.get("question", "Make a scenario"),
                role="scenario",
                year=data.get("year", 2075)
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChoicesView(APIView):
    def post(self, request):
        try:
            data = request.data
            result = run_rag(
                question=data.get("question", "What are the possible choices?"),
                role="choices",
                year=data.get("year", 2075),
                scenario=data.get("scenario")
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OutcomeView(APIView):
    def post(self, request):
        try:
            data = request.data
            result = run_rag(
                question=data.get("question", "What happens next?"),
                role="outcome",
                year=data.get("year", 2075),
                scenario=data.get("scenario"),
                choices=data.get("choices"),
                choice_id=data.get("choice_id")
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




