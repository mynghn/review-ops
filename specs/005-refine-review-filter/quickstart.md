# Quickstart: Refine Review-Needed PR Criteria

**Feature**: 005-refine-review-filter
**Date**: 2025-11-10
**For**: Developers implementing this feature

## What This Feature Does

Expands PR search to include both `review:none` (no reviews yet) and `review:required` (partial reviews submitted) PRs. Filters `review:required` PRs to show only those where team members are still awaited. Ensures perfect deduplication when PRs appear in both searches.

## 5-Minute Overview

### Current Behavior

```python
# Current: Only searches for review:required PRs
gh search prs --review required --review-requested <username>
```

**Problem**: Misses PRs that need reviews but have partial approvals

### New Behavior

```python
# New: Dual search with deduplication + filtering
Search 1: gh search prs --review none --review-requested <username>
Search 2: gh search prs --review required --review-requested <username>
→ Deduplicate PR keys
→ Fetch details once per unique PR
→ Filter review:required PRs by team member presence in reviewRequests
→ Display all included PRs
```

**Benefit**: Complete coverage of PRs needing team attention

---

## Implementation Steps (TDD)

### Step 1: Add Dual Search Logic (P1)

**Test First**:

```python
# tests/unit/test_github_client_dual_search.py
def test_dual_search_executes_both_queries(mock_gh_cli):
    """Test that both review:none and review:required searches execute."""
    client = GitHubClient(token="fake-token")

    # Mock responses
    mock_gh_cli.side_effect = [
        # review:none response
        Mock(stdout='[{"number": 1, "repository": {"nameWithOwner": "org/repo"}}]'),
        # review:required response
        Mock(stdout='[{"number": 2, "repository": {"nameWithOwner": "org/repo"}}]'),
    ]

    # Execute
    prs = client.fetch_team_prs(org="org", team_usernames={"alice"}, updated_after=date(2025, 1, 1))

    # Verify both searches executed
    assert mock_gh_cli.call_count == 2
    assert "--review" in mock_gh_cli.call_args_list[0][0][0]
    assert "none" in mock_gh_cli.call_args_list[0][0][0]
    assert "required" in mock_gh_cli.call_args_list[1][0][0]
```

**Implement**:

```python
# src/github_client.py - Modify fetch_team_prs()

def fetch_team_prs(self, org_name: str, team_usernames: set[str], updated_after: date) -> list[PullRequest]:
    """Fetch open PRs with dual search (review:none + review:required)."""

    pr_keys = set()
    pr_search_metadata = {}  # Track which search found each PR

    for username in team_usernames:
        # Search 1: review:none
        result_none = self._search_prs_by_review_status(
            org_name, username, updated_after, review_status="none"
        )
        for pr_data in json.loads(result_none.stdout):
            pr_key = (pr_data["repository"]["nameWithOwner"], pr_data["number"])
            pr_keys.add(pr_key)
            if pr_key not in pr_search_metadata:
                pr_search_metadata[pr_key] = set()
            pr_search_metadata[pr_key].add("review:none")

        # Search 2: review:required
        result_required = self._search_prs_by_review_status(
            org_name, username, updated_after, review_status="required"
        )
        for pr_data in json.loads(result_required.stdout):
            pr_key = (pr_data["repository"]["nameWithOwner"], pr_data["number"])
            pr_keys.add(pr_key)
            if pr_key not in pr_search_metadata:
                pr_search_metadata[pr_key] = set()
            pr_search_metadata[pr_key].add("review:required")

    # Continue with existing detail fetching...
    # (Pass pr_search_metadata to filtering step)
```

**New Helper Method**:

```python
def _search_prs_by_review_status(
    self, org_name: str, username: str, updated_after: date, review_status: str
) -> subprocess.CompletedProcess:
    """Execute a single search query for a specific review status."""
    return self._retry_with_backoff(
        lambda: self._execute_gh_command([
            "gh", "search", "prs",
            "--owner", org_name,
            "--archived=false",
            "--state", "open",
            "--draft=false",
            "--review", review_status,
            "--review-requested", username,
            "--updated", f">={updated_after.isoformat()}",
            "--limit", str(self.gh_search_limit),
            "--json", "number,repository",
        ]),
        max_retries=self.max_retries,
        backoff_base=self.retry_backoff_base,
    )
```

---

### Step 2: Perfect Deduplication (P1)

**Test First**:

```python
def test_deduplication_when_pr_in_both_searches(mock_gh_cli):
    """Test that PR appearing in both searches is only fetched once."""
    client = GitHubClient(token="fake-token")

    # Same PR in both responses
    same_pr = '{"number": 1, "repository": {"nameWithOwner": "org/repo"}}'
    mock_gh_cli.side_effect = [
        Mock(stdout=f'[{same_pr}]'),  # review:none
        Mock(stdout=f'[{same_pr}]'),  # review:required
        Mock(stdout='{"number": 1, ...}'),  # detail fetch (only once)
    ]

    prs = client.fetch_team_prs(org="org", team_usernames={"alice"}, updated_after=date(2025, 1, 1))

    # Verify detail fetch called only once for the duplicate PR
    detail_calls = [call for call in mock_gh_cli.call_args_list if "pr" in str(call) and "view" in str(call)]
    assert len(detail_calls) == 1
```

