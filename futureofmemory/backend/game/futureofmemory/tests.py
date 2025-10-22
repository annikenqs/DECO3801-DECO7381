from django.test import SimpleTestCase
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

### Base class for API tests.
class BaseAPITest(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.test_pin = "123456"


### Tests for the Session Creation API endpoint.
class SessionAPITests(BaseAPITest):
    
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


### Tests for the Join Session API endpoint.
class JoinSessionAPITests(BaseAPITest):
        
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

### Tests for the Faction Vote API endpoint.
class FactionVoteAPITests(BaseAPITest):
        
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

### Tests for the Faction Result API endpoint.
class FactionResultAPITests(BaseAPITest):
        
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

### Tests for the Scenario API endpoint.
class ScenarioAPITests(BaseAPITest):
        
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

### Tests for the Voting Logic API endpoint.
class VotingLogicAPITests(BaseAPITest):
        
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

### Tests for the Player Vote Check API endpoint.
class PlayerVoteCheckAPITests(BaseAPITest):
        
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

### Tests for the Game State API endpoint.
class GameStateAPITests(BaseAPITest):
        
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

### Tests for the Player Count API endpoint.
class PlayerCountAPITests(BaseAPITest):
        
    @patch("game.futureofmemory.api.views.get_player_count")
    def test_get_player_count(self, mock_get_count):
        mock_get_count.return_value = 3
        
        response = self.client.get(f"/api/session/{self.test_pin}/players/count/")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["player_count"], 3)

### Integration Tests for complete game flow.
class IntegrationTests(BaseAPITest):
        
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
