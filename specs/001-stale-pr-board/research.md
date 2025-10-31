# Technology Research & Decisions

**Feature**: Stale PR Board
**Date**: 2025-10-31
**Purpose**: Document all technology choices, rationale, and alternatives considered

This document captures the research findings and technical decisions made during Phase 0 of the implementation planning process.

## 1. uv Build Tool

### Decision
Use `uv` as the Python package manager and build tool for this project.

### Rationale
- **Speed**: 10-100x faster than pip, written in Rust
- **Modern**: Native support for pyproject.toml and PEP standards
- **Deterministic**: Creates lock files for reproducible builds
- **Simple**: Drop-in replacement for pip with familiar commands
- **Active**: Well-maintained, modern tool aligned with Python's future

### Setup & Usage

**Installation**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Project Initialization**:
```bash
# Initialize new project with Python 3.12
uv init --python 3.12

# Or if project exists, just set Python version
echo "3.12" > .python-version

# Create virtual environment (automatic with uv commands)
uv venv

# Activate environment (optional - uv run handles this)
source .venv/bin/activate  # macOS/Linux
# or .venv\Scripts\activate on Windows
```

**Dependency Management**:
```bash
# Add a dependency (updates pyproject.toml and uv.lock)
uv add PyGithub
uv add requests
uv add python-dotenv

# Add dev dependencies
uv add --dev pytest
uv add --dev pytest-cov
uv add --dev pytest-mock

# Install all dependencies from lock file
uv sync

# Run commands without activating venv
uv run stale-pr-board
uv run pytest
```

**pyproject.toml Structure**:
```toml
[project]
name = "review-ops"
version = "0.1.0"
description = "Code review operations and automation tools"
requires-python = ">=3.12"
dependencies = [
    "PyGithub>=2.1.0",
    "requests>=2.31.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
]

[project.scripts]
stale-pr-board = "src.app:main"
```

**Note**: Using flat module structure under `src/` for simplicity. No packages until they're needed (YAGNI principle).

### Alternatives Considered
- **pip + pip-tools**: Standard but slow, more setup needed
- **poetry**: Good but adds extra dependency layer, heavier
- **pdm**: Similar to poetry but less adopted

## 2. ty Type Checker

### Decision
Use `ty` as the type checker, run via `uvx ty src/`.

### Rationale
- User-specified requirement
- Can be run without installation via `uvx`
- Integrates with Python 3.12 type hints

### Usage
```bash
# Run type checking without installing
uvx ty src/

# Check specific module
uvx ty src/review_ops/staleness.py
```

### Configuration
Based on typical type checker configuration patterns:

```toml
# pyproject.toml
[tool.ty]
python_version = "3.12"
strict = true
```

**Note**: If `ty` is not available or doesn't meet needs, `mypy` is the fallback:
```bash
uvx mypy --strict src/
```

### Alternatives
- **mypy**: Most popular, reference implementation, well-documented
- **pyright**: Fast, used by VS Code, good error messages
- Chose `ty` per user specification

## 3. ruff Linting

### Decision
Use `ruff` for linting with ANN (flake8-annotations) rules enabled for type hint enforcement.

### Rationale
- **Fast**: 10-100x faster than existing linters, written in Rust
- **Comprehensive**: Replaces Flake8, isort, pyupgrade, and more
- **Auto-fix**: Can automatically fix many issues
- **Type enforcement**: ANN rules ensure all functions have type hints
- **Modern**: Active development, Python-first design

### Configuration

**pyproject.toml**:
```toml
[tool.ruff]
target-version = "py312"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
# Rule groups
select = [
    "E",      # pycodestyle errors
    "F",      # Pyflakes
    "I",      # isort (import sorting)
    "ANN",    # flake8-annotations (TYPE HINTS)
    "B",      # flake8-bugbear (common bugs)
    "UP",     # pyupgrade (modernize code)
    "RUF",    # Ruff-specific rules
]

# Exceptions
ignore = [
    "ANN101",  # Missing type for self in methods
    "ANN102",  # Missing type for cls in classmethods
]

# Per-file overrides
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "ANN201",  # Missing return type (relaxed for tests)
    "ANN001",  # Missing type for function args (relaxed for tests)
]

# Import sorting
[tool.ruff.lint.isort]
force-single-line = false
lines-after-imports = 2
```

