import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import random

# Import requisite services and functions
from game.futureofmemory.services.query_service import run_rag
from game.futureofmemory.services.firebase_service import (
    create_session, get_session_by_pin, add_scenario, update_scenarios, 
    update_year, join_session, get_player_count, update_game_state, allocate_pin,
    vote_for_faction, finalize_faction_vote, get_faction_votes,
    increment_choice_vote, pick_winner_from_choices, add_first_scenario_if_absent, add_next_scenario_if_absent 
)

""" Creates a new game session in Firebase. """        
class SessionView(APIView):
    def post(self, request):

        # Try the following:
        try:
            # requisite data, faction, year, pin
            data = request.data
            faction = data.get("faction", "Unknown")
            year = data.get("year", 2075)

            # pin options
            pin = data.get("pin") or allocate_pin()

            # Create a session
            session = create_session(faction, year, "lobby", pin, numberofplayers=0)
             
            # Return the session and a 201 status
            return Response(session, status=status.HTTP_201_CREATED)

        # Handle exceptions if they show up
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

""" Allows a player to join an existing session using PIN. """
class JoinSessionView(APIView):

    def post(self, request):
        # Try the following:
        try:
            # get the requisite data and pin
            data = request.data
            pin = data.get("pin")

            # if the pin doesn't exist:
            if not pin:
                # return an appropriate response
                return Response(
                    {"error": "PIN is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # try joining a session using the pin
            session = join_session(pin)
            
            # Debug: Check what type session is
            if not isinstance(session, dict):
                return Response(
                    {"error": f"Unexpected return type from join_session: {type(session)}, value: {session}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # return a success response with pin and number of players
            return Response({
                "success": True,
                "pin": pin,
                "numberofplayers": session.get("numberofplayers", [])
            }, status=status.HTTP_200_OK)

        # if there's any errors or exceptions, return appropriate responses

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

""" Allows a player to vote for a faction in a session. """
class FactionVoteView(APIView):

    def post(self, request, pin):
        # Try to get the requisite data and faction
        try:
            data = request.data
            faction = data.get("faction")

            # if the faction isn't provided, return an error response
            if not faction:
                return Response(
                    {"error": "Faction is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # if the faction is invalid, return an error response
            if faction not in ["rightists", "resourceists", "responsibilists"]:
                return Response(
                    {"error": "Invalid faction"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # try to get the session by pin
            session = get_session_by_pin(pin)
            # if the session doesn't exist, return an error response
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

            # Record the player's vote
            result = vote_for_faction(pin, faction)

            # Return a success response with faction and voting status
            return Response({
                "success": True,
                "faction": faction,
                "factionVotes": result["factionVotes"],
                "allVoted": result["allVoted"]
            }, status=status.HTTP_200_OK)

        # Handle exceptions and errors and return appropriate error responses
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

""" Retrieves faction voting results and finalizes if all players have voted. """
class FactionResultView(APIView):

    def get(self, request, pin):

        # Try to get the session and voting status
        try:
            session = get_session_by_pin(pin)

            # if the session doesn't exist, return an error response
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

            # Get current vote status
            vote_status = get_faction_votes(pin)
            
            # printing requisite debug info
            print(f"[FactionResultView] PIN: {pin}")
            print(f"[FactionResultView] Vote status: {vote_status}")
            print(f"[FactionResultView] All voted: {vote_status['allVoted']}")
            print(f"[FactionResultView] Current faction: {vote_status['faction']}")

            # If all players have voted and faction hasn't been finalized, finalize it
            if vote_status["allVoted"] and not vote_status["faction"]:
                print(f"[FactionResultView] Finalizing faction vote...")
                result = finalize_faction_vote(pin)
                print(f"[FactionResultView] Finalized faction: {result['faction']}")

                # return finalised response
                return Response({
                    "finalized": True,
                    "faction": result["faction"],
                    "factionVotes": result["factionVotes"],
                    "wasTie": result["wasTie"],
                    "totalPlayers": vote_status["totalPlayers"],
                    "votedPlayers": vote_status["votedPlayers"]
                }, status=status.HTTP_200_OK)
            
            # else, return current voting status (that is not finalised)
            print(f"[FactionResultView] Returning current status (not finalizing)")
            return Response({
                "finalized": vote_status["allVoted"],
                "faction": vote_status["faction"],
                "factionVotes": vote_status["factionVotes"],
                "totalPlayers": vote_status["totalPlayers"],
                "votedPlayers": vote_status["votedPlayers"],
                "allVoted": vote_status["allVoted"]
            }, status=status.HTTP_200_OK)

        # Handle exceptions and return error responses
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

""" Handles scenario generation and retrieval for a session. """
class ScenarioView(APIView):

    def post(self, request, pin):

        # Try to generate or retrieve the current scenario
        try:
            session = get_session_by_pin(pin)
            # if the session doesn't exist, return an error response
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # if the game is not in progress, return an error response
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)
            
            # if the faction is not yet finalized, return an error response
            if not session.get("faction"):
                return Response({"error": "Faction not finalized yet."}, status=status.HTTP_409_CONFLICT)

            # Check for existing scenarios
            scenarios = session.get("scenarios", [])
            if scenarios:
                # Prefer the first scenario that is NOT finalized; otherwise return the last one.
                open_one = next((s for s in scenarios if s.get("chosen") is None), None)
                return Response(open_one or scenarios[-1], status=status.HTTP_200_OK)

            # Try generating a new scenario using RAG
            try:
                rag_result = run_rag(
                year=session["year"],
                faction=session["faction"]
            )
            except Exception as e:
                print(f"[ScenarioView] RAG ERROR: {type(e).__name__}: {e}")
                rag_result = None

            # Construct scenario data from RAG result
            scenario_data = {}
            if isinstance(rag_result, dict):
                scenario_data = rag_result.get("scenario") or rag_result

            # Build candidate scenario
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

        # Handle unexpected exceptions and return error responses
        except Exception as e:
            print(f"[ScenarioView] UNEXPECTED ERROR: {type(e).__name__}: {e}")
            return Response({"error": "Scenario generation failed", "details": str(e)},
                            status=status.HTTP_502_BAD_GATEWAY)


""" Handles progression to the next scenario in a session. """
class NextScenarioView(APIView):

    def post(self, request, pin):
        # Try to generate the next scenario
        try:
            # obtain requisite data
            data = request.data or {}

            # from the data, obtain the id of the previous scenario
            prev_id = int(data.get("previousScenarioId", 0))

            # try to get the session by pin
            session = get_session_by_pin(pin)

            # if the session doesn't exist, return an error response
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # if the game is not in progress, return an error response
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            # try to get the scenarios from the session
            scenarios = session.get("scenarios", [])

            # if there are no scenarios, return an error response
            if not scenarios:
                return Response({"error": "No previous scenario exists. Call /scenario/ first."},
                                status=status.HTTP_409_CONFLICT)

            # Attempts to find the previous scenario using its ID
            # if not found, defaults to the last scenario in the list
            prev = next((s for s in scenarios if int(s.get("id", 0)) == int(prev_id)), scenarios[-1])

            # if there is no chosen scenario in the previous one, return an error response
            if prev.get("chosen") is None:
                return Response({"error": "Previous scenario not finalized (no winner)."},
                                status=status.HTTP_409_CONFLICT)

            # determines what the new scenario ID should be (i.e. one greater than the current max)
            expected_new_id = max(int(s.get("id", 0)) for s in scenarios) + 1

            # extract the chosen text - searches through the previous scenario's choices and finds the 
            # text for the chosen ID
            chosen_text = next((c.get("text") for c in prev.get("choices", [])
                                if int(c.get("id")) == int(prev["chosen"])), None)
            # determine the new year for the next scenario
            new_year = int(session.get("year", 2075)) + 1

            # generates the next scenario using RAG
            try:
                rag_result = run_rag(
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
                "year": new_year,
                "citations": scenario_data.get("citations", []),
            }

            # Atomic: append or return existing
            persisted = add_next_scenario_if_absent(pin, expected_new_id, candidate, new_year)
            return Response(persisted, status=status.HTTP_200_OK)

        # Handle unexpected exceptions and return error responses
        except Exception as e:
            print(f"[NextScenarioView] UNEXPECTED ERROR: {type(e).__name__}: {e}")
            return Response({"error": "Next scenario generation failed", "details": str(e)},
                            status=status.HTTP_502_BAD_GATEWAY)

""" Retrieves the current scenario for a session. """
class CurrentScenarioView(APIView):

    def get(self, request, pin):
        # Try to get the current session using the pin
        session = get_session_by_pin(pin)

        # if the session doesn't exist, return an error response
        if not session:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

        # get the scenarios from the session
        scenarios = session.get("scenarios", [])

        # if there are no scenarios, return an error response
        if not scenarios:
            return Response({"detail": "No scenario yet"}, status=status.HTTP_404_NOT_FOUND)

        # return the first scenario that is not finalized; otherwise return the first one
        return Response(scenarios[0], status=status.HTTP_200_OK)

""" Handles voting logic within a session. """        
class VotingLogicView(APIView):
    def patch(self, request, pin):
        # get requisite data for vote processing
        try:
            # get the data, scenario ID and choice ID
            data = request.data
            scenario_id = data.get("scenarioId")
            choice_id   = data.get("choiceId")

            # attempt to get the session using its pin
            session = get_session_by_pin(pin)
            # if the session doesn't exist, return an error response
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            # if the game is not in progress, return an error response
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            # 1) increment this vote 
            vote_result = increment_choice_vote(pin, scenario_id, choice_id)

            # update the tally from the vote result
            tally = {k: int(v) for k, v in vote_result["votes"].items()}

            # 2) check the number of players and total votes
            number_of_players = int(session.get("numberofplayers", 0))
            total_votes = sum(tally.values())

            # return the voting status response
            return Response({
                    "pin": pin,
                    "scenarioId": scenario_id,
                    "finalized": False,
                    "total_votes": total_votes,
                    "number_of_players": number_of_players,
                    "tally": tally,
                }, status=status.HTTP_200_OK)
        
        # deal with exceptions and return error responses
        except (TypeError, ValueError):
            return Response({"error": "scenarioId and choiceId must be integers"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

""" Compares the number of players who have voted against the total number of players in a session. """
class PlayerVoteCheck(APIView):
    def get(self, request, pin):

        # get the scenario ID from query parameters
        try:
            scenario_id = int(request.query_params.get("scenarioId"))
        # if any errors occur, return an error response
        except (TypeError, ValueError):
            return Response({"error": "scenarioId must be provided as an integer"},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            # try obtaining the session using its pin
            session = get_session_by_pin(pin)

            # if the session doesn't exist, return an error response
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # if the game is not in progress, return an error response
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            # obtain the scenarios from the session
            scenarios = session.get("scenarios", [])

            # obtain the current scenario using its ID
            current = next((s for s in scenarios if s.get("id") == scenario_id), None)

            # if the current scenario doesn't exist, return an error response
            if not current:
                return Response({"error": "Scenario not found"}, status=status.HTTP_404_NOT_FOUND)

            # obtain the current tally, total votes and number of players
            number_of_players = int(session.get("numberofplayers", 0))
            tally = {str(ch["id"]): int(ch.get("votes", 0)) for ch in current.get("choices", [])}
            total_votes = sum(tally.values())

            # If already finalised:
            if current.get("chosen") is not None:
                # return the result's ID and text
                chosen_id = int(current["chosen"])
                chosen_text = next((c.get("text") for c in current.get("choices", []) 
                    if int(c.get("id")) == chosen_id), None)
                # return the finalised response
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
            
            # if there's too many votes (oversubscription):
            if total_votes > number_of_players:
                # return a "oversubscribed" boolean as part of the response to indicate as such 
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
                # otherwise: everyone has voted, so pick a winner
                winner = pick_winner_from_choices(current["choices"])  # deterministic tie-breaker recommended

                # get the winner ID and update the scenario
                current["chosen"] = winner["id"]

                for i, s in enumerate(scenarios):
                    if s.get("id") == scenario_id:
                        scenarios[i] = current
                        break

                update_scenarios(pin, scenarios)  
                
                # return the finalised response
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
            
        # Handle exceptions and return error responses
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
""" Gets the number of players in a session."""
class PlayerCountView(APIView):
    def get(self, request, pin):
        # Try to get the player count using the session pin
        try:
            count = get_player_count(pin)
            # return the pin and player count if successful
            return Response({"pin": pin, "player_count": count}, status=status.HTTP_200_OK)
        
        # Handle exceptions and return error responses
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

""" Returns the current game status (e.g. lobby, in-progress, finished)."""
class GameStateView(APIView):
    def get(self, request, pin):
        # Try to get the session using its pin
        try:
            session = get_session_by_pin(pin)

            # if the session doesn't exist, return an error response
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            # return the current game status
            return Response({"status": session.get("status", "lobby")}, status=status.HTTP_200_OK)
        
        # Handle exceptions and return error responses
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    # updates the game status    
    def patch(self, request, pin):

        # obtain the current state from the data
        try:
            data = request.data
            new_state = data.get("status")

            # if no state is provided, return an error response
            if not new_state:
                return Response({"error": "State is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            # update the game state
            result = update_game_state(pin, new_state)
            # return the updated state if successful
            return Response(result, status=status.HTTP_200_OK)
    
        # Handle exceptions and return error responses
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
