# Research: Table View UI Implementation

**Feature**: Table View UI for Stale PR Board
**Date**: 2025-11-10
**Status**: Complete

## Research Questions

This document consolidates findings from Phase 0 research to resolve all technical unknowns before implementation.

---

## 1. Slack Block Kit Table Format Structure

### Decision: Use `table` block type with `rows` array and `column_settings`

**Rationale**:
- Slack Block Kit supports table blocks as of 2024
- Tables use a `rows` array where each row is an array of cells
- Each cell is a `rich_text` block containing elements
- First row serves as the header row (no special designation needed)

**Structure Pattern**:
```json
{
  "type": "table",
  "column_settings": [
    {"align": "center"},  // Column 1
    {"align": "left"}     // Column 2
  ],
  "rows": [
    [cell1, cell2, ...],  // Header row
    [cell1, cell2, ...],  // Data row 1
    [cell1, cell2, ...]   // Data row 2
  ]
}
```

**Constraints**:
- Maximum 20 columns per table
- Maximum 100 rows (including header row)
- Each cell must be a `rich_text` block

**Alternatives considered**:
- ❌ Section blocks with mrkdwn: Cannot achieve true tabular layout
- ❌ Custom HTML/formatting: Not supported by Slack

---

## 2. Rich Text Cell Construction

### Decision: Use `rich_text` blocks with nested `rich_text_section` elements

**Rationale**:
- Table cells must contain `rich_text` blocks (not mrkdwn)
- Each `rich_text` block has an `elements` array
- Elements include `rich_text_section` which contains the actual content
- Different element types can be mixed in a single section

**Cell Structure Pattern**:
```json
{
  "type": "rich_text",
  "elements": [
    {
      "type": "rich_text_section",
      "elements": [
        {"type": "text", "text": "Plain text"},
        {"type": "emoji", "name": "sparkles"},
        {"type": "link", "text": "Link text", "url": "https://..."},
        {"type": "user", "user_id": "U1234567890"}
      ]
    }
  ]
}
```

**Element Types**:
1. **text**: Plain text with optional style (`bold: true`)
2. **emoji**: Slack emoji by name (`:emoji_name:` → `"name": "emoji_name"`)
3. **link**: Clickable URL with display text
4. **user**: Slack user mention by ID

**Key Discovery**: Line breaks in tables are achieved using `\n` within text elements or by separating elements with newline text blocks.

**Alternatives considered**:
- ❌ mrkdwn format: Not supported in table cells
- ❌ HTML tags: Not supported by Slack

---

## 3. Column Alignment Options

### Decision: Center-align emoji and age columns, left-align PR and reviewers columns

**Rationale**:
- **Center alignment** (`"align": "center"`): Best for short, symbolic content (emoji indicators, compact time strings like "12d")
- **Left alignment** (`"align": "left"`): Standard for text-heavy content (PR titles, reviewer lists)
- Alignment is set per column in `column_settings` array

**Alignment Strategy**:
- Column 1 (Staleness emoji): `center` - single emoji, visually balanced
- Column 2 (Elapsed time): `center` - compact format ("12d"), easy to scan
- Column 3 (PR details): `left` - repo#number and title, text-heavy
- Column 4 (Reviewers): `left` - user mentions, potentially multi-line

**Alternatives considered**:
- ❌ All center-aligned: PR details and reviewers are text-heavy and harder to read centered
- ❌ All left-aligned: Emoji and time lose visual impact when left-aligned

---

## 4. Bilingual Table Implementation

### Decision: Use language switch statements for header text and minimal translatable strings

**Rationale**:
- Existing `SlackClient` already has `self.language` attribute ("en" or "ko")
- Table headers require translation: "Staleness", "Age", "PR", "Reviewers"
- Empty state message requires translation
- Data formatting (elapsed time "12d") remains language-neutral for space efficiency

**Translation Pairs** (7 total, reusing existing from spec):

| Context | English | Korean |
|---------|---------|--------|
| Header title | `:calendar: Code Review Board` | `:calendar: 코드 리뷰 현황판` |
| Column 1 header | `Staleness` | `숙성도` |
| Column 2 header | `Age` | `경과` |
| Column 3 header | `PR` | `PR` |
| Column 4 header | `Reviewers` | `리뷰어` |
| Empty state | `🎉 All clear! No PRs need review` | `🎉 리뷰 대기 중인 PR이 없습니다` |
| Truncation warning | `⚠️ +{count} more PRs not shown. Check GitHub for full list.` | `⚠️ +{count}개 더 있음. 전체 목록은 GitHub에서 확인하세요.` |

**Implementation Pattern**:
```python
def _get_header_text(self, column: str) -> str:
    """Get bilingual header text for table columns."""
    headers = {
        "en": {
            "staleness": "Staleness",
            "age": "Age",
            "pr": "PR",
            "reviewers": "Reviewers"
        },
        "ko": {
            "staleness": "숙성도",
            "age": "경과",
            "pr": "PR",
            "reviewers": "리뷰어"
        }
    }
    return headers[self.language][column]
```

**Alternatives considered**:
- ❌ Separate translation files: Overkill for 7 string pairs
- ❌ Translating elapsed time format: "12d" is compact and universally understood; "12일" takes more space

---

## 5. PR Details Column Format

### Decision: Two-line format - repo#number as link on first line, plain title on second line

**Rationale**:
- Specification explicitly clarifies: "Link on repo#number (first line), plain title text (second line), implemented as 2 separate Slack Block Kit blocks"
- This matches the user-provided sample structure
- Improves scannability - users can quickly identify PRs by repo/number while seeing full titles

