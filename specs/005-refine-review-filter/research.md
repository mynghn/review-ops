# Research: Refine Review-Needed PR Criteria

**Feature**: 005-refine-review-filter
**Date**: 2025-11-10
**Status**: Complete

## Overview

This document captures research findings for implementing dual search queries with deduplication and team member filtering for the review-ops tool.

## Research Questions

### 1. PR Deduplication Strategy

**Question**: How should we deduplicate PRs that appear in both `review:none` and `review:required` search results?

**Decision**: Deduplicate at the PR key level (repo, number) before detail fetching using Python sets

**Rationale**:

- Existing code already uses a set-based approach in Phase 1 of `fetch_team_prs()` (line 462: `pr_keys = set()`)
- Deduplication before detail fetching avoids redundant API calls (more efficient than post-fetch deduplication)
- Python sets provide O(1) membership testing and automatic deduplication
- PR key tuple `(repo_full_name, pr_number)` uniquely identifies a PR across searches

**Alternatives Considered**:

- Post-fetch deduplication: Rejected because it wastes API calls on redundant PR detail fetches
- Dictionary-based deduplication: Rejected because sets are simpler and sufficient for this use case

**Implementation Note**: The dual search will add PR keys to the same set used for single search, requiring no additional data structures.

---

### 2. Team Member Filtering for review:required PRs

**Question**: How should we filter `review:required` PRs to include only those where team members are in the current `reviewRequests`?

**Decision**: Filter after PR detail fetching, checking both individual reviewers and GitHub team members

**Rationale**:

- `reviewRequests` field is only available in PR details (not in search results)
- Must fetch details first to access `reviewRequests`
- Filtering applies ONLY to `review:required` PRs (spec FR-003)
- `review:none` PRs are included without filtering (spec clarification, edge case answer)

**Algorithm**:

1. Track which search query found each PR (add metadata during search phase)
2. After fetching details, check if PR came from `review:required` search
3. If yes, verify at least one team member appears in `pr.reviewers` or `pr.github_team_reviewers` (expanded members)
4. If no team members found, exclude the PR from results

**Alternatives Considered**:

- Filter before detail fetching: Rejected because `reviewRequests` is not available in search results
- Apply filtering to both review:none and review:required: Rejected per spec clarification (filtering only applies to review:required)

**Implementation Note**: Will require tracking search query origin for each PR key during Phase 1.

---

### 3. Dual Search Query Execution with Rate Limiting

**Question**: What's the best approach for executing dual search queries while respecting GitHub API rate limits?

**Decision**: Execute dual searches within the existing username iteration loop, reusing retry/backoff logic

**Rationale**:

- Current implementation iterates through team usernames, searching for PRs where each user is a reviewer
- Each search already uses `_retry_with_backoff()` with exponential backoff (lines 467-484)
- Existing `api_call_delay` parameter (default 2s) prevents secondary rate limits (lines 496-500)
- Dual search doubles the number of API calls but existing safeguards handle this

**Approach**:

```python
for username in team_usernames:
    # Search 1: review:none
    result_none = search_with_retry(review="none", reviewer=username)
    pr_keys.update(extract_pr_keys(result_none))

    # Search 2: review:required (with metadata tracking)
    result_required = search_with_retry(review="required", reviewer=username)
    pr_keys_required = extract_pr_keys(result_required)
    mark_as_review_required(pr_keys_required)  # Track origin
    pr_keys.update(pr_keys_required)

    # Existing API call delay applies between searches
    time.sleep(api_call_delay)
```

**Alternatives Considered**:

- Parallel execution of dual searches: Rejected because it increases rate limit pressure
- Batch all review:none searches, then all review:required searches: Rejected because it delays feedback and doesn't reduce API calls

**Rate Limit Impact**:

- Current: ~15 search calls for 15-member team (1 per username)
- After change: ~30 search calls for 15-member team (2 per username)
- Still well within 5000 requests/hour limit (30 calls = 0.6% of quota)

---

### 4. GitHub Team Expansion Handling

**Question**: How should we handle GitHub team review requests when filtering by team member presence?

**Decision**: Use existing `_fetch_github_team_members()` method, apply 100-member limit with fail-safe inclusion

**Rationale**:

- Existing implementation already expands GitHub teams (lines 292-330)
- Returns empty list on failure, logs warning, shows team name without expansion
- Spec requires 100-member limit with fail-safe (FR-007): if team > 100 members, skip expansion and include PR

**Enhancement Required**:

- Add team size check before expansion
- If team size > 100, log warning and include PR (fail-safe behavior)
- Otherwise, use existing expansion logic

**Team Size Check Approach**:

```python
# First, get team member count without fetching full list
gh api /orgs/{org}/teams/{team_slug} --jq '.members_count'

# If members_count > 100:
#   - Log warning
#   - Skip expansion
#   - Include PR (fail-safe)
# Else:
#   - Use existing _fetch_github_team_members()
```

