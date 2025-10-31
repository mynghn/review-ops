# Implementation Plan: Stale PR Board

**Branch**: `001-stale-pr-board` | **Date**: 2025-10-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-stale-pr-board/spec.md`

**Note**: This file documents the implementation plan for the Stale PR Board feature.

## Summary

Build a Python 3.12 command-line application that fetches open PRs from a GitHub organization involving team members, calculates staleness (days without sufficient approval), and sends a formatted Slack notification with PRs sorted by staleness. PRs are categorized with emojis (✨ Fresh 1-3 days, 🧀 Aging 4-7 days, 🤢 Rotten 8+ days) and displayed in a Slack table with author @mentions, reviewer @mentions, and clickable PR links.

## Technical Context

**Language/Version**: Python 3.12
**Build Tool**: `uv` (Rust-based package manager, 10-100x faster than pip)
**Type Checker**: `ty` (run with `uvx ty src/`)
**Linter**: `ruff` (run with `uvx ruff check .`)
**Primary Dependencies**:
- PyGithub 2.1+ (GitHub API client)
- requests 2.31+ (Slack webhook HTTP calls)
- python-dotenv 1.0+ (environment variable loading from .env)

**Testing**: pytest 7.4+ with pytest-cov (coverage), pytest-mock (mocking)
**Target Platform**: Command-line script (local execution, manual invocation)
**Project Type**: Single project (script-style application)

**Coding Standards**:
- **STRICT TYPE HINTS**: All functions must have complete type annotations (parameters + return type)
- All class attributes must be typed
- No implicit Any types
- Use `from __future__ import annotations` for forward references
- Use modern union syntax: `str | None` instead of `Optional[str]`

**Performance Goals**:
- ≤2 minutes execution time for organizations with up to 50 repositories
- ≤3 minutes execution time for organizations with up to 100 repositories and 200 open PRs

**Constraints**:
- GitHub API rate limit: 5,000 requests/hour (authenticated users)
- Slack message size: 40,000 characters max, 50 blocks max per message
- Must handle rate limiting gracefully (print error with reset time, exit without Slack notification)
- Environment variables stored in .env file (gitignored)
- Configuration file also gitignored (team_members.json)

**Scale/Scope**:
- Organizations with up to 100 repositories
- Up to 200 open PRs across organization
- Teams with 5-20 members
- Single Slack channel notification target

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **Principle I: Simplicity First (NON-NEGOTIABLE)**
- **PASS**: No Pydantic (using stdlib json + dataclasses + python-dotenv)
- **PASS**: No timeline API complexity (using commit-based staleness detection)
- **PASS**: Direct GitHub API calls via PyGithub (no repository patterns or abstractions)
- **PASS**: Minimal dependencies (3 production: PyGithub, requests, python-dotenv; 3 dev: pytest, pytest-cov, pytest-mock)
- **PASS**: Simple configuration (environment variables + JSON file)
- **Justification**: This approach has the minimum necessary components for the MVP with no speculative abstractions

✅ **Principle II: Small Scope (NON-NEGOTIABLE)**
- **PASS**: P1 story (User Story 1 - Basic Stale PR Detection & Notification) fits within one specify-plan-tasks-implement cycle (3-5 days)
- **PASS**: Feature delivers independently testable value (stale PR detection + Slack notification)
- **PASS**: P1 is viable MVP (team can immediately use it to improve code review response times)
- **Scope Breakdown**: Single phase MVP → P2 enhanced UI → P3 configurable scoring (properly decomposed)

✅ **Principle III: Test-Driven Quality (NON-NEGOTIABLE)**
- **PASS**: TDD mandatory: Write tests → Verify fail → Implement → Tests pass
- **PASS**: Automated tests for all 8 acceptance scenarios in P1 user story
- **PASS**: Using real components (PyGithub library, pytest) with mocked external services (GitHub API responses, Slack webhook)
- **Mock justification**: External services (GitHub API, Slack webhooks) require mocking as they are external APIs - setup with real services impractical for test execution
- **PASS**: Clear acceptance scenarios defined in spec.md for independent validation

**Gate Status**: ✅ ALL GATES PASSED - No violations requiring justification

## Project Structure

### Documentation (this feature)

```text
specs/001-stale-pr-board/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── team_members.schema.json      # JSON schema for team configuration
│   ├── github_api_contract.md        # GitHub API endpoints and formats
│   └── slack_webhook_contract.md     # Slack Block Kit message structure
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
review-ops/
├── .python-version      # Pin Python version to 3.12
├── pyproject.toml       # Project metadata, dependencies, tool configs (ty, ruff, pytest)
├── uv.lock             # Dependency lock file (generated by uv)
├── .env.example        # Example environment variables (committed)
├── .env                # Actual secrets (GITIGNORED)
├── team_members.json.example  # Example team configuration (committed)
├── team_members.json   # Actual team config (GITIGNORED)
├── .gitignore          # Git ignore patterns
├── README.md           # Project documentation

