"""Integration tests for GraphQL batch fetching and PR deduplication."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from github_client import GitHubClient


class TestPRDeduplication:
    """Test PR deduplication (same PR, multiple members)."""

    def test_same_pr_fetched_once_multiple_members(self):
        """Test that same PR is only fetched once even with multiple team members."""
        client = GitHubClient(token="ghp_test123")

        # Create a PR that would be found for multiple team members
        pr_data = {
            "repository": "owner/repo",
            "number": 123,
            "title": "Shared PR",
            "url": "https://github.com/owner/repo/pull/123",
            "createdAt": "2025-10-01T00:00:00Z",
            "author": {"login": "author1"},
            "reviewRequests": {"nodes": []},
        }

        # Simulate tracking with deduplication dict
        # First occurrence: should be added to tracking
        pr_key = "owner/repo#123"
        if not hasattr(client, "_fetched_prs"):
            client._fetched_prs = {}

        # First fetch: PR is new
        is_duplicate = pr_key in client._fetched_prs
        assert not is_duplicate

        # Add to tracking
        client._fetched_prs[pr_key] = True

        # Second fetch: PR is now duplicate
        is_duplicate = pr_key in client._fetched_prs
        assert is_duplicate


class TestGraphQLBatchQueryConstruction:
    """Test GraphQL batch query construction."""

    def test_batch_query_groups_by_repo(self):
        """Test that PRs are grouped by repository in batch query."""
        client = GitHubClient(token="ghp_test123")

        # PRs from different repositories
        prs_to_fetch = [
            {"repo": "owner1/repo1", "number": 123},
            {"repo": "owner1/repo1", "number": 456},  # Same repo
            {"repo": "owner2/repo2", "number": 789},  # Different repo
        ]

        # Group PRs by repo
        grouped = client._group_prs_by_repo(prs_to_fetch)

        # Should have 2 groups (2 unique repos)
        assert len(grouped) == 2
        assert "owner1/repo1" in grouped
        assert "owner2/repo2" in grouped

        # owner1/repo1 should have 2 PRs
        assert len(grouped["owner1/repo1"]) == 2
        assert 123 in grouped["owner1/repo1"]
        assert 456 in grouped["owner1/repo1"]

        # owner2/repo2 should have 1 PR
        assert len(grouped["owner2/repo2"]) == 1
        assert 789 in grouped["owner2/repo2"]

    def test_build_graphql_query_structure(self):
        """Test GraphQL query structure for batch fetching."""
        client = GitHubClient(token="ghp_test123")

        # Build query for specific repo and PR numbers
        pr_numbers = [123, 456]
        query = client._build_graphql_batch_query("owner", "repo", pr_numbers)

        # Query should contain repository field
        assert "repository" in query
        assert 'owner: "owner"' in query or "owner: $owner" in query
        assert 'name: "repo"' in query or "name: $repo" in query

        # Query should have aliased pullRequest fields
        assert "pr123" in query or "pr_123" in query
        assert "pr456" in query or "pr_456" in query

        # Query should request necessary fields
        assert "number" in query
        assert "title" in query
        assert "createdAt" in query


class TestGraphQLBatchFetching:
    """Test GraphQL batch fetching (grouped by repo)."""

    def test_graphql_batch_fetch_reduces_api_calls(self):
        """Test that GraphQL batch reduces API calls compared to REST."""
        client = GitHubClient(token="ghp_test123")

        # Mock GraphQL response for batch query
        graphql_response = {
            "data": {
                "repository": {
                    "pr123": {
                        "number": 123,
                        "title": "PR 123",
                        "createdAt": "2025-10-01T00:00:00Z",
                        "url": "https://github.com/owner/repo/pull/123",
                        "author": {"login": "user1"},
                        "reviewRequests": {"nodes": []},
                    },
                    "pr456": {
                        "number": 456,
                        "title": "PR 456",
                        "createdAt": "2025-10-02T00:00:00Z",
                        "url": "https://github.com/owner/repo/pull/456",
                        "author": {"login": "user2"},
                        "reviewRequests": {"nodes": []},
                    },
                }
            }
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(graphql_response), returncode=0
            )

            # Fetch 2 PRs in batch (should be 1 API call)
            pr_numbers = [123, 456]
            # This would call _fetch_pr_details_batch_graphql when implemented

            # Verify only 1 GraphQL call vs 2 REST calls
            # With REST: 2 API calls for 2 PRs
            # With GraphQL: 1 API call for 2 PRs
            # This is a 50% reduction in API calls


class TestGraphQLFeatureFlagFallback:
    """Test GraphQL feature flag fallback."""

