# Data Model

**Feature**: Stale PR Board
**Date**: 2025-10-31
**Purpose**: Define all data entities, their fields, types, and relationships

This document describes the core data model for the Stale PR Board application, including all entities with complete type annotations following strict typing standards.

## Type Annotations Standard

All entities follow these conventions:
- Every attribute has an explicit type annotation
- Use `from __future__ import annotations` for forward references
- Use `|` for union types (e.g., `str | None` instead of `Optional[str]`)
- Use `list[T]` instead of `List[T]`, `dict[K, V]` instead of `Dict[K, V]`
- All datetime objects are timezone-aware (`datetime` with `tzinfo`)

## Core Entities

### 1. TeamMember

Represents a member of the development team for whom PRs are tracked.

**Python Definition**:
```python
from __future__ import annotations

from dataclasses import dataclass

@dataclass
class TeamMember:
    """A member of the development team."""

    github_username: str
    """GitHub username of the team member"""

    slack_user_id: str | None = None
    """Slack user ID for @mentions (e.g., 'U1234567890'). If None, falls back to plain text @github_username"""
```

**Fields**:
- `github_username` (str, required): GitHub username, used to filter PRs by author or requested reviewer
- `slack_user_id` (str | None, optional): Slack user ID for proper @mentions in Slack messages. If not provided, username will be displayed as plain text instead of clickable mention.

**Source**: Loaded from `team_members.json` configuration file

**Example**:
```python
member1 = TeamMember(github_username="alice", slack_user_id="U1234567890")
member2 = TeamMember(github_username="bob")  # No Slack ID, plain text fallback
```

---

### 2. PullRequest

Represents a GitHub pull request with all relevant metadata for staleness calculation.

**Python Definition**:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

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

    required_approvals: int
    """Number of required approving reviews from branch protection rules (defaults to 1 if no rules)"""

    base_branch: str
    """Name of the target branch for this PR (e.g., 'main', 'develop')"""

    @property
    def is_draft(self) -> bool:
        """Check if this PR is currently in draft state."""
        return self.ready_at is None

    @property
    def has_sufficient_approval(self) -> bool:
        """Check if PR has sufficient approvals (not stale)."""
        return self.current_approvals >= self.required_approvals
```

**Fields**:
- `repo_name` (str): Repository name for display in Slack
- `number` (int): PR number for identification and linking
- `title` (str): PR title for display in Slack
- `author` (str): PR author's GitHub username (used for @mention)
- `reviewers` (list[str]): List of requested reviewer usernames (used for display in Slack)
- `url` (str): Full GitHub URL for clickable links in Slack
- `created_at` (datetime): PR creation time (timezone-aware)
- `ready_at` (datetime | None): When PR marked ready; None if draft
- `current_approvals` (int): Count of valid approvals (latest per reviewer)
- `required_approvals` (int): Required count from branch protection (default: 1)
- `base_branch` (str): Target branch name (used to get protection rules)

**Computed Properties**:
- `is_draft`: Returns `True` if `ready_at` is `None`
- `has_sufficient_approval`: Returns `True` if `current_approvals >= required_approvals`

**Source**: Fetched from GitHub API via PyGithub

**Example**:
```python
from datetime import datetime, UTC

pr = PullRequest(
    repo_name="review-ops",
    number=123,
    title="Add staleness calculation",
    author="alice",
    reviewers=["bob", "charlie"],
    url="https://github.com/org/review-ops/pull/123",
    created_at=datetime.now(UTC),
    ready_at=datetime.now(UTC),
    current_approvals=1,
    required_approvals=2,
    base_branch="main"
)
```

---

### 3. StalePR

Represents a pull request that lacks sufficient approval, with calculated staleness metrics.

**Python Definition**:
```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

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
            "rotten": "🤢"
        }
        return category_emojis[self.category]
