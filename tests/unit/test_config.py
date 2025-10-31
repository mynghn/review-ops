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
                    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/XXX",
                },
                clear=True,
            ),
        ):
            config = load_config()
            assert config.github_token == "ghp_test123"
            assert config.github_org == "test-org"
            assert config.slack_webhook_url == "https://hooks.slack.com/services/T00/B00/XXX"
            assert config.log_level == "INFO"  # Default
            assert config.api_timeout == 30  # Default
            assert config.gh_search_limit == 1000  # Default

    def test_load_config_with_optional_vars(self):
        """Test config loading with optional variables set."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/XXX",
                    "LOG_LEVEL": "DEBUG",
                    "API_TIMEOUT": "60",
                    "GH_SEARCH_LIMIT": "2000",
                },
                clear=True,
            ),
        ):
            config = load_config()
            assert config.log_level == "DEBUG"
            assert config.api_timeout == 60
            assert config.gh_search_limit == 2000

    def test_load_config_missing_github_token(self):
        """Test error when GH_TOKEN is missing."""
        with (
            patch("config.load_dotenv"),
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GITHUB_ORG": "test-org",
                    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/XXX",
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
                    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/XXX",
                },
                clear=True,
            ),
            pytest.raises(ValueError, match="GITHUB_ORG is required"),
        ):
            load_config()

    def test_load_config_missing_slack_webhook(self):
        """Test error when SLACK_WEBHOOK_URL is missing."""
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
            pytest.raises(ValueError, match="SLACK_WEBHOOK_URL is required"),
        ):
            load_config()

    def test_load_config_invalid_slack_webhook(self):
        """Test error when SLACK_WEBHOOK_URL format is invalid."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_WEBHOOK_URL": "https://invalid.com/webhook",
                },
                clear=True,
            ),
            pytest.raises(ValueError, match="must be a valid Slack webhook URL"),
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
                    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/XXX",
                    "LOG_LEVEL": "INVALID",
                },
                clear=True,
            ),
            pytest.raises(ValueError, match="Invalid LOG_LEVEL"),
        ):
            load_config()

    def test_load_config_invalid_api_timeout(self):
        """Test error when API_TIMEOUT is not a valid integer."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/XXX",
                    "API_TIMEOUT": "invalid",
                },
                clear=True,
            ),
            pytest.raises(ValueError, match="Invalid API_TIMEOUT"),
        ):
            load_config()

    def test_load_config_negative_api_timeout(self):
        """Test error when API_TIMEOUT is negative."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/XXX",
                "API_TIMEOUT": "-10",
            },
            clear=True,
            ),
            pytest.raises(ValueError, match="Must be a positive integer"),
        ):
            load_config()

    def test_load_config_default_language(self):
        """Test that LANGUAGE defaults to 'en' when not set."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/gh"),
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_test123",
                    "GITHUB_ORG": "test-org",
                    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/XXX",
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
                    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/XXX",
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
                    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/XXX",
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
                    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/XXX",
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
                    "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/T00/B00/XXX",
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
