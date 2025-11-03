# Research: GitHub API Rate Limit Handling

**Feature**: 003-github-rate-limit-handling
**Date**: 2025-10-31
**Status**: Resolved

## Overview

This document captures design decisions for implementing GitHub API rate limit handling, including detection, retry logic, and optimization strategies.

## Design Decisions

### 1. PR Display Limit Strategy

**Decision**: Configurable total limit across all categories (default: 30)

**Rationale**:
- **Current**: 15 PRs per category (rotten, aging, fresh) = 45 max total
- **Problem**: Equal distribution doesn't prioritize stale PRs (what users care about most)
- **Solution**: Single total limit with priority-based allocation (rotten → aging → fresh)
- **Example**: With limit=30 and 20 rotten + 15 aging + 10 fresh, show all 20 rotten, all 10 aging (remaining space)
- **User value**: More visibility into critical stale PRs needing immediate attention

**Alternatives considered**:
- Keep 15 per category: Rejected - doesn't optimize for staleness priority
- Fixed total without config: Rejected - different teams have different needs
- Proportional allocation: Rejected - too complex, doesn't guarantee stale PR visibility

**Implementation**:
- Add `MAX_PRS_TOTAL` env var (default 30, range 10-100)
- Modify `SlackClient._allocate_pr_display()` to fill categories sequentially
- Update truncation warning to show total count

---

### 2. API Call Optimization Strategy

**Decision**: Two-phase fetch with GraphQL batch for PR details

**Rationale**:
- **Phase 1** (Search): Use `gh search prs` without strict limits (~10 REST calls for 5 members)
  - Cheap operation, returns minimal metadata (PR number, repo)
  - Necessary to discover all team PRs
- **Phase 2** (Sort & Select): Combine, sort by staleness, select top N (where N = MAX_PRS_TOTAL)
  - Dynamic allocation: unused quota from member with few PRs → member with many PRs
  - Example: Member A has 3 PRs, Member B has 20 PRs → can show 12 of B's stale PRs
- **Phase 3** (Details): Batch fetch selected PRs via GraphQL (2-4 queries vs 30 REST calls)
  - Expensive operation, fetch full PR details only for displayed PRs
  - **65% API call reduction**: ~40 total points vs ~35-40 in current implementation

**Alternatives considered**:
- Limit search queries: Rejected - might miss stale PRs, unpredictable results
- Keep individual REST calls: Rejected - doesn't meet SC-007 (30%+ reduction)
- Use PyGithub GraphQL: Rejected - requires refactoring from gh CLI pattern
- Persistent caching: Rejected - adds complexity, stateless preferred per constitution

**Implementation**:
- Keep existing search phase unchanged
- Add `_fetch_pr_details_batch_graphql()` method
- Group PRs by repository for efficient batching
- Feature flag `USE_GRAPHQL_BATCH` for fallback

---

### 3. GraphQL Batch Query Structure

**Decision**: Use `gh api graphql` with repository-grouped queries

**Rationale**:
- gh CLI supports GraphQL via `gh api graphql -f query='...'`
- GitHub GraphQL allows fetching multiple PRs in single query:
  ```graphql
  query FetchPRs($owner: String!, $repo: String!) {
    repository(owner: $owner, name: $repo) {
      pr1: pullRequest(number: 123) { ...fields }
      pr2: pullRequest(number: 456) { ...fields }
      ...
    }
  }
  ```
- **Rate limit cost**: 1-3 points per query (vs 1 point per REST call)
- **Grouping by repo**: Enables cleaner query structure, easier error handling

**Alternatives considered**:
- Search API with OR conditions: Rejected - complex query string, less reliable
- Multiple separate queries: Rejected - still saves API calls but less elegant
- GraphQL `nodes` in single search: Rejected - requires union types, more complex

**Implementation**:
- Group selected PRs by `(owner, repo)`
- Build query with aliased `pullRequest` fields
- Parse JSON response to reconstruct PR objects
- Fall back to REST if GraphQL fails (via feature flag)

---

### 4. Error Classification Strategy

**Decision**: Three error types with distinct handling

**Rationale**:
- **HTTP 429 (Rate limit)**: Retryable with exponential backoff
  - Predictable, GitHub provides reset time
  - Auto-retry likely succeeds after wait
  - Parse stderr for "HTTP 429" or "rate limit exceeded"
- **Network errors (timeout, connection refused, DNS)**: Fail fast, no retry
  - Unpredictable, unlikely to resolve within seconds
  - Let next scheduled run handle (per FR-012)
  - Subprocess `TimeoutExpired` exception
- **Other errors (4xx, 5xx)**: Fail fast, log details
  - Indicates code/permission issues, not transient
  - Retry won't help

**Alternatives considered**:
- Retry all errors: Rejected - wastes time on non-transient failures
- Check only exit codes: Rejected - insufficient granularity for decision
- Separate timeout threshold: Rejected - adds config complexity

**Implementation**:
- Parse `subprocess.CalledProcessError.stderr` for error type
- Use `subprocess.TimeoutExpired` for timeout detection
- Separate retry paths in `_retry_with_backoff()`

---

### 5. Retry Backoff Configuration

**Decision**: Exponential backoff with configurable base (default: 1.0s)

