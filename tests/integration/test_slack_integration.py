"""Integration tests for Slack client with mocked webhook calls.

NOTE: Most tests in this file are skipped as they test the old webhook-based
implementation. After migrating to Slack SDK (chat.postMessage API), these tests
are no longer applicable. See test_slack_client.py for current implementation tests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
import requests

from models import PullRequest, StalePR
from slack_client import SlackClient


@pytest.fixture
def slack_client():
    """Create a Slack client instance."""
    return SlackClient(bot_token="xoxb-test-token", channel_id="C1234567890")


@pytest.fixture
def sample_stale_prs():
    """Create sample stale PRs for testing."""
    pr1 = PullRequest(
        repo_name="review-ops",
        number=123,
        title="Add staleness calculation",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/test-org/review-ops/pull/123",
        created_at=datetime(2025, 10, 20, 10, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 10, 20, 10, 0, 0, tzinfo=UTC),
        current_approvals=0,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

    pr2 = PullRequest(
        repo_name="api-service",
        number=456,
        title="Fix authentication bug",
        author="charlie",
        reviewers=["alice", "bob"],
        url="https://github.com/test-org/api-service/pull/456",
        created_at=datetime(2025, 10, 15, 10, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 10, 15, 10, 0, 0, tzinfo=UTC),
        current_approvals=1,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

    return [
        StalePR(pr=pr1, staleness_days=5.2),  # Aging
        StalePR(pr=pr2, staleness_days=10.5),  # Rotten
    ]


def test_slack_client_initialization():
    """Test Slack client can be initialized with bot token and channel ID."""
    client = SlackClient(bot_token="xoxb-test-token", channel_id="C1234567890")
    assert client is not None
    assert client.channel_id == "C1234567890"


@pytest.mark.skip(reason="Obsolete: tests old webhook format_message() method")
def test_format_message_basic(slack_client, sample_stale_prs, sample_team_members):
    """Test formatting a basic Slack message."""
    message = slack_client.format_message(sample_stale_prs, sample_team_members)

    assert message is not None
    assert isinstance(message, str)
    assert "stale PRs" in message.lower() or "review" in message.lower()


@pytest.mark.skip(reason="Obsolete: tests old webhook format_message() method")
def test_format_message_includes_pr_details(slack_client, sample_stale_prs, sample_team_members):
    """Test that message includes PR details."""
    message = slack_client.format_message(sample_stale_prs, sample_team_members)

    # Should include PR titles
    assert "Add staleness calculation" in message
    assert "Fix authentication bug" in message

    # Should include URLs
    assert "https://github.com/test-org/review-ops/pull/123" in message
    assert "https://github.com/test-org/api-service/pull/456" in message


@pytest.mark.skip(reason="Obsolete: tests old webhook format_message() method")
def test_format_message_empty_pr_list(slack_client, sample_team_members):
    """Test formatting message with no stale PRs (celebratory message)."""
    message = slack_client.format_message([], sample_team_members)

    assert message is not None
    assert (
        "no stale" in message.lower()
        or "all caught up" in message.lower()
        or "great" in message.lower()
    )


@pytest.mark.skip(reason="Obsolete: tests old webhook send_message() method")
def test_send_message_success(slack_client):
    """Test successful message sending."""
    with patch("requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        slack_client.send_message("Test message")

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://hooks.slack.com/services/T00/B00/XXX"
        assert "Test message" in str(call_args[1]["json"])


@pytest.mark.skip(reason="Obsolete: tests old webhook send_message() method")
def test_send_message_failure(slack_client):
    """Test handling of failed message sending."""
    with patch("requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "invalid_payload"
        mock_post.return_value = mock_response

        with pytest.raises(Exception):  # noqa: B017
            slack_client.send_message("Test message")


@pytest.mark.skip(reason="Obsolete: tests old webhook send_message() method")
def test_send_message_network_error(slack_client):
    """Test handling of network errors."""
    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")

        with pytest.raises(requests.exceptions.ConnectionError):
            slack_client.send_message("Test message")


@pytest.mark.skip(reason="Obsolete: tests old webhook implementation compatibility")
def test_post_stale_pr_summary_webhook_compatibility(
    slack_client, sample_stale_prs, sample_team_members
):
    """Test that Block Kit implementation maintains webhook compatibility (T031a).

    Verifies:
    - Webhook URL remains unchanged
    - POST method is used
    - Headers include Content-Type: application/json
    - Request timeout is set
    """
    with patch("requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        # Call the Block Kit method
        slack_client.post_stale_pr_summary(sample_stale_prs, sample_team_members)

        # Verify webhook was called exactly once
        mock_post.assert_called_once()

        # Extract call arguments
        call_args = mock_post.call_args
        called_url = call_args[0][0]
        called_kwargs = call_args[1]

        # Verify webhook URL is unchanged
        assert called_url == "https://hooks.slack.com/services/T00/B00/XXX"

        # Verify JSON payload is used (not 'text')
        assert "json" in called_kwargs
        payload = called_kwargs["json"]

        # Verify Block Kit structure
        assert "blocks" in payload
        assert isinstance(payload["blocks"], list)
        assert len(payload["blocks"]) > 0

        # Verify timeout is set
        assert "timeout" in called_kwargs
        assert called_kwargs["timeout"] == 10


@pytest.mark.skip(reason="Obsolete: tests old webhook implementation")
def test_post_stale_pr_summary_full_message_structure(
    slack_client, sample_stale_prs, sample_team_members
):
    """Test full Block Kit message structure validation (T032)."""
    with patch("requests.post") as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        slack_client.post_stale_pr_summary(sample_stale_prs, sample_team_members)

        payload = mock_post.call_args[1]["json"]

        # Validate top-level structure
        assert "blocks" in payload
        blocks = payload["blocks"]
        assert isinstance(blocks, list)

        # Validate block types - table format has header + table + optional context
        block_types = [block.get("type") for block in blocks]
        assert "header" in block_types  # Should have board header
        assert "table" in block_types  # Should have table with PRs

        # Validate each block has required fields
        for block in blocks:
            assert "type" in block
            assert block["type"] in ["header", "table", "context"]

            if block["type"] == "header":
                assert "text" in block
                assert block["text"]["type"] == "plain_text"
                assert "text" in block["text"]

            elif block["type"] == "table":
                assert "rows" in block
                assert isinstance(block["rows"], list)
                assert len(block["rows"]) > 0  # Should have at least header row

        # Ensure block count is under Slack's 50-block limit
        assert len(blocks) <= 50