src/                    # Flat module structure (no packages yet)
├── app.py              # Main application entry point and CLI
├── config.py           # Configuration loading and validation (stdlib only)
├── models.py           # Data models using dataclasses (TeamMember, PullRequest, StalePR, Config)
├── github_client.py    # GitHub API interactions via PyGithub
├── slack_client.py     # Slack webhook posting and Block Kit message formatting
└── staleness.py        # Staleness calculation logic (commit-based detection)

tests/
├── conftest.py         # Pytest configuration and shared fixtures
├── unit/               # Fast unit tests (no external I/O)
│   ├── test_config.py      # Configuration validation tests
│   ├── test_models.py      # Data model tests
│   └── test_staleness.py   # Staleness calculation logic tests
├── integration/        # Integration tests with mocked external APIs
│   ├── test_github_client.py   # GitHub client with mocked API responses
│   └── test_slack_client.py    # Slack client with mocked webhook calls
└── fixtures/           # Test data (mocked API responses, sample configs)
    ├── github_pr_response.json       # Sample GitHub PR API response
    ├── github_reviews_response.json  # Sample GitHub reviews API response
    └── team_members_valid.json       # Valid team configuration example
```

**Structure Decision**: Selected **flat module structure** (no packages) following the "Simplicity First" principle. All application code lives under `src/` as individual Python modules without package hierarchy. This is the simplest structure for a single feature and avoids premature abstraction. When future features are added to the `review-ops` project, shared modules can be factored out into packages as needed (YAGNI - You Aren't Gonna Need It yet).

## Complexity Tracking

No violations requiring justification - all Constitution principles passed without exceptions.

## Phase 0: Research & Technology Decisions

**Objective**: Resolve all technical unknowns and document technology choices with clear rationale.

**Research Topics**:

1. **uv Build Tool**
   - Project initialization with Python 3.12
   - Dependency management workflow (adding, updating, locking dependencies)
   - Virtual environment handling
   - Integration with pyproject.toml

2. **ty Type Checker**
   - Installation and usage with uvx
   - Configuration options for Python 3.12
   - Strict typing enforcement capabilities
   - Comparison with mypy/pyright if needed

3. **ruff Linting**
   - Configuration for Python 3.12
   - ANN rules (flake8-annotations) for enforcing type hints
   - Import sorting (isort integration)
   - Auto-fix capabilities
   - Recommended rule sets for this project

4. **PR Approval Loss Mechanics** (CRITICAL)
   - `dismiss_stale_reviews` branch protection setting (per-branch configuration)
   - How re-requesting reviews affects approval status (spoiler: doesn't invalidate)
   - Commit-based detection strategy (comparing commit time vs approval time)
   - Rationale for MVP approach: Avoid complex timeline API, use commit timestamps
   - Edge cases: Draft PRs, no reviews, multiple commits after approval

5. **GitHub API Integration**
   - Authentication using Personal Access Token (required scopes)
   - Required endpoints:
     - List organization repositories
     - List open pull requests per repository
     - Get PR reviews and approval status
     - Get branch protection rules (for required approval count)
     - Get PR commits (for approval invalidation detection)
   - Rate limit handling strategy (check at start, handle exceptions gracefully)
   - PyGithub library capabilities and limitations

6. **Slack Block Kit for Tables**
   - Formatting sorted tables using section blocks
   - User @mentions (requires Slack user IDs, not display names)
   - Clickable link format: `<url|link text>`
   - Message size limits (40,000 chars, 50 blocks)
   - Best practices for scannable messages (emojis, bold, sections, dividers)

7. **Configuration Strategy (No Pydantic)**
   - Using python-dotenv for .env file loading
   - Manual validation with clear, actionable error messages
   - Type hints for IDE support
   - stdlib json for team_members.json parsing
   - Comparison with Pydantic approach and why stdlib is sufficient for this scope

**Output**: `research.md` documenting each decision with:
- Decision made
- Rationale for the choice
- Alternatives considered and why they were not selected
- Code examples where applicable

## Phase 1: Design & Contracts

**Prerequisites**: Phase 0 research complete

**Tasks**:

### 1. Data Model (`data-model.md`)

Define all entities with complete type annotations:

**TeamMember**
- `github_username: str` - GitHub username

**PullRequest**
- `repo_name: str` - Repository name
- `number: int` - PR number
- `title: str` - PR title
- `author: str` - PR author GitHub username
- `reviewers: list[str]` - List of requested reviewer GitHub usernames
- `url: str` - Full URL to PR on GitHub
- `created_at: datetime` - PR creation timestamp
- `ready_at: datetime | None` - When PR was marked ready for review (None if draft)
- `current_approvals: int` - Number of valid approving reviews
- `required_approvals: int` - Required approvals from branch protection (default: 1)
- `base_branch: str` - Target branch name

**StalePR**
- `pr: PullRequest` - The pull request
- `staleness_days: float` - Days without sufficient approval
- `category: Literal["fresh", "aging", "rotten"]` - Staleness category
- `emoji: str` - Property that returns corresponding emoji (✨/🧀/🤢)

**Config**
- `github_token: str` - GitHub Personal Access Token
- `github_org: str` - GitHub organization name
- `slack_webhook_url: str` - Slack incoming webhook URL
- `log_level: str` - Logging level (default: "INFO")
- `api_timeout: int` - API request timeout in seconds (default: 30)

**Relationships**:
- TeamMember list → used to filter PRs (author or reviewer must be in team)
- Config → initializes GitHubClient and SlackClient
- PullRequest → transformed into StalePR if lacking sufficient approval
- StalePR list → sorted by staleness_days (descending) → formatted into Slack message

**Note on ApprovalEvent**: The spec.md defines an ApprovalEvent entity, but it is not implemented as a dataclass in the plan. Rationale: Approval events are transient API responses used to calculate staleness, not persistent domain objects. The staleness calculation algorithm derives timing information from PR commits and reviews without storing intermediate events.

### 2. API Contracts (`contracts/` directory)

**team_members.schema.json**
- JSON schema defining team_members.json structure
- Array of objects with required `github_username` field (string)
- Optional `slack_user_id` field for @mentions

**staleness_rules.schema.json** *(P3 - Configurable Scoring)*
- JSON schema defining staleness_rules.json structure
- Optional repository_weights object (repo name → multiplier)
- Optional label_bonuses object (label name → added days)
- Optional custom_thresholds for staleness categories
- Documents available scoring rule types per FR-031

**github_api_contract.md**
- Document all GitHub API endpoints used
- Request/response formats
- Required authentication scopes
- Error handling for rate limits, network failures, missing repos
- Example responses for testing fixtures

**slack_webhook_contract.md**
- Document Slack Block Kit message structure
- Block types used (header, section, divider, context)
- Field formats (mrkdwn for clickable links, plain_text for headers)
- Size constraints and how to handle large PR lists
- Example message payloads

### 3. Quickstart Guide (`quickstart.md`)

**Prerequisites**:
- Python 3.12 installed
- uv installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

**Setup Steps**:
1. Clone repository
2. Copy `.env.example` to `.env` and fill in secrets
3. Copy `team_members.json.example` to `team_members.json` and add team
4. Create virtual environment: `uv venv`
5. Install dependencies: `uv sync`

**Running**:
- Execute: `uv run stale-pr-board` or `python src/app.py`
- Type check: `uvx ty src/`
- Lint: `uvx ruff check .`
- Auto-fix: `uvx ruff check --fix .`
- Run tests: `uv run pytest`

**Troubleshooting**:
- Rate limit errors: Wait for reset time shown in error message
- Authentication errors: Verify GitHub token has correct scopes
- Config validation errors: Check .env and team_members.json format
- Slack webhook failures: Verify webhook URL is valid and accessible

### 4. Agent Context Update

Run `.specify/scripts/bash/update-agent-context.sh claude` to add:
- Python 3.12
- uv (build tool)
- ty (type checker with uvx)
- ruff (linter with ANN rules)
- PyGithub (GitHub API client)
- python-dotenv (environment variables)

This updates the Claude-specific context file to help future agent invocations understand the project's technology stack.

**Outputs**: `data-model.md`, `contracts/` (3 files), `quickstart.md`, updated Claude context file

## Key Implementation Notes

### Staleness Calculation Algorithm

```
Algorithm (commit-based, simplified for MVP):