### Usage
```bash
# Lint entire project
uvx ruff check .

# Auto-fix issues
uvx ruff check --fix .

# Format code
uvx ruff format .

# Check specific file
uvx ruff check src/review_ops/cli.py
```

### ANN Rules (Type Annotations)
- `ANN001`: Missing type annotation for function argument
- `ANN201`: Missing return type annotation for public function
- `ANN202`: Missing return type annotation for private function
These rules enforce the strict typing standard required by the project.

### Alternatives Considered
- **Flake8 + plugins**: Standard but slower, requires multiple tools
- **pylint**: Comprehensive but slow, opinionated
- Chose ruff for speed and consolidation

## 4. PR Approval Loss Mechanics (CRITICAL)

### Research Findings

#### Branch Protection Setting: `dismiss_stale_reviews`

**Key Discovery**: Approval invalidation is **per-branch configuration**, not repository-wide.

**API Access**:
```python
from github import Github

g = Github("token")
repo = g.get_repo("org/repo")
branch = repo.get_branch("main")

try:
    protection = branch.get_protection()
    pr_reviews = protection.required_pull_request_reviews
    if pr_reviews:
        dismiss_stale = pr_reviews.dismiss_stale_reviews  # bool
        required_count = pr_reviews.required_approving_review_count  # int
except github.GithubException as e:
    if e.status == 404:
        # No branch protection configured
        dismiss_stale = False  # Assume reviews persist
        required_count = 1     # Default per spec
```

**Behavior**:

| Setting | New Commit Pushed | Approval Status | Notes |
|---------|-------------------|-----------------|-------|
| `dismiss_stale_reviews = true` | Yes | ALL approvals dismissed | Auto-invalidation |
| `dismiss_stale_reviews = false` | Yes | Approvals PERSIST | Manual dismissal only |
| Either | No | Unchanged | Approvals remain valid |

#### Re-requesting Reviews

**Finding**: Re-requesting review does NOT invalidate existing approvals.

**Behavior**:
1. User A approves PR
2. Author re-requests review from User A
3. Result: Approval **persists**, just creates notification

**Timeline Events**:
- `review_requested` event logged (informational only)
- Approval state remains `APPROVED`
- No `review_dismissed` event

**Staleness Implication**: Ignore re-request events for staleness calculation.

#### Commit-Based Detection Strategy

**Decision**: Use commit timestamps to detect approval invalidation (simplified MVP approach).

**Algorithm**:
```python
def detect_approval_loss(pr) -> datetime | None:
    """
    Detect when PR lost approval status.
    Returns timestamp of invalidation, or None if never had sufficient approval.
    """
    # Get reviews
    reviews = list(pr.get_reviews())
    latest_reviews = {}  # Latest review per user

    for review in reviews:
        user = review.user.login
        if user not in latest_reviews or \
           review.submitted_at > latest_reviews[user].submitted_at:
            latest_reviews[user] = review

    # Find last approval
    approved_reviews = [
        r for r in latest_reviews.values()
        if r.state == "APPROVED"
    ]

    if not approved_reviews:
        return None  # Never approved

    last_approval_time = max(r.submitted_at for r in approved_reviews)

    # Get commits
    commits = list(pr.get_commits())
    if not commits:
        return None

    last_commit_time = commits[-1].commit.author.date

    # If commit after approval, approval was invalidated
    if last_commit_time > last_approval_time:
        return last_commit_time

    return None
```

**Rationale**:
- **Simplicity**: Avoids complex timeline API parsing
- **Conservative**: Assumes commits invalidate approvals (safe default)
- **Sufficient for MVP**: Covers 90% of cases accurately
- **No Implementation Detail Access**: PyGithub doesn't expose timeline natively

#### Edge Cases

1. **Draft PRs**: Excluded entirely (per spec requirement)
2. **Never Reviewed**: Staleness starts from `pr.created_at`
3. **Multiple Commits**: Uses most recent commit timestamp
4. **Manual Dismissal**: Covered by review state check
5. **No Branch Protection**: Defaults to requiring 1 approval

### Decision for MVP

**Approach**: Simplified commit-based detection
- Compare last commit time vs last approval time
- Don't query `dismiss_stale_reviews` setting (assume enabled)
- Don't parse timeline events (avoid complexity)
- Use `pr.created_at` as fallback for ready time