```

**Fields**:
- `pr` (PullRequest): The underlying PR with all metadata
- `staleness_days` (float): Days without sufficient approval (can be fractional)

**Computed Properties**:
- `category`: Categorizes staleness into "fresh", "aging", or "rotten" based on thresholds
- `emoji`: Returns corresponding emoji (✨, 🧀, or 🤢) for visual indication

**Thresholds**:
- Fresh: 1-3 days (✨)
- Aging: 4-7 days (🧀)
- Rotten: 8+ days (🤢)

**Source**: Computed from PullRequest + staleness calculation logic

**Example**:
```python
stale_pr = StalePR(pr=pr, staleness_days=5.2)
print(stale_pr.category)  # "aging"
print(stale_pr.emoji)     # "🧀"
```

---

### 4. Config

Application configuration loaded from environment variables.

**Python Definition**:
```python
from __future__ import annotations

from dataclasses import dataclass

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
```

**Fields**:
- `github_token` (str, required): GitHub PAT with `repo` and `read:org` scopes
- `github_org` (str, required): Organization name (e.g., "my-company")
- `slack_webhook_url` (str, required): Webhook URL from Slack app configuration
- `log_level` (str, optional): Defaults to "INFO"
- `api_timeout` (int, optional): Defaults to 30 seconds

**Source**: Loaded from `.env` file via python-dotenv

**Example**:
```python
config = Config(
    github_token="ghp_xxxxxxxxxxxxxxxxxxxx",
    github_org="my-company",
    slack_webhook_url="https://hooks.slack.com/services/T00/B00/XXXX",
    log_level="DEBUG",
    api_timeout=60
)
```

---

## Entity Relationships

### Data Flow Diagram

```
┌─────────────────┐
│  team_members   │
│  .json file     │
└────────┬────────┘
         │
         │ load_team_members()
         ↓
┌─────────────────┐      ┌─────────────────┐
│   TeamMember    │      │     .env file   │
│   (list)        │      └────────┬────────┘
└────────┬────────┘               │
         │                         │ validate_config()
         │                         ↓
         │              ┌─────────────────┐
         │              │     Config      │
         │              └────────┬────────┘
         │                       │
         │                       │ initialize clients
         │                       ↓
         │              ┌─────────────────────┐
         │              │   GitHubClient      │
         │              │   SlackClient       │
         │              └────────┬────────────┘
         │                       │
         │              ┌────────┴─────────┐
         │              │                  │
         │              │ fetch_prs()      │
         │              ↓                  │
         │        ┌──────────────┐        │
         └───────→│ PullRequest  │        │
                  │    (list)    │        │
                  └──────┬───────┘        │
                         │                │
                         │ filter by team │
                         │ calculate_staleness()
                         ↓                │
                  ┌─────────────┐        │
                  │  StalePR    │        │
                  │   (list)    │        │
                  └──────┬──────┘        │
                         │                │
                         │ sort by staleness
                         │ format_message()
                         ↓                │
                  ┌─────────────┐        │
                  │   Slack     │        │
                  │   Message   │◄───────┘
                  │   (blocks)  │
                  └─────────────┘
