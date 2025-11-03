# Data Model: GitHub API Rate Limit Handling

**Feature**: 003-github-rate-limit-handling
**Date**: 2025-10-31

## Overview

This document defines the data models (entities) for rate limit handling, including status tracking, metrics collection, and configuration management.

---

## Entities

### 1. RateLimitStatus

**Purpose**: Represents current GitHub API rate limit state for decision-making

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `remaining` | int | Yes | Remaining API calls in current window | >= 0 |
| `limit` | int | Yes | Total API calls allowed per window | > 0 |
| `reset_timestamp` | int | Yes | Unix timestamp when quota resets | > 0 |
| `is_exhausted` | bool | Yes | Whether quota is depleted (remaining == 0 or HTTP 429) | - |
| `wait_seconds` | int \| None | Yes | Seconds until reset (None if not exhausted) | >= 0 if set |

**Derived Properties**:
- `reset_time`: `datetime` from `reset_timestamp`
- `should_wait`: `bool` based on `wait_seconds < threshold`

**State Transitions**:
```
Normal (remaining > 100)
  → Low (remaining < 100, warn user)
  → Exhausted (remaining == 0 or HTTP 429)
    → Auto-wait (wait_seconds < threshold)
    → Fail-fast (wait_seconds >= threshold)
```

**Example**:
```python
@dataclass
class RateLimitStatus:
    remaining: int              # 45
    limit: int                  # 5000
    reset_timestamp: int        # 1698765432
    is_exhausted: bool          # False
    wait_seconds: int | None    # None
```

**Usage**:
- Returned by `GitHubClient.check_rate_limit()`
- Passed to `GitHubClient._should_proceed()` for decision logic
- Logged in app.py before operations

---

### 2. APICallMetrics

**Purpose**: Track API usage and optimization effectiveness for logging

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `search_calls` | int | Yes | Number of search API calls made | >= 0 |
| `rest_detail_calls` | int | Yes | Number of individual REST calls avoided (via GraphQL) | >= 0 |
| `graphql_calls` | int | Yes | Number of GraphQL batch queries made | >= 0 |
| `retry_attempts` | int | Yes | Total retry attempts across all calls | >= 0 |
| `failed_calls` | int | Yes | Number of calls that failed after retries | >= 0 |

**Derived Metrics**:
- `total_api_points`: Approximate GitHub rate limit points consumed
  - Formula: `search_calls + graphql_calls * 2 + rest_detail_calls`
- `optimization_rate`: Percentage of REST calls saved
  - Formula: `(rest_detail_calls / (rest_detail_calls + graphql_calls)) * 100` if graphql enabled
- `success_rate`: Percentage of successful calls
  - Formula: `((total_calls - failed_calls) / total_calls) * 100`

**Example**:
```python
@dataclass
class APICallMetrics:
    search_calls: int = 10           # 10 search queries (2 per member)
    rest_detail_calls: int = 27      # 27 individual calls avoided
    graphql_calls: int = 3           # 3 batch queries instead
    retry_attempts: int = 2          # 2 retries during run
    failed_calls: int = 0            # All succeeded

# Derived: optimization_rate = 90% (27/(27+3)), total_points ≈ 16
```

**Usage**:
- Initialized in `GitHubClient.__init__()`
- Updated during `fetch_team_prs()` execution
- Logged at end of run in `app.py`

---

### 3. Config (Extended)

**Purpose**: Application configuration including new rate limit parameters

**New Fields** (added to existing Config dataclass):

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `max_prs_total` | int | 30 | 10-100 | Total PRs to display across all categories |
| `max_retries` | int | 3 | 1-5 | Max retry attempts for rate limit errors |
| `rate_limit_wait_threshold` | int | 300 | 60-600 | Max auto-wait seconds (5 minutes default) |
| `retry_backoff_base` | float | 1.0 | 0.5-2.0 | Base backoff duration for exponential retry |
| `use_graphql_batch` | bool | true | - | Enable GraphQL batch fetching |

**Validation Rules**:
- `max_prs_total`: Must be between 10-100 (Slack message size constraints)
- `max_retries`: Must be between 1-5 (prevent excessive retries)
- `rate_limit_wait_threshold`: Must be between 60-600 (1min to 10min reasonable range)
- `retry_backoff_base`: Must be between 0.5-2.0 (ensure reasonable wait times)
- `use_graphql_batch`: Boolean parsed from string ("true", "1", "yes", "on")

