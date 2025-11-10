# Data Model: Refine Review-Needed PR Criteria

**Feature**: 005-refine-review-filter
**Date**: 2025-11-10
**Status**: Complete

## Overview

This feature requires minimal data model changes. The existing data models in `src/models.py` already support the required functionality. This document describes how existing models will be used and identifies one new internal data structure needed for tracking search query origins.

## Existing Models (No Changes Required)

### PullRequest

**Location**: `src/models.py` (lines 38-98)

**Purpose**: Represents a GitHub pull request with all review-related metadata

**Fields Used by This Feature**:

```python
@dataclass
class PullRequest:
    repo_name: str                                    # Repository name
    number: int                                       # PR number
    title: str                                        # PR title
    author: str                                       # PR author GitHub username
    reviewers: list[str]                              # Individual requested reviewers (from reviewRequests)
    github_team_reviewers: list[GitHubTeamReviewRequest]  # Team requested reviewers (from reviewRequests)
    url: str                                          # PR URL
    created_at: datetime                              # Creation timestamp
    ready_at: datetime | None                         # When marked ready for review
    current_approvals: int                            # Count of approving reviews
    review_status: str | None                         # GitHub review decision (APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED, None)
    base_branch: str                                  # Target branch
```

**Key Properties**:

- `reviewers`: Contains individual GitHub usernames from `reviewRequests` field
- `github_team_reviewers`: Contains GitHub teams from `reviewRequests` with expanded member lists
- `review_status`: Distinguishes between APPROVED (all reviews obtained) and REVIEW_REQUIRED (more reviews needed)

**Usage in This Feature**:

1. **Filtering**: Check if team members appear in `reviewers` or `github_team_reviewers[].members`
2. **Display**: Show only reviewers from `reviewers` list (already reflects current `reviewRequests`)
3. **Deduplication**: Use `(repo_name, number)` as unique key

**No modifications needed** - existing fields support all requirements.

---

### GitHubTeamReviewRequest

**Location**: `src/models.py` (lines 24-35)

**Purpose**: Represents a GitHub team review request with resolved member list

**Fields**:

```python
@dataclass
class GitHubTeamReviewRequest:
    team_name: str        # Display name (e.g., "Backend Team")
    team_slug: str        # URL-safe slug (e.g., "backend-team")
    members: list[str]    # GitHub usernames of team members
```

**Usage in This Feature**:

1. **Filtering**: Check if any team members from tracked team appear in `members` list
2. **Display**: Show `team_name` in reviewer column (not expanded members)
3. **Team Expansion**: Populate `members` via existing `_fetch_github_team_members()` method

**No modifications needed** - existing fields support all requirements.

---

### TeamMember

**Location**: `src/models.py` (lines 11-21)

**Purpose**: Represents a tracked team member with GitHub and Slack identities

**Fields**:

```python
@dataclass
class TeamMember:
    github_username: str       # GitHub username
    slack_user_id: str | None  # Slack user ID for @mentions
```

**Usage in This Feature**:

1. **Search**: Use `github_username` to construct search queries
2. **Filtering**: Compare `github_username` (case-insensitive) with `reviewers` and `github_team_reviewers[].members`

**No modifications needed** - existing fields support all requirements.

---

## New Internal Data Structures

### PRSearchMetadata

**Purpose**: Track which search query found each PR to enable conditional filtering

**Type**: Dictionary (in-memory only, not a dataclass)

**Structure**:

```python
# Key: (repo_full_name, pr_number)
# Value: set of search query types that found this PR
pr_search_metadata: dict[tuple[str, int], set[str]] = {}

# Example:
# {
#   ("org/repo1", 123): {"review:none"},
#   ("org/repo2", 456): {"review:required"},
#   ("org/repo3", 789): {"review:none", "review:required"}  # Found by both
# }
```

**Usage**:

1. **During Search Phase**: Add entry when PR key is discovered
   ```python
   pr_key = (repo_full_name, pr_number)
   if pr_key not in pr_search_metadata:
       pr_search_metadata[pr_key] = set()
   pr_search_metadata[pr_key].add("review:required")
   ```

2. **During Filtering Phase**: Check if PR came from review:required search
   ```python
   if "review:required" in pr_search_metadata.get(pr_key, set()):
       # Apply team member filtering
   ```

**Lifecycle**: Created in `fetch_team_prs()`, used during filtering, discarded after filtering completes

