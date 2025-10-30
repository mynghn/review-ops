"""Data models for the Stale PR Board application."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class TeamMember:
    """A member of the development team."""

    github_username: str
    """GitHub username of the team member"""

    slack_user_id: str | None = None
    """Slack user ID for @mentions (e.g., 'U1234567890').
    If None, falls back to plain text @github_username
    """


@dataclass
class PullRequest:
    """A GitHub pull request."""

    repo_name: str
    """Repository name (e.g., 'review-ops')"""

    number: int
    """PR number within the repository"""

    title: str
    """PR title"""

    author: str
    """GitHub username of the PR author"""

    reviewers: list[str]
    """List of GitHub usernames of requested reviewers"""

    url: str
    """Full URL to the PR on GitHub (e.g., 'https://github.com/org/repo/pull/123')"""

    created_at: datetime
    """Timestamp when the PR was created (timezone-aware)"""

    ready_at: datetime | None
    """
    Timestamp when the PR was marked 'Ready for Review'.
    None if the PR is currently in draft state.
    For MVP, may fall back to created_at if PR was never a draft.
    """

    current_approvals: int
    """Number of currently valid approving reviews (not dismissed, not invalidated)"""

    review_status: str | None
    """
    GitHub's computed review status based on branch protection rules.
    Values: 'APPROVED', 'CHANGES_REQUESTED', 'REVIEW_REQUIRED', or None.
    None indicates no review requirements configured or gh CLI unavailable.
    """

    base_branch: str
    """Name of the target branch for this PR (e.g., 'main', 'develop')"""

    @property
    def is_draft(self) -> bool:
        """Check if this PR is currently in draft state."""
        return self.ready_at is None

    @property
    def has_sufficient_approval(self) -> bool:
        """Check if PR has sufficient approvals (not stale)."""
        # If review_status is available, use it (more accurate)
        if self.review_status is not None:
            return self.review_status == "APPROVED"
        # Fallback: if no review requirements configured, consider approved if has any approval
        return self.current_approvals > 0


@dataclass
class StalePR:
    """A stale pull request with staleness calculation."""

    pr: PullRequest
    """The underlying pull request"""

    staleness_days: float
    """
    Number of days the PR has been without sufficient approval.
    Calculated from the most recent of:
    - When PR was marked ready for review
    - When PR lost approval (new commits after approval)
    """

    @property
    def category(self) -> Literal["fresh", "aging", "rotten"]:
        """
        Categorize staleness level:
        - fresh: 1-3 days
        - aging: 4-7 days
        - rotten: 8+ days
        """
        if self.staleness_days >= 8:
            return "rotten"
        elif self.staleness_days >= 4:
            return "aging"
        else:
            return "fresh"

    @property
    def emoji(self) -> str:
        """
        Get emoji representing staleness category:
        - ✨ (sparkles): fresh (1-3 days)
        - 🧀 (cheese): aging (4-7 days)
        - 🤢 (nauseated face): rotten (8+ days)
        """
        category_emojis = {
            "fresh": "✨",
            "aging": "🧀",
            "rotten": "🤢",
        }
        return category_emojis[self.category]


@dataclass
class Config:
    """Application configuration from environment variables."""

    github_token: str
    """GitHub Personal Access Token for API authentication"""

    github_org: str
    """GitHub organization name to scan for PRs"""

    slack_webhook_url: str
    """Slack incoming webhook URL for sending notifications"""

    log_level: str = "INFO"
    """Logging level (DEBUG, INFO, WARNING, ERROR)"""

    api_timeout: int = 30
    """API request timeout in seconds"""
