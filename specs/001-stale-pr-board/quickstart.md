# Quickstart Guide

**Feature**: Stale PR Board
**Date**: 2025-10-31
**Purpose**: Setup instructions and usage guide for the Stale PR Board application

This guide will help you set up and run the Stale PR Board application to track stale pull requests in your GitHub organization and send notifications to Slack.

## Prerequisites

Before you begin, ensure you have:

1. **Python 3.12** installed
   ```bash
   python --version  # Should show 3.12.x
   ```

   If not installed:
   - **macOS**: `brew install python@3.12`
   - **Linux**: `sudo apt install python3.12` or use pyenv
   - **Windows**: Download from [python.org](https://www.python.org/downloads/)

2. **uv** installed (fast Python package manager)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   Verify installation:
   ```bash
   uv --version
   ```

3. **GitHub Personal Access Token**
   - Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token (classic)"
   - Select scopes:
     - `repo` (Full control of private repositories) OR
     - `public_repo` (Access public repositories only)
     - `read:org` (Read org and team membership, read org projects)
   - Copy the token (starts with `ghp_`)

4. **Slack Incoming Webhook URL**
   - Go to your Slack workspace settings
   - Navigate to Apps → Manage → Custom Integrations → Incoming Webhooks
   - Add to workspace and select channel
   - Copy the webhook URL (format: `https://hooks.slack.com/services/T.../B.../...`)

## Setup

### 1. Clone Repository

```bash
cd /path/to/your/projects
# Repository should already exist at review-ops/
cd review-ops
```

### 2. Create Virtual Environment

```bash
# Create virtual environment with Python 3.12
uv venv

# Activate the environment
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows
```

You should see `(.venv)` prefix in your terminal prompt.

### 3. Install Dependencies

```bash
# Install all dependencies from lock file
uv sync

# Verify installation
uv run stale-pr-board --help
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
# Use your preferred text editor
nano .env  # or vim, code, etc.
```

**Edit `.env` file**:
```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_your_actual_token_here
GITHUB_ORG=your-organization-name

# Slack Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX

# Optional: Application Settings
LOG_LEVEL=INFO
API_TIMEOUT=30
```

**Security Note**: Never commit `.env` file to version control! It's already in `.gitignore`.

### 5. Configure Team Members

```bash
# Copy the example team configuration
cp team_members.json.example team_members.json

# Edit team_members.json with your team
nano team_members.json
```

**Edit `team_members.json`**:
```json
[
  {
    "github_username": "alice",
    "slack_user_id": "U1234567890"
  },
  {
    "github_username": "bob",
    "slack_user_id": "U0987654321"
  },
  {
    "github_username": "charlie"
  }
]
```

**Finding Slack User IDs** (optional, for @mentions):
1. Open Slack
2. Click on a team member's profile
3. Click "..." (More)
4. Select "Copy member ID"
5. Paste into `slack_user_id` field

If you don't provide `slack_user_id`, usernames will display as plain text (e.g., `@alice` instead of clickable mention).

**Security Note**: `team_members.json` is gitignored. Keep your team configuration private.

## Running the Application

### Basic Usage

```bash
# Run the application (uv run automatically handles venv)
uv run stale-pr-board

# OR run app.py directly
uv run python src/app.py

# OR activate venv manually first
source .venv/bin/activate
python src/app.py
```

**Expected Output**:
```
INFO: Authenticated as: your-github-username
INFO: Scanning organization: your-org
INFO: Found 15 repositories
INFO: Found 47 open PRs
INFO: Filtered to 23 PRs involving team members
INFO: Identified 8 stale PRs
✓ Sent notification for 8 stale PRs to Slack
```

### Command-Line Options

```bash
# Dry run (don't send Slack notification)
uv run stale-pr-board --dry-run

# Verbose output
uv run stale-pr-board --verbose

# Custom config file location
uv run stale-pr-board --config /path/to/team_members.json

# Show help
uv run stale-pr-board --help
```

### Scheduling (Optional)

To run automatically on a schedule, use cron (Linux/macOS) or Task Scheduler (Windows).

**Example cron entry** (run every weekday at 9 AM):
```bash
crontab -e

# Add this line:
0 9 * * 1-5 cd /path/to/review-ops && uv run stale-pr-board
```

**Example GitHub Actions workflow** (`.github/workflows/stale-pr-check.yml`):
```yaml
name: Stale PR Check

on:
  schedule:
    - cron: '0 9 * * 1-5'  # Every weekday at 9 AM UTC
  workflow_dispatch:  # Allow manual trigger

jobs:
  check-stale-prs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync

      - name: Run stale PR check
        env:
          GITHUB_TOKEN: ${{ secrets.GH_PAT }}
          GITHUB_ORG: ${{ secrets.GH_ORG }}
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
        run: uv run stale-pr-board
```

## Development Workflow

### Type Checking

```bash
# Check types with ty
uvx ty src/

# Or check specific file
uvx ty src/staleness.py
```

**Expected**: No output means no type errors.

### Linting

```bash
# Lint entire project
uvx ruff check .

# Auto-fix issues
uvx ruff check --fix .

# Format code
uvx ruff format .
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_staleness.py

# Run specific test function
uv run pytest tests/unit/test_staleness.py::test_staleness_calculation
```

### Installing Dev Dependencies

```bash
# Add development dependencies
uv add --dev pytest pytest-cov pytest-mock

# Or sync all dependencies (including dev) from lock file
uv sync --all-extras
```

## Troubleshooting

### Common Issues

#### 1. Authentication Error: "Bad credentials"

**Symptom**:
```
ERROR: GitHub API error: 401 Unauthorized
```

**Solution**:
- Verify `GITHUB_TOKEN` in `.env` is correct
- Ensure token hasn't expired
- Check token has required scopes (`repo` and `read:org`)
- Generate new token if needed

#### 2. Rate Limit Exceeded

**Symptom**:
```
ERROR: GitHub API rate limit exceeded
Rate limit resets at: 2025-10-31 15:30:00
Please retry in 25 minutes
```

**Solution**:
- Wait for rate limit reset time shown in error message
- Reduce number of repositories (if possible)
- Use fine-grained token instead of classic token (higher limits)

#### 3. Configuration Validation Error

**Symptom**:
```
ValueError: Missing required environment variable: GITHUB_TOKEN (GitHub Personal Access Token)
```

**Solution**:
- Ensure `.env` file exists in project root
- Check `.env` has all required variables
- Verify no typos in variable names
- Make sure virtual environment is activated

#### 4. Slack Webhook Error: "No service"

**Symptom**:
```
ERROR: Slack webhook failed: 404 Not Found
```

**Solution**:
- Verify `SLACK_WEBHOOK_URL` is correct
- Ensure webhook hasn't been revoked in Slack settings
- Check URL format: `https://hooks.slack.com/services/...`
- Regenerate webhook URL if needed

#### 5. Team Members JSON Parse Error

**Symptom**:
```
ValueError: Invalid JSON in team_members.json: Expecting ',' delimiter
```

**Solution**:
- Validate JSON syntax (use [jsonlint.com](https://jsonlint.com))
- Check for trailing commas (not allowed in JSON)
- Ensure all strings use double quotes, not single quotes
- Verify file encoding is UTF-8

#### 6. No Stale PRs Found (Unexpected)

**Symptom**: Script runs successfully but reports 0 stale PRs when you expect some.

**Debug**:
```bash
# Run with verbose output
uv run stale-pr-board --verbose

# Check logs for:
# - How many PRs were filtered by team
# - Which PRs have sufficient approvals
# - Staleness calculations
```

**Common Causes**:
- Team member usernames in `team_members.json` don't match GitHub usernames (case-sensitive)
- All PRs already have sufficient approvals
- Only draft PRs exist (drafts are excluded)

### Getting Help

**Check Logs**:
```bash
# Run with verbose logging
LOG_LEVEL=DEBUG uv run stale-pr-board

# Or set in .env
LOG_LEVEL=DEBUG
```

**Verify Configuration**:
```bash
# Test GitHub authentication
uv run python -c "from github import Github; g = Github('your-token'); print(g.get_user().login)"

# Test Slack webhook
curl -X POST -H 'Content-Type: application/json' \
  -d '{"text": "Test message"}' \
  https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**Check Dependencies**:
```bash
# List installed packages (uses uv's package management)
uv pip list

# Or check tree of dependencies
uv tree

# Show specific package info
uv pip show PyGithub
```

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | ✅ Yes | - | GitHub Personal Access Token |
| `GITHUB_ORG` | ✅ Yes | - | GitHub organization name |
| `SLACK_WEBHOOK_URL` | ✅ Yes | - | Slack incoming webhook URL |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `API_TIMEOUT` | No | `30` | API request timeout in seconds |

### Team Members JSON Schema

```json
[
  {
    "github_username": "string (required)",
    "slack_user_id": "string (optional, format: U + 10 chars)"
  }
]
```

**Fields**:
- `github_username` (required): GitHub username (case-sensitive)
- `slack_user_id` (optional): Slack user ID for @mentions (format: `U1234567890`)

## Performance Notes

**Estimated Execution Time**:
- 50 repos, 100 PRs: ~20-30 seconds
- 100 repos, 200 PRs: ~45-60 seconds

**API Rate Limit Usage**:
- ~261 API calls for 50 repos with 100 PRs
- Well within GitHub's 5,000 requests/hour limit
- Resets every hour on the hour

## Next Steps

After successful setup:

1. **Test the application** with `--dry-run` flag first
2. **Verify Slack message** formatting and mentions
3. **Set up scheduling** (cron or GitHub Actions) for automated checks
4. **Adjust staleness thresholds** if needed (future enhancement)
5. **Add more team members** to `team_members.json` as team grows

## Additional Resources

- **Feature Specification**: [spec.md](./spec.md)
- **Implementation Plan**: [plan.md](./plan.md)
- **Data Model**: [data-model.md](./data-model.md)
- **API Contracts**: [contracts/](./contracts/)
- **Technology Research**: [research.md](./research.md)

## Support

For issues or questions:
1. Check this quickstart guide
2. Review troubleshooting section
3. Consult contract documentation in `contracts/`
4. Check project README.md
5. Review GitHub API and Slack API documentation

---

**Version**: 1.0.0 (MVP)
**Last Updated**: 2025-10-31
