"""Integration tests for rate limit detection with mocked gh CLI."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from github_client import GitHubClient


class TestRateLimitDetection:
    """Test rate limit detection with mocked gh CLI responses."""

    def test_check_rate_limit_normal_state(self):
        """Test rate limit check with normal quota remaining."""
        mock_response = {
            "limit": 5000,
            "remaining": 4850,
            "reset": 1698765432,
            "used": 150,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_response),
                returncode=0,
            )

            client = GitHubClient(token="ghp_test123")
            # This test will be updated when check_rate_limit returns RateLimitStatus
            # For now, just verify it doesn't raise
            client.check_rate_limit()

    def test_check_rate_limit_low_quota(self):
        """Test rate limit check with low quota (< 100 remaining)."""
        mock_response = {
            "limit": 5000,
            "remaining": 50,
            "reset": 1698765432,
            "used": 4950,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_response),
                returncode=0,
            )

            client = GitHubClient(token="ghp_test123")
            # Test will be expanded when check_rate_limit returns RateLimitStatus
            client.check_rate_limit()


class TestAutoWaitScenario:
    """Test auto-wait behavior when rate limit reset < threshold."""

    def test_auto_wait_when_reset_under_threshold(self):
        """Test that app waits when reset time < configured threshold."""
        import time

        # Mock rate limit response with reset in 2 seconds (under default 300s threshold)
        current_time = int(time.time())
        reset_time = current_time + 2
        mock_response = {
            "limit": 5000,
            "remaining": 0,
            "reset": reset_time,
            "used": 5000,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_response),
                returncode=0,
            )

            client = GitHubClient(token="ghp_test123")
            status = client.check_rate_limit()

            # Verify status indicates exhaustion
            assert status.is_exhausted
            assert status.remaining == 0
            assert status.wait_seconds is not None
            assert status.wait_seconds <= 2

            # Verify _should_proceed returns True (should wait, reset < threshold)
            assert client._should_proceed(status, threshold_seconds=300)


class TestFailFastScenario:
    """Test fail-fast behavior when rate limit reset > threshold."""

    def test_fail_fast_when_reset_over_threshold(self):
        """Test that app fails immediately when reset time > threshold."""
        import time

        # Mock rate limit response with reset in 600 seconds (over default 300s threshold)
        current_time = int(time.time())
        reset_time = current_time + 600
        mock_response = {
            "limit": 5000,
            "remaining": 0,
            "reset": reset_time,
            "used": 5000,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_response),
                returncode=0,
            )

            client = GitHubClient(token="ghp_test123")
            status = client.check_rate_limit()

            # Verify status indicates exhaustion
            assert status.is_exhausted
            assert status.remaining == 0
            assert status.wait_seconds is not None
            assert status.wait_seconds >= 599  # Allow for timing variation

            # Verify _should_proceed returns False (should NOT wait, reset > threshold)
            assert not client._should_proceed(status, threshold_seconds=300)


class TestInconsistentRateLimitData:
    """Test handling of inconsistent rate limit data from GitHub API."""

    def test_inconsistent_rate_limit_handling(self):
        """Test graceful handling of inconsistent rate limit responses."""
        import time

        # Mock rate limit response with inconsistent data (negative remaining)
        current_time = int(time.time())
        mock_response = {
            "limit": 5000,
            "remaining": -10,  # Inconsistent: negative remaining
            "reset": current_time + 60,
            "used": 5010,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_response),
                returncode=0,
            )

            client = GitHubClient(token="ghp_test123")
            status = client.check_rate_limit()

            # Should treat negative remaining as 0 (exhausted)
            assert status.remaining == 0
            assert status.is_exhausted

    def test_missing_rate_limit_fields(self):
        """Test handling of missing fields in rate limit response."""
        # Mock rate limit response with missing fields
        mock_response = {
            "limit": 5000,
            # Missing 'remaining' and 'reset' fields
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_response),
                returncode=0,
            )

            client = GitHubClient(token="ghp_test123")

            # Should raise ValueError or KeyError for missing required fields
            with pytest.raises((ValueError, KeyError)):
                client.check_rate_limit()

    def test_invalid_reset_timestamp(self):
        """Test handling of invalid reset timestamp (in the past)."""
        import time

        # Mock rate limit response with reset timestamp in the past
        current_time = int(time.time())
        mock_response = {
            "limit": 5000,
            "remaining": 0,
            "reset": current_time - 60,  # Reset time in the past
            "used": 5000,
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps(mock_response),
                returncode=0,
            )

            client = GitHubClient(token="ghp_test123")
            status = client.check_rate_limit()

            # Should treat as not exhausted (quota has already reset)
            # Or set wait_seconds to 0
            assert status.wait_seconds is not None
            assert status.wait_seconds <= 0
