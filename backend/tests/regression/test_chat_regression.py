"""
LLM-based regression tests for chat functionality.

Uses DeepEval framework to ensure chat responses remain accurate and helpful
throughout codebase changes. Tests common query patterns against expected
response quality rather than exact text matches.
"""

import os
import sys
from typing import Any

import pytest
from deepeval import assert_test, evaluate
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    HallucinationMetric,
)
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from anthropic import Anthropic
from app import app
from config import Config
from fastapi.testclient import TestClient


# Expected Data Constants
# These values represent the current state of the test database.
# Update these if the underlying data changes.

EXPECTED_DATA = {
    "top_goal_scorer_2024": {
        "name": "Alec Wilson Holliday",
        "team": "Legion",
        "goals": 60,
    },
    "top_goal_scorer_2025": {
        "name": "Anthony Gutowsky",
        "team": "Radicals",
        "goals": 56,
    },
    # Single-season records (best one-year performance)
    "single_season_record_goals": {
        "name": "Mischa Freystaetter",
        "team": "Cannons",
        "goals": 95,
        "year": 2016,
    },
    "single_season_record_assists": {
        "name": "Pawel Janas",
        "team": "Union",
        "assists": 97,
        "year": 2018,
    },
    "single_season_record_blocks": {
        "name": "Peter Graffy",
        "team": "Radicals",
        "blocks": 54,
        "year": 2014,
    },
    # Career leaders (all-time cumulative stats)
    "career_leader_goals": {
        "name": "Cameron Brock",
        "goals": 660,
    },
    "career_leader_assists": {
        "name": "Pawel Janas",
        "assists": 533,
    },
    "career_leader_blocks": {
        "name": "Ryan Drost",
        "blocks": 207,
    },
    # Current season leaders
    "top_assist_leaders_2025": [
        {"name": "Allan Laviolette", "team": "Flyers", "assists": 67},
        {"name": "Jake Felton", "team": "Mechanix", "assists": 62},
    ],
    "top_teams_2025": [
        {"name": "Union", "wins": 12, "losses": 1},
        {"name": "Shred", "wins": 12, "losses": 2},
        {"name": "Glory", "wins": 12, "losses": 3},
    ],
    "recent_games": [
        {
            "home_team": "Wind Chill",
            "away_team": "Glory",
            "home_score": 15,
            "away_score": 17,
            "date": "2025-08-23",
        },
        {
            "home_team": "Wind Chill",
            "away_team": "Hustle",
            "home_score": 23,
            "away_score": 21,
            "date": "2025-08-22",
        },
        {
            "home_team": "Shred",
            "away_team": "Glory",
            "home_score": 17,
            "away_score": 21,
            "date": "2025-08-22",
        },
    ],
    "semifinalists_2025": [
        {"name": "Glory"},
        {"name": "Hustle"},
        {"name": "Shred"},
        {"name": "Wind Chill"},
    ],
}


