"""
Test UFA Data Manager module functionality.
Tests API client, data import, and database integration for UFA data.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add scripts directory to path since ufa_data_manager is in scripts/
scripts_path = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
sys.path.insert(0, scripts_path)

from ufa_data_manager import UFAAPIClient, UFADataManager

# ===== MODULE-LEVEL FIXTURES =====


@pytest.fixture
def mock_db():
    """Mock database for testing"""
    return Mock()


@pytest.fixture
def mock_stats_processor():
    """Mock stats processor"""
    return Mock()


@pytest.fixture
def mock_api_client():
    """Mock API client"""
    return Mock(spec=UFAAPIClient)


@pytest.fixture
def data_manager():
    """UFADataManager with mocked dependencies"""
    with (
        patch("ufa_data_manager.UFAAPIClient") as mock_client_class,
        patch("ufa_data_manager.get_db") as mock_get_db,
        patch("ufa_data_manager.StatsProcessor") as mock_processor_class,
    ):

        mock_client = Mock(spec=UFAAPIClient)
        mock_client_class.return_value = mock_client

        mock_db = Mock()
        mock_get_db.return_value = mock_db

        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor

        manager = UFADataManager()

        # Store mocks for easy access
        manager._mock_api_client = mock_client
        manager._mock_db = mock_db
        manager._mock_stats_processor = mock_processor

        return manager


class TestUFAAPIClient:
    """Test UFAAPIClient functionality"""

    @pytest.fixture
    def api_client(self):
        """UFAAPIClient instance for testing"""
        return UFAAPIClient()

    def test_init_default_url(self):
        """Test API client initialization with default URL"""
        client = UFAAPIClient()
        assert client.base_url == "https://www.backend.ufastats.com/api/v1"
        assert client.session is not None

    def test_init_custom_url(self):
        """Test API client initialization with custom URL"""
        custom_url = "https://custom-api.com/v2/"
        client = UFAAPIClient(custom_url)
        assert (
            client.base_url == "https://custom-api.com/v2"
        )  # Should strip trailing slash

    @patch("ufa_data_manager.requests.Session.get")
    def test_make_request_success(self, mock_get, api_client):
        """Test successful API request"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": 1, "name": "Test Team"}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = api_client._make_request("teams")

        assert result["data"] == [{"id": 1, "name": "Test Team"}]
        mock_get.assert_called_once()

    @patch("ufa_data_manager.requests.Session.get")
    def test_make_request_with_params(self, mock_get, api_client):
        """Test API request with parameters"""
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        params = {"year": 2024, "team": "test"}
        api_client._make_request("games", params)

        # Verify params were passed
        call_args = mock_get.call_args
        assert call_args[1]["params"] == params

    @patch("ufa_data_manager.requests.Session.get")
    @patch("ufa_data_manager.time.sleep")
    def test_make_request_retry_on_failure(self, mock_sleep, mock_get, api_client):
        """Test API request retry mechanism"""
        # First two calls fail, third succeeds
        mock_get.side_effect = [
            Exception("Connection error"),
            Exception("Timeout"),
            Mock(json=lambda: {"data": []}, raise_for_status=lambda: None),
        ]

        result = api_client._make_request("teams", retries=3)

        assert result["data"] == []
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2  # Sleep between retries

    @patch("ufa_data_manager.requests.Session.get")
    def test_make_request_all_retries_fail(self, mock_get, api_client):
        """Test API request when all retries fail"""
        mock_get.side_effect = Exception("Permanent failure")

        with pytest.raises(Exception, match="Permanent failure"):
            api_client._make_request("teams", retries=2)

        assert mock_get.call_count == 2


