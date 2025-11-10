"""Unit tests for GitHubClient filtering logic (User Story 3 & 4)."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from unittest.mock import Mock, patch

import pytest

from github_client import GitHubClient
from models import GitHubTeamReviewRequest, PullRequest


@pytest.fixture
def github_client():
    """Create a GitHub client instance for testing."""
    return GitHubClient(token="test_token")


# ============================================================================
# User Story 3 Tests: Filter by Team Member Presence
# ============================================================================


def test_filter_review_required_pr_with_team_member_included(github_client):
    """Test that review:required PR with team member in reviewers is included."""
    # Create PR with team member in reviewers
    pr = PullRequest(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        author="external-user",
        reviewers=["alice", "external-reviewer"],
        github_team_reviewers=[],
        url="https://github.com/org/test-repo/pull/123",
        created_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        current_approvals=0,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

    # Mock metadata showing this PR came from review:required search
    pr_search_metadata = {
        ("test-repo", 123): {"review:required"}
    }

    # Filter
    team_usernames = {"alice", "bob"}
    filtered_prs = github_client._filter_by_team_member_presence(
        [pr], pr_search_metadata, team_usernames
    )

    # Verify PR is included (alice is a team member and in reviewers)
    assert len(filtered_prs) == 1
    assert filtered_prs[0].number == 123


def test_filter_review_required_pr_without_team_members_excluded(github_client):
    """Test that review:required PR without team members in reviewers is excluded."""
    # Create PR with only external reviewers
    pr = PullRequest(
        repo_name="test-repo",
        number=456,
        title="Test PR 2",
        author="external-user",
        reviewers=["external-reviewer-1", "external-reviewer-2"],
        github_team_reviewers=[],
        url="https://github.com/org/test-repo/pull/456",
        created_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        current_approvals=1,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

    # Mock metadata showing this PR came from review:required search
    pr_search_metadata = {
        ("test-repo", 456): {"review:required"}
    }

    # Filter
    team_usernames = {"alice", "bob"}
    filtered_prs = github_client._filter_by_team_member_presence(
        [pr], pr_search_metadata, team_usernames
    )

    # Verify PR is excluded (no team members in reviewers)
    assert len(filtered_prs) == 0


def test_filter_review_none_pr_without_team_members_included(github_client):
    """Test that review:none PR without team members is included (no filtering)."""
    # Create PR with only external reviewers
    pr = PullRequest(
        repo_name="test-repo",
        number=789,
        title="Test PR 3",
        author="external-user",
        reviewers=["external-reviewer"],
        github_team_reviewers=[],
        url="https://github.com/org/test-repo/pull/789",
        created_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    # Mock metadata showing this PR came from review:none search (NOT review:required)
    pr_search_metadata = {
        ("test-repo", 789): {"review:none"}
    }

    # Filter
    team_usernames = {"alice", "bob"}
    filtered_prs = github_client._filter_by_team_member_presence(
        [pr], pr_search_metadata, team_usernames
    )

    # Verify PR is included (review:none PRs are not filtered)
    assert len(filtered_prs) == 1
    assert filtered_prs[0].number == 789


def test_filter_case_insensitive_username_comparison(github_client):
    """Test that username comparison is case-insensitive (Alice matches alice)."""
    # Create PR with reviewer "Alice" (uppercase)
    pr = PullRequest(
        repo_name="test-repo",
        number=111,
        title="Test PR Case",
        author="external-user",
        reviewers=["Alice", "Bob"],  # Mixed case
        github_team_reviewers=[],
        url="https://github.com/org/test-repo/pull/111",
        created_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        current_approvals=0,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

    # Mock metadata
    pr_search_metadata = {
        ("test-repo", 111): {"review:required"}
    }

    # Filter with lowercase team usernames
    team_usernames = {"alice", "bob"}  # lowercase
    filtered_prs = github_client._filter_by_team_member_presence(
        [pr], pr_search_metadata, team_usernames
    )

    # Verify PR is included (case-insensitive match)
    assert len(filtered_prs) == 1


def test_filter_empty_reviewers_list_causes_exclusion(github_client):
    """Test that PRs with empty reviewers list are excluded from filtering."""
    # Create PR with empty reviewers
    pr = PullRequest(
        repo_name="test-repo",
        number=222,
        title="Test PR Empty Reviewers",
        author="external-user",
        reviewers=[],  # Empty reviewers list
        github_team_reviewers=[],
        url="https://github.com/org/test-repo/pull/222",
        created_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        current_approvals=0,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

    # Mock metadata
    pr_search_metadata = {
        ("test-repo", 222): {"review:required"}
    }

    # Filter
    team_usernames = {"alice", "bob"}
    filtered_prs = github_client._filter_by_team_member_presence(
        [pr], pr_search_metadata, team_usernames
    )

    # Verify PR is excluded (no reviewers means no team members)
    assert len(filtered_prs) == 0


# ============================================================================
# User Story 4 Tests: GitHub Team Review Requests
# ============================================================================


def test_filter_review_required_pr_with_team_member_in_github_team_included(github_client):
    """Test that review:required PR with team member in GitHub team reviewers is included."""
    # Create PR with GitHub team containing team member
    pr = PullRequest(
        repo_name="test-repo",
        number=333,
        title="Test PR with GitHub Team",
        author="external-user",
        reviewers=[],
        github_team_reviewers=[
            GitHubTeamReviewRequest(
                team_name="Backend Team",
                team_slug="backend-team",
                members=["alice", "charlie", "dave"],
            )
        ],
        url="https://github.com/org/test-repo/pull/333",
        created_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        current_approvals=0,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

    # Mock metadata
    pr_search_metadata = {
        ("test-repo", 333): {"review:required"}
    }

    # Filter (alice is in the GitHub team)
    team_usernames = {"alice", "bob"}
    filtered_prs = github_client._filter_by_team_member_presence(
        [pr], pr_search_metadata, team_usernames
    )

    # Verify PR is included (alice is in GitHub team members)
    assert len(filtered_prs) == 1


def test_filter_review_required_pr_with_github_team_no_tracked_members_excluded(github_client):
    """Test that review:required PR with GitHub team containing no tracked members is excluded."""
    # Create PR with GitHub team NOT containing any team members
    pr = PullRequest(
        repo_name="test-repo",
        number=444,
        title="Test PR with GitHub Team No Match",
        author="external-user",
        reviewers=[],
        github_team_reviewers=[
            GitHubTeamReviewRequest(
                team_name="Frontend Team",
                team_slug="frontend-team",
                members=["charlie", "dave", "eve"],  # No tracked team members
            )
        ],
        url="https://github.com/org/test-repo/pull/444",
        created_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        current_approvals=0,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

    # Mock metadata
    pr_search_metadata = {
        ("test-repo", 444): {"review:required"}
    }

    # Filter
    team_usernames = {"alice", "bob"}
    filtered_prs = github_client._filter_by_team_member_presence(
        [pr], pr_search_metadata, team_usernames
    )

    # Verify PR is excluded (no tracked team members in GitHub team)
    assert len(filtered_prs) == 0


@patch("github_client.subprocess.run")
def test_fetch_github_team_members_with_limit_checks_size(mock_run, github_client):
    """Test that team size check is performed before expansion."""
    # Mock team with 50 members (within limit)
    size_check_result = Mock()
    size_check_result.returncode = 0
    size_check_result.stdout = "50"

    members_result = Mock()
    members_result.returncode = 0
    members_result.stdout = "alice\nbob\ncharlie"

    mock_run.side_effect = [size_check_result, members_result]

    # Call the method
    members = github_client._fetch_github_team_members_with_limit("test-org", "test-team", max_size=100)

    # Verify team size was checked
    assert mock_run.call_count == 2
    assert "/orgs/test-org/teams/test-team" in str(mock_run.call_args_list[0])
    assert "members_count" in str(mock_run.call_args_list[0])

    # Verify members were fetched
    assert members == ["alice", "bob", "charlie"]


@patch("github_client.subprocess.run")
def test_fetch_github_team_members_with_limit_skips_oversized_teams(mock_run, github_client):
    """Test that teams exceeding size limit return None (fail-safe)."""
    # Mock team with 150 members (exceeds limit)
    size_check_result = Mock()
    size_check_result.returncode = 0
    size_check_result.stdout = "150"

    mock_run.return_value = size_check_result

    # Call the method
    members = github_client._fetch_github_team_members_with_limit("test-org", "large-team", max_size=100)

    # Verify None is returned (fail-safe signal)
    assert members is None

    # Verify only size check was called, not member fetch
    assert mock_run.call_count == 1


def test_filter_failsafe_includes_pr_with_none_members(github_client):
    """Test that PRs with None members (fail-safe from team expansion) are included."""
    # Create PR with GitHub team that has None members (oversized team)
    pr = PullRequest(
        repo_name="test-repo",
        number=555,
        title="Test PR with Oversized Team",
        author="external-user",
        reviewers=[],
        github_team_reviewers=[
            GitHubTeamReviewRequest(
                team_name="Large Team",
                team_slug="large-team",
                members=None,  # Fail-safe signal from team expansion
            )
        ],
        url="https://github.com/org/test-repo/pull/555",
        created_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC),
        current_approvals=0,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

    # Mock metadata
    pr_search_metadata = {
        ("test-repo", 555): {"review:required"}
    }

    # Filter
    team_usernames = {"alice", "bob"}
    filtered_prs = github_client._filter_by_team_member_presence(
        [pr], pr_search_metadata, team_usernames
    )

    # Verify PR is included (fail-safe behavior)
    assert len(filtered_prs) == 1
    assert filtered_prs[0].number == 555