**Implementation**: Already handled by using `pr_keys` set in Step 1!

---

### Step 3: Filter review:required PRs by Team Member Presence (P3)

**Test First**:

```python
def test_filter_review_required_pr_without_team_members(mock_gh_cli):
    """Test that review:required PRs with no team members in reviewRequests are excluded."""
    client = GitHubClient(token="fake-token")
    team_members = {"alice", "bob"}

    # Mock: review:required PR with only external reviewers
    mock_gh_cli.side_effect = [
        Mock(stdout='[{"number": 1, "repository": {"nameWithOwner": "org/repo"}}]'),  # search
        Mock(stdout=json.dumps({  # detail fetch
            "number": 1,
            "reviewRequests": [{"login": "external-reviewer"}],  # No team members
            "reviewDecision": "REVIEW_REQUIRED",
            # ... other fields
        })),
    ]

    prs = client.fetch_team_prs(org="org", team_usernames=team_members, updated_after=date(2025, 1, 1))

    # PR should be excluded (no team members in reviewRequests)
    assert len(prs) == 0
```

**Implement**:

```python
# Add after detail fetching in fetch_team_prs()

def _filter_by_team_member_presence(
    self, all_prs: list[PullRequest], pr_search_metadata: dict, team_usernames: set[str]
) -> list[PullRequest]:
    """Filter review:required PRs to include only those with team members in reviewRequests."""
    filtered_prs = []
    team_usernames_lower = {u.lower() for u in team_usernames}

    for pr in all_prs:
        pr_key = (pr.repo_name, pr.number)

        # Only filter review:required PRs
        if "review:required" in pr_search_metadata.get(pr_key, set()):
            # Check individual reviewers
            has_team_member = any(
                reviewer.lower() in team_usernames_lower for reviewer in pr.reviewers
            )

            # Check GitHub team reviewers
            if not has_team_member:
                for team_review in pr.github_team_reviewers:
                    if any(member.lower() in team_usernames_lower for member in team_review.members):
                        has_team_member = True
                        break

            # Exclude if no team members found
            if not has_team_member:
                logger.debug(f"Excluding PR {pr.repo_name}#{pr.number} (no team members in reviewRequests)")
                continue

        # Include PR (either passed filter or was from review:none search)
        filtered_prs.append(pr)

    return filtered_prs
```

---

### Step 4: Handle GitHub Team Expansion with Size Limit (P3)

**Test First**:

```python
def test_skip_expansion_for_oversized_github_team():
    """Test that teams > 100 members skip expansion and include PR (fail-safe)."""
    client = GitHubClient(token="fake-token")

    # Mock team with 150 members
    mock_team_info = Mock(stdout='{"members_count": 150}')

    # Should skip expansion and return empty list (signals fail-safe inclusion)
    members = client._fetch_github_team_members_with_limit("org", "large-team", max_size=100)

    assert members == []
    # PR should still be included (fail-safe behavior in filtering logic)
```

**Implement**:

```python
def _fetch_github_team_members_with_limit(
    self, org: str, team_slug: str, max_size: int = 100
) -> list[str] | None:
    """
    Fetch GitHub team members with size limit check.

    Returns:
        List of member usernames, or None if size exceeds limit (signals fail-safe inclusion)
    """
    try:
        # Check team size first
        result = subprocess.run(
            ["gh", "api", f"/orgs/{org}/teams/{team_slug}", "--jq", ".members_count"],
            capture_output=True, text=True, check=True, env=os.environ, timeout=10,
        )
        member_count = int(result.stdout.strip())

        if member_count > max_size:
            logger.warning(
                f"GitHub team {org}/{team_slug} has {member_count} members "
                f"(exceeds limit of {max_size}). Skipping expansion (fail-safe: including PR)."
            )
            return None  # Signal fail-safe inclusion

        # Proceed with existing expansion
        return self._fetch_github_team_members(org, team_slug)

    except Exception as e:
        logger.warning(f"Failed to check team size for {org}/{team_slug}: {e}. Using fail-safe.")
        return None
```

**Filtering Adjustment**:

```python
# In _filter_by_team_member_presence():

for team_review in pr.github_team_reviewers:
    if team_review.members is None:  # Fail-safe signal from expansion
        has_team_member = True  # Include PR by default
        break
    if any(member.lower() in team_usernames_lower for member in team_review.members):
        has_team_member = True
        break
```

---

### Step 5: Add Observability Logging (FR-012)

```python
# In fetch_team_prs() after searches complete:

review_none_count = sum(1 for metadata in pr_search_metadata.values() if "review:none" in metadata)
review_required_count = sum(1 for metadata in pr_search_metadata.values() if "review:required" in metadata)
both_count = sum(1 for metadata in pr_search_metadata.values() if len(metadata) == 2)

logger.info(
    f"Search results: {review_none_count} from review:none, "
    f"{review_required_count} from review:required, "
    f"{both_count} in both (deduplicated to {len(pr_keys)} unique PRs)"
)
```