class TestUFAAPIClientTeams:
    """Test teams API functionality"""

    @pytest.fixture
    def api_client_with_mock_request(self):
        """API client with mocked _make_request method"""
        client = UFAAPIClient()
        client._make_request = Mock()
        return client

    def test_get_teams_success(self, api_client_with_mock_request):
        """Test successful teams retrieval"""
        mock_teams_data = {
            "data": [
                {
                    "teamID": "ATL",
                    "name": "Atlanta Hustle",
                    "city": "Atlanta",
                    "division": {"divisionID": "south", "name": "South Division"},
                }
            ]
        }
        api_client_with_mock_request._make_request.return_value = mock_teams_data

        result = api_client_with_mock_request.get_teams(years=[2024])

        assert len(result) == 1
        assert result[0]["teamID"] == "ATL"
        assert result[0]["name"] == "Atlanta Hustle"
        assert result[0]["divisionID"] == "south"
        assert result[0]["divisionName"] == "South Division"
        assert "division" not in result[0]  # Should be flattened

    def test_get_teams_with_filters(self, api_client_with_mock_request):
        """Test teams retrieval with filters"""
        api_client_with_mock_request._make_request.return_value = {"data": []}

        api_client_with_mock_request.get_teams(
            years=[2023, 2024], team_ids=["ATL", "BOS"], division_ids=["south", "east"]
        )

        # Verify correct parameters were passed
        call_args = api_client_with_mock_request._make_request.call_args
        params = call_args[0][1]

        assert params["years"] == "2023,2024"
        assert params["teamIDs"] == "ATL,BOS"
        assert params["divisionIDs"] == "south,east"

    def test_get_teams_no_data(self, api_client_with_mock_request):
        """Test teams retrieval when no data returned"""
        api_client_with_mock_request._make_request.return_value = {"data": []}

        result = api_client_with_mock_request.get_teams()

        assert result == []

    def test_get_teams_no_division_data(self, api_client_with_mock_request):
        """Test teams retrieval when team has no division data"""
        mock_teams_data = {
            "data": [
                {
                    "teamID": "IND",
                    "name": "Independent Team",
                    "city": "Somewhere",
                    "division": None,
                }
            ]
        }
        api_client_with_mock_request._make_request.return_value = mock_teams_data

        result = api_client_with_mock_request.get_teams()

        assert len(result) == 1
        assert result[0]["teamID"] == "IND"
        assert "divisionID" not in result[0] or result[0]["divisionID"] is None


class TestUFAAPIClientPlayers:
    """Test players API functionality"""

    @pytest.fixture
    def api_client_with_mock_request(self):
        """API client with mocked _make_request method"""
        client = UFAAPIClient()
        client._make_request = Mock()
        return client

    def test_get_players_success(self, api_client_with_mock_request):
        """Test successful players retrieval"""
        mock_players_data = {
            "data": [
                {
                    "playerID": "player1",
                    "firstName": "John",
                    "lastName": "Doe",
                    "teams": [
                        {
                            "teamID": "ATL",
                            "active": True,
                            "year": 2024,
                            "jerseyNumber": 7,
                        }
                    ],
                }
            ]
        }
        api_client_with_mock_request._make_request.return_value = mock_players_data

        result = api_client_with_mock_request.get_players()

        assert len(result) == 1
        assert result[0]["playerID"] == "player1"
        assert result[0]["firstName"] == "John"
        assert result[0]["lastName"] == "Doe"
        assert result[0]["fullName"] == "John Doe"
        assert result[0]["teamID"] == "ATL"
        assert result[0]["year"] == 2024
        assert result[0]["jerseyNumber"] == 7

    def test_get_players_multiple_teams(self, api_client_with_mock_request):
        """Test player with multiple team associations"""
        mock_players_data = {
            "data": [
                {
                    "playerID": "player1",
                    "firstName": "Jane",
                    "lastName": "Smith",
                    "teams": [
                        {"teamID": "ATL", "year": 2023, "active": False},
                        {"teamID": "BOS", "year": 2024, "active": True},
                    ],
                }
            ]
        }
        api_client_with_mock_request._make_request.return_value = mock_players_data

        result = api_client_with_mock_request.get_players()

        # Should create one record per team
        assert len(result) == 2
        assert result[0]["teamID"] == "ATL"
        assert result[0]["year"] == 2023
        assert result[1]["teamID"] == "BOS"
        assert result[1]["year"] == 2024

    def test_get_players_no_teams(self, api_client_with_mock_request):
        """Test player with no team data"""
        mock_players_data = {
            "data": [
                {
                    "playerID": "player1",
                    "firstName": "Solo",
                    "lastName": "Player",
                    "teams": [],
                }
            ]
        }
        api_client_with_mock_request._make_request.return_value = mock_players_data

        result = api_client_with_mock_request.get_players()

        assert len(result) == 1
        assert result[0]["playerID"] == "player1"
        assert "teamID" not in result[0] or result[0]["teamID"] is None

    def test_get_players_with_filters(self, api_client_with_mock_request):
        """Test players retrieval with filters"""
        api_client_with_mock_request._make_request.return_value = {"data": []}

        api_client_with_mock_request.get_players(
            years=[2024], team_ids=["ATL"], player_ids=["player1", "player2"]
        )

        # Verify correct parameters
        call_args = api_client_with_mock_request._make_request.call_args
        params = call_args[0][1]

        assert params["years"] == "2024"
        assert params["teamIDs"] == "ATL"
        assert params["playerIDs"] == "player1,player2"


