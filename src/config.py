"""Configuration loading and validation."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

from models import Config, TeamMember

# Supported languages for Slack message formatting
SUPPORTED_LANGUAGES = {"en", "ko"}


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

    gh_search_limit_str = os.getenv("GH_SEARCH_LIMIT", "1000")
    try:
        gh_search_limit = int(gh_search_limit_str)
        if gh_search_limit <= 0:
            msg = "GH_SEARCH_LIMIT must be a positive integer"
            raise ValueError(msg)
    except ValueError as e:
        msg = f"Invalid GH_SEARCH_LIMIT '{gh_search_limit_str}'. Must be a positive integer."
        raise ValueError(msg) from e

    language = os.getenv("LANGUAGE", "en").lower()
    if language not in SUPPORTED_LANGUAGES:
        msg = (
            f"Invalid LANGUAGE '{language}'. "
            f"Must be one of: {', '.join(sorted(SUPPORTED_LANGUAGES))}"
        )
        raise ValueError(msg)

    # Rate limiting configuration
    max_prs_total_str = os.getenv("MAX_PRS_TOTAL", "30")
    try:
        max_prs_total = int(max_prs_total_str)
        if not 10 <= max_prs_total <= 100:
            msg = "MAX_PRS_TOTAL must be between 10 and 100"
            raise ValueError(msg)
    except ValueError as e:
        msg = f"Invalid MAX_PRS_TOTAL '{max_prs_total_str}'. Must be between 10 and 100."
        raise ValueError(msg) from e

    max_retries_str = os.getenv("MAX_RETRIES", "3")
    try:
        max_retries = int(max_retries_str)
        if not 1 <= max_retries <= 5:
            msg = "MAX_RETRIES must be between 1 and 5"
            raise ValueError(msg)
    except ValueError as e:
        msg = f"Invalid MAX_RETRIES '{max_retries_str}'. Must be between 1 and 5."
        raise ValueError(msg) from e

    rate_limit_wait_threshold_str = os.getenv("RATE_LIMIT_WAIT_THRESHOLD", "300")
    try:
        rate_limit_wait_threshold = int(rate_limit_wait_threshold_str)
        if not 60 <= rate_limit_wait_threshold <= 600:
            msg = "RATE_LIMIT_WAIT_THRESHOLD must be between 60 and 600"
            raise ValueError(msg)
    except ValueError as e:
        msg = (
            f"Invalid RATE_LIMIT_WAIT_THRESHOLD '{rate_limit_wait_threshold_str}'. "
            "Must be between 60 and 600."
        )
        raise ValueError(msg) from e

    retry_backoff_base_str = os.getenv("RETRY_BACKOFF_BASE", "1.0")
    try:
        retry_backoff_base = float(retry_backoff_base_str)
        if not 0.5 <= retry_backoff_base <= 2.0:
            msg = "RETRY_BACKOFF_BASE must be between 0.5 and 2.0"
            raise ValueError(msg)
    except ValueError as e:
        msg = f"Invalid RETRY_BACKOFF_BASE '{retry_backoff_base_str}'. Must be between 0.5 and 2.0."
        raise ValueError(msg) from e

    use_graphql_batch_str = os.getenv("USE_GRAPHQL_BATCH", "true").lower()
    use_graphql_batch = use_graphql_batch_str in {"true", "1", "yes", "on"}

    # API call delay to prevent secondary rate limits (in seconds)
    api_call_delay_str = os.getenv("API_CALL_DELAY", "2.0")
    try:
        api_call_delay = float(api_call_delay_str)
        if not 0.0 <= api_call_delay <= 10.0:
            msg = "API_CALL_DELAY must be between 0.0 and 10.0"
            raise ValueError(msg)
    except ValueError as e:
        msg = f"Invalid API_CALL_DELAY '{api_call_delay_str}'. Must be between 0.0 and 10.0."
        raise ValueError(msg) from e

    # Check for gh CLI availability
    _check_gh_cli_available()

    return Config(
        github_token=github_token,
        github_org=github_org,
        slack_webhook_url=slack_webhook_url,
        log_level=log_level,
        api_timeout=api_timeout,
        gh_search_limit=gh_search_limit,
        language=language,
        max_prs_total=max_prs_total,
        max_retries=max_retries,
        rate_limit_wait_threshold=rate_limit_wait_threshold,
        retry_backoff_base=retry_backoff_base,
        use_graphql_batch=use_graphql_batch,
        api_call_delay=api_call_delay,
    )


def _check_gh_cli_available() -> None:
    """
    Check if gh CLI is available and raise error if not found.

    The application requires gh CLI for efficient PR searching and fetching.
    Without it, the application cannot function properly.

    Raises:
        ValueError: If gh CLI is not installed
    """
    if not shutil.which("gh"):
        import platform

        system = platform.system()
        install_cmd = {
            "Darwin": "brew install gh",
            "Linux": "See https://github.com/cli/cli/blob/trunk/docs/install_linux.md",
            "Windows": (
                "See https://github.com/cli/cli#installation "
                "or use: winget install GitHub.cli"
            )
        }.get(system, "See https://cli.github.com/")

        msg = (
            "GitHub CLI (gh) is not installed, which is required for this application.\n\n"
            f"Installation for {system}:\n"
            f"  {install_cmd}\n\n"
            "After installing, authenticate with:\n"
            "  gh auth login\n\n"
            "Or set your token:\n"
            "  gh auth login --with-token < your-token-file"
        )
        raise ValueError(msg)


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

    # Validate team size (FR-017)
    if len(data) > 15:
        msg = (
            f"Team has {len(data)} members, which exceeds the recommended limit of 15. "
            "Large teams may experience GitHub API rate limit issues. "
            "Consider splitting into multiple runs or increasing MAX_PRS_TOTAL."
        )
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
