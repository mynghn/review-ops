# Quickstart: GitHub API Rate Limit Handling

**Feature**: 003-github-rate-limit-handling
**Date**: 2025-10-31

## Overview

This guide shows how to configure and use the GitHub API rate limit handling features once implemented.

---

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# --- Rate Limiting Configuration ---

# Maximum total PRs to display across all categories (default: 30, range: 10-100)
# Higher values show more PRs but consume more API quota
MAX_PRS_TOTAL=30

# Maximum retry attempts for rate limit errors (default: 3, range: 1-5)
# More retries = more resilient but slower failure detection
MAX_RETRIES=3

# Maximum auto-wait time in seconds (default: 300 = 5 minutes, range: 60-600)
# If rate limit resets within this threshold, app waits automatically
# If beyond threshold, app fails fast with error
RATE_LIMIT_WAIT_THRESHOLD=300

# Base backoff duration for exponential retry (default: 1.0, range: 0.5-2.0)
# Formula: wait_time = base * (2 ^ attempt)
# Example with base=1.0: 1s, 2s, 4s
# Example with base=0.5: 0.5s, 1s, 2s
RETRY_BACKOFF_BASE=1.0

# Enable GraphQL batch fetching for PR details (default: true)
# Reduces API calls by 60-70% compared to individual REST calls
# Set to false to fall back to REST API if GraphQL causes issues
USE_GRAPHQL_BATCH=true
```

---

## Usage Scenarios

### Scenario 1: Small Team (5 members), Typical Usage

**Configuration**:
```bash
MAX_PRS_TOTAL=30
MAX_RETRIES=3
RATE_LIMIT_WAIT_THRESHOLD=300
RETRY_BACKOFF_BASE=1.0
USE_GRAPHQL_BATCH=true
```

**Expected Behavior**:
- Fetches ~10-15 PRs typically
- Uses ~12-16 API points per run (vs 35-40 without optimization)
- Completes in <2 minutes
- Auto-waits if rate limit hit and resets within 5 minutes
- Shows up to 30 PRs prioritized by staleness (rotten → aging → fresh)

**Run Command**:
```bash
uv run python src/app.py
```

**Example Output**:
```
INFO - GitHub API rate limit: 4850/5000 remaining
INFO - Fetching PRs for 5 team members...
INFO - Found 42 PRs total, displaying top 30 by staleness
INFO - API calls: 10 searches, 3 GraphQL batches (saved 27 REST calls)
INFO - Optimization: 90% API call reduction via GraphQL batching
```

---

### Scenario 2: CI/CD Environment (Fast Feedback)

**Configuration**:
```bash
MAX_PRS_TOTAL=20                    # Fewer PRs for faster execution
MAX_RETRIES=2                       # Fewer retries for fast failure
RATE_LIMIT_WAIT_THRESHOLD=120      # 2 minutes max wait
RETRY_BACKOFF_BASE=0.5             # Faster retries (0.5s, 1s, 2s)
USE_GRAPHQL_BATCH=true
```

**Expected Behavior**:
- Prioritizes speed over completeness
- Fails fast if rate limit reset > 2 minutes
- Shows only 20 most stale PRs
- Faster retry cycles

**Run Command**:
```bash
uv run python src/app.py
```

---

### Scenario 3: Large Team (12-15 members)

**Configuration**:
```bash
MAX_PRS_TOTAL=50                    # Show more PRs for visibility
MAX_RETRIES=5                       # More retries for resilience
RATE_LIMIT_WAIT_THRESHOLD=600      # 10 minutes max wait
RETRY_BACKOFF_BASE=2.0             # Slower retries (2s, 4s, 8s)
USE_GRAPHQL_BATCH=true             # CRITICAL for quota management
```

**Expected Behavior**:
- Higher API usage (~25-30 points per run)
- More patient retry/wait strategy
- Shows up to 50 PRs (still prioritized by staleness)
- GraphQL batching essential to stay under quota

**Run Command**:
```bash
uv run python src/app.py
```

**Warning**: If team exceeds 15 members:
```
ERROR - Team has 18 members, which exceeds the recommended limit of 15.
Large teams may experience GitHub API rate limit issues.
Consider splitting into multiple runs or increasing MAX_PRS_TOTAL.
```

---

### Scenario 4: Debugging (Dry-Run Mode)

**Configuration**: (use defaults)

**Run Command**:
```bash
uv run python src/app.py --dry-run
```

**Expected Behavior**:
- No Slack message sent
- Prints formatted message to console
- Shows partial results even if rate limit exceeded
- Useful for testing without consuming Slack quota

**Example Output (Rate Limit Hit)**:
```
WARNING - GitHub API rate limit exhausted (0/5000 remaining)
WARNING - Rate limit resets in 8 minutes (2025-10-31 14:35:00 UTC)
WARNING - Showing partial results (15 of 42 PRs fetched)
INFO - Partial PR list:
  [rotten PRs displayed...]