**Error Messages**:
```python
# Example validation error
ValueError("MAX_PRS_TOTAL must be between 10 and 100")
ValueError("Invalid RETRY_BACKOFF_BASE '3.0': must be between 0.5 and 2.0")
```

**Loading**:
- Loaded in `config.load_config()` from environment variables
- Validated immediately during load
- Raises `ValueError` with clear messages for invalid values

---

### 4. TeamMember (No Changes)

**Status**: Existing entity, no modifications needed

**Note**: Team size validation added to `load_team_members()`:
- Max 15 members (FR-017)
- Raises `ValueError` if exceeded

---

### 5. SlackClient (Modified)

**Purpose**: Display configuration changes from per-category to total limit

**Modified Fields/Methods**:

| Change | Before | After |
|--------|--------|-------|
| Class constant | `MAX_PRS_PER_CATEGORY = 15` | (removed) |
| Constructor param | `language: str` | `max_prs_total: int, language: str` |
| Instance field | - | `self.max_prs_total` |

**New Method**:
```python
def _allocate_pr_display(
    self, by_category: dict[str, list[StalePR]]
) -> dict[str, list[StalePR]]:
    """
    Allocate PRs from total budget, prioritizing staleness.

    Args:
        by_category: Dict mapping category to full PR lists

    Returns:
        Dict mapping category to allocated (truncated) PR lists
    """
    remaining = self.max_prs_total
    rotten_display = by_category["rotten"][:remaining]
    remaining -= len(rotten_display)
    aging_display = by_category["aging"][:remaining]
    remaining -= len(aging_display)
    fresh_display = by_category["fresh"][:remaining]

    return {
        "rotten": rotten_display,
        "aging": aging_display,
        "fresh": fresh_display
    }
```

---

## Relationships

```
Config
  ├─> max_prs_total ──> SlackClient (display allocation)
  ├─> max_retries ──> GitHubClient (retry logic)
  ├─> rate_limit_wait_threshold ──> GitHubClient (wait decision)
  ├─> retry_backoff_base ──> GitHubClient (backoff calculation)
  └─> use_graphql_batch ──> GitHubClient (fetch strategy)

GitHubClient
  ├─> check_rate_limit() ──returns──> RateLimitStatus
  ├─> fetch_team_prs() ──updates──> APICallMetrics
  └─> _retry_with_backoff() ──uses──> Config (max_retries, backoff_base)

RateLimitStatus
  └─> _should_proceed() ──uses──> Config (rate_limit_wait_threshold)

SlackClient
  └─> _allocate_pr_display() ──uses──> Config (max_prs_total)

app.py
  ├─> creates ──> GitHubClient, SlackClient (with Config)
  ├─> calls ──> check_rate_limit() before fetch
  └─> logs ──> APICallMetrics at end of run
```

---

## Validation Summary

| Entity | Validation Type | Enforced At |
|--------|----------------|-------------|
| `Config` | Range checks (10-100, 1-5, etc.) | `load_config()` function |
| `RateLimitStatus` | Type checks, non-negative values | Dataclass initialization |
| `APICallMetrics` | Non-negative counters | Runtime assertions |
| `TeamMember` | Size limit (max 15) | `load_team_members()` function |
| `SlackClient` | Constructor param validation | `__init__()` method |

---

## Storage

**Persistence**: None (all in-memory for single run)

**Lifetime**:
- `Config`: Loaded at startup, immutable throughout run
- `RateLimitStatus`: Created per rate limit check, transient
- `APICallMetrics`: Created at start, updated during run, logged at end
- PR deduplication: In-memory dict, discarded after run

**Justification**: Stateless design per constitution Principle I (Simplicity First)

---

## Migration

**Impact**: Configuration changes only, no data migration needed

**Backward Compatibility**:
- New env vars have defaults, existing deployments work unchanged
- Slack display change visible to users but graceful (more stale PRs shown)
- Feature flag `USE_GRAPHQL_BATCH=false` allows rollback if needed

---

## Testing Considerations

### Unit Tests
- Config validation: Test all range boundaries (9, 10, 100, 101)
- RateLimitStatus: Test state transitions (normal → low → exhausted)
- APICallMetrics: Test derived metric calculations

### Integration Tests
- End-to-end with mocked gh CLI responses
- Verify allocation logic with various PR distributions
- Test metrics accuracy across full run

---

## Next Steps

1. Implement dataclasses in `src/models.py`
2. Add config loading in `src/config.py`
3. Generate `quickstart.md` with usage examples
4. Update `CLAUDE.md` via agent context script
