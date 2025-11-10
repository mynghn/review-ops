# review-ops Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-31

## Active Technologies
- Python 3.12 (existing) + requests (existing), Slack Block Kit (JSON format - no new libraries)
- N/A (stateless message generation from team_members.json + GitHub API)
- N/A (stateless CLI application, in-memory PR deduplication only) (003-github-rate-limit-handling)
- Python 3.12 (existing) + requests (existing), Slack Block Kit API (JSON format - no new libraries) (004-table-view-ui)
- N/A (stateless CLI application, in-memory processing only) (004-table-view-ui)

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

### Translation Strings (Table View)
1. Board title: ":calendar: Code Review Board" / ":calendar: 코드 리뷰 현황판"
2. Staleness legend (rotten): ":nauseated_face: Rotten (8d~)" / ":nauseated_face: 부패 중.. (8d~)"
3. Staleness legend (aging): ":cheese_wedge: Aging (4~7d)" / ":cheese_wedge: 숙성 중.. (4~7d)"
4. Staleness legend (fresh): ":sparkles: Fresh (~3d)" / ":sparkles: 신규 (~3d)"
5. Column header: "Staleness" / "신선도"
6. Column header: "Age" / "경과"
7. Column header: "PR" / "PR"
8. Column header: "Author" / "Author" (same English expression used in both languages)
9. Column header: "Reviewers" / "리뷰어"
10. Empty state: "🎉 All clear! No PRs need review" / "🎉 리뷰 대기 중인 PR이 없습니다"
11. Truncation warning: "⚠️ +{count} more PRs not shown. Check GitHub for full list." / "⚠️ +{count}개 더 있음. 전체 목록은 GitHub에서 확인하세요."

## Recent Changes

- Added staleness legend context block to Slack message
  - Added `SlackClient._build_staleness_legend_block()` method for legend generation
  - Legend displays between board header and table with 3 category indicators
  - Categories shown: Rotten (8d~), Aging (4~7d), Fresh (~3d)
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
- 004-table-view-ui: Implemented table view UI for Stale PR Board
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
- 003-github-rate-limit-handling: Added Python 3.12 (existing)
  - Added `SlackClient.post_stale_pr_summary()` method for Block Kit messages
  - Added language parameter to `SlackClient.__init__()`
  - Added `LANGUAGE` config validation in `config.py`

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
