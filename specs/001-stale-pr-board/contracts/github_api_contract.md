# GitHub API Contract

**Feature**: Stale PR Board
**Date**: 2025-10-31
**Purpose**: Document GitHub API endpoints, request/response formats, and error handling

This document defines the contract between the application and the GitHub REST API v3, accessed via the PyGithub library.

## Authentication

**Method**: Personal Access Token (PAT)

**Required Scopes**:
- `repo` (or `repo:read` for read-only access to private repositories)
- `read:org` (to list organization repositories)

**Header**:
```
Authorization: Bearer <token>
Accept: application/vnd.github.v3+json
```

**PyGithub Usage**:
```python
from github import Github

g = Github("<token>")
user = g.get_user()  # Verify authentication
```

## Rate Limiting

**Limits**:
- Authenticated requests: 5,000 requests/hour
- Search API: 30 requests/minute
- Reset: Every hour on the hour

**Headers** (in responses):
```
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4999
X-RateLimit-Reset: 1635724800
X-RateLimit-Resource: core
```

**Checking Rate Limit**:
```python
rate_limit = g.get_rate_limit()
print(f"Remaining: {rate_limit.core.remaining}")
print(f"Resets at: {rate_limit.core.reset}")
```

**Handling Exceeded Limit**:
```python
from github import RateLimitExceededException

try:
    # API calls
except RateLimitExceededException as e:
    reset_time = e.rate_limit.core.reset
    # Print error with reset time, exit without Slack notification
```

## Endpoints

### 1. List Organization Repositories

**Endpoint**: `GET /orgs/{org}/repos`

**PyGithub**:
```python
org = g.get_organization("my-org")
repos = org.get_repos(type="all")  # all, public, private
```

**Response Fields** (relevant subset):
```json
{
  "name": "review-ops",
  "full_name": "my-org/review-ops",
  "private": false,
  "html_url": "https://github.com/my-org/review-ops"
}
```

**Error Handling**:
- `404 Not Found`: Organization doesn't exist or user lacks access
- `403 Forbidden`: Token lacks `read:org` scope

---

### 2. List Pull Requests

**Endpoint**: `GET /repos/{owner}/{repo}/pulls`

**Query Parameters**:
- `state`: `open` (required for this application)
- `sort`: `created` (optional)
- `direction`: `desc` (optional)

**PyGithub**:
```python
pulls = repo.get_pulls(state="open", sort="created", direction="desc")
```

**Response Fields** (relevant subset):
```json
{
  "number": 123,
  "title": "Add new feature",
  "html_url": "https://github.com/my-org/review-ops/pull/123",
  "state": "open",
  "draft": false,
  "created_at": "2025-10-25T10:30:00Z",
  "updated_at": "2025-10-30T14:22:00Z",
  "user": {
    "login": "alice"
  },
  "requested_reviewers": [
    {"login": "bob"},
    {"login": "charlie"}
  ],
  "base": {
    "ref": "main"
  }
}
```

**PyGithub Access**:
```python
pr.number          # int
pr.title           # str
pr.html_url        # str
pr.draft           # bool
pr.created_at      # datetime
pr.user.login      # str (author)
pr.requested_reviewers  # list[NamedUser]
pr.base.ref        # str (target branch)
```

**Error Handling**:
- `404 Not Found`: Repository doesn't exist or user lacks access
- `403 Forbidden`: Token lacks `repo` scope

---

### 3. List Pull Request Reviews

**Endpoint**: `GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews`

**PyGithub**:
```python
reviews = pr.get_reviews()
```

**Response Fields** (relevant subset):
```json
{
  "id": 789456123,
  "user": {
    "login": "bob"
  },
  "body": "Looks good!",
  "state": "APPROVED",
  "submitted_at": "2025-10-28T15:45:00Z"
}
```

**Review States**:
- `APPROVED`: Reviewer approved changes
- `CHANGES_REQUESTED`: Reviewer requested changes
- `COMMENTED`: Review comment without approval/rejection
- `DISMISSED`: Review was dismissed (manually or automatically)
- `PENDING`: Review in progress (rare in API responses)

**PyGithub Access**:
```python
review.user.login     # str
review.state          # str (APPROVED, CHANGES_REQUESTED, etc.)
review.submitted_at   # datetime
```

**Counting Valid Approvals**:
```python
# Get latest review per user (latest wins)
latest_reviews = {}
for review in reviews:
    user = review.user.login
    if user not in latest_reviews or \
       review.submitted_at > latest_reviews[user].submitted_at:
        latest_reviews[user] = review

# Count APPROVED reviews
approved_count = sum(
    1 for r in latest_reviews.values()
    if r.state == "APPROVED"
)
```

**Error Handling**:
- `404 Not Found`: PR doesn't exist
- `403 Forbidden`: Token lacks access

---

### 4. Get Branch Protection

**Endpoint**: `GET /repos/{owner}/{repo}/branches/{branch}/protection`

**PyGithub**:
```python
branch = repo.get_branch(pr.base.ref)
protection = branch.get_protection()
pr_reviews = protection.required_pull_request_reviews
```

**Response Fields** (relevant subset):
```json
{
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 2
  }
}
```

**PyGithub Access**:
```python
pr_reviews.dismiss_stale_reviews            # bool
pr_reviews.required_approving_review_count  # int
```

**Error Handling**:
- `404 Not Found`: Branch protection not configured (use default: 1 required approval)
- `403 Forbidden`: User lacks admin access to repository

