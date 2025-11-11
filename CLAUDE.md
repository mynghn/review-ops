# review-ops Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-31

## Active Technologies
- Python 3.12 (existing) + requests (existing), Slack Block Kit (JSON format - no new libraries)
- N/A (stateless message generation from team_members.json + GitHub API)
- N/A (stateless CLI application, in-memory PR deduplication only) (003-github-rate-limit-handling)
- Python 3.12 (existing) + requests (existing), Slack Block Kit API (JSON format - no new libraries) (004-table-view-ui)
- N/A (stateless CLI application, in-memory processing only) (004-table-view-ui)
- Python 3.12 (existing) + requests, PyGithub, gh CLI (existing), Slack Block Kit (JSON format) (005-refine-review-filter)
- Python 3.12 + holidays library (>=0.56) for business day calculations (006-business-day-staleness)

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

### Dual Search with Smart Filtering (005-refine-review-filter)
- **Dual search execution**: For each team member, executes TWO GitHub searches:
  1. `review:none` - PRs with no reviews submitted yet
  2. `review:required` - PRs with some reviews submitted, more needed
- **Perfect deduplication**: PRs appearing in both searches are fetched only once
- **Smart filtering**: `review:required` PRs are filtered to include only those where team members appear in current `reviewRequests` field
- **Team member presence check**: Case-insensitive comparison of GitHub usernames in individual reviewers and GitHub team members
- **GitHub team expansion**: Expands GitHub team review requests to check if tracked team members are part of the requested team
- **Fail-safe behavior**: PRs with review:none status are always included (no filtering applied)
- **Observability logging**: Logs search statistics (PRs from each search type, deduplication count, filtering count)

#### Implementation Details
- **Helper method**: `_search_prs_by_review_status()` encapsulates single search execution with retry logic
- **Metadata tracking**: `pr_search_metadata` dict tracks which searches found each PR for conditional filtering
- **Filtering method**: `_filter_by_team_member_presence()` applies team member filtering only to review:required PRs
- **Phase-based approach**:
  - Phase 1: Dual search & deduplication
  - Phase 2: Fetch PR details
  - Phase 3: Filter by team member presence

### Table View UI (Block Kit Slack Formatting)
- **Unified table format**: All PRs displayed in a single sorted table (replaces category-based sections)
- **5-column layout**: Staleness emoji, Age, PR details, Author, Reviewers
- **Sorting**: PRs sorted by staleness (oldest first) for quick priority identification
- **Rich text cells**: Uses Slack Block Kit `rich_text` elements (emoji, link, user mentions)
- **Column alignment**: Center-aligned for emoji/age/author, left-aligned for PR/reviewers
- **Bilingual support**: English and Korean translations for table headers (Author uses same English expression in both languages)
- **Automatic truncation**: Max 99 PRs displayed (Slack limit: 100 rows total including header)
- **Empty state handling**: Shows celebratory message when no PRs need review

### Language Support
- **English (`en`)**: Default language
- **Korean (`ko`)**: Full translation support with workplace-appropriate expressions
- Configure via `LANGUAGE` environment variable in `.env`
- Supported values: `'en'` or `'ko'` (case-insensitive)

### Business Day Staleness Calculation (006-business-day-staleness)
- **Business day counting**: Staleness calculated in business days (Mon-Fri), excluding weekends and holidays
- **Holiday calendar**: Uses `holidays` library with configurable country/region via `HOLIDAYS_COUNTRY` env var
- **Updated thresholds**:
  - Fresh: 0-3 business days (unchanged threshold, but now business days)
  - Aging: 4-10 business days (increased from 4-7 to account for business days)
  - Rotten: 11+ business days (increased from 8+ to account for business days)
- **Fractional business days**: Supports partial business days (e.g., 1.5 days = 1 day + 12 business hours)
- **Weekend handling**: PRs created/updated on weekends start counting from next business day
- **Holiday support**: Configurable by country code (US, KR, GB, CA, etc.)
- **Configuration**:
  - `HOLIDAYS_COUNTRY` environment variable (default: "US")
  - Supported country codes: US, GB, CA, AU, FR, DE, JP, KR, CN, IN, BR, MX, and more
  - See https://pypi.org/project/holidays/ for full list of supported countries

