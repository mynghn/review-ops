"""Integration tests for GitHub client with mocked API responses."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

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


@patch("github_client.subprocess.run")
def test_fetch_team_prs_includes_team_reviewer(mock_run, github_client):
    """Test that PRs with current team reviewers are included."""
    team_usernames = {"alice", "bob"}
    org_name = "test-org"
    updated_after = date.today() - timedelta(days=7)

    # Mock rate limit check
    rate_limit_result = Mock()
    rate_limit_result.returncode = 0
    rate_limit_result.stdout = json.dumps({
        "remaining": 5000,
        "limit": 5000,
        "reset": 1635724800
    })

    # Mock search results
    empty_search_result = Mock()
    empty_search_result.returncode = 0
    empty_search_result.stdout = json.dumps([])

    pr_search_result = Mock()
    pr_search_result.returncode = 0
    pr_search_result.stdout = json.dumps([
        {
            "number": 789,
            "url": "https://github.com/test-org/test-repo/pull/789",
            "repository": {"nameWithOwner": "test-org/test-repo"}
        }
    ])

    # Mock PR details - external author, but bob is current reviewer (GraphQL format)
    pr_details = Mock()
    pr_details.returncode = 0
    pr_details.stdout = json.dumps({
        "data": {
            "repository": {
                "pr_789": {
                    "number": 789,
                    "title": "External PR with Team Reviewer",
                    "url": "https://github.com/test-org/test-repo/pull/789",
                    "author": {"login": "external_user"},  # Not a team member
                    "reviewRequests": {
                        "nodes": [
                            {"requestedReviewer": {"login": "bob"}}  # Bob is current reviewer (team member)
                        ]
                    },
                    "createdAt": "2025-10-27T10:00:00Z",
                    "isDraft": False,
                    "baseRefName": "main",
                    "headRefName": "feature",
                    "additions": 15,
                    "deletions": 8
                }
            }
        }
    })

    # Mock calls: rate_limit, then 4 searches (dual search per user), then pr_details (GraphQL)
    mock_run.side_effect = [
        rate_limit_result,
        empty_search_result,  # alice review:none search
        empty_search_result,  # alice review:required search
        empty_search_result,  # bob review:none search
        pr_search_result,     # bob review:required search - returns the PR
        pr_details            # GraphQL batch query for PR details
    ]

    # Execute
    prs = github_client.fetch_team_prs(org_name, team_usernames, updated_after)

    # Verify: PR should be included (team member is current reviewer)
    assert len(prs) == 1
    assert prs[0].author == "external_user"
    assert "bob" in prs[0].reviewers
    assert prs[0].number == 789


@patch("github_client.subprocess.run")
def test_fetch_team_prs_excludes_fully_external_prs(mock_run, github_client):
    """Test that PRs with only external authors and reviewers are excluded."""
    team_usernames = {"alice", "bob"}
    org_name = "test-org"
    updated_after = date.today() - timedelta(days=7)

    # Mock rate limit check
    rate_limit_result = Mock()
    rate_limit_result.returncode = 0
    rate_limit_result.stdout = json.dumps({
        "remaining": 5000,
        "limit": 5000,
        "reset": 1635724800
    })

    # Mock search results
    empty_search_result = Mock()
    empty_search_result.returncode = 0
    empty_search_result.stdout = json.dumps([])

    pr_search_result = Mock()
    pr_search_result.returncode = 0
    pr_search_result.stdout = json.dumps([
        {
            "number": 999,
            "url": "https://github.com/test-org/test-repo/pull/999",
            "repository": {"nameWithOwner": "test-org/test-repo"}
        }
    ])

    # Mock PR details - external author and external reviewers
    pr_details = Mock()
    pr_details.returncode = 0
    pr_details.stdout = json.dumps({
        "number": 999,
        "title": "Fully External PR",
        "url": "https://github.com/test-org/test-repo/pull/999",
        "author": {"login": "external_user1"},  # Not a team member
        "reviewRequests": [
            {"login": "external_user2"},  # Not a team member
            {"login": "external_user3"}   # Not a team member
        ],
        "createdAt": "2025-10-28T10:00:00Z",
        "isDraft": False,
        "baseRefName": "main",
        "headRefName": "feature",
        "additions": 25,
        "deletions": 12
    })

    # Mock calls: rate_limit, then 4 searches (dual search per user)
    # Note: All searches return empty, so no GraphQL call should be made
    mock_run.side_effect = [
        rate_limit_result,
        empty_search_result,  # alice review:none search
        empty_search_result,  # alice review:required search
        empty_search_result,  # bob review:none search
        empty_search_result,  # bob review:required search
    ]

    # Execute
    prs = github_client.fetch_team_prs(org_name, team_usernames, updated_after)

    # Verify: PR should be excluded (no team member involvement)
    assert len(prs) == 0


@patch("github_client.subprocess.run")
def test_fetch_team_prs_includes_mixed_reviewers(mock_run, github_client):
    """Test that PRs with mixed team/external reviewers are included."""
    team_usernames = {"alice", "bob"}
    org_name = "test-org"
    updated_after = date.today() - timedelta(days=7)

    # Mock rate limit check
    rate_limit_result = Mock()
    rate_limit_result.returncode = 0
    rate_limit_result.stdout = json.dumps({
        "remaining": 5000,
        "limit": 5000,
        "reset": 1635724800
    })

    # Mock search results
    empty_search_result = Mock()
    empty_search_result.returncode = 0
    empty_search_result.stdout = json.dumps([])

    pr_search_result = Mock()
    pr_search_result.returncode = 0
    pr_search_result.stdout = json.dumps([
        {
            "number": 555,
            "url": "https://github.com/test-org/test-repo/pull/555",
            "repository": {"nameWithOwner": "test-org/test-repo"}
        }
    ])

    # Mock PR details - external author, mixed reviewers (team + external) (GraphQL format)
    pr_details = Mock()
    pr_details.returncode = 0
    pr_details.stdout = json.dumps({
        "data": {
            "repository": {
                "pr_555": {
                    "number": 555,
                    "title": "Mixed Reviewers PR",
                    "url": "https://github.com/test-org/test-repo/pull/555",
                    "author": {"login": "external_user"},  # Not a team member
                    "reviewRequests": {
                        "nodes": [
                            {"requestedReviewer": {"login": "alice"}},  # Team member
                            {"requestedReviewer": {"login": "external_user2"}}  # Not a team member
                        ]
                    },
                    "createdAt": "2025-10-29T10:00:00Z",
                    "isDraft": False,
                    "baseRefName": "main",
                    "headRefName": "feature",
                    "additions": 30,
                    "deletions": 15
                }
            }
        }
    })

    # Mock calls: rate_limit, then 4 searches (dual search per user), then pr_details (GraphQL)
    mock_run.side_effect = [
        rate_limit_result,
        pr_search_result,     # alice review:none search - returns the PR
        empty_search_result,  # alice review:required search
        empty_search_result,  # bob review:none search
        empty_search_result,  # bob review:required search
        pr_details            # GraphQL batch query for PR details
    ]

    # Execute
    prs = github_client.fetch_team_prs(org_name, team_usernames, updated_after)

    # Verify: PR should be included (at least one team member is reviewer)
    assert len(prs) == 1
    assert prs[0].number == 555
    assert "alice" in prs[0].reviewers
    assert "external_user2" in prs[0].reviewers
