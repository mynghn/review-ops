# ReviewOps

Stale PR detection and Slack notification tool for GitHub organizations.

## Overview

`review-ops` helps teams stay on top of code reviews by automatically detecting pull requests that need attention and sending formatted notifications to Slack. It categorizes PRs by staleness (Fresh, Aging, Rotten) and provides actionable information to improve code review response times.

### Features

- **Automatic Stale PR Detection**: Identifies PRs lacking sufficient approvals
- **Staleness Categories**: Visual indicators (✨ Fresh 1-3 days, 🧀 Aging 4-7 days, 🤢 Rotten 8+ days)
- **Slack Integration**: Sends formatted notifications with clickable links and @mentions
- **Team Filtering**: Only tracks PRs involving your team members
- **Branch Protection Aware**: Respects repository branch protection rules for required approvals

## Installation

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- [GitHub CLI (gh)](https://cli.github.com/) - **Required** for efficient PR searching and review status fetching

### Setup

1. Install GitHub CLI if not already installed:
```bash
# macOS
brew install gh

# Linux
# See https://github.com/cli/cli/blob/trunk/docs/install_linux.md

# Windows
# See https://github.com/cli/cli#installation
```

2. Clone the repository:
```bash
git clone https://github.com/your-org/review-ops.git
cd review-ops
```

3. Install dependencies:
```bash
uv sync
```

## Configuration

### 1. Environment Variables

Copy the example file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Required
GITHUB_TOKEN=ghp_your_github_personal_access_token_here
GITHUB_ORG=your-org-name
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Optional
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
API_TIMEOUT=30  # API request timeout in seconds
GH_SEARCH_LIMIT=1000  # Maximum PRs to fetch per search query (default: 1000)
```

#### Getting a GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with these scopes:
   - `repo` (for private repositories) or `public_repo` (for public only)
   - `read:org` (to list organization repositories)

#### Getting a Slack Webhook URL

1. Go to https://api.slack.com/apps
2. Create a new app or select existing app
3. Navigate to "Incoming Webhooks"
4. Add a new webhook to your desired channel
5. Copy the webhook URL

### 2. Team Members

Copy the example file and configure:

```bash
cp team_members.json.example team_members.json
```

Edit `team_members.json` with your team:

```json
[
  {
    "github_username": "alice",
    "slack_id": "U01234ABCDE"
  },
  {
    "github_username": "bob",
    "slack_id": "U56789FGHIJ"
  },
  {
    "github_username": "charlie"
  }
]
```

**Notes**:
- `github_username` is required for each team member
- `slack_id` is optional but recommended for proper @mentions
- To find Slack user IDs: Right-click user in Slack → View profile → More → Copy member ID

## Usage

### Normal Mode (Send to Slack)

Run the stale PR detection:

```bash
uv run python src/app.py
```

The tool will:
1. Fetch all open PRs from your GitHub organization
2. Filter to PRs involving your team members (as author or reviewer)
3. Calculate staleness for PRs lacking sufficient approvals
4. Send a formatted Slack notification

### Dry-Run Mode (Test Without Slack)

Test the tool without sending to Slack:

```bash
uv run python src/app.py --dry-run
```

This mode:
- ✅ Fetches real PRs from GitHub
- ✅ Calculates staleness with actual data
- ✅ Prints the formatted Slack message to your console
- ✅ Skips sending to Slack (no webhook needed)
- ✅ Perfect for testing before getting Slack admin approval

**Use dry-run mode when**:
- Testing the tool for the first time
- You don't have Slack webhook access yet
- Verifying PR detection logic
- Debugging message formatting

**Note**: This tool is designed for local execution or AWS Lambda deployment. No PyPI package is published.

### Example Output

When stale PRs are found:
```
📋 Stale PR Report - 3 PRs need review

🤢 Rotten (8+ days)
• review-ops#123 - Add staleness calculation
  Author: @alice | Reviewers: @bob | 10 days old

🧀 Aging (4-7 days)
• api-service#456 - Fix authentication bug
  Author: @charlie | Reviewers: @alice, @bob | 5 days old

✨ Fresh (1-3 days)
• frontend#789 - Update dashboard UI
  Author: @bob | Reviewers: @alice | 2 days old
```

When no stale PRs:
```
🎉 Great news! No stale PRs found. The team is all caught up on code reviews!
```

## Development

### Running Tests

Run all tests:
```bash
uv run pytest
```

Run with coverage:
```bash
uv run pytest --cov=src --cov-report=term-missing
```

Run specific test file:
```bash
uv run pytest tests/unit/test_models.py -v
```

### Code Quality

Type checking:
```bash
uvx ty src/
```

Linting:
```bash
uvx ruff check .
```

Auto-fix linting issues:
```bash
uvx ruff check --fix .
```

Format code:
```bash
uvx ruff format .
```

### Project Structure

```
review-ops/
├── src/                    # Source code
│   ├── app.py              # Main application entry point
│   ├── config.py           # Configuration loading
│   ├── models.py           # Data models (dataclasses)
│   ├── github_client.py    # GitHub API client
│   ├── slack_client.py     # Slack webhook client
│   └── staleness.py        # Staleness calculation logic
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   ├── fixtures/           # Test data
│   └── conftest.py         # Shared fixtures
├── .env.example            # Example environment variables
├── team_members.json.example  # Example team configuration
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## How It Works

### Staleness Calculation

A PR is considered "stale" if:
1. It is NOT in draft mode
2. It has fewer approvals than required by branch protection rules

Staleness is calculated from the time the PR was marked "Ready for Review" (or created_at for non-draft PRs).

### Categories

- **Fresh** (✨): 1-3 days without sufficient approval
- **Aging** (🧀): 4-7 days without sufficient approval
- **Rotten** (🤢): 8+ days without sufficient approval

### Branch Protection

The tool automatically detects required approval counts from branch protection rules:
- If protection rules exist: Uses `required_approving_review_count`
- If no protection: Defaults to requiring 1 approval

## Performance

### API Call Optimization

The tool is designed for efficient GitHub API usage using a hybrid approach:

**Search Phase** (via GitHub CLI):
- For each team member, runs 2 searches: `--author` and `--review-requested`
- Uses `gh search prs` which is much faster than iterating through all repos
- Collects all PR references first, then deduplicates before fetching details

**Detail Fetching Phase** (via GitHub CLI):
- Fetches complete PR details (reviews, approvals, status) for each unique PR
- Uses `gh pr view --json` which combines multiple REST API calls into one

### Typical API Usage

For a team of **5 members** with **20 unique PRs**:
- **Search calls**: 10 (2 per member: author + review-requested)
- **Detail calls**: 20 (1 per unique PR)
- **Total API calls**: ~30

The tool automatically deduplicates PRs found in multiple searches, so you're never fetching the same PR details twice.

### Rate Limits

- **GitHub API**: 5,000 requests/hour for authenticated users
- **gh CLI**: Respects GitHub's rate limits automatically
- **Estimated capacity**: Can handle organizations with 100+ team members and 500+ PRs per run

### Configuration

Adjust `GH_SEARCH_LIMIT` in your `.env` file if your organization has very large numbers of PRs:
```env
GH_SEARCH_LIMIT=2000  # Increase if you have >1000 PRs per search
```

## Troubleshooting

### "GITHUB_TOKEN is required"
Make sure your `.env` file exists and contains a valid GitHub token.

### "SLACK_WEBHOOK_URL must be a valid Slack webhook URL"
Webhook URLs must start with `https://hooks.slack.com/`. Verify your Slack webhook configuration.

### "Team members file not found"
Create `team_members.json` based on `team_members.json.example`.

### No PRs detected
Verify that:
- Your GitHub token has the correct scopes (`repo` and `read:org`)
- Team member GitHub usernames in `team_members.json` match exactly
- PRs exist in your organization repositories

### Rate Limiting
GitHub API has a rate limit of 5,000 requests/hour for authenticated users. The tool will exit gracefully if rate limited, showing the reset time.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run tests and linting: `uv run pytest && uvx ruff check .`
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

Built with:
- [GitHub CLI (gh)](https://cli.github.com/) - Primary tool for efficient PR searching and fetching
- [PyGithub](https://github.com/PyGithub/PyGithub) - GitHub API authentication
- [requests](https://requests.readthedocs.io/) - HTTP library for Slack webhooks
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment variable management
- [pytest](https://pytest.org/) - Testing framework
- [ruff](https://github.com/astral-sh/ruff) - Fast Python linter
- [uv](https://github.com/astral-sh/uv) - Ultra-fast Python package manager