**Default Behavior**:
```python
try:
    branch = repo.get_branch(pr.base.ref)
    protection = branch.get_protection()
    required = protection.required_pull_request_reviews.required_approving_review_count
except github.GithubException as e:
    if e.status == 404:
        required = 1  # Default per spec
    else:
        raise
```

---

### 5. List Pull Request Commits

**Endpoint**: `GET /repos/{owner}/{repo}/pulls/{pull_number}/commits`

**PyGithub**:
```python
commits = pr.get_commits()
```

**Response Fields** (relevant subset):
```json
{
  "sha": "abc123def456",
  "commit": {
    "author": {
      "name": "Alice Developer",
      "email": "alice@example.com",
      "date": "2025-10-29T16:20:00Z"
    },
    "message": "Fix bug in authentication"
  }
}
```

**PyGithub Access**:
```python
commit.sha                     # str
commit.commit.author.date      # datetime
commit.commit.message          # str
```

**Usage for Staleness**:
```python
commits = list(pr.get_commits())
if commits:
    last_commit_time = commits[-1].commit.author.date
    # Compare with last_approval_time to detect invalidation
```

**Error Handling**:
- `404 Not Found`: PR doesn't exist
- `422 Unprocessable Entity`: PR has no commits (edge case)

---

## Error Handling Summary

### Common Errors

| Status Code | Meaning | Action |
|-------------|---------|--------|
| `401 Unauthorized` | Invalid or expired token | Exit with error, instruct user to check GITHUB_TOKEN |
| `403 Forbidden` | Insufficient permissions or rate limit | Check rate limit, verify token scopes |
| `404 Not Found` | Resource doesn't exist | For branch protection: use default (1 approval). For other resources: log warning, skip |
| `422 Unprocessable Entity` | Invalid request | Log error, skip resource |
| `500/502/503` | GitHub server error | Log error, retry or skip |

### Error Handling Strategy

**Rate Limit Exceeded**:
```python
try:
    # API operations
except RateLimitExceededException as e:
    reset_time = e.rate_limit.core.reset
    wait_minutes = (reset_time - datetime.now()).total_seconds() / 60

    print(f"ERROR: GitHub API rate limit exceeded", file=sys.stderr)
    print(f"Rate limit resets at: {reset_time}", file=sys.stderr)
    print(f"Please retry in {int(wait_minutes)} minutes", file=sys.stderr)

    sys.exit(1)  # Exit WITHOUT sending Slack notification
```

**Network Errors**:
```python
try:
    # API operations
except github.GithubException as e:
    print(f"GitHub API error: {e.status} {e.data}", file=sys.stderr)
    sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"Network error: {e}", file=sys.stderr)
    sys.exit(1)
```

**Missing Resources** (non-fatal):
```python
try:
    branch = repo.get_branch(pr.base.ref)
    protection = branch.get_protection()
    required = protection.required_pull_request_reviews.required_approving_review_count
except github.GithubException as e:
    if e.status == 404:
        required = 1  # Default, continue processing
        print(f"INFO: No branch protection for {repo.name}/{pr.base.ref}, using default")
    else:
        raise  # Re-raise unexpected errors
```

**Repository Access Denied**:
```python
for repo in org.get_repos():
    try:
        pulls = repo.get_pulls(state="open")
        # Process pulls...
    except github.GithubException as e:
        if e.status == 403 or e.status == 404:
            print(f"WARNING: Cannot access {repo.name}, skipping", file=sys.stderr)
            continue  # Skip this repo, continue with others
        else:
            raise
```

## Data Validation

**Required Validations**:

1. **PR Draft Status**: Always check `pr.draft` before processing
2. **Timezone Awareness**: All datetime objects from GitHub API are timezone-aware (UTC)
3. **Null Checks**: Handle cases where `requested_reviewers` may be empty
4. **User Access**: Verify user can access repository before querying PRs

**Example Validation**:
```python
def is_valid_pr(pr) -> bool:
    """Check if PR is valid for staleness tracking."""
    # Skip drafts
    if pr.draft:
        return False

    # Must have valid created_at
    if pr.created_at is None:
        return False

    # Must have valid base branch
    if not pr.base or not pr.base.ref:
        return False

    return True
```

## Testing Strategy

**Unit Tests**: Mock GitHub API responses using fixtures
**Integration Tests**: Use real GitHub API with test repository (limit API calls)
**Fixtures**: Store sample API responses in `tests/fixtures/github_*.json`

**Example Fixture** (`tests/fixtures/github_pr_response.json`):
```json
{
  "number": 123,
  "title": "Test PR",
  "html_url": "https://github.com/test/repo/pull/123",
  "state": "open",
  "draft": false,
  "created_at": "2025-10-25T10:00:00Z",
  "user": {"login": "alice"},
  "requested_reviewers": [{"login": "bob"}],
  "base": {"ref": "main"}
}
```

## Rate Limit Optimization

**Best Practices**:
1. **Check rate limit at startup** before processing
2. **Batch operations** where possible (e.g., get all repos at once)
3. **Cache repository metadata** to avoid redundant calls
4. **Skip inaccessible repositories** rather than retrying

**Estimated API Calls** (for 50 repos, 100 PRs):
- List org repos: 1 call
- List PRs per repo: 50 calls (1 per repo)
- Get reviews per PR: 100 calls (1 per PR)
- Get commits per PR: 100 calls (1 per PR)
- Get branch protection: ~10 calls (cached per unique base branch)
- **Total**: ~261 calls (well within 5,000/hour limit)

## Next Steps

With this GitHub API contract defined:
1. Implement `GitHubClient` in `src/review_ops/github_client.py`
2. Create test fixtures in `tests/fixtures/`
3. Write integration tests with mocked responses
4. Implement error handling as specified