**Implementation**:
```json
{
  "type": "rich_text",
  "elements": [
    {
      "type": "rich_text_section",
      "elements": [
        {"type": "text", "text": "carsharing-reservation#1802\n"},
        {"type": "link", "text": "[NEWCS-2798] SyncReservation 구현", "url": "https://github.com/..."}
      ]
    }
  ]
}
```

**Key Details**:
- First element: plain text with repo#number and `\n`
- Second element: link with PR title and GitHub URL
- Both elements are in the same `rich_text_section`

**Alternatives considered**:
- ❌ Single line with link: Would make titles and repo names hard to distinguish
- ❌ Separate rich_text blocks: Adds unnecessary complexity; newline within section is sufficient

---

## 6. Reviewer Display Format

### Decision: Vertical list with newline-separated user mentions

**Rationale**:
- Multiple reviewers are easier to read when stacked vertically
- Matches the user-provided sample structure
- Horizontal comma-separated lists become cluttered with 3+ reviewers

**Implementation**:
```json
{
  "type": "rich_text",
  "elements": [
    {
      "type": "rich_text_section",
      "elements": [
        {"type": "user", "user_id": "U07J3FER6DN"},
        {"type": "text", "text": "\n"},
        {"type": "user", "user_id": "UJ5N2KA81"},
        {"type": "text", "text": "\n"},
        {"type": "user", "user_id": "U06C5EL74CC"}
      ]
    }
  ]
}
```

**Edge Case - No reviewers**: Display single dash "-" as plain text element

**Alternatives considered**:
- ❌ Comma-separated horizontal list: Cluttered with 3+ reviewers
- ❌ Empty cell: Less clear than explicit "-" indicator

---

## 7. Staleness Emoji Mapping

### Decision: Reuse existing emoji mapping (🤢 rotten, 🧀 aging, ✨ fresh)

**Rationale**:
- These emojis are already established in the current UI
- Users are familiar with the mapping
- Emoji element type in rich_text: `{"type": "emoji", "name": "nauseated_face"}`

**Mapping**:
- Rotten (8+ days): 🤢 `:nauseated_face:` → `{"type": "emoji", "name": "nauseated_face"}`
- Aging (4-7 days): 🧀 `:cheese_wedge:` → `{"type": "emoji", "name": "cheese_wedge"}`
- Fresh (1-3 days): ✨ `:sparkles:` → `{"type": "emoji", "name": "sparkles"}`

**Alternatives considered**:
- ❌ Changing emojis: Would confuse existing users
- ❌ Text labels instead of emojis: Less visually distinctive

---

## 8. Elapsed Time Format

### Decision: Compact days format "Xd" (e.g., "12d", "5d", "2d")

**Rationale**:
- Space-efficient for table display
- Universally understood across languages
- Matches the user-provided sample
- No need for translation (works in both EN and KO)

**Implementation**: `f"{int(staleness_days)}d"`

**Alternatives considered**:
- ❌ Verbose format ("12 days old"): Takes too much space in table
- ❌ Localized format ("12일"): Longer in Korean, adds translation complexity

---

## 9. Sorting and Truncation Strategy

### Decision: Sort all PRs by staleness_days descending, then truncate at max_prs_total

**Rationale**:
- Table view eliminates category-based grouping
- Users want to see the stalest PRs first (highest priority)
- Single sort ensures consistent ordering
- Truncation at 99 rows max (100 - 1 header = 99 PRs) due to Slack limit

**Implementation**:
```python
# Sort all PRs by staleness descending (stalest first)
sorted_prs = sorted(stale_prs, key=lambda pr: pr.staleness_days, reverse=True)

# Truncate to max_prs_total (capped at 99)
display_limit = min(self.max_prs_total, 99)
displayed_prs = sorted_prs[:display_limit]
truncated_count = len(sorted_prs) - len(displayed_prs)
```

**Alternatives considered**:
- ❌ Sort within categories: No longer needed without category sections
- ❌ Show newest first: Contradicts goal of highlighting stale PRs

---

## 10. Empty State Handling

### Decision: Skip table entirely and show plain text message block

**Rationale**:
- Specification explicitly states: "Skip table entirely and show plain text message block"
- Cleaner UI when no data exists
- Matches existing empty state pattern from current implementation

**Implementation**:
```json
{
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": ":calendar: Code Review Board",  // or Korean equivalent
        "emoji": true
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "🎉 All clear! No PRs need review"  // or Korean equivalent
      }
    }
  ]
}
```

**Alternatives considered**:
- ❌ Show empty table: Confusing visual with no data rows
- ❌ Show table with "No data" row: Adds unnecessary complexity

---

## Implementation Checklist

Based on research findings, the implementation will:

- [x] Use Slack Block Kit `table` block type with `rows` array
- [x] Construct cells using `rich_text` blocks with `rich_text_section` elements
- [x] Set column alignment: center for emoji/age, left for PR/reviewers
- [x] Implement bilingual support with switch statements for 7 translation pairs
- [x] Format PR details as two-line (repo#number link + plain title)
- [x] Display reviewers as vertical newline-separated list
- [x] Reuse existing emoji mapping (🤢, 🧀, ✨)
- [x] Use compact elapsed time format ("Xd")
- [x] Sort all PRs by staleness descending before rendering
- [x] Truncate at min(max_prs_total, 99) and show warning
- [x] Skip table and show empty state message when no PRs exist

---

## Risk Assessment

**Low Risk**:
- Slack Block Kit table format is well-documented and stable
- No external dependencies beyond existing `requests` library
- Change is isolated to `SlackClient.build_blocks()` method

**Mitigation**:
- Comprehensive unit tests will validate table structure
- Dry-run mode allows testing without sending to Slack
- Bilingual tests will ensure translation correctness

---

**Research Complete**: All technical unknowns resolved. Ready for Phase 1 (Design).
