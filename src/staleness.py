"""Staleness calculation logic for pull requests."""

from __future__ import annotations

from datetime import UTC, datetime

from models import PullRequest


def calculate_staleness(pr: PullRequest) -> float | None:
    """
    Calculate staleness in days for a pull request.

    A PR is considered stale if it lacks sufficient approvals.
    Staleness is calculated from the time the PR was ready for review.

    Args:
        pr: The pull request to calculate staleness for

    Returns:
        Number of days the PR has been stale, or None if:
        - PR is a draft (ready_at is None)
        - PR has sufficient approvals (current_approvals >= required_approvals)

    Notes:
        - Draft PRs are excluded from staleness calculation
        - PRs with sufficient approval are not considered stale
        - Staleness is calculated as days since ready_at timestamp
        - Returns fractional days (e.g., 1.5 for 36 hours)
    """
    # Skip draft PRs
    if pr.is_draft:
        return None

    # Skip PRs with sufficient approval
    if pr.has_sufficient_approval:
        return None

    # Calculate staleness from ready_at time
    if pr.ready_at is None:
        # This shouldn't happen as is_draft checks ready_at, but handle defensively
        return None

    now = datetime.now(UTC)
    staleness_seconds = (now - pr.ready_at).total_seconds()
    staleness_days = staleness_seconds / 86400  # 86400 seconds in a day

    return staleness_days