#### Implementation Details
- **Helper function**: `_count_business_days()` in `staleness.py` handles business day calculation
- **Core calculation**: `calculate_staleness()` now accepts `country` parameter for holiday calendar
- **Date iteration**: Iterates through each day, skipping weekends (Sat/Sun) and country-specific holidays
- **Fractional handling**: Calculates partial business days at start/end of time range
- **Model updates**: `StalePR.category` property thresholds updated to 4/11 (from 4/8)
- **UI updates**: Slack legend updated to reflect new thresholds (11d+, 4~10d)

### Translation Strings (Table View)
1. Board title: "[yyyy-MM-dd] Stale PR Board :help:" / "[yyyy-MM-dd] 리뷰가 필요한 PR들 :help:"
2. Staleness legend (rotten): ":nauseated_face: Rotten (11d+)" / ":nauseated_face: 부패 중.. (11d+)"
3. Staleness legend (aging): ":cheese_wedge: Aging (4~10d)" / ":cheese_wedge: 숙성 중.. (4~10d)"
4. Staleness legend (fresh): ":sparkles: Fresh (~3d)" / ":sparkles: 신규 (~3d)"
5. Column header: "Staleness" / "신선도"
6. Column header: "Age" / "경과"
7. Column header: "PR" / "PR"
8. Column header: "Author" / "Author" (same English expression used in both languages)
9. Column header: "Review awiaited" / "리뷰 대기 중"
10. Empty state: "🎉 All clear! No PRs need review" / "🎉 리뷰 대기 중인 PR이 없습니다"
11. Truncation warning: "⚠️ +{count} more PRs not shown. Check GitHub for full list." / "⚠️ +{count}개 더 있음. 전체 목록은 GitHub에서 확인하세요."

## Recent Changes
- 006-business-day-staleness: Implemented business day staleness calculation
  - Added `holidays>=0.56` library dependency in `pyproject.toml`
  - Added `HOLIDAYS_COUNTRY` configuration field in `src/config.py` with validation
  - Created `_count_business_days()` helper function in `src/staleness.py`
  - Updated `calculate_staleness()` to accept `country` parameter and use business days
  - Updated `StalePR.category` thresholds from 4/8 to 4/11 business days
  - Updated staleness legend text from "8d+/4~7d" to "11d+/4~10d" in EN and KO
  - Updated all unit tests for business day logic and new thresholds
  - Updated app.py to pass `config.holidays_country` to `calculate_staleness()`
  - Business days exclude weekends (Sat/Sun) and country-specific holidays
  - Supports fractional business days for precise staleness tracking
- 005-refine-review-filter: Added Python 3.12 (existing) + requests, PyGithub, gh CLI (existing), Slack Block Kit (JSON format)

- Added staleness legend context block to Slack message
  - Added `SlackClient._build_staleness_legend_block()` method for legend generation
  - Legend displays between board header and table with 3 category indicators
  - Categories shown: Rotten (8d+), Aging (4~7d), Fresh (~3d)
  - Bilingual support (EN/KO) with workplace-appropriate Korean expressions
  - Updated `SlackClient.build_blocks()` to insert legend block
  - Created 4 new unit tests in `TestBuildStalenessLegendBlock` class
  - Updated 5 existing tests to expect new block structure
- 004-table-view-ui: Added Author column to table view UI
  - Updated table layout from 4 columns to 5 columns (Staleness, Age, PR, Author, Reviewers)
  - Author column uses same English expression for both EN and KO languages
  - Author column displays user Slack mentions (center-aligned)
  - Updated `SlackClient._build_table_header_row()` to include Author column
  - Updated `SlackClient._build_table_data_row()` to add author cell with user mention
  - Updated `SlackClient.build_blocks()` column_settings to 5 columns
  - Updated all unit tests to expect 5 columns
  - Replaced category-based Block Kit format with unified table view
  - Added `SlackClient._build_table_header_row()` for bilingual table headers
  - Added `SlackClient._build_table_data_row()` for PR row generation
  - Added `SlackClient._build_board_header_block()` for board title
  - Added `SlackClient._get_staleness_emoji()` for emoji mapping
  - Added `SlackClient._build_rich_text_cell()` for table cell construction
  - Added `SlackClient._build_reviewer_elements()` for reviewer mentions
  - Updated `SlackClient.build_blocks()` to generate table format
  - Updated `SlackClient._build_empty_state_blocks()` for simplified empty state
  - Created 4 new unit tests for table view functionality
  - Code coverage: 73% for slack_client.py (maintained baseline)
  - Added `SlackClient.post_stale_pr_summary()` method for Block Kit messages
  - Added language parameter to `SlackClient.__init__()`
  - Added `LANGUAGE` config validation in `config.py`

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