1. Skip if pr.draft == True (draft PRs excluded)

2. Count current valid approvals:
   - Get all reviews for PR
   - Keep only latest review per user (latest wins)
   - Count reviews with state == "APPROVED"

3. Return None if current_approvals >= required_approvals (not stale)

4. Determine staleness start time:
   - Get last commit timestamp from pr.get_commits()
   - Get last approval timestamp from reviews

   - If approval exists AND last_commit_time > last_approval_time:
       staleness_start = last_commit_time  (approval was invalidated)
   - Else:
       staleness_start = pr.created_at  (never sufficiently approved)

5. Calculate staleness:
   - staleness_days = (now - staleness_start).total_seconds() / 86400
   - Return staleness_days

6. Categorize:
   - 1-3 days: "fresh" (✨)
   - 4-7 days: "aging" (🧀)
   - 8+ days: "rotten" (🤢)
```

**Edge Cases Handled**:
- Re-requesting review: Ignored (doesn't reset staleness)
- Draft PRs: Excluded entirely from stale list
- Never reviewed: Staleness starts from PR creation time
- Multiple commits after approval: Uses most recent commit time
- No branch protection rules: Defaults to requiring 1 approval

**Simplification Note (FR-010)**: Spec.md FR-010 requires "examining PR state transitions" to identify when a PR was marked "Ready for Review". The plan simplifies this by using the PR's `ready_at` timestamp directly from the GitHub API, avoiding complex timeline API parsing. This MVP approach is sufficient for staleness calculation and aligns with the Simplicity First principle. The `ready_at` field is null for draft PRs and set when the PR transitions to ready state.

**Future Enhancements** (P2/P3):
- Check `dismiss_stale_reviews` setting per branch
- Parse timeline API for exact `ready_for_review` events if `ready_at` proves insufficient
- Detect manual vs automatic review dismissals

### Slack Message Format

**Structure**:
```
[Header Block]
🔔 Stale PR Board