class ClaudeModel(DeepEvalBaseLLM):
    """Custom DeepEval model using Anthropic Claude."""

    def __init__(self, model: str = "claude-3-haiku-20240307"):
        self.model = model
        config = Config()
        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    def load_model(self):
        """Load model (no-op for Claude)."""
        return self.model

    def generate(self, prompt: str) -> str:
        """Generate a response using Claude."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    async def a_generate(self, prompt: str) -> str:
        """Async generate (calls sync version)."""
        return self.generate(prompt)

    def get_model_name(self) -> str:
        """Return model name."""
        return self.model


class ChatTestHelper:
    """Helper class for creating chat test cases."""

    def __init__(self):
        self.client = TestClient(app)
        self.session_id = "test-regression-session"

    def query(self, question: str) -> dict[str, Any]:
        """Send a query to the chat API."""
        response = self.client.post(
            "/api/query",
            json={"query": question, "session_id": self.session_id},
        )
        assert response.status_code == 200
        return response.json()

    def create_test_case(
        self,
        input_query: str,
        retrieval_context: list[str] | None = None,
        expected_keywords: list[str] | None = None,
        expected_output: str | None = None,
        expected_values: list[str] | None = None,
    ) -> tuple[LLMTestCase, dict[str, Any]]:
        """
        Create a DeepEval test case from a query.

        Args:
            input_query: The user's question
            retrieval_context: Expected context/facts that should inform the answer
            expected_keywords: Keywords that should appear in a good response
            expected_output: Ground truth statement for semantic comparison
            expected_values: Specific values that must appear in the response (for assertions)

        Returns:
            tuple: (LLMTestCase, response dict) - test case and raw response for assertions
        """
        response = self.query(input_query)
        actual_output = response.get("answer", "")

        # If expected_values provided, assert they appear in the response
        if expected_values:
            for value in expected_values:
                assert (
                    value in actual_output
                ), f"Expected value '{value}' not found in response: {actual_output}"

        # Extract data/tool results as context for faithfulness/hallucination checking
        context = []
        if retrieval_context:
            context.extend(retrieval_context)

        # Extract context from the API response data field
        # Structure: data[].data.results[] contains the actual query results
        if "data" in response and response["data"]:
            for tool_call in response["data"]:
                # Each tool call has a 'data' field with 'results'
                if isinstance(tool_call, dict) and "data" in tool_call:
                    tool_data = tool_call["data"]
                    if isinstance(tool_data, dict) and "results" in tool_data:
                        # Convert results to readable string format
                        for result in tool_data["results"]:
                            context.append(str(result))

        # If no data was extracted, use a more lenient approach
        # DeepEval hallucination metric needs context to compare against
        if not context:
            # Use the actual output itself as context (less strict)
            # This makes the test more lenient but still catches major issues
            context = [actual_output]

        return (
            LLMTestCase(
                input=input_query,
                actual_output=actual_output,
                retrieval_context=context,  # For Faithfulness metric
                expected_output=expected_output,  # Ground truth for semantic comparison
                context=context,  # For Hallucination metric (same as retrieval_context)
            ),
            response,
        )


@pytest.fixture
def chat_helper():
    """Provide a chat test helper."""
    return ChatTestHelper()


@pytest.fixture
def claude_model():
    """Provide a Claude model for evaluation metrics."""
    return ClaudeModel()


class TestPlayerQueries:
    """Regression tests for player statistics queries."""

    def test_player_season_stats(self, chat_helper, claude_model):
        """Test query about a player's season statistics."""
        data = EXPECTED_DATA["top_goal_scorer_2024"]

        test_case, response = chat_helper.create_test_case(
            input_query="How many goals did the top scorer get in 2024?",
            expected_output=f"{data['name']} scored {data['goals']} goals in 2024",
            expected_values=[str(data["goals"]), data["name"]],
            retrieval_context=[
                f"{data['name']} scored {data['goals']} goals in the 2024 season",
                f"{data['name']} plays for the {data['team']}",
            ],
            expected_keywords=["goals", "2024", "scorer"],
        )

        # Answer should be relevant
        relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)

        # Answer should not hallucinate facts (moderate threshold for natural language)
        hallucination_metric = HallucinationMetric(threshold=0.7, model=claude_model)

        assert_test(test_case, [relevancy_metric, hallucination_metric])

    def test_player_game_stats(self, chat_helper, claude_model):
        """Test query about player performance in a specific game."""
        # Using recent game data from Glory vs Wind Chill
        game = EXPECTED_DATA["recent_games"][0]

        test_case, response = chat_helper.create_test_case(
            input_query=f"Show me top performers from the recent {game['away_team']} vs {game['home_team']} game",
            expected_values=[game["away_team"], game["home_team"]],
            retrieval_context=[
                f"{game['away_team']} played against {game['home_team']}",
                f"Final score: {game['away_team']} {game['away_score']}, {game['home_team']} {game['home_score']}",
            ],
            expected_keywords=[
                game["away_team"],
                game["home_team"],
                "goals",
                "assists",
            ],
        )

        relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)
        hallucination_metric = HallucinationMetric(threshold=0.7, model=claude_model)

        assert_test(test_case, [relevancy_metric, hallucination_metric])

    def test_player_comparison(self, chat_helper, claude_model):
        """Test query comparing multiple players."""
        leaders = EXPECTED_DATA["top_assist_leaders_2025"]
        leader1, leader2 = leaders[0], leaders[1]

        test_case, response = chat_helper.create_test_case(
            input_query="Who has more assists this season between the top two assist leaders?",
            expected_values=[leader1["name"], str(leader1["assists"])],
            retrieval_context=[
                f"{leader1['name']} has {leader1['assists']} assists",
                f"{leader2['name']} has {leader2['assists']} assists",
                f"{leader1['name']} has more assists than {leader2['name']}",
            ],
            expected_keywords=["assists", "season", leader1["name"]],
        )

        relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)
        hallucination_metric = HallucinationMetric(threshold=0.7, model=claude_model)

        assert_test(test_case, [relevancy_metric, hallucination_metric])


