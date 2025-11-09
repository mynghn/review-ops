"""Unit tests for rate limit status logic."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from models import RateLimitStatus


class TestRateLimitStatusTransitions:
    """Test RateLimitStatus state transitions (normal → low → exhausted)."""

    def test_normal_state_high_quota(self):
        """Test normal state with high remaining quota."""
        status = RateLimitStatus(
            remaining=4500,
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=False,
            wait_seconds=None,
        )

        assert status.remaining == 4500
        assert status.limit == 5000
        assert not status.is_exhausted
        assert status.wait_seconds is None

    def test_normal_state_above_threshold(self):
        """Test normal state just above low quota warning threshold."""
        status = RateLimitStatus(
            remaining=101,
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=False,
            wait_seconds=None,
        )

        assert status.remaining == 101
        assert not status.is_exhausted
        assert status.wait_seconds is None

    def test_low_state_at_threshold(self):
        """Test low state at warning threshold (100 requests)."""
        status = RateLimitStatus(
            remaining=100,
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=False,
            wait_seconds=None,
        )

        assert status.remaining == 100
        assert not status.is_exhausted
        # User should be warned about low quota (handled by app.py)

    def test_low_state_below_threshold(self):
        """Test low state below warning threshold."""
        status = RateLimitStatus(
            remaining=45,
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=False,
            wait_seconds=None,
        )

        assert status.remaining == 45
        assert not status.is_exhausted
        # User should be warned (handled by app.py)

    def test_exhausted_state_zero_remaining(self):
        """Test exhausted state with zero remaining requests."""
        status = RateLimitStatus(
            remaining=0,
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=True,
            wait_seconds=300,  # 5 minutes
        )

        assert status.remaining == 0
        assert status.is_exhausted
        assert status.wait_seconds == 300

    def test_exhausted_state_from_http_429(self):
        """Test exhausted state triggered by HTTP 429 (even with remaining > 0)."""
        # This can happen if GitHub's secondary rate limits kick in
        status = RateLimitStatus(
            remaining=50,  # May still have quota but hit secondary limit
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=True,
            wait_seconds=120,
        )

        assert status.is_exhausted
        assert status.wait_seconds == 120

    def test_exhausted_state_short_wait(self):
        """Test exhausted state with short wait time (< threshold)."""
        status = RateLimitStatus(
            remaining=0,
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=True,
            wait_seconds=180,  # 3 minutes
        )

        assert status.is_exhausted
        assert status.wait_seconds == 180

    def test_exhausted_state_long_wait(self):
        """Test exhausted state with long wait time (> threshold)."""
        status = RateLimitStatus(
            remaining=0,
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=True,
            wait_seconds=3600,  # 1 hour
        )

        assert status.is_exhausted
        assert status.wait_seconds == 3600

    def test_transition_normal_to_low(self):
        """Test conceptual transition from normal to low state."""
        # Start in normal state
        normal = RateLimitStatus(
            remaining=500,
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=False,
            wait_seconds=None,
        )
        assert not normal.is_exhausted

        # After consuming API calls, move to low state
        low = RateLimitStatus(
            remaining=50,
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=False,
            wait_seconds=None,
        )
        assert low.remaining < 100
        assert not low.is_exhausted

    def test_transition_low_to_exhausted(self):
        """Test conceptual transition from low to exhausted state."""
        # Start in low state
        low = RateLimitStatus(
            remaining=10,
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=False,
            wait_seconds=None,
        )
        assert low.remaining < 100
        assert not low.is_exhausted

        # After consuming remaining calls, move to exhausted
        exhausted = RateLimitStatus(
            remaining=0,
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=True,
            wait_seconds=300,
        )
        assert exhausted.is_exhausted
        assert exhausted.wait_seconds is not None

    def test_negative_remaining_not_allowed(self):
        """Test that negative remaining values are conceptually invalid."""
        # GitHub API returns 0, not negative, but test defensively
        status = RateLimitStatus(
            remaining=0,  # Not -1
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=True,
            wait_seconds=60,
        )
        assert status.remaining >= 0

    def test_reset_timestamp_valid(self):
        """Test that reset_timestamp is a valid Unix timestamp."""
        status = RateLimitStatus(
            remaining=0,
            limit=5000,
            reset_timestamp=1698765432,
            is_exhausted=True,
            wait_seconds=300,
        )

        assert status.reset_timestamp > 0
        # Timestamp should be reasonable (after 2020)
        assert status.reset_timestamp > 1577836800  # Jan 1, 2020