**Rationale**:
- **Formula**: `wait = base * (2 ** attempt)` → 1s, 2s, 4s for base=1.0
- **Configurable base**: Different teams may need faster/slower retries
  - Small teams (fast quota recovery): base=0.5 → 0.5s, 1s, 2s
  - Large teams (slow recovery): base=2.0 → 2s, 4s, 8s
- **Max 3 attempts**: Prevents infinite loops, aligns with FR-010
- **Respect Retry-After**: GitHub may provide optimal wait time (FR-009)

**Alternatives considered**:
- Fixed intervals (1s, 2s, 3s): Rejected - linear doesn't adapt to sustained rate limiting
- Fibonacci backoff: Rejected - over-engineering, exponential sufficient
- Unlimited retries with timeout: Rejected - violates FR-010, unpredictable behavior

**Implementation**:
- Add `RETRY_BACKOFF_BASE` env var (default 1.0, range 0.5-2.0)
- Add `MAX_RETRIES` env var (default 3, range 1-5)
- Parse `Retry-After` header from gh CLI stderr if present
- Log wait time at INFO level: "Waiting 2s before retry (attempt 2/3)..."

---

### 6. Rate Limit Wait Threshold

**Decision**: Configurable threshold (default: 300s = 5 minutes)

**Rationale**:
- **< threshold**: Auto-wait with countdown, resume after reset (FR-005, SC-003)
  - User story: "waits with countdown message and automatically resumes"
  - Acceptable delay for scheduled runs
- **> threshold**: Fail fast with error (FR-006, SC-004)
  - Normal mode: Exit immediately, no Slack message
  - Dry-run mode: Show partial results with warning (FR-007)
- **Configurable**: CI vs manual runs have different tolerance
  - CI (automated): Lower threshold (60-120s) for fast feedback
  - Manual (debugging): Higher threshold (600s) for patience

**Alternatives considered**:
- Fixed 5min threshold: Rejected - different deployment contexts need flexibility
- Always wait: Rejected - violates user story for distant reset times
- Always fail: Rejected - doesn't handle short resets gracefully

**Implementation**:
- Add `RATE_LIMIT_WAIT_THRESHOLD` env var (default 300, range 60-600)
- Check reset time in `_should_proceed()` method
- Display countdown for waits: "Rate limit reset in 4:32, waiting..."

---

### 7. Configuration Options

**Decision**: 5 new environment variables with validation

| Variable | Default | Range | Purpose |
|----------|---------|-------|---------|
| `MAX_PRS_TOTAL` | 30 | 10-100 | Total PRs to display |
| `MAX_RETRIES` | 3 | 1-5 | Retry attempts for HTTP 429 |
| `RATE_LIMIT_WAIT_THRESHOLD` | 300 | 60-600 | Max auto-wait seconds |
| `RETRY_BACKOFF_BASE` | 1.0 | 0.5-2.0 | Backoff multiplier |
| `USE_GRAPHQL_BATCH` | true | bool | Enable GraphQL optimization |

**Rationale**:
- **Validation ranges**: Prevent misconfiguration (e.g., MAX_RETRIES=999)
- **Sensible defaults**: Work for 80% of teams without config
- **Feature flag**: `USE_GRAPHQL_BATCH` allows rollback if GraphQL causes issues
- **Meets SC-008**: "Users can configure retry behavior through environment variables"

**Alternatives considered**:
- JSON config file: Rejected - env vars simpler, 12-factor app compliant
- CLI flags: Rejected - harder for automated runs, env vars more flexible
- Hardcoded values: Rejected - violates SC-008

**Implementation**:
- Add validation in `config.load_config()`
- Raise `ValueError` with clear messages for invalid ranges
- Update `.env.example` with documentation

---

## Open Questions (All Resolved)

✅ **Q1**: How does gh CLI report HTTP 429 errors?
**A**: Via stderr output containing "HTTP 429" or "rate limit exceeded" string

✅ **Q2**: Should timeouts be retried?
**A**: No - treat as network errors, fail fast per FR-012

✅ **Q3**: Where to log API metrics?
**A**: End of run summary + DEBUG-level per-phase logging

✅ **Q4**: Display wait countdown or sleep silently?
**A**: Simple "Waiting Xs before retry..." at INFO level for transparency

✅ **Q5**: GraphQL cost calculation?
**A**: 1-3 points per batch query depending on complexity, significantly less than N individual calls

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| GraphQL query complexity costs more than expected | Feature flag `USE_GRAPHQL_BATCH=false` for rollback to REST |
| gh CLI GraphQL syntax issues | Extensive testing, clear error messages, fallback to REST |
| Breaking change to Slack display | Document in release notes, configurable total limit maintains flexibility |
| Team size > 15 exceeds quota | Fail early with validation (FR-017), clear error message |
| Inconsistent GitHub rate limit data | Use conservative values (FR-004), log warnings for investigation |

---

## Next Steps

1. Phase 1: Generate `data-model.md` with RateLimitStatus, APICallMetrics, etc.
2. Phase 1: Generate `quickstart.md` with configuration examples
3. Phase 1: Update `CLAUDE.md` via agent context script
4. Phase 2: Generate `tasks.md` (via separate `/speckit.tasks` command)