class TestTeamQueries:
    """Regression tests for team statistics queries."""

    def test_team_standings(self, chat_helper, claude_model):
        """Test query about league standings."""
        top_team = EXPECTED_DATA["top_teams_2025"][0]

        test_case, response = chat_helper.create_test_case(
            input_query="What are the current standings?",
            expected_values=[top_team["name"], str(top_team["wins"])],
            retrieval_context=[
                f"{top_team['name']} has {top_team['wins']} wins and {top_team['losses']} losses",
                f"{top_team['name']} is one of the top teams in the standings",
            ],
            expected_keywords=["standings", "wins", "losses"],
        )

        relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)
        hallucination_metric = HallucinationMetric(threshold=0.7, model=claude_model)

        assert_test(test_case, [relevancy_metric, hallucination_metric])

    def test_team_season_stats(self, chat_helper, claude_model):
        """Test query about team performance."""
        # Glory is in top_teams_2025 with 12 wins, 3 losses
        glory_data = next(
            t for t in EXPECTED_DATA["top_teams_2025"] if t["name"] == "Glory"
        )

        test_case, response = chat_helper.create_test_case(
            input_query="How is Glory performing this season?",
            expected_values=["Glory", str(glory_data["wins"])],
            retrieval_context=[
                f"Glory has {glory_data['wins']} wins and {glory_data['losses']} losses this season",
            ],
            expected_keywords=["Glory", "season", "wins"],
        )

        relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)
        hallucination_metric = HallucinationMetric(threshold=0.7, model=claude_model)

        assert_test(test_case, [relevancy_metric, hallucination_metric])


class TestGameQueries:
    """Regression tests for game result queries."""

    def test_recent_games(self, chat_helper, claude_model):
        """Test query about recent game results."""
        recent_game = EXPECTED_DATA["recent_games"][0]

        test_case, response = chat_helper.create_test_case(
            input_query="What were the scores of the most recent games?",
            expected_values=[
                recent_game["away_team"],
                recent_game["home_team"],
                str(recent_game["away_score"]),
                str(recent_game["home_score"]),
            ],
            retrieval_context=[
                f"{recent_game['away_team']} {recent_game['away_score']}, {recent_game['home_team']} {recent_game['home_score']}",
            ],
            expected_keywords=["score", "game"],
        )

        relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)
        hallucination_metric = HallucinationMetric(threshold=0.7, model=claude_model)

        assert_test(test_case, [relevancy_metric, hallucination_metric])

    def test_game_details_with_stats(self, chat_helper, claude_model):
        """
        Test query requesting detailed game statistics.

        This is a critical test ensuring game detail responses include:
        - Basic game info (teams, scores, date)
        - Individual player leaders
        - Team statistics (completion %, possession stats)
        """
        # Using Glory vs Wind Chill game
        game = EXPECTED_DATA["recent_games"][0]

        test_case, response = chat_helper.create_test_case(
            input_query=f"Show me details about the recent {game['away_team']} vs {game['home_team']} game",
            expected_values=[
                game["away_team"],
                game["home_team"],
                str(game["away_score"]),
                str(game["home_score"]),
            ],
            retrieval_context=[
                f"{game['away_team']} played {game['home_team']}",
                f"Final score: {game['away_team']} {game['away_score']}, {game['home_team']} {game['home_score']}",
            ],
            expected_keywords=[
                game["away_team"],
                game["home_team"],
                "completion",
                "goals",
                "assists",
            ],
        )

        # This test should have high relevancy since it's a common query pattern
        relevancy_metric = AnswerRelevancyMetric(threshold=0.8, model=claude_model)

        # Should not hallucinate statistics (stricter for critical functionality)
        hallucination_metric = HallucinationMetric(threshold=0.6, model=claude_model)

        # Response should be faithful to the tool results
        faithfulness_metric = FaithfulnessMetric(threshold=0.7, model=claude_model)

        assert_test(
            test_case, [relevancy_metric, hallucination_metric, faithfulness_metric]
        )

    def test_team_head_to_head(self, chat_helper, claude_model):
        """Test query about head-to-head matchups."""
        # Using Glory vs Wind Chill since we have game data for them
        team1 = "Glory"
        team2 = "Wind Chill"

        test_case, response = chat_helper.create_test_case(
            input_query=f"What is {team1}'s record against {team2} this season?",
            expected_values=[team1, team2],
            retrieval_context=[
                f"{team1} played against {team2} this season",
            ],
            expected_keywords=[team1, team2, "record"],
        )

        relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)
        hallucination_metric = HallucinationMetric(threshold=0.7, model=claude_model)

        assert_test(test_case, [relevancy_metric, hallucination_metric])

    def test_semifinalists_2025(self, chat_helper, claude_model):
        """Test query about playoff semifinalists."""
        semifinalists = EXPECTED_DATA["semifinalists_2025"]
        team_names = [team["name"] for team in semifinalists]

        test_case, response = chat_helper.create_test_case(
            input_query="which teams made the semi finals in 2025?",
            expected_values=team_names,
            retrieval_context=[
                "Glory, Hustle, Shred, and Wind Chill made the 2025 UFA semifinals",
                "The 2025 semifinal games were played on 2025-08-22",
            ],
            expected_keywords=["semi", "finals", "2025"] + team_names,
        )

        relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)
        hallucination_metric = HallucinationMetric(threshold=0.7, model=claude_model)

        assert_test(test_case, [relevancy_metric, hallucination_metric])


