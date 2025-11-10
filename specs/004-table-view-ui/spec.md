# Feature Specification: Table View UI for Stale PR Board

**Feature Branch**: `004-table-view-ui`
**Created**: 2025-11-10
**Status**: Draft
**Input**: User description: "Revise stale PR board's message UI into a sorted table view using Slack Block Kit table format with columns for staleness (emoji), elapsed time, PR details, and reviewers"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unified Table View (Priority: P1)

Team members receive a single consolidated table showing all PRs sorted by staleness in descending order, with visual indicators for staleness level, allowing them to quickly identify the most critical PRs requiring attention.

**Why this priority**: This is the core value proposition - transforming the current category-based list into a sortable table view that prioritizes the stalest PRs. This directly addresses the primary use case of identifying which PRs need immediate attention.

**Independent Test**: Can be fully tested by sending a stale PR notification and verifying that all PRs appear in a single table sorted by age (oldest first), with correct emojis, elapsed time formatting, PR links, and reviewer mentions.

**Acceptance Scenarios**:

1. **Given** multiple PRs across different staleness categories, **When** the board message is generated, **Then** all PRs appear in a single table sorted by staleness days (descending order)
2. **Given** PRs with different staleness levels, **When** viewing the table, **Then** each row displays the correct emoji indicator (🤢 for rotten 8+ days, 🧀 for aging 4-7 days, ✨ for fresh 1-3 days)
3. **Given** a PR in the table, **When** viewing its elapsed time column, **Then** the time is displayed in compact format (e.g., "12d" for days)
4. **Given** a PR with multiple reviewers, **When** viewing the reviewers column, **Then** all reviewers are listed with Slack user mentions (using newline separators)
5. **Given** a PR title in the table, **When** viewing the PR column, **Then** the PR number and title appear as a clickable link to GitHub

---

### User Story 2 - Bilingual Table Headers (Priority: P2)

Users see table headers in their configured language (English or Korean), with column labels reflecting the terminology appropriate for their workplace culture.

**Why this priority**: Maintains existing bilingual support but applies it to the new table format. Important for user experience consistency but can be implemented after the core table structure.

**Independent Test**: Can be tested by setting LANGUAGE=ko and LANGUAGE=en environment variables and verifying the table headers change accordingly ("신선도/Staleness", "경과/Age", "PR/PR", "리뷰 대기 중/Review awaited").

**Acceptance Scenarios**:

1. **Given** LANGUAGE is set to "ko", **When** the table is rendered, **Then** headers display as "신선도", "경과", "PR", "리뷰 대기 중"
2. **Given** LANGUAGE is set to "en", **When** the table is rendered, **Then** headers display as "Staleness", "Age", "PR", "Review awaited"
3. **Given** elapsed time formatting, **When** LANGUAGE is "ko", **Then** time is displayed as "12d" (compact format, same as English for table space efficiency)

---

### User Story 3 - Maintain Truncation Behavior (Priority: P3)

When total PRs exceed the configured limit (default 30), the table displays the stalest PRs up to the limit and shows a warning message indicating how many additional PRs were not shown.

**Why this priority**: Preserves existing functionality to prevent overwhelming users with large tables. This is a constraint rather than new functionality.

**Independent Test**: Can be tested by configuring max_prs_total to a low value (e.g., 5) and verifying that only the 5 stalest PRs appear in the table with a warning message below.

**Acceptance Scenarios**:

1. **Given** 50 total PRs and max_prs_total=30, **When** the table is generated, **Then** only the 30 stalest PRs appear in the table
2. **Given** PRs were truncated, **When** viewing the message, **Then** a warning message appears below the table (e.g., "⚠️ +20 more PRs not shown. Check GitHub for full list.")
3. **Given** LANGUAGE is "ko", **When** the truncation warning appears, **Then** it displays in Korean (e.g., "⚠️ +20개 더 있음. 전체 목록은 GitHub에서 확인하세요.")

---

### Edge Cases

- What happens when there are no PRs to display? (Empty state: skip table entirely and show celebration message "🎉 All clear! No PRs need review" in configured language)
- What happens when a PR has no reviewers assigned? (Display single dash "-" in reviewers column)
- What happens when PR title is very long? (Slack Block Kit table will handle text wrapping automatically)
- What happens when there's only 1 PR? (Still display as table with header row)
- What happens when reviewer mentions include users without Slack IDs? (Fall back to @github_username format)

## Clarifications

### Session 2025-11-10