[Section Block]
@author1 @author2 @author3

X PRs need review:
🤢 Rotten (8+ days): N
🧀 Aging (4-7 days): N
✨ Fresh (1-3 days): N

[Divider]

[Section Block - Category Header]
🤢 Rotten (8+ days)

[Section Block - PR Row]
🤢 <https://github.com/org/repo/pull/123|repo#123>
_Fix critical bug in authentication_
Author: @alice | Reviewers: @bob, @charlie | 8 days | Approvals: 0/2

[Section Block - PR Row]
🤢 <https://github.com/org/repo/pull/456|repo#456>
_Update API documentation_
Author: @dave | Reviewers: @eve | 10 days | Approvals: 0/1

[Divider]

[Section Block - Category Header]
🧀 Aging (4-7 days)

[Section Block - PR Row]
🧀 <https://github.com/org/repo/pull/789|repo#789>
_Add new feature endpoint_
Author: @bob | Reviewers: @alice, @dave | 5 days | Approvals: 1/2

[Divider]

[Section Block - Category Header]
✨ Fresh (1-3 days)

[Section Block - PR Row]
✨ <https://github.com/org/repo/pull/234|repo#234>
_Refactor user service_
Author: @charlie | Reviewers: @eve | 2 days | Approvals: 0/1

[Context Block]
🤖 Generated at 2025-10-31 14:30:00 UTC
```

**Celebratory Message** (when no stale PRs):
```
[Header Block]
🎉 All Caught Up!