**Rationale**:

- Filtering applies ONLY to `review:required` PRs (spec FR-003)
- `review:none` PRs must be included without filtering
- Need to track search origin to apply conditional filtering
- Dictionary with tuple keys is efficient (O(1) lookup) and simple

**Alternative Considered**: Add `search_queries: set[str]` field to `PullRequest` model
- **Rejected**: Pollutes the model with temporary metadata not needed outside `fetch_team_prs()`
- Internal dictionary is cleaner and scoped to the method

---

## Entity Relationships

```text
PullRequest
├── reviewers: list[str]                          # Individual reviewers from reviewRequests
├── github_team_reviewers: list[GitHubTeamReviewRequest]
│   └── members: list[str]                        # Expanded team members
└── (Used for filtering against)
    TeamMember.github_username                     # Tracked team members

PRSearchMetadata (internal)
├── Key: (repo_name, number) -> Maps to PullRequest identity
└── Value: set[str] -> Tracks which searches found this PR
```

**Filtering Logic Flow**:

1. Search Phase: Collect PR keys + populate `PRSearchMetadata`
2. Detail Fetch Phase: Fetch `PullRequest` objects for unique keys
3. Filtering Phase:
   ```python
   for pr in all_prs:
       pr_key = (pr.repo_name, pr.number)
       if "review:required" in pr_search_metadata.get(pr_key, set()):
           # Check if any team member in pr.reviewers or pr.github_team_reviewers[].members
           if not has_team_member(pr, team_members):
               # Exclude PR
               continue
       # Include PR
       filtered_prs.append(pr)
   ```

---

## Validation Rules

### Team Member Presence Check (FR-013)

**Rule**: Case-insensitive comparison of GitHub usernames

**Implementation**:

```python
def has_team_member(pr: PullRequest, team_members: list[TeamMember]) -> bool:
    """Check if any team member is in PR's requested reviewers."""
    team_usernames_lower = {member.github_username.lower() for member in team_members}

    # Check individual reviewers
    for reviewer in pr.reviewers:
        if reviewer.lower() in team_usernames_lower:
            return True

    # Check GitHub team reviewers (expanded members)
    for team_review in pr.github_team_reviewers:
        for member_username in team_review.members:
            if member_username.lower() in team_usernames_lower:
                return True

    return False
```

**Rationale**: GitHub usernames are case-insensitive, so "Alice" and "alice" refer to the same user

---

### Empty reviewRequests Handling (FR-014)

**Rule**: Display "-" when `reviewRequests` field is empty

**Validation**: Already handled by existing `SlackClient._build_table_data_row()` method

**Filter Behavior**: PRs with empty `reviewRequests` are excluded during filtering (no team members present)

---

### Team Size Limit (FR-007)

**Rule**: Skip expansion if GitHub team has > 100 members; include PR by default (fail-safe)

**Implementation**:

```python
def _fetch_github_team_members_with_limit(org: str, team_slug: str, max_size: int = 100) -> list[str]:
    """Fetch team members with size limit check."""
    # First, check team size
    team_info = gh api /orgs/{org}/teams/{team_slug} --jq '.members_count'

    if team_info['members_count'] > max_size:
        logger.warning(
            f"GitHub team {org}/{team_slug} has {team_info['members_count']} members "
            f"(exceeds limit of {max_size}). Skipping expansion (fail-safe: including PR)."
        )
        return []  # Empty list signals "skip filtering for this team"

    # Proceed with existing expansion logic
    return _fetch_github_team_members(org, team_slug)
```

**Filtering Adjustment**: If team expansion returns empty list due to size limit, treat as "team has members" (fail-safe inclusion)

---

## State Transitions

### PR Review Status Flow

```text
review:none → review:required → review:approved
    ↑              ↓
    └──────────────┘
   (new commits invalidate approvals, revert to review:required)
```

**Impact on This Feature**:

- PRs captured by `review:none` search: No reviews submitted yet
- PRs captured by `review:required` search: Some reviews submitted, more needed
- PRs NOT captured (review:approved): All required reviews obtained (excluded by search filter)

**Deduplication Handling**: If PR transitions during search execution, it may appear in both searches. Deduplication ensures it's only fetched once and appears once in final results.

---

## Data Flow Summary

