"""Unit tests for data models."""

from __future__ import annotations

from datetime import UTC, datetime

from models import PullRequest, StalePR, TeamMember


def test_team_member_with_slack_id():
    """Test TeamMember creation with Slack ID."""
    member = TeamMember(github_username="alice", slack_user_id="U1234567890")
    assert member.github_username == "alice"
    assert member.slack_user_id == "U1234567890"


def test_team_member_without_slack_id():
    """Test TeamMember creation without Slack ID."""
    member = TeamMember(github_username="bob")
    assert member.github_username == "bob"
    assert member.slack_user_id is None


def test_pull_request_is_draft():
    """Test PullRequest.is_draft property."""
    # Draft PR (ready_at is None)
    draft_pr = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Draft PR",
        author="alice",
        reviewers=[],
        url="https://github.com/org/repo/pull/1",
        created_at=datetime.now(UTC),
        ready_at=None,
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )
    assert draft_pr.is_draft is True

    # Ready PR (ready_at is set)
    ready_pr = PullRequest(
        repo_name="test-repo",
        number=2,
        title="Ready PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/2",
        created_at=datetime.now(UTC),
        ready_at=datetime.now(UTC),
        current_approvals=0,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )
    assert ready_pr.is_draft is False


def test_pull_request_has_sufficient_approval():
    """Test PullRequest.has_sufficient_approval property with review_status."""
    # Review status: APPROVED
    pr_approved = PullRequest(
        repo_name="test-repo",
        number=1,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/1",
        created_at=datetime.now(UTC),
        ready_at=datetime.now(UTC),
        current_approvals=2,
        review_status="APPROVED",
        base_branch="main",
    )
    assert pr_approved.has_sufficient_approval is True

    # Review status: REVIEW_REQUIRED
    pr_review_required = PullRequest(
        repo_name="test-repo",
        number=2,
        title="Test PR",
        author="alice",
        reviewers=["bob", "charlie"],
        url="https://github.com/org/repo/pull/2",
        created_at=datetime.now(UTC),
        ready_at=datetime.now(UTC),
        current_approvals=1,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )
    assert pr_review_required.has_sufficient_approval is False

    # Review status: CHANGES_REQUESTED
    pr_changes_requested = PullRequest(
        repo_name="test-repo",
        number=3,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/3",
        created_at=datetime.now(UTC),
        ready_at=datetime.now(UTC),
        current_approvals=0,
        review_status="CHANGES_REQUESTED",
        base_branch="main",
    )
    assert pr_changes_requested.has_sufficient_approval is False

    # Fallback: review_status is None but has approvals
    pr_fallback_with_approvals = PullRequest(
        repo_name="test-repo",
        number=4,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/4",
        created_at=datetime.now(UTC),
        ready_at=datetime.now(UTC),
        current_approvals=1,
        review_status=None,
        base_branch="main",
    )
    assert pr_fallback_with_approvals.has_sufficient_approval is True

    # Fallback: review_status is None and no approvals
    pr_fallback_no_approvals = PullRequest(
        repo_name="test-repo",
        number=5,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/5",
        created_at=datetime.now(UTC),
        ready_at=datetime.now(UTC),
        current_approvals=0,
        review_status=None,
        base_branch="main",
    )
    assert pr_fallback_no_approvals.has_sufficient_approval is False


def test_stale_pr_category_fresh():
    """Test StalePR.category for fresh PRs (1-3 days)."""
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
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

    # 1 day
    stale_pr = StalePR(pr=pr, staleness_days=1.0)
    assert stale_pr.category == "fresh"

    # 3 days
    stale_pr = StalePR(pr=pr, staleness_days=3.0)
    assert stale_pr.category == "fresh"

    # 3.99 days (edge case)
    stale_pr = StalePR(pr=pr, staleness_days=3.99)
    assert stale_pr.category == "fresh"


def test_stale_pr_category_aging():
    """Test StalePR.category for aging PRs (4-7 days)."""
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
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

    # 4 days
    stale_pr = StalePR(pr=pr, staleness_days=4.0)
    assert stale_pr.category == "aging"

    # 7 days
    stale_pr = StalePR(pr=pr, staleness_days=7.0)
    assert stale_pr.category == "aging"

    # 7.99 days (edge case)
    stale_pr = StalePR(pr=pr, staleness_days=7.99)
    assert stale_pr.category == "aging"


def test_stale_pr_category_rotten():
    """Test StalePR.category for rotten PRs (8+ days)."""
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
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

    # 8 days
    stale_pr = StalePR(pr=pr, staleness_days=8.0)
    assert stale_pr.category == "rotten"

    # 30 days
    stale_pr = StalePR(pr=pr, staleness_days=30.0)
    assert stale_pr.category == "rotten"


def test_stale_pr_emoji():
    """Test StalePR.emoji property."""
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
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

    # Fresh emoji
    stale_pr_fresh = StalePR(pr=pr, staleness_days=2.0)
    assert stale_pr_fresh.emoji == "✨"

    # Aging emoji
    stale_pr_aging = StalePR(pr=pr, staleness_days=5.0)
    assert stale_pr_aging.emoji == "🧀"

    # Rotten emoji
    stale_pr_rotten = StalePR(pr=pr, staleness_days=10.0)
    assert stale_pr_rotten.emoji == "🤢"
