# review-ops Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-31

## Active Technologies
- Python 3.12 (existing) + requests (existing), Slack Block Kit (JSON format - no new libraries)
- N/A (stateless message generation from team_members.json + GitHub API)
- N/A (stateless CLI application, in-memory PR deduplication only) (003-github-rate-limit-handling)

## Project Structure

```text
src/
  app.py               # Main entry point
  config.py            # Configuration loading (includes LANGUAGE validation)
  slack_client.py      # Slack webhook client with Block Kit formatting
  github_client.py     # GitHub PR fetching
  models.py            # Data models
  staleness.py         # Staleness calculation

tests/
  unit/                # Unit tests
  integration/         # Integration tests
```

## Commands

Run tests:
```bash
uv run pytest
```

Run linting:
```bash
uvx ruff check .
```

Run the application:
```bash
# Set LANGUAGE environment variable (optional, defaults to 'en')
export LANGUAGE=ko  # or 'en'
uv run python src/app.py

# Dry-run mode (print to console, no Slack sending)
uv run python src/app.py --dry-run
```

## Code Style

Python 3.12: Follow standard conventions
- Max line length: 100 characters
- Use ruff for linting
- Use pytest for testing

## Features

### Block Kit Slack Formatting
- Visual enhancement using Slack Block Kit (headers, sections, dividers, context blocks)
- Supports English and Korean languages
- Automatic truncation (15 PRs per category max)
- Markdown escaping for safe display

### Language Support
- **English (`en`)**: Default language
- **Korean (`ko`)**: Full translation support with workplace-appropriate expressions
- Configure via `LANGUAGE` environment variable in `.env`
- Supported values: `'en'` or `'ko'` (case-insensitive)

### Translation Strings (7 pairs)
1. Category headers: "Rotten PRs" / "PR 부패 중..."
2. Category headers: "Aging PRs" / "PR 숙성 중..."
3. Category headers: "Fresh PRs" / "갓 태어난 PR"
4. Age format: "{days} days old" / "{days}일 묵음"
5. Review count: "{count} reviews pending" / "리뷰 {count}개 대기중"
6. Truncation warning: "+{count} more PRs not shown" / "+{count}개 더 있음"
7. Empty state: "No PRs in this category" / "이 카테고리에 PR 없음"

## Recent Changes
- 003-github-rate-limit-handling: Added Python 3.12 (existing)
- 003-github-rate-limit-handling: Added Python 3.12 (existing)
- 002-ui-enhance-on-stale-pr-board: Implemented Block Kit formatting with bilingual support (EN/KO)
  - Added `SlackClient.post_stale_pr_summary()` method for Block Kit messages
  - Added language parameter to `SlackClient.__init__()`
  - Added `LANGUAGE` config validation in `config.py`
  - Created 35 unit tests for Block Kit functionality
  - All 86 tests passing, 73% code coverage

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