```text
1. Search Phase (fetch_team_prs)
   ┌─────────────────────────────────────────────────────────┐
   │ For each team member:                                    │
   │   Search 1: review:none + reviewer=username              │
   │   → Add keys to pr_keys set                              │
   │   → Record in pr_search_metadata["review:none"]          │
   │                                                           │
   │   Search 2: review:required + reviewer=username          │
   │   → Add keys to pr_keys set (auto-dedupe)                │
   │   → Record in pr_search_metadata["review:required"]      │
   └─────────────────────────────────────────────────────────┘
                              ↓
2. Detail Fetch Phase
   ┌─────────────────────────────────────────────────────────┐
   │ For each unique PR key in pr_keys:                       │
   │   Fetch PullRequest details (includes reviewers,         │
   │   github_team_reviewers, review_status)                  │
   └─────────────────────────────────────────────────────────┘
                              ↓
3. Filtering Phase (NEW)
   ┌─────────────────────────────────────────────────────────┐
   │ For each fetched PullRequest:                            │
   │   If came from "review:required" search:                 │
   │     Check if any team member in reviewers or             │
   │     github_team_reviewers[].members                      │
   │     → If no: Exclude PR                                  │
   │     → If yes: Include PR                                 │
   │   Else (came from "review:none" only):                   │
   │     Include PR (no filtering)                            │
   └─────────────────────────────────────────────────────────┘
                              ↓
4. Display Phase (unchanged)
   ┌─────────────────────────────────────────────────────────┐
   │ For each included PullRequest:                           │
   │   Display reviewers from pr.reviewers                    │
   │   Display teams from pr.github_team_reviewers            │
   └─────────────────────────────────────────────────────────┘
```

---

## Schema Impact

**No database schema changes** - this is a stateless CLI application with in-memory processing only.

**Configuration Schema** (`team_members.json`): No changes required

**API Response Schema** (GitHub API): No changes required - uses existing fields from GitHub's REST/GraphQL API

---

## Testing Data Model

### Test Fixtures

**Minimal PullRequest for filtering tests**:

```python
@pytest.fixture
def pr_with_team_member_reviewer():
    """PR with team member in individual reviewers list."""
    return PullRequest(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        author="external-contributor",
        reviewers=["team-member-alice", "external-reviewer"],
        github_team_reviewers=[],
        url="https://github.com/org/test-repo/pull/123",
        created_at=datetime.now(),
        ready_at=datetime.now(),
        current_approvals=0,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

@pytest.fixture
def pr_with_team_in_github_team():
    """PR with team member in GitHub team reviewer."""
    return PullRequest(
        repo_name="test-repo",
        number=456,
        title="Test PR 2",
        author="external-contributor",
        reviewers=[],
        github_team_reviewers=[
            GitHubTeamReviewRequest(
                team_name="Backend Team",
                team_slug="backend-team",
                members=["team-member-bob", "team-member-charlie"],
            )
        ],
        url="https://github.com/org/test-repo/pull/456",
        created_at=datetime.now(),
        ready_at=datetime.now(),
        current_approvals=1,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )

@pytest.fixture
def pr_no_team_members():
    """PR with no team members in reviewers."""
    return PullRequest(
        repo_name="test-repo",
        number=789,
        title="Test PR 3",
        author="external-contributor",
        reviewers=["external-reviewer-1", "external-reviewer-2"],
        github_team_reviewers=[],
        url="https://github.com/org/test-repo/pull/789",
        created_at=datetime.now(),
        ready_at=datetime.now(),
        current_approvals=0,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )
```

### Test Scenarios

1. **Deduplication**: PR appears in both searches → Only fetched once
2. **Filtering (review:required)**: Team member present → Included
3. **Filtering (review:required)**: No team members → Excluded
4. **No filtering (review:none)**: No team members → Included (no filtering applied)
5. **Team expansion**: GitHub team contains team member → Included
6. **Team expansion failure**: Empty members list → Included (fail-safe)
7. **Case-insensitive matching**: "Alice" matches "alice" → Included

---

## Summary

**No changes to existing models** - `PullRequest`, `GitHubTeamReviewRequest`, and `TeamMember` already support all requirements.

**One new internal data structure** - `pr_search_metadata` dictionary to track search query origins for conditional filtering.

**Key insight**: GitHub's `reviewRequests` field (exposed via `PullRequest.reviewers` and `PullRequest.github_team_reviewers`) is the single source of truth for pending reviewers. No additional state needed.
