from django.test import SimpleTestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

class BaseAPITest(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.test_pin = "123456"

class SessionAPITests(BaseAPITest):
    """Tests for the session creation endpoint."""
    @patch("game.futureofmemory.api.views.create_session")
    @patch("game.futureofmemory.api.views.allocate_pin")
    def test_create_session_success(self, mock_allocate_pin, mock_create_session):
        mock_allocate_pin.return_value = self.test_pin
        mock_create_session.return_value = {
            "pin": self.test_pin,
            "faction": "rightists",
            "year": 2075,
            "status": "lobby",
            "numberofplayers": 0
        }
        
        response = self.client.post("/api/session/", {
            "faction": "rightists",
            "year": 2075
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["pin"], self.test_pin)
        self.assertEqual(response.data["faction"], "rightists")
        
    @patch("game.futureofmemory.api.views.create_session")
    def test_create_session_with_custom_pin(self, mock_create_session):
        custom_pin = "999999"
        mock_create_session.return_value = {
            "pin": custom_pin,
            "faction": "resourceists",
            "year": 2080,
            "status": "lobby",
            "numberofplayers": 0
        }
        
        response = self.client.post("/api/session/", {
            "pin": custom_pin,
            "faction": "resourceists",
            "year": 2080
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["pin"], custom_pin)


class CurrentScenarioViewAPITests(BaseAPITest):
    """Tests for the current scenario retrieval endpoint."""
    @patch("game.futureofmemory.api.views.get_session_by_pin")
    def test_current_scenario_session_not_found(self, mock_get_session):
        mock_get_session.return_value = None

        resp = self.client.get(f"/api/session/{self.test_pin}/scenario/current/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", resp.data)

    @patch("game.futureofmemory.api.views.get_session_by_pin")
    def test_current_scenario_none_exists(self, mock_get_session):
        mock_get_session.return_value = {
            "pin": self.test_pin,
            "status": "in-progress",
            "scenarios": []
        }

        resp = self.client.get(f"/api/session/{self.test_pin}/scenario/current/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", resp.data)

    @patch("game.futureofmemory.api.views.get_session_by_pin")
    def test_current_scenario_success_returns_first(self, mock_get_session):
        scenarios = [
            {"id": 1, "text": "First", "choices": [], "chosen": None},
            {"id": 2, "text": "Second", "choices": [], "chosen": None},
        ]
        mock_get_session.return_value = {
            "pin": self.test_pin,
            "status": "in-progress",
            "scenarios": scenarios
        }

        resp = self.client.get(f"/api/session/{self.test_pin}/scenario/current/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data.get("id"), 1)
        self.assertEqual(resp.data.get("text"), "First")


class NextScenarioViewAPITests(BaseAPITest):
    """Tests for the next scenario generation endpoint."""
    @patch("game.futureofmemory.api.views.get_session_by_pin")
    def test_next_scenario_session_not_found(self, mock_get_session):
        mock_get_session.return_value = None

        resp = self.client.post(f"/api/session/{self.test_pin}/scenario/next/", {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", resp.data)

    @patch("game.futureofmemory.api.views.get_session_by_pin")
    def test_next_scenario_game_not_started(self, mock_get_session):
        mock_get_session.return_value = {
            "pin": self.test_pin,
            "status": "lobby",
            "scenarios": [{"id": 1, "text": "S1", "choices": [], "chosen": 1}]
        }

        resp = self.client.post(f"/api/session/{self.test_pin}/scenario/next/", {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("error", resp.data)

    @patch("game.futureofmemory.api.views.get_session_by_pin")
    def test_next_scenario_no_previous_exists(self, mock_get_session):
        mock_get_session.return_value = {
            "pin": self.test_pin,
            "status": "in-progress",
            "scenarios": []
        }

        resp = self.client.post(f"/api/session/{self.test_pin}/scenario/next/", {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("error", resp.data)

    @patch("game.futureofmemory.api.views.get_session_by_pin")
    def test_next_scenario_previous_not_finalized(self, mock_get_session):
        mock_get_session.return_value = {
            "pin": self.test_pin,
            "status": "in-progress",
            "year": 2075,
            "faction": "rightists",
            "scenarios": [
                {"id": 1, "text": "S1", "choices": [{"id": 1, "text": "A"}], "chosen": None}
            ]
        }

        resp = self.client.post(
            f"/api/session/{self.test_pin}/scenario/next/",
            {"previousScenarioId": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("error", resp.data)

    @patch("game.futureofmemory.api.views.add_next_scenario_if_absent")
    @patch("game.futureofmemory.api.views.run_rag")
    @patch("game.futureofmemory.api.views.get_session_by_pin")
    
    def test_next_scenario_success_appends_or_returns_existing(
        self, mock_get_session, mock_rag, mock_add_next
    ):
        mock_get_session.return_value = {
            "pin": self.test_pin,
            "status": "in-progress",
            "year": 2077,
            "faction": "resourceists",
            "scenarios": [
                {"id": 1, "text": "Year 2076", "choices": [{"id": 1, "text": "A"}, {"id": 2, "text": "B"}], "chosen": 2},
                {"id": 2, "text": "Year 2077", "choices": [{"id": 1, "text": "C"}, {"id": 2, "text": "D"}], "chosen": 1},
            ],
        }

        mock_rag.return_value = {
            "scenario": {
                "text": "Generated 2078",
                "choices": [{"id": 1, "text": "X"}, {"id": 2, "text": "Y"}, {"id": 3, "text": "Z"}],
                "citations": [],
            }
        }

        mock_add_next.return_value = {
            "id": 3,
            "text": "Generated 2078",
            "choices": [{"id": 1, "text": "X", "votes": 0}, {"id": 2, "text": "Y", "votes": 0}, {"id": 3, "text": "Z", "votes": 0}],
            "chosen": None,
            "year": 2078,
            "citations": [],
        }

        resp = self.client.post(
            f"/api/session/{self.test_pin}/scenario/next/",
            {"previousScenarioId": 2},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data.get("id"), 3)
        self.assertEqual(resp.data.get("year"), 2078)
        self.assertIn("choices", resp.data)

        args, kwargs = mock_add_next.call_args
        self.assertEqual(args[0], self.test_pin)
        self.assertEqual(args[1], 3)
        self.assertIsInstance(args[2], dict)
        self.assertEqual(args[3], 2078)

class JoinSessionAPITests(BaseAPITest):
    """Tests for the join session endpoint."""
    @patch("game.futureofmemory.api.views.join_session")
    def test_join_session_success(self, mock_join_session):
        mock_join_session.return_value = {
            "numberofplayers": 2,
            "status": "lobby"
        }
        
        response = self.client.post("/api/session/join/", {
            "pin": self.test_pin
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["pin"], self.test_pin)
        
    def test_join_session_without_pin(self):
        response = self.client.post("/api/session/join/", {}, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

class FactionVoteAPITests(BaseAPITest):
    """Tests for the faction voting endpoint."""
    @patch("game.futureofmemory.api.views.get_session_by_pin")
    @patch("game.futureofmemory.api.views.vote_for_faction")
    def test_faction_vote_success(self, mock_vote, mock_get_session):
        mock_get_session.return_value = {
            "pin": self.test_pin,
            "status": "lobby"
        }
        mock_vote.return_value = {
            "factionVotes": {"rightists": 1},
            "allVoted": False
        }
        
        response = self.client.post(f"/api/session/{self.test_pin}/faction/vote/", {
            "faction": "rightists"
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["faction"], "rightists")
        
    @patch("game.futureofmemory.api.views.get_session_by_pin")
    def test_faction_vote_invalid_faction(self, mock_get_session):
        mock_get_session.return_value = {"pin": self.test_pin}
        
        response = self.client.post(f"/api/session/{self.test_pin}/faction/vote/", {
            "faction": "invalid_faction"
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    @patch("game.futureofmemory.api.views.get_session_by_pin")
    def test_faction_vote_session_not_found(self, mock_get_session):
        mock_get_session.return_value = None
        
        response = self.client.post(f"/api/session/{self.test_pin}/faction/vote/", {
            "faction": "rightists"
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class FactionResultAPITests(BaseAPITest):
    """Tests for the faction result endpoint."""
    @patch("game.futureofmemory.api.views.get_session_by_pin")
    @patch("game.futureofmemory.api.views.get_faction_votes")
    @patch("game.futureofmemory.api.views.finalize_faction_vote")
    def test_faction_result_finalized(self, mock_finalize, mock_get_votes, mock_get_session):
        mock_get_session.return_value = {"pin": self.test_pin}
        mock_get_votes.return_value = {
            "allVoted": True,
            "faction": None,
            "factionVotes": {"rightists": 2, "resourceists": 1},
            "totalPlayers": 3,
            "votedPlayers": 3
        }
        mock_finalize.return_value = {
            "faction": "rightists",
            "factionVotes": {"rightists": 2, "resourceists": 1},
            "wasTie": False
        }
        
        response = self.client.get(f"/api/session/{self.test_pin}/faction/result/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["finalized"])
        self.assertEqual(response.data["faction"], "rightists")

class ScenarioAPITests(BaseAPITest):
    """Tests for the scenario retrieval and generation endpoint."""
    @patch("game.futureofmemory.api.views.get_session_by_pin")
    @patch("game.futureofmemory.api.views.run_rag")
    @patch("game.futureofmemory.api.views.add_first_scenario_if_absent")
    def test_create_first_scenario(self, mock_add_scenario, mock_rag, mock_get_session):
        mock_get_session.return_value = {
            "pin": self.test_pin,
            "status": "in-progress",
            "faction": "rightists",
            "year": 2075,
            "scenarios": []
        }
        mock_rag.return_value = {
            "scenario": {
                "text": "test scenario text",
                "choices": [
                    {"id": 1, "text": "Option A", "votes": 0},
                    {"id": 2, "text": "Option B", "votes": 0}
                ],
                "citations": []
            }
        }
        mock_add_scenario.return_value = {
            "id": 1,
            "text": "test scenario text",
            "choices": [
                {"id": 1, "text": "Option A", "votes": 0},
                {"id": 2, "text": "Option B", "votes": 0}
            ],
            "year": 2075,
            "citations": []
        }
        
        response = self.client.post(f"/api/session/{self.test_pin}/scenario/", format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text", response.data)
        self.assertIn("choices", response.data)
        
    @patch("game.futureofmemory.api.views.get_session_by_pin")
    def test_scenario_game_not_started(self, mock_get_session):
        mock_get_session.return_value = {
            "pin": self.test_pin,
            "status": "lobby"
        }
        
        response = self.client.post(f"/api/session/{self.test_pin}/scenario/", format="json")
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class VotingLogicAPITests(BaseAPITest):
    """Tests for the player voting endpoint."""
    @patch("game.futureofmemory.api.views.get_session_by_pin")
    @patch("game.futureofmemory.api.views.increment_choice_vote")
    def test_cast_vote_success(self, mock_increment, mock_get_session):
        mock_get_session.return_value = {
            "pin": self.test_pin,
            "status": "in-progress",
            "numberofplayers": 3
        }
        mock_increment.return_value = {
            "votes": {"1": 1, "2": 0}
        }
        
        response = self.client.patch(f"/api/session/{self.test_pin}/vote/", {
            "scenarioId": 1,
            "choiceId": 1
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["pin"], self.test_pin)
        self.assertIn("tally", response.data)

class PlayerVoteCheckAPITests(BaseAPITest):
    """Tests for the player vote status checking endpoint."""
    @patch("game.futureofmemory.api.views.get_session_by_pin")
    def test_vote_check_not_finalized(self, mock_get_session):
        mock_get_session.return_value = {
            "pin": self.test_pin,
            "status": "in-progress",
            "numberofplayers": 3,
            "scenarios": [{
                "id": 1,
                "choices": [
                    {"id": 1, "text": "Option A", "votes": 1},
                    {"id": 2, "text": "Option B", "votes": 0}
                ]
            }]
        }
        
        response = self.client.get(f"/api/session/{self.test_pin}/votes/status/?scenarioId=1")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["persisted"])
        self.assertEqual(response.data["total_votes"], 1)

class GameStateAPITests(BaseAPITest):
    """Tests for the game state retrieval and update endpoint."""
    @patch("game.futureofmemory.api.views.get_session_by_pin")
    def test_get_game_state(self, mock_get_session):
        mock_get_session.return_value = {
            "pin": self.test_pin,
            "status": "in-progress"
        }
        
        response = self.client.get(f"/api/session/{self.test_pin}/state/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "in-progress")
        
    @patch("game.futureofmemory.api.views.update_game_state")
    def test_update_game_state(self, mock_update):
        mock_update.return_value = {
            "status": "in-progress",
            "pin": self.test_pin
        }
        
        response = self.client.patch(f"/api/session/{self.test_pin}/state/", {
            "status": "in-progress"
        }, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class PlayerCountAPITests(BaseAPITest):
    """Tests for the player count retrieval endpoint."""
    @patch("game.futureofmemory.api.views.get_player_count")
    def test_get_player_count(self, mock_get_count):
        mock_get_count.return_value = 3
        
        response = self.client.get(f"/api/session/{self.test_pin}/players/count/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["player_count"], 3)

class IntegrationTests(BaseAPITest):
    """Tests for the complete game flow."""
    @patch("game.futureofmemory.api.views.create_session")
    @patch("game.futureofmemory.api.views.allocate_pin")
    @patch("game.futureofmemory.api.views.join_session")
    @patch("game.futureofmemory.api.views.get_session_by_pin")
    @patch("game.futureofmemory.api.views.vote_for_faction")
    @patch("game.futureofmemory.api.views.update_game_state")
    def test_complete_game_flow(self, mock_update_state, mock_vote, mock_get_session, 
                                mock_join, mock_allocate, mock_create):
        test_pin = "123456"
        
        mock_allocate.return_value = test_pin
        mock_create.return_value = {
            "pin": test_pin,
            "faction": "Unknown",
            "year": 2075,
            "status": "lobby",
            "numberofplayers": 0
        }
        
        create_response = self.client.post("/api/session/", {
            "faction": "Unknown",
            "year": 2075
        }, format="json")
        
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        mock_join.return_value = {"numberofplayers": 1}
        join_response = self.client.post("/api/session/join/", {
            "pin": test_pin
        }, format="json")
        
        self.assertEqual(join_response.status_code, status.HTTP_200_OK)
        
        mock_get_session.return_value = {"pin": test_pin, "status": "lobby"}
        mock_vote.return_value = {
            "factionVotes": {"rightists": 1},
            "allVoted": True
        }
        
        vote_response = self.client.post(f"/api/session/{test_pin}/faction/vote/", {
            "faction": "rightists"
        }, format="json")
        
        self.assertEqual(vote_response.status_code, status.HTTP_200_OK)
        
        mock_update_state.return_value = {"status": "in-progress"}
        start_response = self.client.patch(f"/api/session/{test_pin}/state/", {
            "status": "in-progress"
        }, format="json")
        
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)