**Alternatives Considered**:

- Always expand teams regardless of size: Rejected due to potential API quota exhaustion for large teams
- Exclude PRs with oversized teams: Rejected because it risks missing important notifications (fail-safe principle)

---

### 5. Search Query Parameter Validation

**Question**: Do `gh search prs --review none` and `--review required` work as expected?

**Decision**: Confirmed via GitHub CLI documentation and manual testing

**Research Findings**:

- `--review none`: Returns PRs with no reviews submitted yet
- `--review required`: Returns PRs where review decision is not yet approved (more reviews needed)
- `--review approved`: Returns PRs where all required reviews obtained (will exclude these)

**Validation**:

```bash
# Test query structure (from existing code)
gh search prs \
  --owner <org> \
  --archived=false \
  --state open \
  --draft=false \
  --review required \
  --review-requested <username> \
  --updated ">=2025-10-10" \
  --limit 100 \
  --json number,repository
```

**Confirmed Behavior**:

- Both `--review none` and `--review required` are mutually exclusive filters
- Must execute as separate queries (cannot combine in single query)
- Both filters are supported in `gh search prs` (GitHub CLI v2.0+)

---

## Technology Decisions

### Primary Technologies

- **Python 3.12**: Existing language, no changes
- **GitHub CLI (`gh`)**: Existing dependency, supports both `--review none` and `--review required` filters
- **pytest**: Existing testing framework, sufficient for new tests

### No New Dependencies

All required functionality available with existing dependencies:

- `subprocess` module: For `gh` CLI execution (existing)
- `json` module: For parsing `gh` output (existing)
- `set` data structure: For PR deduplication (existing)
- `logging` module: For observability (existing)

---

## Implementation Approach Summary

1. **Dual Search Execution**:
   - Modify `fetch_team_prs()` to execute two searches per username
   - First search: `--review none` (existing behavior)
   - Second search: `--review required` (new)
   - Track which PRs came from `review:required` search (metadata)

2. **Deduplication**:
   - Use existing `pr_keys` set to automatically deduplicate
   - No changes needed to deduplication logic

3. **Team Member Filtering**:
   - Add filtering step after detail fetching
   - Apply ONLY to PRs from `review:required` search
   - Check both `pr.reviewers` and expanded `pr.github_team_reviewers`
   - Case-insensitive comparison (FR-013)

4. **GitHub Team Expansion**:
   - Add team size check before expansion
   - If size > 100, skip expansion and include PR (fail-safe)
   - Log occurrence for monitoring (FR-007)

5. **Observability**:
   - Log count of PRs from each search query (FR-012)
   - Log when team member filtering excludes PRs
   - Log when team size exceeds limit

---

## Performance Considerations

**API Call Impact**:

- Current: 1 search call per team member + 1 detail fetch per unique PR
- After change: 2 search calls per team member + 1 detail fetch per unique PR (deduplicated)
- Example: 15 members, 30 unique PRs → 30 searches + 30 details = 60 API calls
- Well within 5000 requests/hour limit

**Optimization Preserved**:

- GraphQL batch fetching still applies (reduces detail API calls by ~65%)
- Deduplication before detail fetching avoids redundant calls
- Existing retry/backoff handles rate limit errors

**Expected Performance**:

- Dual search + deduplication: 10-15 seconds (double current search time)
- Detail fetching: Unchanged (same number of unique PRs)
- Total: ~25-30 seconds for 15 members, 30 PRs (within 30s target)

---

## Edge Cases Covered

1. **PR appears in both searches**: Deduplicated via set (no redundant detail fetch)
2. **reviewRequests is empty**: PR excluded from review:required results (filtering)
3. **GitHub team expansion fails**: Falls back to showing team name, includes PR (fail-safe)
4. **Team size > 100 members**: Skips expansion, includes PR, logs warning (fail-safe)
5. **Rate limit during dual search**: Existing retry/backoff handles both queries
6. **No team members in reviewRequests**: PR excluded from review:required results

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Doubled search API calls hit rate limits | Tool fails or becomes slow | Use existing retry/backoff; API call delay between searches; fail-fast if rate limit exhausted |
| Deduplication logic misses PRs | Redundant API calls | Use Python sets with tuple keys (proven approach) |
| Team member filtering too aggressive | Miss important PRs | Apply filtering ONLY to review:required PRs; include review:none PRs without filtering |
| GitHub team expansion timeout | Tool hangs | Use existing 10s timeout; fall back to team name; log warning |
| Oversized teams exhaust API quota | Tool becomes slow | Check team size before expansion; fail-safe to include PR |

---

## References

- GitHub CLI documentation: https://cli.github.com/manual/gh_search_prs
- GitHub API rate limits: https://docs.github.com/en/rest/rate-limit
- Existing `github_client.py` implementation (lines 425-881)
- Feature spec: `specs/005-refine-review-filter/spec.md`
