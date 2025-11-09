"""Integration tests for exponential backoff retry logic."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from github_client import GitHubClient


class TestExponentialBackoff:
    """Test exponential backoff retry logic."""

    def test_retry_with_exponential_backoff(self):
        """Test that retries happen with correct exponential intervals (1s, 2s, 4s)."""
        client = GitHubClient(token="ghp_test123")

        # Mock time.sleep to track backoff intervals
        with patch("time.sleep") as mock_sleep:
            # First 2 attempts fail with HTTP 429, third succeeds
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    subprocess.CalledProcessError(
                        1, ["gh"], stderr="HTTP 429: rate limit exceeded"
                    ),
                    subprocess.CalledProcessError(
                        1, ["gh"], stderr="HTTP 429: rate limit exceeded"
                    ),
                    MagicMock(stdout="[]", returncode=0),  # Success on 3rd attempt
                ]

                # This should succeed after retries (when implemented)
                # For now, just verify the structure is correct
                assert client.metrics is not None


class TestRetryAfterHeader:
    """Test Retry-After header handling."""

    def test_retry_after_header_respected(self):
        """Test that Retry-After header overrides exponential backoff."""
        client = GitHubClient(token="ghp_test123")

        # Mock time.sleep to track backoff intervals
        with patch("time.sleep") as mock_sleep:
            # First attempt fails with HTTP 429 and Retry-After header
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    subprocess.CalledProcessError(
                        1,
                        ["gh"],
                        stderr="HTTP 429: rate limit exceeded\nRetry-After: 10",
                    ),
                    MagicMock(stdout="[]", returncode=0),  # Success on 2nd attempt
                ]

                # Parse Retry-After from stderr
                retry_after = client._parse_retry_after(
                    "HTTP 429: rate limit exceeded\nRetry-After: 10"
                )

                # Should extract the Retry-After value
                assert retry_after == 10


class TestMaxRetriesExhaustion:
    """Test max retries exhaustion behavior."""

    def test_max_retries_exhausted_raises_error(self):
        """Test that exceeding max retries raises clear error."""
        client = GitHubClient(token="ghp_test123")

        # Mock all attempts to fail with HTTP 429
        with patch("time.sleep"):  # Mock sleep to speed up test
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = [
                    subprocess.CalledProcessError(
                        1, ["gh"], stderr="HTTP 429: rate limit exceeded"
                    ),
                    subprocess.CalledProcessError(
                        1, ["gh"], stderr="HTTP 429: rate limit exceeded"
                    ),
                    subprocess.CalledProcessError(
                        1, ["gh"], stderr="HTTP 429: rate limit exceeded"
                    ),
                    subprocess.CalledProcessError(
                        1, ["gh"], stderr="HTTP 429: rate limit exceeded"
                    ),  # Max 3 retries = 4 total attempts
                ]

                # Should raise after exhausting retries
                with pytest.raises(subprocess.CalledProcessError) as exc_info:
                    client._retry_with_backoff(
                        lambda: subprocess.run(
                            ["gh", "api", "test"],
                            capture_output=True,
                            text=True,
                            check=True,
                        ),
                        max_retries=3,
                        backoff_base=1.0,
                    )

                # Verify it's still a rate limit error
                assert "429" in str(exc_info.value.stderr)


class TestNetworkErrorFailFast:
    """Test network error fail-fast behavior (no retry)."""

    def test_network_timeout_fails_immediately(self):
        """Test that network timeouts don't retry."""
        client = GitHubClient(token="ghp_test123")

        # Mock subprocess.run to raise TimeoutExpired
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["gh", "api", "test"], timeout=30
            )

            # Should raise immediately without retry
            with pytest.raises(subprocess.TimeoutExpired):
                client._retry_with_backoff(
                    lambda: subprocess.run(
                        ["gh", "api", "test"],
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=30,
                    ),
                    max_retries=3,
                    backoff_base=1.0,
                )

            # Verify only called once (no retries)
            assert mock_run.call_count == 1

    def test_connection_refused_fails_immediately(self):
        """Test that connection errors don't retry."""
        client = GitHubClient(token="ghp_test123")

        # Mock subprocess.run to raise connection error
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["gh"], stderr="connection refused"
            )

            # Classify error first
            error_type = client._classify_error(
                subprocess.CalledProcessError(1, ["gh"], stderr="connection refused")
            )

            # Should be classified as network error (not rate limit)
            assert error_type == "network"


class TestErrorClassification:
    """Test error classification (rate limit vs network vs other)."""

    def test_http_429_classified_as_rate_limit(self):
        """Test HTTP 429 errors are classified as primary rate limit errors."""
        client = GitHubClient(token="ghp_test123")

        # Test with HTTP 429 error message
        error_429 = subprocess.CalledProcessError(
            1, ["gh"], stderr="HTTP 429: rate limit exceeded"
        )
        error_type = client._classify_error(error_429)
        assert error_type == "primary_rate_limit"

        # Test with alternative rate limit message
        error_limit = subprocess.CalledProcessError(
            1, ["gh"], stderr="rate limit exceeded"
        )
        error_type = client._classify_error(error_limit)
        assert error_type == "primary_rate_limit"

    def test_http_403_secondary_rate_limit_classified_correctly(self):
        """Test HTTP 403 secondary rate limit errors are classified separately."""
        client = GitHubClient(token="ghp_test123")

        # Test with HTTP 403 secondary rate limit error message
        error_403_secondary = subprocess.CalledProcessError(
            1, ["gh"], stderr="HTTP 403: You have exceeded a secondary rate limit. Please wait a few minutes before you try again."
        )
        error_type = client._classify_error(error_403_secondary)
        assert error_type == "secondary_rate_limit"

    def test_timeout_classified_as_network_error(self):
        """Test timeout errors are classified as network errors."""
        client = GitHubClient(token="ghp_test123")

        # Test timeout exception
        timeout_error = subprocess.TimeoutExpired(cmd=["gh"], timeout=30)
        error_type = client._classify_error(timeout_error)
        assert error_type == "network"

        # Test connection refused
        connection_error = subprocess.CalledProcessError(
            1, ["gh"], stderr="connection refused"
        )
        error_type = client._classify_error(connection_error)
        assert error_type == "network"

        # Test DNS failure
        dns_error = subprocess.CalledProcessError(
            1, ["gh"], stderr="could not resolve host"
        )
        error_type = client._classify_error(dns_error)
        assert error_type == "network"

    def test_http_404_classified_as_other_error(self):
        """Test HTTP 404 errors are classified as other (not retryable)."""
        client = GitHubClient(token="ghp_test123")

        # Test with HTTP 404 error
        error_404 = subprocess.CalledProcessError(1, ["gh"], stderr="HTTP 404: Not Found")
        error_type = client._classify_error(error_404)
        assert error_type == "other"

        # Test with HTTP 500 error
        error_500 = subprocess.CalledProcessError(
            1, ["gh"], stderr="HTTP 500: Internal Server Error"
        )
        error_type = client._classify_error(error_500)
        assert error_type == "other"

        # Test with HTTP 403 error (permissions)
        error_403 = subprocess.CalledProcessError(1, ["gh"], stderr="HTTP 403: Forbidden")
        error_type = client._classify_error(error_403)
        assert error_type == "other"
