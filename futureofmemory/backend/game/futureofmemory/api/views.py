import uuid
import json
import threading
from typing import Dict, Any

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from game.futureofmemory.services.query_service import run_rag
from game.futureofmemory.services.query_service import run_rag_query
from game.futureofmemory.services.llm_service import (
    generate_json,
    first_scenario_and_choices_prompt,
    next_scenario_and_choices_prompt,
    SYSTEM_RULES,
    _approx_tokens,
    _clip_context,
    _normalize_scenario,
)

from game.futureofmemory.services.firebase_service import (
    create_session, get_session_by_pin, add_scenario, update_scenarios, 
    update_year, join_session, get_player_count, update_game_state, allocate_pin,
    vote_for_faction, finalize_faction_vote, get_faction_votes,
    increment_choice_vote, pick_winner_from_choices, add_first_scenario_if_absent, add_next_scenario_if_absent 
)

class SessionView(APIView):
    """ Creates a new game session with optional faction, year, and PIN. """
    def post(self, request):

        try:
            data = request.data
            faction = data.get("faction", "Unknown")
            year = data.get("year", 2075)
            pin = data.get("pin") or allocate_pin()
            session = create_session(faction, year, "lobby", pin, numberofplayers=0)

            return Response(session, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class JoinSessionView(APIView):
    """ Allows a player to join an existing session using a PIN. """
    def post(self, request):
        
        try:
            data = request.data
            pin = data.get("pin")

            # Validate input
            if not pin:
                return Response(
                    {"error": "PIN is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Attempt to join session
            session = join_session(pin)
            if not isinstance(session, dict):
                return Response(
                    {"error": f"Unexpected return type from join_session: {type(session)}, value: {session}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Success
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
    """ Allows a player to vote for a faction in a session. """
    def post(self, request, pin):

        try:
            data = request.data
            faction = data.get("faction")

            # Validate input
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

            # Validate session
            session = get_session_by_pin(pin)
            if not session:
                return Response(
                    {"error": "Session not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # Record the player's vote
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
    """ Retrieves faction voting results and finalizes if all players have voted. """
    def get(self, request, pin):
        
        try:
            # Validate session
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
            
            # Else, return current voting status (that is not finalized)
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
    "Generate and persist the first scenario for a session."
    def post(self, request, pin):

        try:
            # Validate session
            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)
            if not session.get("faction"):
                return Response({"error": "Faction not finalized yet."}, status=status.HTTP_409_CONFLICT)

            # Return existing first scenario if present
            scenarios = session.get("scenarios", [])
            if scenarios:
                return Response(scenarios[0], status=status.HTTP_200_OK)

            # Build RAG context
            docs = run_rag_query(
                query=f"neurotechnology memory implants ethics {session['faction']} {session.get('year', 2075)}"
            ) or []
            context_text = "\n\n".join([getattr(d, "page_content", str(d))[:500] for d in docs])
            context_text = _clip_context(context_text, 1500)


            # Prompt for first scenario
            prompt = first_scenario_and_choices_prompt.format(
                system_rules=json.dumps(SYSTEM_RULES),
                context=context_text,
                year=int(session.get("year", 2075)),
                faction=session["faction"],
                citations=""
            )

            # Generate scenario
            raw = generate_json(prompt, max_new_tokens=180, temperature=0.7)

            # Normalize and persist scenario 
            new_id = 1
            year = int(session.get("year", 2075))
            scenario = _normalize_scenario(raw, year, new_id)
            persisted = add_first_scenario_if_absent(pin, scenario)
            print(f"[ScenarioView] pin={pin} PERSISTED first scenario id={persisted.get('id')}")
            return Response(persisted, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class NextScenarioView(APIView):
    """Generate and persist the next scenario in a session based on the previous outcome."""
    def post(self, request, pin):

        try:
            data = request.data or {}
            prev_id = int(data.get("previousScenarioId", 0))
            session = get_session_by_pin(pin)

            # Validate session state before generating next scenario
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            scenarios = session.get("scenarios", [])
            if not scenarios:
                return Response({"error": "No previous scenario exists. Call /scenario/ first."}, status=status.HTTP_409_CONFLICT)

            # Attempts to find the previous scenario
            prev = next((s for s in scenarios if int(s.get("id", 0)) == int(prev_id)), scenarios[-1])

            # Ensure previous scenario is finalized before generating the next
            if prev.get("chosen") is None:
                return Response({"error": "Previous scenario not finalized (no winner)."}, status=status.HTTP_409_CONFLICT)

            # Get text of the chosen choice to drive the next scenario
            chosen_text = next(
                (c.get("text") for c in prev.get("choices", []) if int(c.get("id")) == int(prev["chosen"])),
                None
            )

            # Compute next scenario's year and ID
            new_year = int(session.get("year", 2075)) + 1
            expected_new_id = (max(int(s.get("id", 0)) for s in scenarios) + 1) if scenarios else 1

            # Build RAG contex
            docs = run_rag_query(
                query=f"{prev.get('text','')} consequence {chosen_text} faction:{session.get('faction')} year:{new_year}"
            ) or []
            context_text = "\n\n".join([getattr(d, "page_content", str(d))[:500] for d in docs])
            context_text = _clip_context(context_text, 1500)


            # Prompt for next year
            prompt = next_scenario_and_choices_prompt.format(
                system_rules=json.dumps(SYSTEM_RULES),
                context=context_text,
                year=new_year,
                previous_scenario=prev.get("text", ""),
                chosen_choice=chosen_text or "",
                citations=""
            )
            
            print(f"[Prompt length] {len(prompt)} chars ≈ {_approx_tokens(prompt)} tokens")

            # Generate next scenario text and choices
            raw = generate_json(prompt, max_new_tokens=300, temperature=0.65)

            # Normalize and persist scenario
            scenario = _normalize_scenario(raw, new_year, expected_new_id)
            persisted = add_next_scenario_if_absent(pin, expected_new_id, scenario, new_year)
            print(f"[NextScenarioView] pin={pin} PERSISTED next scenario id={persisted.get('id')} year={persisted.get('year')}")
            return Response(persisted, status=200)

        except ValueError as ve:
            return Response({"error": str(ve)}, status=400)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": "Next scenario generation failed", "details": str(e)}, status=502)

class CurrentScenarioView(APIView):
    """Retrieve the current active scenario for a session."""
    def get(self, request, pin):
        # Validate session
        session = get_session_by_pin(pin)
        if not session:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
        
        scenarios = session.get("scenarios", [])
        if not scenarios:
            return Response({"detail": "No scenario yet"}, status=status.HTTP_404_NOT_FOUND)

        # Select the first unfinalized scenario to be displayed (not finalized). If all finalized, show the most recent one.
        open_one = next((s for s in scenarios if s.get("chosen") is None), None)
        current = open_one or scenarios[-1]
        return Response(current, status=status.HTTP_200_OK)

class VotingLogicView(APIView):
    """Handle player voting within an active session.""" 
    def patch(self, request, pin):
        
        try:
            data = request.data
            scenario_id = data.get("scenarioId")
            choice_id   = data.get("choiceId")
            
            # Validate session
            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            # Increment vote count for the selected choice
            vote_result = increment_choice_vote(pin, scenario_id, choice_id)

            # Build updated vote tally
            tally = {k: int(v) for k, v in vote_result["votes"].items()}
            number_of_players = int(session.get("numberofplayers", 0))
            total_votes = sum(tally.values())

            # Return current vote status
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

class PlayerVoteCheck(APIView):
    """Check voting progress and finalize scenario if all players have voted."""
    def get(self, request, pin):

        # Validate query parameter
        try:
            scenario_id = int(request.query_params.get("scenarioId"))
        except (TypeError, ValueError):
            return Response({"error": "scenarioId must be provided as an integer"},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            # Validate session
            session = get_session_by_pin(pin)
            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            if session.get("status") != "in-progress":
                return Response({"error": "Game has not started yet."}, status=status.HTTP_403_FORBIDDEN)

            scenarios = session.get("scenarios", [])
            current = next((s for s in scenarios if s.get("id") == scenario_id), None)
            if not current:
                return Response({"error": "Scenario not found"}, status=status.HTTP_404_NOT_FOUND)

            # Calculate vote tally and totals
            number_of_players = int(session.get("numberofplayers", 0))
            tally = {str(ch["id"]): int(ch.get("votes", 0)) for ch in current.get("choices", [])}
            total_votes = sum(tally.values())

            # If scenario already finalized, return final result
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

            # If everyone hasn't voted yet: return what we've got so far
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
            
            # If there's too many votes (oversubscription):
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

            # Otherwise: everyone has voted, pick winner
            else:
                winner = pick_winner_from_choices(current["choices"]) 
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
                    "tally": tally,
                    "total_votes": total_votes,
                    "number_of_players": number_of_players,
                }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
class PlayerCountView(APIView):
    """ Gets the number of players in a session."""
    def get(self, request, pin):

        try:
            count = get_player_count(pin)
            return Response({"pin": pin, "player_count": count}, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GameStateView(APIView):
    """Retrieve or update the current game state for a session."""
    def get(self, request, pin):
        """Return the current game status (e.g., lobby, in-progress, finished)."""
        try:
            session = get_session_by_pin(pin)

            if not session:
                return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"status": session.get("status", "lobby")}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    def patch(self, request, pin):
        """Update the game status for a given session."""
        try:
            data = request.data
            new_state = data.get("status")

            if not new_state:
                return Response({"error": "State is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            result = update_game_state(pin, new_state)

            return Response(result, status=status.HTTP_200_OK)
    
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