- Q: PR details column format - should repo#number and title be inline, two-line, or original format? → A: Link on repo#number (first line), plain title text (second line), implemented as 2 separate Slack Block Kit blocks
- Q: Empty state rendering - should it show empty table, plain message, or table with colspan message? → A: Skip table entirely and show plain text message block with a celebration message
- Q: Empty state celebration message content - what should the message say? → A: "🎉 All clear! No PRs need review" (EN) / "🎉 리뷰 대기 중인 PR이 없습니다" (KO)
- Q: No reviewers display - should it show dash, word "none", or empty cell? → A: Display single dash "-" (language-neutral, concise)
- Q: PR details and reviewers column alignment - should they be left, center, or mixed? → A: Left alignment for both PR details and reviewers columns (standard for text content)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST render all PRs in a single Slack Block Kit table block with 4 columns (staleness emoji, elapsed time, PR details, reviewers)
- **FR-002**: System MUST sort all PRs by staleness_days in descending order (stalest/oldest first) before rendering the table
- **FR-003**: System MUST display staleness category as emoji in the first column (🤢 for rotten, 🧀 for aging, ✨ for fresh)
- **FR-004**: System MUST format elapsed time in compact days format (e.g., "12d", "5d", "2d") in the second column
- **FR-005**: System MUST display PR identifier and title in the third column using 2 separate Slack Block Kit blocks: first block contains repo#number as clickable GitHub link, second block contains PR title as plain text (no link)
- **FR-006**: System MUST display all reviewers as Slack user mentions separated by newlines in the fourth column; when no reviewers are assigned, display single dash "-"
- **FR-007**: System MUST render table header row with column labels in the configured language (EN: "Staleness", "Age", "PR", "Review awaited" / KO: "신선도", "경과", "PR", "리뷰 대기 중")
- **FR-008**: System MUST apply center alignment to the first two columns (staleness emoji and elapsed time) and left alignment to the last two columns (PR details and reviewers)
- **FR-009**: System MUST respect max_prs_total configuration, truncating the table to show only the stalest N PRs
- **FR-010**: System MUST display a truncation warning message when PRs are not shown, indicating the count of hidden PRs
- **FR-011**: System MUST replace existing category-based Block Kit format (separate headers and dividers per category) with single table format
- **FR-012**: Table header MUST include an emoji and title in configured language (EN: ":help: 2025-11-11 Stale PR Board" / KO: ":help: 2025-11-11 리뷰가 필요한 PR들")
- **FR-013**: System MUST skip table rendering when no PRs exist and display a plain text message block with celebration message: "🎉 All clear! No PRs need review" (EN) / "🎉 리뷰 대기 중인 PR이 없습니다" (KO)

### Key Entities

- **TableBlock**: Slack Block Kit table structure containing header row and PR rows
- **TableRow**: Single row in the table representing either header or PR data
- **TableCell**: Individual cell containing rich_text elements (text, emoji, link, or user mention)
- **ColumnSettings**: Alignment configuration for each column (center for emoji/age, left for PR/reviewers)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view all PRs in a single unified table without navigating between category sections
- **SC-002**: PRs are visually ordered by urgency (stalest first), allowing users to identify critical reviews in under 3 seconds
- **SC-003**: Table layout displays consistently across Slack desktop and mobile clients with proper column alignment
- **SC-004**: Message rendering time remains under 1 second for up to 30 PRs (no performance degradation from format change)
- **SC-005**: Existing bilingual support (EN/KO) works correctly with table headers matching configured language

## Dependencies & Constraints

### Dependencies

- Slack Block Kit API must support `table` block type (available as of 2024)
- Existing data models (StalePR, PullRequest, TeamMember) remain unchanged
- Existing staleness calculation logic remains unchanged

### Constraints

- Table block structure must follow Slack Block Kit table specification (rows array with cells containing rich_text elements)
- Table cells use rich_text blocks (not mrkdwn), requiring different formatting approach than current section blocks
- Maximum table width is constrained by Slack's rendering (4 columns is reasonable limit)
- Truncation behavior must preserve staleness-based priority (show oldest PRs first)

## Assumptions

- The sample Slack Block Kit JSON provided represents the desired final structure accurately
- Current emoji indicators (🤢, 🧀, ✨) remain appropriate for table view
- Elapsed time format can be compact ("12d") rather than verbose ("12 days old") for table space efficiency
- Center alignment for emoji and age columns improves visual clarity
- Reviewers displayed vertically (newline-separated) is acceptable for readability
- Category-based grouping (rotten/aging/fresh sections) is no longer needed in favor of single sorted table
- The `:calendar:` emoji in the header is universally understood across cultures