class TestUFAAPIClientGames:
    """Test games API functionality"""

    @pytest.fixture
    def api_client_with_mock_request(self):
        """API client with mocked _make_request method"""
        client = UFAAPIClient()
        client._make_request = Mock()
        return client

    def test_get_games_success(self, api_client_with_mock_request):
        """Test successful games retrieval"""
        mock_games_data = {
            "data": [
                {
                    "gameID": "game1",
                    "homeTeam": "ATL",
                    "awayTeam": "BOS",
                    "homeScore": 15,
                    "awayScore": 12,
                    "status": "Final",
                }
            ]
        }
        api_client_with_mock_request._make_request.return_value = mock_games_data

        result = api_client_with_mock_request.get_games(date_range="2024")

        assert len(result) == 1
        assert result[0]["gameID"] == "game1"
        assert result[0]["homeScore"] == 15

    def test_get_games_multiple_years(self, api_client_with_mock_request):
        """Test games retrieval for multiple years"""
        # Mock different responses for different years
        api_client_with_mock_request._make_request.side_effect = [
            {"data": [{"gameID": "game2023"}]},
            {"data": [{"gameID": "game2024"}]},
        ]

        result = api_client_with_mock_request.get_games(years=[2023, 2024])

        # Should combine results from both years
        assert len(result) == 2
        game_ids = [game["gameID"] for game in result]
        assert "game2023" in game_ids
        assert "game2024" in game_ids

    def test_get_games_with_filters(self, api_client_with_mock_request):
        """Test games retrieval with various filters"""
        api_client_with_mock_request._make_request.return_value = {"data": []}

        api_client_with_mock_request.get_games(
            date_range="2024-01-01:2024-12-31",
            game_ids=["game1", "game2"],
            team_ids=["ATL", "BOS"],
            statuses=["Final", "Live"],
            weeks=["Week 1", "Week 2"],
        )

        # Verify parameters
        call_args = api_client_with_mock_request._make_request.call_args
        params = call_args[0][1]

        assert params["date"] == "2024-01-01:2024-12-31"
        assert params["gameIDs"] == "game1,game2"
        assert params["teamIDs"] == "ATL,BOS"
        assert params["statuses"] == "Final,Live"
        assert params["weeks"] == "Week 1,Week 2"

    @patch("ufa_data_manager.datetime")
    def test_get_games_default_current_year(
        self, mock_datetime, api_client_with_mock_request
    ):
        """Test games retrieval defaults to current year"""
        # Mock current year as 2024
        mock_datetime.now.return_value.year = 2024
        api_client_with_mock_request._make_request.return_value = {"data": []}

        api_client_with_mock_request.get_games()

        # Should use current year as default
        call_args = api_client_with_mock_request._make_request.call_args
        params = call_args[0][1]
        assert params["date"] == "2024"