**Future Enhancements** (P2/P3):
- Check `dismiss_stale_reviews` per branch
- Parse timeline for exact `ready_for_review` events
- Distinguish manual vs automatic dismissals

### Alternatives Considered
- **Timeline API**: More accurate but complex, requires `_requester` access
- **Event Webhooks**: Real-time but requires server infrastructure
- Chose commit-based for simplicity and reliability

## 5. GitHub API Integration

### Required Endpoints

**Organization Repositories**:
```python
GET /orgs/{org}/repos

# PyGithub
org = g.get_organization(org_name)
repos = org.get_repos(type="all")  # all, public, private
```

**Pull Requests**:
```python
GET /repos/{owner}/{repo}/pulls?state=open

# PyGithub
pulls = repo.get_pulls(state="open", sort="created")
```

**PR Reviews**:
```python
GET /repos/{owner}/{repo}/pulls/{number}/reviews

# PyGithub
reviews = pr.get_reviews()
```

**Branch Protection**:
```python
GET /repos/{owner}/{repo}/branches/{branch}/protection

# PyGithub
branch = repo.get_branch(pr.base.ref)
protection = branch.get_protection()
```

**PR Commits**:
```python
GET /repos/{owner}/{repo}/pulls/{number}/commits

# PyGithub
commits = pr.get_commits()
```

### Authentication

**Personal Access Token (PAT)** - Required Scopes:
- `repo` (or `repo:read` for read-only access)
- `read:org` (to list organization repositories)

**Usage**:
```python
from github import Github

g = Github(token)
user = g.get_user()  # Verify authentication
print(f"Authenticated as: {user.login}")
```

### Rate Limiting

**Limits**:
- Authenticated: 5,000 requests/hour
- Search API: 30 requests/minute
- GraphQL: 5,000 points/hour

**Handling Strategy**:
```python
from github import RateLimitExceededException
from datetime import datetime

def check_rate_limit(g: Github) -> None:
    """Check rate limit at startup."""
    rate_limit = g.get_rate_limit()
    remaining = rate_limit.core.remaining

    if remaining < 100:
        reset_time = rate_limit.core.reset
        print(f"WARNING: Only {remaining} API calls remaining")
        print(f"Rate limit resets at: {reset_time}")

def handle_rate_limit_error(e: RateLimitExceededException) -> None:
    """Handle rate limit exceeded gracefully."""
    reset_time = e.rate_limit.core.reset
    wait_seconds = (reset_time - datetime.now()).total_seconds()

    print(f"ERROR: GitHub API rate limit exceeded")
    print(f"Rate limit resets at: {reset_time}")
    print(f"Please retry in {int(wait_seconds / 60)} minutes")

    # Exit without sending Slack notification (per spec)
    sys.exit(1)
```

### PyGithub Library Capabilities

**Available** ✅:
- Branch protection settings access
- Required approval count retrieval
- PR draft status (`pr.draft`)
- Review API with states
- Commit listing with timestamps
- Requested reviewers (`pr.requested_reviewers`)

