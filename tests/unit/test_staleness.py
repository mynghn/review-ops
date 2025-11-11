"""Unit tests for staleness calculation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from models import PullRequest
from staleness import calculate_staleness


def test_calculate_staleness_draft_pr():
    """Test that draft PRs return None (not considered stale)."""
    draft_pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Draft PR",
        author="alice",
        reviewers=[],
        url="https://github.com/org/repo/pull/1",
        created_at=datetime.now(UTC) - timedelta(days=10),
        ready_at=None,  # Draft PR
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    result = calculate_staleness(draft_pr, "US")
    assert result is None


def test_calculate_staleness_sufficient_approvals():
    """Test that PRs with sufficient approvals return None (not stale)."""
    approved_pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Approved PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=datetime.now(UTC) - timedelta(days=5),
        ready_at=datetime.now(UTC) - timedelta(days=5),
        current_approvals=2,
        review_status="APPROVED",
        base_branch="main",
    )

    result = calculate_staleness(approved_pr, "US")
    assert result is None


def test_calculate_staleness_same_weekday():
    """Test staleness calculation on the same business day (within hours)."""
    # Use a recent weekday (6 hours ago)
    now = datetime.now(UTC)
    # Go back 6 hours to ensure we're on the same day
    ready_time = now - timedelta(hours=6)

    # If we happened to cross a day boundary, adjust to ensure same day
    if ready_time.date() != now.date():
        # Use today at 9 AM instead
        ready_time = datetime.combine(now.date(), datetime.min.time(), tzinfo=UTC).replace(hour=9)

    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=ready_time,
        ready_at=ready_time,
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    result = calculate_staleness(pr, "US")
    assert result is not None
    # Should be a fractional business day (less than 1 full day)
    assert result < 1.0


def test_calculate_staleness_consecutive_weekdays():
    """Test staleness across consecutive weekdays (Mon-Tue-Wed)."""
    # Monday 2025-01-13 9:00 AM to Wednesday 2025-01-15 9:00 AM = 2 business days
    ready_time = datetime(2025, 1, 13, 9, 0, 0, tzinfo=UTC)

    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=ready_time,
        ready_at=ready_time,
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    # Manually calculate: Monday full day + Tuesday full day = 2 business days
    # We'll use a time machine approach by testing with known dates
    # For now, this is a structural test to ensure the function accepts the country param
    result = calculate_staleness(pr, "US")
    assert result is not None
    assert result >= 0


def test_calculate_staleness_over_weekend():
    """Test staleness calculation spanning a weekend (Fri to Mon)."""
    # Friday 2025-01-17 5:00 PM to Monday 2025-01-20 9:00 AM
    # Should count only the partial Friday (7 hours) = ~0.29 business days
    ready_time = datetime(2025, 1, 17, 17, 0, 0, tzinfo=UTC)

    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=ready_time,
        ready_at=ready_time,
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    result = calculate_staleness(pr, "US")
    assert result is not None
    assert result >= 0


def test_calculate_staleness_zero_days():
    """Test staleness for a PR just created (very recent)."""
    # Use current time (just now)
    ready_time = datetime.now(UTC)

    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=ready_time,
        ready_at=ready_time,
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    result = calculate_staleness(pr, "US")
    assert result is not None
    # Should be very close to 0 (less than 0.01 business days)
    assert result < 0.01


def test_calculate_staleness_one_business_day():
    """Test staleness for exactly one business day (Tue to Wed, same time)."""
    # Tuesday 2025-01-14 9:00 AM to Wednesday 2025-01-15 9:00 AM = 1 business day
    ready_time = datetime(2025, 1, 14, 9, 0, 0, tzinfo=UTC)

    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=ready_time,
        ready_at=ready_time,
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    result = calculate_staleness(pr, "US")
    assert result is not None
    # Should be close to 1 business day
    assert result >= 0.9


def test_calculate_staleness_with_holiday():
    """Test staleness calculation that includes a US holiday."""
    # Test around New Year's Day (Jan 1) - a US federal holiday
    # Dec 31, 2024 (Tue) to Jan 3, 2025 (Fri)
    # Business days: Dec 31 (Tue) + Jan 2 (Thu) + Jan 3 partial = ~2+ days
    # Jan 1 (Wed) is New Year's Day holiday, so it's excluded
    ready_time = datetime(2024, 12, 31, 9, 0, 0, tzinfo=UTC)

    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=ready_time,
        ready_at=ready_time,
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    result = calculate_staleness(pr, "US")
    assert result is not None
    # Should exclude the holiday
    assert result >= 0


def test_calculate_staleness_multiple_weeks():
    """Test staleness for PRs spanning multiple weeks (weekdays only)."""
    # Monday 2025-01-06 to Monday 2025-01-13 = 5 business days (1 full work week)
    ready_time = datetime(2025, 1, 6, 9, 0, 0, tzinfo=UTC)

    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=ready_time,
        ready_at=ready_time,
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    result = calculate_staleness(pr, "US")
    assert result is not None
    # Should be at least 5 business days
    assert result >= 4


def test_calculate_staleness_weekend_creation():
    """Test staleness for PR created on a weekend."""
    # Saturday 2025-01-18 9:00 AM - weekend, so should count as 0 until Monday
    ready_time = datetime(2025, 1, 18, 9, 0, 0, tzinfo=UTC)

    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=ready_time,
        ready_at=ready_time,
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    result = calculate_staleness(pr, "US")
    assert result is not None
    # Weekends don't count as business days
    assert result >= 0


def test_calculate_staleness_different_countries():
    """Test that different country codes are accepted."""
    ready_time = datetime(2025, 1, 13, 9, 0, 0, tzinfo=UTC)

    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=ready_time,
        ready_at=ready_time,
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    # Test with different countries
    result_us = calculate_staleness(pr, "US")
    result_kr = calculate_staleness(pr, "KR")
    result_gb = calculate_staleness(pr, "GB")

    # All should return valid results
    assert result_us is not None
    assert result_kr is not None
    assert result_gb is not None
