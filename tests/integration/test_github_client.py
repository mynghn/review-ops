"""Integration tests for GitHub client with mocked API responses."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from github import GithubException

from github_client import GitHubClient


@pytest.fixture
def github_client():
    """Create a GitHub client instance."""
    return GitHubClient(token="test_token")


def test_github_client_initialization():
    """Test GitHub client can be initialized with a token."""
    client = GitHubClient(token="test_token_123")
    assert client is not None


@pytest.fixture
def mock_github_org():
    """Create a mock GitHub organization."""
    org = Mock()
    return org


@pytest.fixture
def mock_github_repo():
    """Create a mock GitHub repository."""
    repo = Mock()
    repo.name = "test-repo"
    repo.full_name = "test-org/test-repo"
    return repo


@pytest.fixture
def mock_github_pr():
    """Create a mock GitHub pull request."""
    pr = Mock()
    pr.number = 123
    pr.title = "Test PR"
    pr.user = Mock()
    pr.user.login = "alice"
    pr.html_url = "https://github.com/test-org/test-repo/pull/123"
    pr.created_at = datetime(2025, 10, 25, 10, 0, 0, tzinfo=UTC)
    pr.draft = False
    pr.base = Mock()
    pr.base.ref = "main"

    # Mock requested_reviewers
    reviewer = Mock()
    reviewer.login = "bob"
    pr.requested_reviewers = [reviewer]

    return pr
