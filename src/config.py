"""Configuration loading and validation."""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

from models import Config, TeamMember


def load_config() -> Config:
    """
    Load and validate configuration from environment variables.

    Loads from .env file if present, then reads required environment variables.

    Returns:
        Config object with validated configuration values

    Raises:
        ValueError: If required environment variables are missing or invalid
    """
    # Load .env file if it exists
    load_dotenv()

    # Required variables
    github_token = os.getenv("GH_TOKEN")
    if not github_token:
        msg = (
            "GH_TOKEN is required. "
            "Create a GitHub Personal Access Token with 'repo' and 'read:org' scopes "
            "and set it in your .env file."
        )
        raise ValueError(msg)

    github_org = os.getenv("GITHUB_ORG")
    if not github_org:
        msg = (
            "GITHUB_ORG is required. "
            "Set the name of your GitHub organization in your .env file."
        )
        raise ValueError(msg)

    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not slack_webhook_url:
        msg = (
            "SLACK_WEBHOOK_URL is required. "
            "Create a Slack incoming webhook and set the URL in your .env file. "
            "(Or use --dry-run to skip Slack sending)"
        )
        raise ValueError(msg)

    # Validate Slack webhook URL format
    if not slack_webhook_url.startswith("https://hooks.slack.com/"):
        msg = (
            "SLACK_WEBHOOK_URL must be a valid Slack webhook URL "
            "(should start with 'https://hooks.slack.com/')."
        )
        raise ValueError(msg)

    # Optional variables with defaults
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        msg = (
            f"Invalid LOG_LEVEL '{log_level}'. "
            "Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
        )
        raise ValueError(msg)

    api_timeout_str = os.getenv("API_TIMEOUT", "30")
    try:
        api_timeout = int(api_timeout_str)
        if api_timeout <= 0:
            msg = "API_TIMEOUT must be a positive integer"
            raise ValueError(msg)
    except ValueError as e:
        msg = f"Invalid API_TIMEOUT '{api_timeout_str}'. Must be a positive integer."
        raise ValueError(msg) from e

    # Check for gh CLI availability
    _check_gh_cli_available()

    return Config(
        github_token=github_token,
        github_org=github_org,
        slack_webhook_url=slack_webhook_url,
        log_level=log_level,
        api_timeout=api_timeout,
    )


def _check_gh_cli_available() -> None:
    """
    Check if gh CLI is available and warn if not found.

    The application will fall back gracefully if gh CLI is unavailable,
    but review decision accuracy may be reduced.
    """
    if not shutil.which("gh"):
        logger = logging.getLogger(__name__)
        logger.warning(
            "gh CLI not found. Install with 'brew install gh' (macOS) or see https://cli.github.com/. "
            "Application will continue but review decision accuracy may be reduced."
        )


def load_team_members(file_path: str = "team_members.json") -> list[TeamMember]:
    """
    Load team members from JSON configuration file.

    Args:
        file_path: Path to the team members JSON file (default: team_members.json)

    Returns:
        List of TeamMember objects

    Raises:
        FileNotFoundError: If the team members file does not exist
        ValueError: If the file format is invalid or required fields are missing
        json.JSONDecodeError: If the file is not valid JSON
    """
    path = Path(file_path)
    if not path.exists():
        msg = (
            f"Team members file not found: {file_path}\n"
            f"Create this file based on team_members.json.example"
        )
        raise FileNotFoundError(msg)

    try:
        with path.open("r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in {file_path}: {e}"
        raise ValueError(msg) from e

    if not isinstance(data, list):
        msg = f"Team members file must contain a JSON array, got {type(data).__name__}"
        raise ValueError(msg)

    if not data:
        msg = "Team members file must contain at least one team member"
        raise ValueError(msg)

    team_members = []
    for idx, member_data in enumerate(data):
        if not isinstance(member_data, dict):
            msg = f"Team member at index {idx} must be an object, got {type(member_data).__name__}"
            raise ValueError(msg)

        if "github_username" not in member_data:
            msg = f"Team member at index {idx} is missing required field 'github_username'"
            raise ValueError(msg)

        github_username = member_data["github_username"]
        if not isinstance(github_username, str) or not github_username.strip():
            msg = (
                f"Team member at index {idx} has invalid 'github_username': "
                "must be a non-empty string"
            )
            raise ValueError(msg)

        slack_user_id = member_data.get("slack_id")
        if slack_user_id is not None and (
            not isinstance(slack_user_id, str) or not slack_user_id.strip()
        ):
            msg = (
                f"Team member at index {idx} has invalid 'slack_id': "
                "must be a non-empty string or omitted"
            )
            raise ValueError(msg)

        team_members.append(
            TeamMember(
                github_username=github_username.strip(),
                slack_user_id=slack_user_id.strip() if slack_user_id else None,
            )
        )

    return team_members