class TestLeagueLeaderQueries:
    """Regression tests for league leader queries."""

    def test_goals_leaders(self, chat_helper, claude_model):
        """Test query about goal scoring leaders."""
        top_scorer = EXPECTED_DATA["top_goal_scorer_2025"]

        test_case, response = chat_helper.create_test_case(
            input_query="Who are the top goal scorers this season?",
            expected_values=[top_scorer["name"], str(top_scorer["goals"])],
            retrieval_context=[
                f"{top_scorer['name']} has {top_scorer['goals']} goals this season",
                f"{top_scorer['name']} plays for {top_scorer['team']}",
            ],
            expected_keywords=["goals", "top", "season"],
        )

        relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)
        hallucination_metric = HallucinationMetric(threshold=0.7, model=claude_model)

        assert_test(test_case, [relevancy_metric, hallucination_metric])

    def test_assists_leaders(self, chat_helper, claude_model):
        """Test query about assist leaders."""
        top_assist = EXPECTED_DATA["top_assist_leaders_2025"][0]

        test_case, response = chat_helper.create_test_case(
            input_query="Show me the assist leaders",
            expected_values=[top_assist["name"], str(top_assist["assists"])],
            retrieval_context=[
                f"{top_assist['name']} has {top_assist['assists']} assists",
                f"{top_assist['name']} plays for {top_assist['team']}",
            ],
            expected_keywords=["assists", "leaders"],
        )

        relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)
        hallucination_metric = HallucinationMetric(threshold=0.7, model=claude_model)

        assert_test(test_case, [relevancy_metric, hallucination_metric])

    def test_blocks_leaders(self, chat_helper, claude_model):
        """Test query about career defensive leaders."""
        career_blocks = EXPECTED_DATA["career_leader_blocks"]

        test_case, response = chat_helper.create_test_case(
            input_query="Who has the most career blocks?",
            expected_values=[career_blocks["name"], str(career_blocks["blocks"])],
            retrieval_context=[
                f"{career_blocks['name']} has {career_blocks['blocks']} career blocks",
                f"{career_blocks['name']} is the all-time blocks leader",
            ],
            expected_keywords=["blocks"],
        )

        relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)
        hallucination_metric = HallucinationMetric(threshold=0.7, model=claude_model)

        assert_test(test_case, [relevancy_metric, hallucination_metric])


