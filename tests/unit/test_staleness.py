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

    result = calculate_staleness(draft_pr)
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

    result = calculate_staleness(approved_pr)
    assert result is None


def test_calculate_staleness_from_ready_time():
    """Test staleness calculation from ready_at time."""
    ready_time = datetime.now(UTC) - timedelta(days=3, hours=6)
    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=datetime.now(UTC) - timedelta(days=5),
        ready_at=ready_time,
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    result = calculate_staleness(pr)
    assert result is not None
    # Should be approximately 3.25 days
    assert 3.2 <= result <= 3.3


def test_calculate_staleness_zero_days():
    """Test staleness for a PR just created."""
    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=datetime.now(UTC),
        ready_at=datetime.now(UTC),
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    result = calculate_staleness(pr)
    assert result is not None
    # Should be very close to 0
    assert result < 0.01


def test_calculate_staleness_exactly_one_day():
    """Test staleness for exactly one day old PR."""
    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=datetime.now(UTC) - timedelta(days=1),
        ready_at=datetime.now(UTC) - timedelta(days=1),
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    result = calculate_staleness(pr)
    assert result is not None
    # Should be approximately 1 day
    assert 0.99 <= result <= 1.01


def test_calculate_staleness_fractional_days():
    """Test staleness with fractional days (hours)."""
    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=datetime.now(UTC) - timedelta(hours=36),
        ready_at=datetime.now(UTC) - timedelta(hours=36),
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    result = calculate_staleness(pr)
    assert result is not None
    # 36 hours = 1.5 days
    assert 1.49 <= result <= 1.51


def test_calculate_staleness_many_days():
    """Test staleness for PRs stale for many days."""
    pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=datetime.now(UTC) - timedelta(days=30),
        ready_at=datetime.now(UTC) - timedelta(days=30),
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )

    result = calculate_staleness(pr)
    assert result is not None
    # Should be approximately 30 days
    assert 29.9 <= result <= 30.1