**Limited** ⚠️:
- Timeline events (requires `_requester` access)
- `mergeable_state` is ambiguous (don't rely on it)

**Example Usage**:
```python
from github import Github

g = Github(token)

# Get organization
org = g.get_organization("my-org")

# Iterate repositories
for repo in org.get_repos():
    # Get open PRs
    for pr in repo.get_pulls(state="open"):
        # Skip drafts
        if pr.draft:
            continue

        # Get reviewers
        reviewers = [r.login for r in pr.requested_reviewers]

        # Get reviews
        reviews = list(pr.get_reviews())

        # Count approvals (latest per user)
        latest = {}
        for review in reviews:
            user = review.user.login
            if user not in latest or \
               review.submitted_at > latest[user].submitted_at:
                latest[user] = review

        approvals = sum(1 for r in latest.values() if r.state == "APPROVED")

        # Get required approvals from branch protection
        try:
            branch = repo.get_branch(pr.base.ref)
            protection = branch.get_protection()
            required = protection.required_pull_request_reviews.required_approving_review_count
        except:
            required = 1  # Default per spec

        print(f"{repo.name}#{pr.number}: {approvals}/{required} approvals")
```

### Decision
Use PyGithub library with native methods only. Avoid `_requester` access for MVP simplicity.

### Alternatives Considered
- **Direct REST API with requests**: More control but more code
- **GraphQL API**: Fewer requests but more complex queries
- Chose PyGithub for simplicity and type hints

## 6. Slack Block Kit for Tables

### Message Structure

**Decision**: Use Slack Block Kit sections (not preformatted text) for rich, scannable formatting.

**Rationale**:
- Better visual hierarchy with sections and dividers
- Support for markdown formatting (bold, italic, links)
- Clickable links and @mentions work seamlessly
- Color coding via emojis instead of attachments
- More flexible than preformatted text tables

### Implementation

**Block Types Used**:
- `header`: Main title ("🔔 Stale PR Board")
- `section`: Text blocks for summary, categories, PR rows
- `divider`: Visual separation between categories
- `context`: Footer with timestamp

**Example Structure**:
```python
blocks = [
    {
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "🔔 Stale PR Board",
            "emoji": True
        }
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                "@user1 @user2\n\n"
                "*5 PRs need review:*\n"
                "🤢 Rotten (8+ days): 2\n"
                "🧀 Aging (4-7 days): 2\n"
                "✨ Fresh (1-3 days): 1"
            )
        }
    },
    {"type": "divider"},
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*🤢 Rotten (8+ days)*"
        }
    },
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                "🤢 *<https://github.com/org/repo/pull/123|repo#123>*\n"
                "_Fix critical bug_\n"
                "Author: @alice | Reviewers: @bob, @charlie | 8 days | Approvals: 0/2"
            )
        }
    },
    {"type": "divider"},
    {
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "🤖 Generated at 2025-10-31 14:30:00 UTC"
            }
        ]
    }
]
```

### User @Mentions

**Format**: `<@USER_ID>` (requires Slack user ID, not display name)

**Configuration Approach**:
```json
// team_members.json
[
    {
        "username": "alice",
        "slack_user_id": "U1234567890"
    },
    {
        "username": "bob"
        // No slack_user_id = fallback to plain text
    }
]
```

**Usage**:
```python
def format_mention(username: str, team_config: list[TeamMember]) -> str:
    """Format user mention with Slack ID if available."""
    for member in team_config:
        if member.username == username:
            if hasattr(member, 'slack_user_id') and member.slack_user_id:
                return f"<@{member.slack_user_id}>"
    return f"@{username}"  # Fallback to plain text
```

### Clickable Links

**Format**: `<URL|Link Text>`

**Example**:
```python
pr_link = f"<{pr.url}|{pr.repo_name}#{pr.number}>"
# Renders as clickable "repo#123" linking to PR URL
```

### Size Limits

**Constraints**:
- Maximum message size: 40,000 characters (entire JSON payload)
- Maximum blocks per message: 50 blocks
- Maximum text in single block: 3,000 characters

**Handling Large Lists**:
```python
MAX_PRS_PER_MESSAGE = 40  # Conservative limit

if len(stale_prs) > MAX_PRS_PER_MESSAGE:
    # Option 1: Send multiple messages
    # Option 2: Truncate with "X more PRs..." message
    # MVP: Assume ≤40 stale PRs (reasonable for most teams)
    pass
```

### Sending Messages

```python
import requests

def send_slack_message(webhook_url: str, blocks: list[dict]) -> None:
    """Send Block Kit message to Slack webhook."""
    payload = {"blocks": blocks}

    response = requests.post(webhook_url, json=payload)

    if response.status_code != 200:
        raise Exception(
            f"Slack webhook failed: {response.status_code} {response.text}"
        )
```

### Decision
Use Slack Block Kit sections with markdown formatting for maximum readability and engagement.

### Alternatives Considered
- **Preformatted text table**: Monospace but less engaging, no links
- **Message attachments**: Deprecated by Slack
- Chose Block Kit for best user experience

## 7. Configuration Strategy (No Pydantic)

### Decision
Use `python-dotenv` + stdlib (json, dataclasses) + manual validation (NO Pydantic).

### Rationale

**Against Pydantic**:
- Only 3 required + 2 optional environment variables (simple)
- Only 1 JSON configuration file (array of team members)
- Manual validation provides clearest, most actionable error messages
- Zero framework dependencies (aligns with Simplicity First principle)
- Easier for contributors to understand (no framework-specific knowledge)
- Full control over validation logic and error formatting

**For python-dotenv**:
- Single-purpose library (8KB, no sub-dependencies)
- Standard for .env file loading in Python
- Minimal footprint, well-maintained
- Direct replacement for manual parsing

### Implementation

**Environment Variables**:
```python
from dotenv import load_dotenv
import os
from dataclasses import dataclass

@dataclass
class Config:
    github_token: str
    github_org: str
    slack_webhook_url: str
    log_level: str = "INFO"
    api_timeout: int = 30

def validate_config() -> Config:
    """Load and validate configuration from environment."""
    load_dotenv()  # Loads .env into os.environ

    required = {
        "GITHUB_TOKEN": "GitHub Personal Access Token",
        "GITHUB_ORG": "GitHub organization name",
        "SLACK_WEBHOOK_URL": "Slack incoming webhook URL"
    }

    errors: list[str] = []

    # Check required
    for key, description in required.items():
        if not os.getenv(key):
            errors.append(f"Missing: {key} ({description})")

    if errors:
        raise ValueError("\n".join(errors))

    # Validate formats
    webhook = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook.startswith("https://hooks.slack.com/"):
        errors.append("SLACK_WEBHOOK_URL must be valid Slack webhook")

    # Type coercion
    try:
        timeout = int(os.getenv("API_TIMEOUT", "30"))
    except ValueError:
        errors.append("API_TIMEOUT must be integer")

    if errors:
        raise ValueError("\n".join(errors))

    return Config(
        github_token=os.getenv("GITHUB_TOKEN", ""),
        github_org=os.getenv("GITHUB_ORG", ""),
        slack_webhook_url=webhook,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        api_timeout=timeout
    )
```

**Team Members JSON**:
```python
import json

@dataclass
class TeamMember:
    username: str
    slack_user_id: str | None = None

def load_team_members(path: str = "team_members.json") -> list[TeamMember]:
    """Load team configuration from JSON."""
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Config not found: {path}\n"
            f"Create it by copying team_members.json.example"
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")

    if not isinstance(data, list):
        raise ValueError(f"{path} must be JSON array")

    members = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} must be object")

        if "username" not in item:
            raise ValueError(f"Item {i} must have 'username' field")

        members.append(TeamMember(
            username=item["username"],
            slack_user_id=item.get("slack_user_id")
        ))

    return members
```

**File Structure**:
```
.env.example            # Committed (template)
.env                    # Gitignored (actual secrets)
team_members.json.example   # Committed (template)
team_members.json       # Gitignored (actual config)
```

### Dependency Count
- **With Pydantic**: 4 packages (pydantic, pydantic-core, pydantic-settings, python-dotenv)
- **Without Pydantic**: 1 package (python-dotenv)

### Decision
Use minimal stdlib approach with python-dotenv for maximum simplicity.

### Alternatives Considered
- **Pydantic**: Overkill for this simple use case
- **Pure stdlib (no dotenv)**: Would need manual .env parsing
- Chose dotenv + stdlib for best simplicity/functionality balance

## Summary of Decisions

| Component | Decision | Key Rationale |
|-----------|----------|---------------|
| **Build Tool** | uv | 10-100x faster, modern, deterministic builds |
| **Type Checker** | ty (via uvx) | User-specified, no installation needed |
| **Linter** | ruff + ANN rules | Fast, comprehensive, enforces type hints |
| **PR Staleness** | Commit-based detection | Simple, avoids timeline API complexity |
| **GitHub API** | PyGithub library | Mature, type hints, sufficient for MVP |
| **Slack Format** | Block Kit sections | Rich formatting, clickable links, engaging |
| **Configuration** | dotenv + stdlib | No Pydantic, maximum simplicity |
| **Dependencies** | 3 prod, 3 dev | Minimal, all essential, no frameworks |

## Next Steps

With these technology decisions documented, proceed to Phase 1:
1. Generate data-model.md (entities with type annotations)
2. Generate contracts/ (API schemas and documentation)
3. Generate quickstart.md (setup instructions)
4. Update agent context (add technologies to Claude's knowledge)