class TestUFADataManager:
    """Test UFADataManager functionality"""

    def test_init(self, data_manager):
        """Test UFADataManager initialization"""
        assert hasattr(data_manager, "api_client")
        assert hasattr(data_manager, "db")
        assert hasattr(data_manager, "stats_processor")


class TestImportFromAPI:
    """Test import_from_api functionality"""

    def test_import_from_api_success(self, data_manager):
        """Test successful API import"""
        # Mock API responses
        data_manager._mock_api_client.get_teams.return_value = [
            {"teamID": "ATL", "name": "Atlanta Hustle"}
        ]
        data_manager._mock_api_client.get_players.return_value = [
            {"playerID": "p1", "firstName": "John", "lastName": "Doe"}
        ]
        data_manager._mock_api_client.get_games.return_value = [
            {"gameID": "g1", "homeTeam": "ATL", "awayTeam": "BOS"}
        ]

        # Mock import methods
        data_manager._import_teams_from_api = Mock(return_value=1)
        data_manager._import_players_from_api = Mock(return_value=1)
        data_manager._import_games_from_api = Mock(return_value=1)

        result = data_manager.import_from_api([2024])

        # Verify results
        assert result["teams"] == 1
        assert result["players"] == 1
        assert result["games"] == 1

        # Verify API calls
        data_manager._mock_api_client.get_teams.assert_called_once_with(years=[2024])
        data_manager._mock_api_client.get_players.assert_called_once_with(years=[2024])
        data_manager._mock_api_client.get_games.assert_called_once_with(years=[2024])

    def test_import_from_api_default_years(self, data_manager):
        """Test API import with default years"""
        # Mock empty responses
        data_manager._mock_api_client.get_teams.return_value = []
        data_manager._mock_api_client.get_players.return_value = []
        data_manager._mock_api_client.get_games.return_value = []

        data_manager._import_teams_from_api = Mock(return_value=0)
        data_manager._import_players_from_api = Mock(return_value=0)
        data_manager._import_games_from_api = Mock(return_value=0)

        result = data_manager.import_from_api()  # No years specified

        # Should use default years (2012-2025 excluding 2020)
        teams_call = data_manager._mock_api_client.get_teams.call_args[1]["years"]
        assert 2012 in teams_call
        assert 2025 in teams_call
        assert 2020 not in teams_call  # COVID year excluded

    def test_import_from_api_clear_existing(self, data_manager):
        """Test API import with clear_existing=True"""
        data_manager._mock_api_client.get_teams.return_value = []
        data_manager._mock_api_client.get_players.return_value = []
        data_manager._mock_api_client.get_games.return_value = []

        data_manager._clear_database = Mock()
        data_manager._import_teams_from_api = Mock(return_value=0)
        data_manager._import_players_from_api = Mock(return_value=0)
        data_manager._import_games_from_api = Mock(return_value=0)

        data_manager.import_from_api([2024], clear_existing=True)

        # Should clear database first
        data_manager._clear_database.assert_called_once()

    def test_import_from_api_no_clear(self, data_manager):
        """Test API import with clear_existing=False"""
        data_manager._mock_api_client.get_teams.return_value = []
        data_manager._mock_api_client.get_players.return_value = []
        data_manager._mock_api_client.get_games.return_value = []

        data_manager._clear_database = Mock()
        data_manager._import_teams_from_api = Mock(return_value=0)
        data_manager._import_players_from_api = Mock(return_value=0)
        data_manager._import_games_from_api = Mock(return_value=0)

        data_manager.import_from_api([2024], clear_existing=False)

        # Should not clear database
        data_manager._clear_database.assert_not_called()

    def test_import_from_api_error_handling(self, data_manager):
        """Test API import error handling"""
        # Mock API error
        data_manager._mock_api_client.get_teams.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            data_manager.import_from_api([2024])


