"""Unit tests for configuration loading."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from config import load_config, load_team_members


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_success(self):
        """Test successful config loading with all required variables."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                },
                clear=True,
            ),
        ):
            config = load_config()
            assert config.github_token == "ghp_test123"
            assert config.github_org == "test-org"
            assert config.slack_bot_token == "xoxb-test-token"
            assert config.log_level == "INFO"  # Default

    def test_load_config_with_optional_vars(self):
        """Test config loading with optional variables set."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                    "LOG_LEVEL": "DEBUG",
                    "GH_SEARCH_WINDOW_SIZE": "60",
                },
                clear=True,
            ),
        ):
            config = load_config()
            assert config.log_level == "DEBUG"
            assert config.gh_search_window_size == 60

    def test_load_config_missing_github_token(self):
        """Test error when GH_TOKEN is missing."""
        with (
            patch("config.load_dotenv"),
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                },
                clear=True,
            ),
            pytest.raises(ValueError, match="GH_TOKEN is required"),
        ):
            load_config()

    def test_load_config_missing_github_org(self):
        """Test error when GITHUB_ORG is missing."""
        with (
            patch("config.load_dotenv"),
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                },
                clear=True,
            ),
            pytest.raises(ValueError, match="GITHUB_ORG is required"),
        ):
            load_config()

    def test_load_config_missing_slack_webhook(self):
        """Test error when SLACK_BOT_TOKEN is missing."""
        with (
            patch("config.load_dotenv"),
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                },
                clear=True,
            ),
            pytest.raises(ValueError, match="SLACK_BOT_TOKEN is required"),
        ):
            load_config()

    def test_load_config_invalid_slack_webhook(self):
        """Test error when SLACK_BOT_TOKEN format is invalid."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "https://invalid.com/webhook",
                    "SLACK_CHANNEL_ID": "C1234567890",
                },
                clear=True,
            ),
            pytest.raises(ValueError, match="must be a valid Bot User OAuth Token"),
        ):
            load_config()

    def test_load_config_invalid_log_level(self):
        """Test error when LOG_LEVEL is invalid."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                    "LOG_LEVEL": "INVALID",
                },
                clear=True,
            ),
            pytest.raises(ValueError, match="Invalid LOG_LEVEL"),
        ):
            load_config()

    def test_load_config_default_language(self):
        """Test that LANGUAGE defaults to 'en' when not set."""
        with (
            patch("config.load_dotenv"),
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                },
                clear=True,
            ),
        ):
            config = load_config()
            assert config.language == "en"

    def test_load_config_valid_language_en(self):
        """Test successful config loading with LANGUAGE='en'."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                    "LANGUAGE": "en",
                },
                clear=True,
            ),
        ):
            config = load_config()
            assert config.language == "en"

    def test_load_config_valid_language_ko(self):
        """Test successful config loading with LANGUAGE='ko'."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                    "LANGUAGE": "ko",
                },
                clear=True,
            ),
        ):
            config = load_config()
            assert config.language == "ko"

    def test_load_config_language_case_insensitive(self):
        """Test that LANGUAGE is case-insensitive."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                    "LANGUAGE": "EN",
                },
                clear=True,
            ),
        ):
            config = load_config()
            assert config.language == "en"

    def test_load_config_invalid_language(self):
        """Test error when LANGUAGE is invalid."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                    "LANGUAGE": "fr",
                },
                clear=True,
            ),
            pytest.raises(ValueError, match="Invalid LANGUAGE"),
        ):
            load_config()


class TestLoadTeamMembers:
    """Tests for load_team_members function."""

    def test_load_team_members_success(self, tmp_path: Path):
        """Test successful team members loading."""
        team_file = tmp_path / "team.json"
        team_file.write_text(
            json.dumps(
                [
                    {"github_username": "alice", "slack_id": "U1234567890"},
                    {"github_username": "bob"},
                    {"github_username": "charlie", "slack_id": "U0987654321"},
                ]
            )
        )

        members = load_team_members(str(team_file))
        assert len(members) == 3
        assert members[0].github_username == "alice"
        assert members[0].slack_user_id == "U1234567890"
        assert members[1].github_username == "bob"
        assert members[1].slack_user_id is None
        assert members[2].github_username == "charlie"
        assert members[2].slack_user_id == "U0987654321"

    def test_load_team_members_file_not_found(self):
        """Test error when team members file does not exist."""
        with pytest.raises(FileNotFoundError, match="Team members file not found"):
            load_team_members("nonexistent.json")

    def test_load_team_members_invalid_json(self, tmp_path: Path):
        """Test error when file contains invalid JSON."""
        team_file = tmp_path / "team.json"
        team_file.write_text("{ invalid json }")

        with pytest.raises(ValueError, match="Invalid JSON"):
            load_team_members(str(team_file))

    def test_load_team_members_not_array(self, tmp_path: Path):
        """Test error when JSON is not an array."""
        team_file = tmp_path / "team.json"
        team_file.write_text(json.dumps({"github_username": "alice"}))

        with pytest.raises(ValueError, match="must contain a JSON array"):
            load_team_members(str(team_file))

    def test_load_team_members_empty_array(self, tmp_path: Path):
        """Test error when array is empty."""
        team_file = tmp_path / "team.json"
        team_file.write_text(json.dumps([]))

        with pytest.raises(ValueError, match="must contain at least one team member"):
            load_team_members(str(team_file))

    def test_load_team_members_missing_github_username(self, tmp_path: Path):
        """Test error when github_username is missing."""
        team_file = tmp_path / "team.json"
        team_file.write_text(json.dumps([{"slack_id": "U1234567890"}]))

        with pytest.raises(ValueError, match="missing required field 'github_username'"):
            load_team_members(str(team_file))

    def test_load_team_members_invalid_github_username(self, tmp_path: Path):
        """Test error when github_username is invalid (empty string)."""
        team_file = tmp_path / "team.json"
        team_file.write_text(json.dumps([{"github_username": "   "}]))

        with pytest.raises(ValueError, match="invalid 'github_username'"):
            load_team_members(str(team_file))

    def test_load_team_members_invalid_slack_id(self, tmp_path: Path):
        """Test error when slack_id is invalid (empty string)."""
        team_file = tmp_path / "team.json"
        team_file.write_text(json.dumps([{"github_username": "alice", "slack_id": "   "}]))

        with pytest.raises(ValueError, match="invalid 'slack_id'"):
            load_team_members(str(team_file))

    def test_load_team_members_strips_whitespace(self, tmp_path: Path):
        """Test that whitespace is stripped from usernames and IDs."""
        team_file = tmp_path / "team.json"
        team_file.write_text(
            json.dumps(
                [
                    {"github_username": "  alice  ", "slack_id": "  U1234567890  "},
                ]
            )
        )

        members = load_team_members(str(team_file))
        assert members[0].github_username == "alice"
        assert members[0].slack_user_id == "U1234567890"


class TestRateLimitConfigValidation:
    """Tests for rate limit configuration validation."""

    def test_max_prs_total_valid_minimum(self):
        """Test MAX_PRS_TOTAL at minimum valid value (10)."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                    "MAX_PRS_TOTAL": "10",
                },
                clear=True,
            ),
        ):
            config = load_config()
            assert config.max_prs_total == 10

    def test_max_prs_total_valid_maximum(self):
        """Test MAX_PRS_TOTAL at maximum valid value (100)."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                    "MAX_PRS_TOTAL": "100",
                },
                clear=True,
            ),
        ):
            config = load_config()
            assert config.max_prs_total == 100

    def test_max_prs_total_below_minimum(self):
        """Test MAX_PRS_TOTAL below minimum (9) raises error."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                    "MAX_PRS_TOTAL": "9",
                },
                clear=True,
            ),pytest.raises(ValueError, match="Invalid MAX_PRS_TOTAL.*Must be between 10 and 100")
        ):
            load_config()

    def test_max_prs_total_above_maximum(self):
        """Test MAX_PRS_TOTAL above maximum (101) raises error."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                    "MAX_PRS_TOTAL": "101",
                },
                clear=True,
            ),pytest.raises(ValueError, match="Invalid MAX_PRS_TOTAL.*Must be between 10 and 100")
        ):
            load_config()

    def test_rate_limit_wait_threshold_valid_boundaries(self):
        """Test RATE_LIMIT_WAIT_THRESHOLD at boundaries (60, 600)."""
        for value in [60, 300, 600]:
            with (
                patch("shutil.which", return_value="/usr/local/bin/gh"),
                patch.dict(
                    os.environ,
                    {
                        "GH_TOKEN": "ghp_test123",
                        "GITHUB_ORG": "test-org",
                        "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                        "RATE_LIMIT_WAIT_THRESHOLD": str(value),
                    },
                    clear=True,
                ),
            ):
                config = load_config()
                assert config.rate_limit_wait_threshold == value

    def test_rate_limit_wait_threshold_below_minimum(self):
        """Test RATE_LIMIT_WAIT_THRESHOLD below minimum (59) raises error."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                    "RATE_LIMIT_WAIT_THRESHOLD": "59",
                },
                clear=True,
            ),
        ):
            with pytest.raises(ValueError, match="Invalid RATE_LIMIT_WAIT_THRESHOLD.*Must be between 60 and 600"):
                load_config()

    def test_rate_limit_wait_threshold_above_maximum(self):
        """Test RATE_LIMIT_WAIT_THRESHOLD above maximum (601) raises error."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                    "RATE_LIMIT_WAIT_THRESHOLD": "601",
                },
                clear=True,
            ),
        ):
            with pytest.raises(ValueError, match="Invalid RATE_LIMIT_WAIT_THRESHOLD.*Must be between 60 and 600"):
                load_config()

    def test_all_rate_limit_configs_together(self):
        """Test all rate limit configs can be set together."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "SLACK_CHANNEL_ID": "C1234567890",
                    "MAX_PRS_TOTAL": "50",
                    "RATE_LIMIT_WAIT_THRESHOLD": "600",
                },
                clear=True,
            ),
        ):
            config = load_config()
            assert config.max_prs_total == 50
            assert config.rate_limit_wait_threshold == 600


class TestTeamSizeValidation:
    """Tests for team size validation (max 15 members)."""

    def test_team_size_at_maximum(self, tmp_path: Path):
        """Test team with exactly 15 members is valid."""
        team_file = tmp_path / "team.json"
        members = [{"github_username": f"user{i}"} for i in range(15)]
        team_file.write_text(json.dumps(members))

        result = load_team_members(str(team_file))
        assert len(result) == 15

    def test_team_size_exceeds_maximum(self, tmp_path: Path):
        """Test team with 16 members raises error."""
        team_file = tmp_path / "team.json"
        members = [{"github_username": f"user{i}"} for i in range(16)]
        team_file.write_text(json.dumps(members))

        with pytest.raises(ValueError, match="Team has 16 members.*exceeds.*limit of 15"):
            load_team_members(str(team_file))

    def test_team_size_well_over_maximum(self, tmp_path: Path):
        """Test team with 20 members raises error."""
        team_file = tmp_path / "team.json"
        members = [{"github_username": f"user{i}"} for i in range(20)]
        team_file.write_text(json.dumps(members))

        with pytest.raises(ValueError, match="Team has 20 members.*exceeds.*limit of 15"):
            load_team_members(str(team_file))