[Section Block]
Great job team! All open PRs have sufficient approvals or are being actively reviewed. No stale PRs found.

[Context Block]
🤖 Generated at 2025-10-31 14:30:00 UTC
```

**Key Details**:
- Emojis: ✨ (Fresh 1-3 days), 🧀 (Aging 4-7 days), 🤢 (Rotten 8+ days)
- Links: `<url|text>` format for clickable PR titles
- @mentions: `<@SLACK_USER_ID>` if configured, else plain username
- Sorted: Most stale PRs at top, within each category
- Grouped by staleness category for easy scanning

### Configuration Implementation (No Pydantic)

**Loading Environment Variables**:
```python
from dotenv import load_dotenv
import os

def validate_config() -> Config:
    """Load and validate configuration from environment variables."""
    load_dotenv()  # Load .env file into os.environ

    required = {
        "GITHUB_TOKEN": "GitHub Personal Access Token",
        "GITHUB_ORG": "GitHub organization name",
        "SLACK_WEBHOOK_URL": "Slack incoming webhook URL"
    }

    errors: list[str] = []

    # Check required variables
    for key, description in required.items():
        if not os.getenv(key):
            errors.append(f"Missing required environment variable: {key} ({description})")

    if errors:
        raise ValueError("\n".join(errors))

    # Validate webhook URL format
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook_url.startswith("https://hooks.slack.com/"):
        errors.append("SLACK_WEBHOOK_URL must be a valid Slack webhook URL")

    # Type coercion for optional int field
    try:
        api_timeout = int(os.getenv("API_TIMEOUT", "30"))
    except ValueError:
        errors.append("API_TIMEOUT must be an integer")

    if errors:
        raise ValueError("\n".join(errors))

    return Config(
        github_token=os.getenv("GITHUB_TOKEN", ""),
        github_org=os.getenv("GITHUB_ORG", ""),
        slack_webhook_url=webhook_url,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        api_timeout=api_timeout
    )
```

**Loading Team Members**:
```python
import json

def load_team_members(path: str = "team_members.json") -> list[TeamMember]:
    """Load team members from JSON configuration file."""
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Configuration file not found: {path}\n"
            f"Please create it by copying team_members.json.example"
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")

    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array of team members")

    members = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} in {path} must be an object")

        if "github_username" not in item:
            raise ValueError(f"Item {i} in {path} must have 'github_username' field")

        members.append(TeamMember(github_username=item["github_username"]))

    return members
```

**Rationale for No Pydantic**:
- Only 3 required environment variables + 2 optional
- Simple JSON array for team configuration
- Manual validation provides clearest error messages
- Zero framework dependencies (Simplicity First principle)
- Full control over validation logic
- Easier for contributors to understand and modify

### Strict Typing Rules

All Python source files must follow these rules:

```python
from __future__ import annotations  # At top of every module

from typing import Literal
from dataclasses import dataclass
from datetime import datetime

# ✅ GOOD: Complete type hints
def calculate_staleness(
    pr: PullRequest,
    required_approvals: int
) -> float | None:
    """Calculate staleness in days. Returns None if not stale."""
    if pr.draft:
        return None
    # implementation...