class TestImportHelpers:
    """Test import helper methods"""

    def test_import_teams_from_api(self, data_manager):
        """Test teams import from API data"""
        teams_data = [
            {
                "teamID": "ATL",
                "name": "Atlanta Hustle",
                "city": "Atlanta",
                "abbrev": "ATL",
                "wins": 12,
                "losses": 6,
            }
        ]
        years = [2024]

        result = data_manager._import_teams_from_api(teams_data, years)

        # Should call database execute_query for each team/year combo
        assert data_manager._mock_db.execute_query.call_count >= 1

        # Verify correct data structure
        call_args = data_manager._mock_db.execute_query.call_args_list[0]
        query = call_args[0][0]
        params = call_args[0][1]

        assert "INSERT" in query
        assert "teams" in query
        assert params["team_id"] == "ATL"
        assert params["name"] == "Atlanta Hustle"
        assert params["year"] == 2024

    def test_import_players_from_api(self, data_manager):
        """Test players import from API data"""
        players_data = [
            {
                "playerID": "p1",
                "firstName": "John",
                "lastName": "Doe",
                "fullName": "John Doe",
                "teamID": "ATL",
                "active": True,
                "year": 2024,
                "jerseyNumber": 7,
            }
        ]

        result = data_manager._import_players_from_api(players_data)

        # Should insert player into database
        assert data_manager._mock_db.execute_query.call_count >= 1

        call_args = data_manager._mock_db.execute_query.call_args_list[0]
        query = call_args[0][0]
        params = call_args[0][1]

        assert "INSERT" in query
        assert "players" in query
        assert params["player_id"] == "p1"
        assert params["first_name"] == "John"
        assert params["team_id"] == "ATL"

    def test_import_games_from_api(self, data_manager):
        """Test games import from API data"""
        games_data = [
            {
                "gameID": "g1",
                "homeTeam": "ATL",
                "awayTeam": "BOS",
                "homeScore": 15,
                "awayScore": 12,
                "status": "Final",
                "startTimestamp": "2024-06-15T19:00:00Z",
            }
        ]

        result = data_manager._import_games_from_api(games_data)

        # Should insert game into database
        assert data_manager._mock_db.execute_query.call_count >= 1

        call_args = data_manager._mock_db.execute_query.call_args_list[0]
        query = call_args[0][0]
        params = call_args[0][1]

        assert "INSERT" in query
        assert "games" in query
        assert params["game_id"] == "g1"
        assert params["home_team_id"] == "ATL"
        assert params["away_team_id"] == "BOS"

    def test_import_teams_database_error(self, data_manager):
        """Test teams import with database error"""
        data_manager._mock_db.execute_query.side_effect = Exception("DB Error")

        teams_data = [{"teamID": "ATL", "name": "Test"}]
        result = data_manager._import_teams_from_api(teams_data, [2024])

        # Should handle error gracefully and return 0
        assert result == 0

    def test_clear_database(self, data_manager):
        """Test database clearing"""
        data_manager._clear_database()

        # Should execute DELETE queries for all tables
        delete_calls = [
            call
            for call in data_manager._mock_db.execute_query.call_args_list
            if "DELETE" in str(call[0][0])
        ]

        # Should have multiple DELETE statements
        assert len(delete_calls) > 0

        # Should include main tables
        all_calls = str(data_manager._mock_db.execute_query.call_args_list)
        assert "players" in all_calls
        assert "teams" in all_calls
        assert "games" in all_calls


