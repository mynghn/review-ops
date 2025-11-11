"""Data models for the Stale PR Board application."""

from __future__ import annotations

from dataclasses import dataclass, field
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
class GitHubTeamReviewRequest:
    """A GitHub team review request with resolved member list."""

    team_name: str
    """Display name of the GitHub team (e.g., 'Backend Team')"""

    team_slug: str
    """URL-safe slug of the GitHub team (e.g., 'backend-team')"""

    members: list[str]
    """List of GitHub usernames of team members"""


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

    github_team_reviewers: list[GitHubTeamReviewRequest] = field(default_factory=list)
    """List of GitHub team review requests with resolved members"""

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
    Number of business days the PR has been without sufficient approval.
    Business days exclude weekends (Sat/Sun) and holidays.
    Calculated from the most recent of:
    - When PR was marked ready for review
    - When PR lost approval (new commits after approval)
    """

    @property
    def category(self) -> Literal["fresh", "aging", "rotten"]:
        """
        Categorize staleness level (business days):
        - fresh: 0-3 days
        - aging: 4-10 days
        - rotten: 11+ days
        """
        if self.staleness_days >= 11:
            return "rotten"
        elif self.staleness_days >= 4:
            return "aging"
        else:
            return "fresh"

    @property
    def emoji(self) -> str:
        """
        Get emoji representing staleness category (business days):
        - ✨ (sparkles): fresh (0-3 days)
        - 🧀 (cheese): aging (4-10 days)
        - 🤢 (nauseated face): rotten (11+ days)
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

    slack_bot_token: str
    """Slack Bot User OAuth Token for chat.postMessage API"""

    slack_channel_id: str
    """Slack channel ID where messages will be posted"""

    log_level: str = "INFO"
    """Logging level (DEBUG, INFO, WARNING, ERROR)"""

    gh_search_window_size: int = 30
    """Number of days to look back for recently updated PRs"""

    language: str = "en"
    """Language for Slack message formatting ('en' or 'ko')"""

    max_prs_total: int = 30
    """Total PRs to display across all categories"""

    rate_limit_wait_threshold: int = 300
    """Max auto-wait seconds (5 minutes default)"""

    show_non_team_reviewers: bool = True
    """Whether to show non-team member reviewers in table"""

    holidays_country: str = "US"
    """Country code for holiday calendar used in business day calculation (e.g., 'US', 'KR')"""


@dataclass
class RateLimitStatus:
    """GitHub API rate limit status for decision-making."""

    remaining: int
    """Remaining API calls in current window"""

    limit: int
    """Total API calls allowed per window"""

    reset_timestamp: int
    """Unix timestamp when quota resets"""

    is_exhausted: bool
    """Whether quota is depleted (remaining == 0 or HTTP 429)"""

    wait_seconds: int | None
    """Seconds until reset (None if not exhausted)"""

    @property
    def reset_time(self) -> datetime:
        """Get reset time as datetime object."""
        return datetime.fromtimestamp(self.reset_timestamp)

    @property
    def should_wait(self) -> bool:
        """Check if wait time is reasonable (< 5 minutes default threshold)."""
        if self.wait_seconds is None:
            return False
        return self.wait_seconds <= 300  # 5 minutes


@dataclass
class APICallMetrics:
    """Track API usage and optimization effectiveness."""

    search_calls: int = 0
    """Number of search API calls made"""

    rest_detail_calls: int = 0
    """Number of individual REST calls avoided (via GraphQL)"""

    graphql_calls: int = 0
    """Number of GraphQL batch queries made"""

    retry_attempts: int = 0
    """Total retry attempts across all calls"""

    failed_calls: int = 0
    """Number of calls that failed after retries"""

    @property
    def total_api_points(self) -> int:
        """
        Calculate approximate GitHub rate limit points consumed.

        Formula: search_calls + graphql_calls * 2 + rest_detail_calls
        """
        return self.search_calls + self.graphql_calls * 2 + self.rest_detail_calls

    @property
    def optimization_rate(self) -> float:
        """
        Calculate percentage of REST calls saved via GraphQL batching.

        Returns 0.0 if GraphQL not used.
        """
        total_detail_calls = self.rest_detail_calls + self.graphql_calls
        if total_detail_calls == 0:
            return 0.0
        return (self.rest_detail_calls / total_detail_calls) * 100

    @property
    def success_rate(self) -> float:
        """
        Calculate percentage of successful API calls.

        Returns 100.0 if no calls made.
        """
        total_calls = self.search_calls + self.graphql_calls + self.rest_detail_calls
        if total_calls == 0:
            return 100.0
        successful = total_calls - self.failed_calls
        return (successful / total_calls) * 100


@dataclass
class OldPRReport:
    """A report entry for an old PR time range with GitHub search URL."""

    title: str
    """Display title for this report (e.g., "PRs updated 31-60 days ago")"""

    pr_count: int
    """Number of PRs found in this time range"""

    github_url: str
    """GitHub search URL to view these PRs"""

    time_range_description: str
    """Human-readable description of time range (e.g., "31-60 days")"""
