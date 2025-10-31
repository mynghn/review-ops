"""Pytest configuration and shared fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from models import Config, PullRequest, TeamMember


@pytest.fixture
def sample_config() -> Config:
    """Provide a sample Config object for testing."""
    return Config(
        github_token="ghp_test_token_1234567890",
        github_org="test-org",
        slack_webhook_url="https://hooks.slack.com/services/T00/B00/XXXX",
        log_level="DEBUG",
        api_timeout=30,
    )


@pytest.fixture
def sample_team_members() -> list[TeamMember]:
    """Provide sample team members for testing."""
    return [
        TeamMember(github_username="alice", slack_user_id="U1234567890"),
        TeamMember(github_username="bob"),
        TeamMember(github_username="charlie-dev", slack_user_id="U0987654321"),
    ]


@pytest.fixture
def sample_pr() -> PullRequest:
    """Provide a sample PullRequest for testing."""
    return PullRequest(
        repo_name="review-ops",
        number=123,
        title="Add staleness calculation",
        author="alice",
        reviewers=["bob", "charlie-dev"],
        url="https://github.com/test-org/review-ops/pull/123",
        created_at=datetime(2025, 10, 25, 10, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 10, 25, 10, 0, 0, tzinfo=UTC),
        current_approvals=0,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )


@pytest.fixture
def sample_pr_with_approvals() -> PullRequest:
    """Provide a sample PullRequest with sufficient approvals."""
    return PullRequest(
        repo_name="review-ops",
        number=124,
        title="Update documentation",
        author="bob",
        reviewers=["alice", "charlie-dev"],
        url="https://github.com/test-org/review-ops/pull/124",
        created_at=datetime(2025, 10, 20, 10, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 10, 20, 10, 0, 0, tzinfo=UTC),
        current_approvals=2,
        review_status="APPROVED",
        base_branch="main",
    )


@pytest.fixture
def sample_draft_pr() -> PullRequest:
    """Provide a sample draft PullRequest."""
    return PullRequest(
        repo_name="review-ops",
        number=125,
        title="WIP: Refactor config loading",
        author="charlie-dev",
        reviewers=[],
        url="https://github.com/test-org/review-ops/pull/125",
        created_at=datetime(2025, 10, 28, 10, 0, 0, tzinfo=UTC),
        ready_at=None,  # Draft PR
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def team_members_json_path(fixtures_dir: Path) -> Path:
    """Return the path to the valid team members JSON file."""
    return fixtures_dir / "team_members_valid.json"


@pytest.fixture
def github_pr_response_path(fixtures_dir: Path) -> Path:
    """Return the path to the GitHub PR response fixture."""
    return fixtures_dir / "github_pr_response.json"


@pytest.fixture
def github_reviews_response_path(fixtures_dir: Path) -> Path:
    """Return the path to the GitHub reviews response fixture."""
    return fixtures_dir / "github_reviews_response.json"
