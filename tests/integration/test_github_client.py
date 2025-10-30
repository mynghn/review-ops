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


def test_fetch_organization_repos(github_client, mock_github_org, mock_github_repo):
    """Test fetching repositories from an organization."""
    with patch.object(github_client.client, "get_organization") as mock_get_org:
        mock_get_org.return_value = mock_github_org
        mock_github_org.get_repos.return_value = [mock_github_repo]

        repos = github_client.fetch_organization_repos("test-org")

        assert len(repos) == 1
        assert repos[0].name == "test-repo"
        mock_get_org.assert_called_once_with("test-org")


def test_fetch_open_prs(github_client, mock_github_repo, mock_github_pr):
    """Test fetching open pull requests from a repository."""
    mock_github_repo.get_pulls.return_value = [mock_github_pr]

    with (
        patch.object(github_client, "get_review_status", return_value="REVIEW_REQUIRED"),
        patch.object(github_client, "count_current_approvals", return_value=0),
    ):
        prs = github_client.fetch_open_prs(mock_github_repo)

    assert len(prs) == 1
    assert prs[0].number == 123
    assert prs[0].title == "Test PR"
    assert prs[0].author == "alice"
    mock_github_repo.get_pulls.assert_called_once_with(state="open", sort="created")


def test_fetch_open_prs_filters_drafts(github_client, mock_github_repo):
    """Test that draft PRs are filtered out."""
    draft_pr = Mock()
    draft_pr.draft = True

    ready_pr = Mock()
    ready_pr.number = 124
    ready_pr.title = "Ready PR"
    ready_pr.user = Mock()
    ready_pr.user.login = "bob"
    ready_pr.html_url = "https://github.com/test-org/test-repo/pull/124"
    ready_pr.created_at = datetime(2025, 10, 26, 10, 0, 0, tzinfo=UTC)
    ready_pr.draft = False
    ready_pr.base = Mock()
    ready_pr.base.ref = "main"
    ready_pr.requested_reviewers = []

    mock_github_repo.get_pulls.return_value = [draft_pr, ready_pr]

    with (
        patch.object(github_client, "get_review_status", return_value="REVIEW_REQUIRED"),
        patch.object(github_client, "count_current_approvals", return_value=0),
    ):
        prs = github_client.fetch_open_prs(mock_github_repo)

    # Only ready PR should be returned
    assert len(prs) == 1
    assert prs[0].number == 124


def test_get_review_status_approved(github_client, mock_github_repo):
    """Test getting review status when PR is approved."""
    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.stdout = '{"reviewDecision": "APPROVED"}'
        mock_run.return_value = mock_result

        status = github_client.get_review_status("test-org/test-repo", 123)

        assert status == "APPROVED"


def test_get_review_status_review_required(github_client, mock_github_repo):
    """Test getting review status when review is required."""
    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.stdout = '{"reviewDecision": "REVIEW_REQUIRED"}'
        mock_run.return_value = mock_result

        status = github_client.get_review_status("test-org/test-repo", 123)

        assert status == "REVIEW_REQUIRED"


def test_count_current_approvals(github_client, mock_github_pr):
    """Test counting current approvals from reviews."""
    # Mock reviews
    review1 = Mock()
    review1.user = Mock()
    review1.user.login = "bob"
    review1.state = "APPROVED"
    review1.submitted_at = datetime(2025, 10, 26, 10, 0, 0, tzinfo=UTC)

    review2 = Mock()
    review2.user = Mock()
    review2.user.login = "charlie"
    review2.state = "APPROVED"
    review2.submitted_at = datetime(2025, 10, 26, 11, 0, 0, tzinfo=UTC)

    mock_github_pr.get_reviews.return_value = [review1, review2]

    count = github_client.count_current_approvals(mock_github_pr)

    assert count == 2


def test_count_current_approvals_only_latest_review_per_user(github_client, mock_github_pr):
    """Test that only the latest review per user is counted."""
    # Bob approved, then requested changes
    review1 = Mock()
    review1.user = Mock()
    review1.user.login = "bob"
    review1.state = "APPROVED"
    review1.submitted_at = datetime(2025, 10, 26, 10, 0, 0, tzinfo=UTC)

    review2 = Mock()
    review2.user = Mock()
    review2.user.login = "bob"
    review2.state = "CHANGES_REQUESTED"
    review2.submitted_at = datetime(2025, 10, 26, 11, 0, 0, tzinfo=UTC)

    mock_github_pr.get_reviews.return_value = [review1, review2]

    count = github_client.count_current_approvals(mock_github_pr)

    # Bob's latest review is CHANGES_REQUESTED, so count should be 0
    assert count == 0
