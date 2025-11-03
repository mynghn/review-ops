"""Integration tests for GitHub client with mocked API responses."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from github_client import GitHubClient


@pytest.fixture
def github_client():
    """Create a GitHub client instance."""
    return GitHubClient(token="test_token", use_graphql_batch=False)


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
def test_fetch_team_prs_filters_out_removed_reviewers(mock_run, github_client):
    """Test that PRs where team member was removed as reviewer are excluded."""
    team_usernames = {"alice", "bob"}
    org_name = "test-org"

    # Mock rate limit check
    rate_limit_result = Mock()
    rate_limit_result.returncode = 0
    rate_limit_result.stdout = json.dumps({
        "remaining": 5000,
        "limit": 5000,
        "reset": 1635724800
    })

    # Mock search results - empty results for alice, one result for bob
    empty_search_result = Mock()
    empty_search_result.returncode = 0
    empty_search_result.stdout = json.dumps([])

    bob_search_result = Mock()
    bob_search_result.returncode = 0
    bob_search_result.stdout = json.dumps([
        {
            "number": 123,
            "url": "https://github.com/test-org/test-repo/pull/123",
            "repository": {"nameWithOwner": "test-org/test-repo"}
        }
    ])

    # Mock PR details - bob is NO LONGER in reviewers list
    pr_details = Mock()
    pr_details.returncode = 0
    pr_details.stdout = json.dumps({
        "number": 123,
        "title": "External PR",
        "url": "https://github.com/test-org/test-repo/pull/123",
        "author": {"login": "external_user"},  # Not a team member
        "reviewRequests": [],  # Bob was removed - empty reviewers
        "createdAt": "2025-10-25T10:00:00Z",
        "isDraft": False,
        "baseRefName": "main",
        "headRefName": "feature",
        "additions": 10,
        "deletions": 5
    })

    # Mock calls: rate_limit, then 4 searches (2 users x 2 types), then pr_details
    # We return the PR in one search to simulate historical involvement
    mock_run.side_effect = [
        rate_limit_result,
        empty_search_result,  # search 1
        bob_search_result,    # search 2 - returns the PR
        empty_search_result,  # search 3
        empty_search_result,  # search 4
        pr_details            # PR details fetch
    ]

    # Execute
    prs = github_client.fetch_team_prs(org_name, team_usernames)

    # Verify: PR should be excluded (no current team involvement)
    assert len(prs) == 0


@patch("github_client.subprocess.run")
def test_fetch_team_prs_includes_team_author(mock_run, github_client):
    """Test that PRs authored by team members are always included."""
    team_usernames = {"alice", "bob"}
    org_name = "test-org"

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

    alice_search_result = Mock()
    alice_search_result.returncode = 0
    alice_search_result.stdout = json.dumps([
        {
            "number": 456,
            "url": "https://github.com/test-org/test-repo/pull/456",
            "repository": {"nameWithOwner": "test-org/test-repo"}
        }
    ])

    # Mock PR details - alice is author (team member), no reviewers
    pr_details = Mock()
    pr_details.returncode = 0
    pr_details.stdout = json.dumps({
        "number": 456,
        "title": "Alice's PR",
        "url": "https://github.com/test-org/test-repo/pull/456",
        "author": {"login": "alice"},  # Team member author
        "reviewRequests": [],  # No reviewers
        "createdAt": "2025-10-26T10:00:00Z",
        "isDraft": False,
        "baseRefName": "main",
        "headRefName": "feature",
        "additions": 20,
        "deletions": 10
    })

    # Mock calls: rate_limit, then 4 searches, then pr_details
    mock_run.side_effect = [
        rate_limit_result,
        alice_search_result,  # search 1 - returns alice's PR
        empty_search_result,  # search 2
        empty_search_result,  # search 3
        empty_search_result,  # search 4
        pr_details            # PR details fetch
    ]

    # Execute
    prs = github_client.fetch_team_prs(org_name, team_usernames)

    # Verify: PR should be included (team member is author)
    assert len(prs) == 1
    assert prs[0].author == "alice"
    assert prs[0].number == 456


@patch("github_client.subprocess.run")
def test_fetch_team_prs_includes_team_reviewer(mock_run, github_client):
    """Test that PRs with current team reviewers are included."""
    team_usernames = {"alice", "bob"}
    org_name = "test-org"

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

    # Mock PR details - external author, but bob is current reviewer
    pr_details = Mock()
    pr_details.returncode = 0
    pr_details.stdout = json.dumps({
        "number": 789,
        "title": "External PR with Team Reviewer",
        "url": "https://github.com/test-org/test-repo/pull/789",
        "author": {"login": "external_user"},  # Not a team member
        "reviewRequests": [{"login": "bob"}],  # Bob is current reviewer (team member)
        "createdAt": "2025-10-27T10:00:00Z",
        "isDraft": False,
        "baseRefName": "main",
        "headRefName": "feature",
        "additions": 15,
        "deletions": 8
    })

    # Mock calls: rate_limit, then 4 searches, then pr_details
    mock_run.side_effect = [
        rate_limit_result,
        empty_search_result,  # search 1
        empty_search_result,  # search 2
        pr_search_result,     # search 3 - returns the PR
        empty_search_result,  # search 4
        pr_details            # PR details fetch
    ]

    # Execute
    prs = github_client.fetch_team_prs(org_name, team_usernames)

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

    # Mock calls: rate_limit, then 4 searches, then pr_details
    mock_run.side_effect = [
        rate_limit_result,
        empty_search_result,  # search 1
        empty_search_result,  # search 2
        empty_search_result,  # search 3
        pr_search_result,     # search 4 - returns the PR
        pr_details            # PR details fetch
    ]

    # Execute
    prs = github_client.fetch_team_prs(org_name, team_usernames)

    # Verify: PR should be excluded (no team member involvement)
    assert len(prs) == 0


@patch("github_client.subprocess.run")
def test_fetch_team_prs_includes_mixed_reviewers(mock_run, github_client):
    """Test that PRs with mixed team/external reviewers are included."""
    team_usernames = {"alice", "bob"}
    org_name = "test-org"

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

    # Mock PR details - external author, mixed reviewers (team + external)
    pr_details = Mock()
    pr_details.returncode = 0
    pr_details.stdout = json.dumps({
        "number": 555,
        "title": "Mixed Reviewers PR",
        "url": "https://github.com/test-org/test-repo/pull/555",
        "author": {"login": "external_user"},  # Not a team member
        "reviewRequests": [
            {"login": "alice"},  # Team member
            {"login": "external_user2"}  # Not a team member
        ],
        "createdAt": "2025-10-29T10:00:00Z",
        "isDraft": False,
        "baseRefName": "main",
        "headRefName": "feature",
        "additions": 30,
        "deletions": 15
    })

    # Mock calls: rate_limit, then 4 searches, then pr_details
    mock_run.side_effect = [
        rate_limit_result,
        pr_search_result,     # search 1 - returns the PR
        empty_search_result,  # search 2
        empty_search_result,  # search 3
        empty_search_result,  # search 4
        pr_details            # PR details fetch
    ]

    # Execute
    prs = github_client.fetch_team_prs(org_name, team_usernames)

    # Verify: PR should be included (at least one team member is reviewer)
    assert len(prs) == 1
    assert prs[0].number == 555
    assert "alice" in prs[0].reviewers
    assert "external_user2" in prs[0].reviewers