---

## Testing Strategy

### Unit Tests (TDD)

1. **Dual search execution**: Both queries execute with correct parameters
2. **Deduplication**: PR in both searches → fetched once
3. **Filtering (review:required)**: Team member present → included
4. **Filtering (review:required)**: No team members → excluded
5. **No filtering (review:none)**: No team members → included
6. **Team expansion**: Team members present → included
7. **Team size limit**: > 100 members → fail-safe inclusion
8. **Case-insensitive matching**: "Alice" == "alice" → included
9. **Empty reviewRequests**: → excluded from review:required results

### Integration Tests

1. **Rate limit handling**: Dual search respects retry/backoff
2. **API call delay**: Delay applied between searches
3. **GraphQL batching**: Still works with dual search
4. **Error handling**: Search failure → logged, no Slack notification

### Manual Testing

```bash
# 1. Set up test environment
export GH_TOKEN="your-token"
export GITHUB_ORG="your-org"
export LANGUAGE="en"

# 2. Create test PRs:
#    - PR #1: review:none, team member reviewer
#    - PR #2: review:required (1 approval, 1 pending), team member in pending
#    - PR #3: review:required, only external reviewers
#    - PR #4: review:none, same as PR #2 (for deduplication test)

# 3. Run with debug logging
LOG_LEVEL=DEBUG uv run python src/app.py --dry-run

# 4. Verify output:
#    - PR #1: Included (review:none)
#    - PR #2: Included once (deduplicated, team member pending)
#    - PR #3: Excluded (no team members)
#    - PR #4: Deduplicated with PR #2
```

---

## Common Pitfalls

### Pitfall 1: Forgetting to Track Search Origin

**Problem**: Filtering applied to all PRs, including review:none PRs

**Solution**: Use `pr_search_metadata` to track which search found each PR

```python
# WRONG: Filters all PRs
for pr in all_prs:
    if not has_team_member(pr):
        continue  # Excludes review:none PRs without team members!

# CORRECT: Only filters review:required PRs
for pr in all_prs:
    pr_key = (pr.repo_name, pr.number)
    if "review:required" in pr_search_metadata.get(pr_key, set()):
        if not has_team_member(pr):
            continue  # Only excludes review:required PRs
```

---

### Pitfall 2: Fetching Details Before Deduplication

**Problem**: Redundant API calls for PRs in both searches

**Solution**: Deduplicate PR keys first, then fetch details

```python
# WRONG: Fetch details in search loop
for username in team_usernames:
    result = search(username)
    for pr_data in result:
        pr_details = fetch_details(pr_data)  # May fetch same PR twice!

# CORRECT: Deduplicate keys, then fetch
pr_keys = set()
for username in team_usernames:
    result = search(username)
    for pr_data in result:
        pr_keys.add((repo, number))  # Deduplicate

for pr_key in pr_keys:
    pr_details = fetch_details(pr_key)  # Fetch each PR only once
```

---

### Pitfall 3: Case-Sensitive Username Comparison

**Problem**: "Alice" vs "alice" treated as different users

**Solution**: Always lowercase usernames before comparison (FR-013)

```python
# WRONG
if reviewer in team_usernames:  # Case-sensitive

# CORRECT
team_usernames_lower = {u.lower() for u in team_usernames}
if reviewer.lower() in team_usernames_lower:  # Case-insensitive
```

---

## Performance Expectations

- **Search time**: 10-15 seconds (double current time due to dual searches)
- **Detail fetch time**: Unchanged (same number of unique PRs)
- **Total time**: ~25-30 seconds for 15 members, 30 unique PRs
- **API calls**: ~60 calls (30 searches + 30 details via GraphQL batching)

---

## Rollout Plan

1. **Merge to main**: After all tests pass and code review approved
2. **Monitor first run**: Check logs for:
   - Dual search execution
   - Deduplication count
   - Filtering exclusions
   - No rate limit errors
3. **Validate results**: Team confirms PRs shown match expectations
4. **Update docs**: Add dual search behavior to CLAUDE.md

---

## Success Criteria

✅ Both `review:none` and `review:required` searches execute
✅ PRs in both searches are deduplicated (fetched once)
✅ `review:required` PRs without team members are excluded
✅ `review:none` PRs are included regardless of team member presence
✅ Reviewer column shows only current pending reviewers (from `reviewRequests`)
✅ Existing rate limit handling works with dual searches
✅ All tests pass (unit + integration)
✅ Total execution time < 30 seconds for typical workloads

---

## Next Steps

After implementing this feature:

1. Run `/speckit.tasks` to generate implementation task breakdown
2. Follow TDD workflow: Write test → Verify failure → Implement → Test passes
3. Monitor first production run for any edge cases
4. Consider future enhancements (e.g., parallel searches, caching)

---

## Questions?

- Check [research.md](./research.md) for detailed decision rationale
- Check [data-model.md](./data-model.md) for data structure details
- Check [spec.md](./spec.md) for full requirements and acceptance criteria