# ✅ GOOD: Typed dataclass attributes
@dataclass
class Config:
    github_token: str
    github_org: str
    slack_webhook_url: str
    log_level: str = "INFO"
    api_timeout: int = 30

# ✅ GOOD: Explicit None return
def send_notification(message: str) -> None:
    """Send notification to Slack."""
    print(message)

# ✅ GOOD: List and union types
def filter_prs(
    prs: list[PullRequest],
    team_members: list[str]
) -> list[PullRequest]:
    return [pr for pr in prs if pr.author in team_members]

# ❌ BAD: Missing return type
def calculate_staleness(pr: PullRequest, required_approvals: int):
    ...

# ❌ BAD: Missing parameter types
def filter_prs(prs, team_members):
    ...

# ❌ BAD: Untyped class attribute
class Config:
    github_token = ""  # Should be: github_token: str
```

**Enforced by**:
- ruff with ANN rules (flake8-annotations)
- ty type checker
- Code review checklist

### Tool Configuration

**pyproject.toml** (key sections):
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

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "ANN", "B", "UP", "RUF"]
ignore = ["ANN101", "ANN102"]  # Skip self, cls annotations

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["ANN201", "ANN001"]  # Relax in tests

[tool.ruff.lint.isort]
force-single-line = false
lines-after-imports = 2

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = ["--strict-markers", "--strict-config"]
```

### Testing Strategy

**TDD Workflow**:
1. Write test for specific scenario (e.g., "PR with commit after approval should calculate staleness from commit time")
2. Run `pytest tests/unit/test_staleness.py` → test fails
3. Implement staleness logic
4. Run test → passes
5. Refactor if needed (tests still pass)
6. Repeat for next scenario

**Test Categories**:

**Unit Tests** (fast, no I/O):
- `test_staleness.py`: All staleness calculation scenarios from spec
- `test_config.py`: Config validation (valid/invalid inputs, missing fields, type errors)
- `test_models.py`: Data model properties and methods

**Integration Tests** (with mocked external APIs):
- `test_github_client.py`: GitHub client with fixture responses
- `test_slack_client.py`: Slack client with mocked requests

**Test Fixtures**:
- `fixtures/github_pr_response.json`: Sample PR API response
- `fixtures/github_reviews_response.json`: Sample reviews API response
- `fixtures/team_members_valid.json`: Valid team configuration

**Example Test**:
```python
def test_staleness_with_commit_after_approval():
    """PR with commits after approval should have staleness from commit time."""
    # Arrange
    pr = PullRequest(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        author="alice",
        reviewers=["bob"],
        url="https://github.com/org/repo/pull/123",
        created_at=datetime.now(UTC) - timedelta(days=10),
        ready_at=datetime.now(UTC) - timedelta(days=10),
        current_approvals=0,  # Approval lost
        required_approvals=1,
        base_branch="main"
    )

    # Mock: Last approval 5 days ago, last commit 3 days ago
    with patch('staleness.get_last_approval_time', return_value=datetime.now(UTC) - timedelta(days=5)):
        with patch('staleness.get_last_commit_time', return_value=datetime.now(UTC) - timedelta(days=3)):
            # Act
            staleness = calculate_staleness(pr, required_approvals=1)

            # Assert
            assert staleness == 3.0, "Staleness should be 3 days (from last commit)"
```

## Post-Phase 1 Deliverables

After Phase 1 completion, the following artifacts will exist:

1. **plan.md** (this file) - Complete implementation plan
2. **research.md** - Technology decisions and rationale
3. **data-model.md** - All entities with complete type definitions
4. **quickstart.md** - Setup and usage instructions
5. **contracts/** - API contracts for GitHub, Slack, and configuration
6. **Updated agent context** - Claude knows project tech stack

**Next Step**: Run `/speckit.tasks` to generate tasks.md with actionable implementation tasks organized by user story and dependency order.