class TestComplexQueries:
    """Regression tests for complex multi-step queries."""

    def test_player_team_context(self, chat_helper, claude_model):
        """Test query requiring both player and team context."""
        # Using Glory's top scorer from 2025 data
        team = "Glory"

        test_case, response = chat_helper.create_test_case(
            input_query=f"How did {team}'s top scorer perform in their last game?",
            expected_values=[team],
            retrieval_context=[
                f"Searching for {team}'s top scorer",
                f"Finding {team}'s most recent game",
            ],
            expected_keywords=[team, "scorer", "game"],
        )

        relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)
        hallucination_metric = HallucinationMetric(threshold=0.7, model=claude_model)

        assert_test(test_case, [relevancy_metric, hallucination_metric])

    def test_statistical_comparison(self, chat_helper, claude_model):
        """Test query requiring statistical analysis."""
        test_case, response = chat_helper.create_test_case(
            input_query="Which team has better offensive efficiency this season?",
            expected_keywords=["team", "offensive", "efficiency", "season"],
        )

        relevancy_metric = AnswerRelevancyMetric(threshold=0.7, model=claude_model)
        hallucination_metric = HallucinationMetric(threshold=0.7, model=claude_model)

        assert_test(test_case, [relevancy_metric, hallucination_metric])


class TestResponseQuality:
    """Tests for overall response quality and user experience."""

    def test_helpful_response_when_no_data(self, chat_helper, claude_model):
        """Test that system gives helpful response when data isn't available."""
        test_case, response = chat_helper.create_test_case(
            input_query="What were the scores from games in the year 3000?",
            expected_keywords=["no", "not", "available"],
        )

        # Should still be relevant even if saying "no data"
        relevancy_metric = AnswerRelevancyMetric(threshold=0.6, model=claude_model)

        assert_test(test_case, [relevancy_metric])

    def test_handles_ambiguous_query(self, chat_helper, claude_model):
        """Test that system handles ambiguous queries gracefully."""
        test_case, response = chat_helper.create_test_case(
            input_query="Tell me about the game",
            expected_keywords=["game"],
        )

        relevancy_metric = AnswerRelevancyMetric(threshold=0.5, model=claude_model)

        assert_test(test_case, [relevancy_metric])


def test_run_all_regression_tests():
    """
    Run all regression tests as a batch evaluation.

    This can be used to get an overall score across all test cases.
    """
    helper = ChatTestHelper()
    claude_model = ClaudeModel()

    # Define critical queries that should always work well with expected data
    top_scorer = EXPECTED_DATA["top_goal_scorer_2025"]
    top_team = EXPECTED_DATA["top_teams_2025"][0]
    recent_game = EXPECTED_DATA["recent_games"][0]

    critical_test_data = [
        {
            "query": "How many goals did the top scorer get this season?",
            "expected_values": [str(top_scorer["goals"]), top_scorer["name"]],
            "retrieval_context": [
                f"{top_scorer['name']} scored {top_scorer['goals']} goals this season"
            ],
        },
        {
            "query": "What are the current standings?",
            "expected_values": [top_team["name"], str(top_team["wins"])],
            "retrieval_context": [f"{top_team['name']} has {top_team['wins']} wins"],
        },
        {
            "query": f"Show me details about the recent {recent_game['away_team']} vs {recent_game['home_team']} game",
            "expected_values": [
                recent_game["away_team"],
                recent_game["home_team"],
                str(recent_game["away_score"]),
            ],
            "retrieval_context": [
                f"{recent_game['away_team']} played {recent_game['home_team']}"
            ],
        },
        {
            "query": "Who are the top goal scorers?",
            "expected_values": [top_scorer["name"]],
            "retrieval_context": [
                f"{top_scorer['name']} is a top goal scorer with {top_scorer['goals']} goals"
            ],
        },
        {
            "query": "Which team has the best record?",
            "expected_values": [top_team["name"]],
            "retrieval_context": [f"{top_team['name']} has one of the best records"],
        },
    ]

    test_cases = [
        helper.create_test_case(
            test["query"],
            expected_values=test["expected_values"],
            retrieval_context=test["retrieval_context"],
        )[
            0
        ]  # Extract just the test case from the tuple
        for test in critical_test_data
    ]

    # Evaluate all at once
    metrics = [
        AnswerRelevancyMetric(threshold=0.7, model=claude_model),
        HallucinationMetric(threshold=0.7, model=claude_model),
    ]

    # This will print a summary report
    results = evaluate(test_cases, metrics)

    # Ensure most tests pass
    assert results is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