class TestMainFunction:
    """Test main function and command line interface"""

    @patch("sys.argv", ["ufa_data_manager.py", "import-api"])
    @patch("ufa_data_manager.UFADataManager")
    def test_main_import_api_no_years(self, mock_manager_class):
        """Test main function with import-api command, no years"""
        from ufa_data_manager import main

        mock_manager = Mock()
        mock_manager.import_from_api.return_value = {
            "teams": 5,
            "players": 100,
            "games": 50,
        }
        mock_manager_class.return_value = mock_manager

        main()

        # Should call import_from_api with None (default years)
        mock_manager.import_from_api.assert_called_once_with(None)

    @patch("sys.argv", ["ufa_data_manager.py", "import-api", "2023", "2024"])
    @patch("ufa_data_manager.UFADataManager")
    def test_main_import_api_with_years(self, mock_manager_class):
        """Test main function with specific years"""
        from ufa_data_manager import main

        mock_manager = Mock()
        mock_manager.import_from_api.return_value = {
            "teams": 2,
            "players": 50,
            "games": 25,
        }
        mock_manager_class.return_value = mock_manager

        main()

        # Should call import_from_api with specified years
        mock_manager.import_from_api.assert_called_once_with([2023, 2024])

    @patch("sys.argv", ["ufa_data_manager.py"])
    def test_main_no_command(self):
        """Test main function with no command"""
        from ufa_data_manager import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("sys.argv", ["ufa_data_manager.py", "unknown-command"])
    def test_main_unknown_command(self):
        """Test main function with unknown command"""
        from ufa_data_manager import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("sys.argv", ["ufa_data_manager.py", "import-api", "invalid-year"])
    def test_main_invalid_year(self):
        """Test main function with invalid year argument"""
        from ufa_data_manager import main

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("sys.argv", ["ufa_data_manager.py", "import-api"])
    @patch("ufa_data_manager.UFADataManager")
    def test_main_operation_error(self, mock_manager_class):
        """Test main function with operation error"""
        from ufa_data_manager import main

        mock_manager = Mock()
        mock_manager.import_from_api.side_effect = Exception("Operation failed")
        mock_manager_class.return_value = mock_manager

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1


class TestIntegration:
    """Integration tests with real-like data"""

    def test_full_import_workflow(self, data_manager):
        """Test complete import workflow"""
        # Mock realistic API responses
        data_manager._mock_api_client.get_teams.return_value = [
            {
                "teamID": "ATL",
                "name": "Atlanta Hustle",
                "city": "Atlanta",
                "abbrev": "ATL",
                "wins": 12,
                "losses": 6,
                "divisionID": "south",
                "divisionName": "South",
            }
        ]

        data_manager._mock_api_client.get_players.return_value = [
            {
                "playerID": "johndoe",
                "firstName": "John",
                "lastName": "Doe",
                "fullName": "John Doe",
                "teamID": "ATL",
                "active": True,
                "year": 2024,
                "jerseyNumber": 7,
            }
        ]

        data_manager._mock_api_client.get_games.return_value = [
            {
                "gameID": "atl-vs-bos-2024-06-15",
                "homeTeam": "ATL",
                "awayTeam": "BOS",
                "homeScore": 15,
                "awayScore": 12,
                "status": "Final",
                "startTimestamp": "2024-06-15T19:00:00Z",
            }
        ]

        # Execute import
        result = data_manager.import_from_api([2024])

        # Verify all components were called
        assert result["teams"] >= 0
        assert result["players"] >= 0
        assert result["games"] >= 0

        # Verify database operations occurred
        assert data_manager._mock_db.execute_query.call_count >= 3

    def test_error_recovery(self, data_manager):
        """Test error recovery during import"""
        # First API call fails, others succeed
        data_manager._mock_api_client.get_teams.side_effect = Exception(
            "Teams API failed"
        )
        data_manager._mock_api_client.get_players.return_value = []
        data_manager._mock_api_client.get_games.return_value = []

        # Should raise exception and not continue
        with pytest.raises(Exception, match="Teams API failed"):
            data_manager.import_from_api([2024])

    def test_partial_data_handling(self, data_manager):
        """Test handling of incomplete/partial data"""
        # API returns partial data
        data_manager._mock_api_client.get_teams.return_value = [
            {"teamID": "ATL", "name": "Atlanta"}  # Missing some fields
        ]
        data_manager._mock_api_client.get_players.return_value = [
            {"playerID": "p1", "firstName": "John"}  # Missing lastName
        ]
        data_manager._mock_api_client.get_games.return_value = []

        # Should handle gracefully
        result = data_manager.import_from_api([2024])

        # Should still return counts (even if 0 due to validation errors)
        assert isinstance(result["teams"], int)
        assert isinstance(result["players"], int)
        assert isinstance(result["games"], int)