```

---

## Monitoring & Troubleshooting

### Check Rate Limit Status

Before running, check current quota:
```bash
gh api rate_limit
```

Example output:
```json
{
  "resources": {
    "core": {
      "limit": 5000,
      "used": 150,
      "remaining": 4850,
      "reset": 1698765432
    }
  }
}
```

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
uv run python src/app.py
```

Debug output includes:
- Detailed rate limit checks
- Retry attempt logs
- GraphQL query construction
- API call metrics breakdown

---

## Metrics Interpretation

### Example Metrics Output

```
INFO - API Metrics Summary:
INFO -   Search calls: 10 (2 per member × 5 members)
INFO -   GraphQL batches: 3 (grouped by repository)
INFO -   REST calls avoided: 27 (30 PRs - 3 batches)
INFO -   Retry attempts: 2 (auto-recovered from rate limit)
INFO -   Failed calls: 0
INFO -   Total API points: ~16 (10 search + 3×2 GraphQL)
INFO -   Optimization rate: 90% (27 avoided / 30 total)
INFO -   Success rate: 100%
```

### What the Numbers Mean

| Metric | Meaning | Good Range |
|--------|---------|------------|
| Total API points | GitHub rate limit consumption | < 50 per run |
| Optimization rate | % of REST calls avoided by GraphQL | > 60% |
| Success rate | % of calls that succeeded | > 95% |
| Retry attempts | Number of auto-recovered failures | 0-5 acceptable |

---

## Common Issues

### Issue 1: "Rate limit exhausted, reset in 45 minutes"

**Cause**: Exceeded GitHub API quota, reset time too distant

**Solution**:
```bash
# Option 1: Increase wait threshold (if acceptable)
RATE_LIMIT_WAIT_THRESHOLD=600  # 10 minutes

# Option 2: Wait for reset and try again
# Check reset time:
gh api rate_limit --jq '.resources.core.reset' | xargs -I {} date -r {}

# Option 3: Reduce team size or PR limit
MAX_PRS_TOTAL=20
```

---

### Issue 2: "GraphQL query failed"

**Cause**: GraphQL API issue or malformed query

**Solution**:
```bash
# Disable GraphQL, fall back to REST
USE_GRAPHQL_BATCH=false
uv run python src/app.py
```

---

### Issue 3: "Team has 18 members, exceeds limit"

**Cause**: Team too large for single run with rate limits

**Solution**:
```bash
# Option 1: Split team into multiple runs
# Create team_members_group1.json (10 members)
# Create team_members_group2.json (8 members)
uv run python src/app.py  # Uses default team_members.json (group 1)
# Manually switch to group 2 and run again

# Option 2: Increase PR limit to justify more API usage
MAX_PRS_TOTAL=60

# Option 3: Request rate limit increase from GitHub
# (for GitHub Enterprise or paid plans)
```

---

### Issue 4: Slow execution

**Cause**: Many retries or long wait times

**Diagnosis**:
```bash
# Check retry metrics
export LOG_LEVEL=DEBUG
uv run python src/app.py 2>&1 | grep -i "retry"

# Output example:
# DEBUG - Retrying after 1s (attempt 1/3)
# DEBUG - Retrying after 2s (attempt 2/3)
# DEBUG - Retrying after 4s (attempt 3/3)
```

**Solution**:
```bash
# Reduce retry attempts
MAX_RETRIES=2

# Reduce backoff base for faster retries
RETRY_BACKOFF_BASE=0.5

# Or accept that rate limiting is happening and increase threshold
RATE_LIMIT_WAIT_THRESHOLD=600
```

---

## Best Practices

### 1. For Scheduled Runs (Cron/CI)

```bash
# Conservative settings for reliability
MAX_PRS_TOTAL=30
MAX_RETRIES=3
RATE_LIMIT_WAIT_THRESHOLD=300
RETRY_BACKOFF_BASE=1.0
USE_GRAPHQL_BATCH=true
LOG_LEVEL=INFO
```

### 2. For Manual/Debug Runs

```bash
# More verbose, patient settings
MAX_PRS_TOTAL=50
MAX_RETRIES=5
RATE_LIMIT_WAIT_THRESHOLD=600
RETRY_BACKOFF_BASE=2.0
USE_GRAPHQL_BATCH=true
LOG_LEVEL=DEBUG
```

### 3. For Testing New Features

```bash
# Dry-run mode, minimal changes
uv run python src/app.py --dry-run
# Always test with --dry-run first to avoid Slack spam
```

---

## Next Steps After Implementation

1. **Test in dry-run mode**: `uv run python src/app.py --dry-run`
2. **Monitor first real run**: Check metrics output for optimization rate
3. **Adjust configuration**: Based on team size and quota usage
4. **Set up monitoring**: Track API points consumed per run over time
5. **Review Slack output**: Verify priority-based PR display (rotten first)

---

## Support

For issues or questions:
1. Check debug logs: `LOG_LEVEL=DEBUG uv run python src/app.py`
2. Verify configuration: Ensure all env vars are in valid ranges
3. Test feature flags: Try disabling `USE_GRAPHQL_BATCH` if issues occur
4. Review metrics: Look for patterns in retry attempts and failed calls
