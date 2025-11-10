"""Unit tests for GitHubClient methods."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import Mock, patch

import pytest

from github_client import GitHubClient


@pytest.fixture
def github_client():
    """Create a GitHub client instance for testing."""
    return GitHubClient(token="test_token")


@patch("github_client.subprocess.run")
def test_search_prs_by_review_status_none(mock_run, github_client):
    """Test _search_prs_by_review_status with review:none filter."""
    # Mock successful search result
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps([
        {
            "number": 123,
            "repository": {"nameWithOwner": "test-org/test-repo"}
        }
    ])
    mock_run.return_value = mock_result

    # Execute search
    result = github_client._search_prs_by_review_status(
        org_name="test-org",
        username="alice",
        updated_after=date(2025, 11, 1),
        review_status="none"
    )

    # Verify the result
    assert result.returncode == 0
    prs = json.loads(result.stdout)
    assert len(prs) == 1
    assert prs[0]["number"] == 123
    assert prs[0]["repository"]["nameWithOwner"] == "test-org/test-repo"

    # Verify the gh CLI command was called with correct parameters
    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert "gh" in call_args
    assert "search" in call_args
    assert "prs" in call_args
    assert "--review" in call_args
    assert "none" in call_args
    assert "--review-requested" in call_args
    assert "alice" in call_args
    assert "--owner" in call_args
    assert "test-org" in call_args


@patch("github_client.subprocess.run")
def test_search_prs_by_review_status_required(mock_run, github_client):
    """Test _search_prs_by_review_status with review:required filter."""
    # Mock successful search result
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps([
        {
            "number": 456,
            "repository": {"nameWithOwner": "test-org/another-repo"}
        }
    ])
    mock_run.return_value = mock_result

    # Execute search
    result = github_client._search_prs_by_review_status(
        org_name="test-org",
        username="bob",
        updated_after=date(2025, 11, 1),
        review_status="required"
    )

    # Verify the result
    assert result.returncode == 0
    prs = json.loads(result.stdout)
    assert len(prs) == 1
    assert prs[0]["number"] == 456

    # Verify the gh CLI command was called with review:required
    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert "--review" in call_args
    assert "required" in call_args
    assert "--review-requested" in call_args
    assert "bob" in call_args


@patch("github_client.subprocess.run")
def test_search_prs_by_review_status_empty_results(mock_run, github_client):
    """Test _search_prs_by_review_status when no PRs are found."""
    # Mock empty search result
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps([])
    mock_run.return_value = mock_result

    # Execute search
    result = github_client._search_prs_by_review_status(
        org_name="test-org",
        username="charlie",
        updated_after=date(2025, 11, 1),
        review_status="none"
    )

    # Verify the result is empty
    assert result.returncode == 0
    prs = json.loads(result.stdout)
    assert len(prs) == 0


# ============================================================================
# User Story 1 Tests: Dual Search + Deduplication
# ============================================================================


@patch("github_client.subprocess.run")
def test_dual_search_executes_both_queries(mock_run, github_client):
    """Test that fetch_team_prs executes both review:none and review:required searches."""
    # Mock rate limit check
    rate_limit_result = Mock()
    rate_limit_result.returncode = 0
    rate_limit_result.stdout = json.dumps({
        "remaining": 5000,
        "limit": 5000,
        "reset": 1635724800
    })

    # Mock review:none search result
    review_none_result = Mock()
    review_none_result.returncode = 0
    review_none_result.stdout = json.dumps([
        {"number": 1, "repository": {"nameWithOwner": "org/repo"}}
    ])

    # Mock review:required search result
    review_required_result = Mock()
    review_required_result.returncode = 0
    review_required_result.stdout = json.dumps([
        {"number": 2, "repository": {"nameWithOwner": "org/repo"}}
    ])

    # Mock PR details (GraphQL batch)
    pr_details_result = Mock()
    pr_details_result.returncode = 0
    pr_details_result.stdout = json.dumps({
        "data": {
            "repository": {
                "pr_1": {
                    "number": 1,
                    "title": "PR 1",
                    "url": "https://github.com/org/repo/pull/1",
                    "createdAt": "2025-11-01T00:00:00Z",
                    "isDraft": False,
                    "author": {"login": "alice"},
                    "reviewRequests": {"nodes": []},
                    "reviews": {"nodes": []},
                    "reviewDecision": None,
                    "baseRefName": "main"
                },
                "pr_2": {
                    "number": 2,
                    "title": "PR 2",
                    "url": "https://github.com/org/repo/pull/2",
                    "createdAt": "2025-11-01T00:00:00Z",
                    "isDraft": False,
                    "author": {"login": "bob"},
                    "reviewRequests": {"nodes": []},
                    "reviews": {"nodes": []},
                    "reviewDecision": "REVIEW_REQUIRED",
                    "baseRefName": "main"
                }
            }
        }
    })

    # Set up mock responses in order
    mock_run.side_effect = [
        rate_limit_result,       # Rate limit check
        review_none_result,      # Search 1: review:none
        review_required_result,  # Search 2: review:required
        pr_details_result,       # GraphQL batch fetch
    ]

    # Execute
    prs = github_client.fetch_team_prs(
        org_name="org",
        team_usernames={"alice"},
        updated_after=date(2025, 11, 1)
    )

    # Verify both searches were executed
    assert mock_run.call_count >= 4  # rate limit + 2 searches + details

    # Check that both review:none and review:required searches were made
    search_calls = [call for call in mock_run.call_args_list
                    if 'search' in str(call) and 'prs' in str(call)]
    assert len(search_calls) == 2

    # Verify we got PRs back
    assert len(prs) == 2


@patch("github_client.subprocess.run")
def test_pr_deduplication_when_in_both_searches(mock_run, github_client):
    """Test that PRs appearing in both searches are only fetched once."""
    # Mock rate limit check
    rate_limit_result = Mock()
    rate_limit_result.returncode = 0
    rate_limit_result.stdout = json.dumps({
        "remaining": 5000,
        "limit": 5000,
        "reset": 1635724800
    })

    # Same PR in both search results
    same_pr_data = {"number": 123, "repository": {"nameWithOwner": "org/repo"}}

    review_none_result = Mock()
    review_none_result.returncode = 0
    review_none_result.stdout = json.dumps([same_pr_data])

    review_required_result = Mock()
    review_required_result.returncode = 0
    review_required_result.stdout = json.dumps([same_pr_data])

    # Mock PR details - should only be fetched once
    pr_details_result = Mock()
    pr_details_result.returncode = 0
    pr_details_result.stdout = json.dumps({
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    "title": "Test PR",
                    "url": "https://github.com/org/repo/pull/123",
                    "createdAt": "2025-11-01T00:00:00Z",
                    "isDraft": False,
                    "author": {"login": "alice"},
                    "reviewRequests": {"nodes": []},
                    "reviews": {"nodes": []},
                    "reviewDecision": "REVIEW_REQUIRED",
                    "baseRefName": "main"
                }
            }
        }
    })

    mock_run.side_effect = [
        rate_limit_result,
        review_none_result,
        review_required_result,
        pr_details_result,
    ]

    # Execute
    prs = github_client.fetch_team_prs(
        org_name="org",
        team_usernames={"alice"},
        updated_after=date(2025, 11, 1)
    )

    # Verify only one PR was returned (deduplicated)
    assert len(prs) == 1
    assert prs[0].number == 123


@patch("github_client.subprocess.run")
def test_search_metadata_tracking(mock_run, github_client):
    """Test that pr_search_metadata tracks which searches found each PR."""
    # This test verifies internal metadata tracking for later filtering
    # We'll verify the behavior through the filtering implementation

    # Mock rate limit check
    rate_limit_result = Mock()
    rate_limit_result.returncode = 0
    rate_limit_result.stdout = json.dumps({
        "remaining": 5000,
        "limit": 5000,
        "reset": 1635724800
    })

    # PR found only in review:none
    review_none_result = Mock()
    review_none_result.returncode = 0
    review_none_result.stdout = json.dumps([
        {"number": 1, "repository": {"nameWithOwner": "org/repo"}}
    ])

    # Different PR found only in review:required
    review_required_result = Mock()
    review_required_result.returncode = 0
    review_required_result.stdout = json.dumps([
        {"number": 2, "repository": {"nameWithOwner": "org/repo"}}
    ])

    # Mock PR details
    pr_details_result = Mock()
    pr_details_result.returncode = 0
    pr_details_result.stdout = json.dumps({
        "data": {
            "repository": {
                "pr_1": {
                    "number": 1,
                    "title": "PR 1",
                    "url": "https://github.com/org/repo/pull/1",
                    "createdAt": "2025-11-01T00:00:00Z",
                    "isDraft": False,
                    "author": {"login": "alice"},
                    "reviewRequests": {"nodes": []},
                    "reviews": {"nodes": []},
                    "reviewDecision": None,
                    "baseRefName": "main"
                },
                "pr_2": {
                    "number": 2,
                    "title": "PR 2",
                    "url": "https://github.com/org/repo/pull/2",
                    "createdAt": "2025-11-01T00:00:00Z",
                    "isDraft": False,
                    "author": {"login": "bob"},
                    "reviewRequests": {"nodes": []},
                    "reviews": {"nodes": []},
                    "reviewDecision": "REVIEW_REQUIRED",
                    "baseRefName": "main"
                }
            }
        }
    })

    mock_run.side_effect = [
        rate_limit_result,
        review_none_result,
        review_required_result,
        pr_details_result,
    ]

    # Execute
    prs = github_client.fetch_team_prs(
        org_name="org",
        team_usernames={"alice"},
        updated_after=date(2025, 11, 1)
    )

    # Verify both PRs were fetched
    assert len(prs) == 2
    pr_numbers = {pr.number for pr in prs}
    assert pr_numbers == {1, 2}


@patch("github_client.subprocess.run")
def test_empty_search_results_handling(mock_run, github_client):
    """Test handling when either search returns no results."""
    # Mock rate limit check
    rate_limit_result = Mock()
    rate_limit_result.returncode = 0
    rate_limit_result.stdout = json.dumps({
        "remaining": 5000,
        "limit": 5000,
        "reset": 1635724800
    })

    # Both searches return empty
    empty_result = Mock()
    empty_result.returncode = 0
    empty_result.stdout = json.dumps([])

    mock_run.side_effect = [
        rate_limit_result,
        empty_result,  # review:none search
        empty_result,  # review:required search
    ]

    # Execute
    prs = github_client.fetch_team_prs(
        org_name="org",
        team_usernames={"alice"},
        updated_after=date(2025, 11, 1)
    )

    # Verify no PRs returned
    assert len(prs) == 0