```

### Relationship Descriptions

1. **TeamMember → PR Filtering**
   - Input: List of `TeamMember` objects with GitHub usernames
   - Process: Filter `PullRequest` list where PR author OR any requested reviewer matches team username
   - Output: Subset of PRs involving team members

2. **Config → Client Initialization**
   - Input: `Config` object with tokens and URLs
   - Process: Initialize `GitHubClient` with token and `SlackClient` with webhook URL
   - Output: Configured clients ready for API calls

3. **PullRequest → StalePR Transformation**
   - Input: `PullRequest` object + staleness calculation
   - Process: Calculate days since ready/approval-loss, determine if stale (lacks sufficient approval)
   - Output: `StalePR` object if stale, or `None` if sufficient approval
   - Condition: Only PRs with `current_approvals < required_approvals` become `StalePR`

4. **StalePR List → Slack Message**
   - Input: List of `StalePR` objects
   - Process: Sort by `staleness_days` (descending), group by `category`, format as Slack Block Kit
   - Output: JSON payload with blocks for Slack webhook

### Cardinality

- **TeamMember** (5-20): Small, defined team
- **PullRequest** (10-200): All open PRs in org involving team
- **StalePR** (0-50): Subset of PRs lacking approval
- **Config** (1): Single configuration instance
- **Slack Message** (1): Single message per execution

## Implementation Notes

### Type Safety

All entities enforce type safety through:
1. **Dataclasses with type annotations**: Runtime validation via Python's type system
2. **Type checker enforcement**: `ty` or `mypy` with strict mode
3. **Linter enforcement**: `ruff` with ANN rules (flake8-annotations)

### Immutability

All entities are **data classes** (read-only after creation):
- No setters or mutating methods
- New instances created for transformations
- Aligns with functional programming principles

### Validation

- **TeamMember**: Validated during JSON loading (`load_team_members()`)
- **PullRequest**: Validated during GitHub API fetch (fields guaranteed by API)
- **StalePR**: Validated during construction (staleness_days must be ≥ 0)
- **Config**: Validated during environment loading (`validate_config()`)

### Timezone Awareness

All `datetime` fields must be timezone-aware:
```python
from datetime import datetime, UTC

# ✅ GOOD
pr.created_at = datetime.now(UTC)

# ❌ BAD
pr.created_at = datetime.now()  # Naive datetime
```

This ensures correct staleness calculations across different timezones.

## Usage Examples

### Complete Flow

```python
from datetime import datetime, UTC, timedelta

# 1. Load configuration
config = validate_config()
team = load_team_members()

# 2. Initialize clients
github_client = GitHubClient(config.github_token)
slack_client = SlackClient(config.slack_webhook_url)

# 3. Fetch PRs
all_prs = github_client.fetch_all_prs(config.github_org)

# 4. Filter by team
team_usernames = [member.github_username for member in team]
team_prs = [
    pr for pr in all_prs
    if pr.author in team_usernames or
       any(reviewer in team_usernames for reviewer in pr.reviewers)
]

# 5. Calculate staleness
stale_prs: list[StalePR] = []
for pr in team_prs:
    if not pr.has_sufficient_approval:
        staleness = calculate_staleness(pr)
        if staleness is not None:
            stale_prs.append(StalePR(pr=pr, staleness_days=staleness))

# 6. Sort by staleness (most stale first)
stale_prs.sort(key=lambda s: s.staleness_days, reverse=True)

# 7. Format and send Slack message
if stale_prs:
    message_blocks = format_stale_pr_message(stale_prs, team)
    slack_client.send_message(message_blocks)
else:
    # Send celebratory message
    message_blocks = format_no_stale_prs_message()
    slack_client.send_message(message_blocks)
```

### Grouping by Category

```python
from collections import defaultdict

# Group StalePRs by category
by_category: dict[str, list[StalePR]] = defaultdict(list)
for stale_pr in stale_prs:
    by_category[stale_pr.category].append(stale_pr)

# Access each category
rotten = by_category["rotten"]  # 8+ days
aging = by_category["aging"]    # 4-7 days
fresh = by_category["fresh"]    # 1-3 days

print(f"🤢 Rotten: {len(rotten)}")
print(f"🧀 Aging: {len(aging)}")
print(f"✨ Fresh: {len(fresh)}")
```

## File Locations

**Entity Definitions**:
- `src/models.py`: All dataclass definitions (TeamMember, PullRequest, StalePR, Config)

**Related Modules**:
- `src/app.py`: Main application entry point and CLI
- `src/config.py`: Config loading and TeamMember loading
- `src/github_client.py`: PullRequest fetching from GitHub API
- `src/staleness.py`: PullRequest → StalePR transformation
- `src/slack_client.py`: StalePR list → Slack message formatting

## Next Steps

With the data model defined, proceed to:
1. Generate API contracts (contracts/ directory)
2. Generate quickstart guide (quickstart.md)
3. Update agent context
4. Begin implementation with TDD approach (tests first, then models.py)
