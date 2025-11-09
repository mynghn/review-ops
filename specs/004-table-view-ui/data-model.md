# Data Model: Table View UI

**Feature**: Table View UI for Stale PR Board
**Date**: 2025-11-10

## Overview

This document defines the data structures for the table view UI. The feature reuses existing Python data models (`StalePR`, `PullRequest`, `TeamMember`) and introduces new Slack Block Kit JSON structures for table rendering.

---

## Existing Python Models (No Changes)

### StalePR

Represents a stale pull request with calculated staleness metadata.

**Source**: `src/models.py`

```python
@dataclass
class StalePR:
    pr: PullRequest
    staleness_days: float
    category: str  # "rotten", "aging", or "fresh"
```

**Usage in Table**: Each `StalePR` instance maps to one data row in the table.

---

### PullRequest

Represents a GitHub pull request with metadata.

**Source**: `src/models.py`

```python
@dataclass
class PullRequest:
    repo_name: str          # e.g., "carsharing-reservation"
    number: int             # e.g., 1802
    title: str              # PR title
    url: str                # GitHub URL
    author: str             # GitHub username
    reviewers: list[str]    # List of GitHub usernames
    # ... other fields ...
```

**Usage in Table**:
- `repo_name` + `number` → PR details column (line 1)
- `title` → PR details column (line 2)
- `url` → Link target
- `reviewers` → Reviewers column (mapped to Slack user IDs)

---

### TeamMember

Represents a team member with GitHub-to-Slack mapping.

**Source**: `src/models.py`

```python
@dataclass
class TeamMember:
    github_username: str
    slack_user_id: str | None
```

**Usage in Table**: Provides `github_username` → `slack_user_id` mapping for reviewer mentions in the reviewers column.

---

## New Slack Block Kit Structures (JSON)

These are JSON structures returned by `SlackClient.build_blocks()`, not Python classes.

### TableBlock

Top-level Slack Block Kit table structure.

```json
{
  "type": "table",
  "column_settings": [
    {"align": "center"},  // Staleness emoji
    {"align": "center"},  // Age
    {"align": "left"},    // PR details
    {"align": "left"}     // Reviewers
  ],
  "rows": [
    [...],  // Header row
    [...],  // Data row 1
    [...]   // Data row 2
  ]
}
```

**Properties**:
- `type`: Always `"table"`
- `column_settings`: Array of alignment configs (4 elements, one per column)
- `rows`: Array of row arrays (first row = header, subsequent rows = data)

**Constraints**:
- Maximum 20 columns (we use 4)
- Maximum 100 rows including header (we cap at 99 data rows + 1 header)

---

### TableRow (Header)

First row in `rows` array, defines column headers.

```json
[
  {
    "type": "rich_text",
    "elements": [
      {
        "type": "rich_text_section",
        "elements": [
          {"type": "text", "text": "Staleness", "style": {"bold": true}}
        ]
      }
    ]
  },
  {
    "type": "rich_text",
    "elements": [
      {
        "type": "rich_text_section",
        "elements": [
          {"type": "text", "text": "Age", "style": {"bold": true}}
        ]
      }
    ]
  },
  {
    "type": "rich_text",
    "elements": [
      {
        "type": "rich_text_section",
        "elements": [
          {"type": "text", "text": "PR", "style": {"bold": true}}
        ]
      }
    ]
  },
  {
    "type": "rich_text",
    "elements": [
      {
        "type": "rich_text_section",
        "elements": [
          {"type": "text", "text": "Reviewers", "style": {"bold": true}}
        ]
      }
    ]
  }
]
```

**Properties**:
- Each column header is a `rich_text` cell
- Text elements have `"style": {"bold": true}` for emphasis
- Header text is language-specific (EN/KO)

---

### TableRow (Data)

Subsequent rows in `rows` array, one per `StalePR`.

```json
[
  {
    "type": "rich_text",
    "elements": [
      {
        "type": "rich_text_section",
        "elements": [
          {"type": "emoji", "name": "nauseated_face"}
        ]
      }
    ]
  },
  {
    "type": "rich_text",
    "elements": [
      {
        "type": "rich_text_section",
        "elements": [
          {"type": "text", "text": "12d"}
        ]
      }
    ]
  },
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
  },
  {
    "type": "rich_text",
    "elements": [
      {
        "type": "rich_text_section",
        "elements": [
          {"type": "user", "user_id": "U07J3FER6DN"},
          {"type": "text", "text": "\n"},
          {"type": "user", "user_id": "UJ5N2KA81"}
        ]
      }
    ]
  }
]
```

**Column Mapping**:
1. **Staleness**: Emoji element based on `stale_pr.category`
2. **Age**: Text element with `f"{int(stale_pr.staleness_days)}d"`
3. **PR Details**: Two elements (repo#number text + link with title)
4. **Reviewers**: User elements separated by newline text elements

---

### TableCell (rich_text)

Each cell in a row is a `rich_text` block.

```json
{
  "type": "rich_text",
  "elements": [
    {
      "type": "rich_text_section",
      "elements": [
        // Array of text, emoji, link, or user elements
      ]
    }
  ]
}
```

**Supported Element Types**:

#### Text Element
```json
{"type": "text", "text": "Plain text"}
{"type": "text", "text": "Bold text", "style": {"bold": true}}
```

#### Emoji Element
```json
{"type": "emoji", "name": "nauseated_face"}  // 🤢
{"type": "emoji", "name": "cheese_wedge"}    // 🧀
{"type": "emoji", "name": "sparkles"}         // ✨
```

#### Link Element
```json
{
  "type": "link",
  "text": "[NEWCS-2798] SyncReservation 구현",
  "url": "https://github.com/socar-inc/carsharing-reservation/pull/1802"
}
```

#### User Element
```json
{"type": "user", "user_id": "U07J3FER6DN"}  // Slack user mention
```

---

## Translation String Model

Bilingual strings for table UI elements.

```python
TRANSLATIONS = {
    "en": {
        "board_title": ":calendar: Code Review Board",
        "col_staleness": "Staleness",
        "col_age": "Age",
        "col_pr": "PR",
        "col_reviewers": "Reviewers",
        "empty_state": "🎉 All clear! No PRs need review",
        "truncation_warning": "⚠️ +{count} more PRs not shown. Check GitHub for full list."
    },
    "ko": {
        "board_title": ":calendar: 코드 리뷰 현황판",
        "col_staleness": "숙성도",
        "col_age": "경과",
        "col_pr": "PR",
        "col_reviewers": "리뷰어",
        "empty_state": "🎉 리뷰 대기 중인 PR이 없습니다",
        "truncation_warning": "⚠️ +{count}개 더 있음. 전체 목록은 GitHub에서 확인하세요."
    }
}
```

**Usage**: Accessed via `TRANSLATIONS[self.language][key]`

---

## State Transitions

### StalePR List → Table Blocks

```
Input: List[StalePR], List[TeamMember]
  ↓
Sort by staleness_days descending
  ↓
Truncate to min(max_prs_total, 99)
  ↓
Generate header row (bilingual)
  ↓
For each StalePR:
  - Map category → emoji
  - Format staleness_days → "Xd"
  - Format PR details (repo#number + title)
  - Map reviewers → Slack user IDs
  - Build table row
  ↓
Wrap in table block with column_settings
  ↓
Output: List[dict] (Slack Block Kit blocks)
```

---

## Validation Rules

### Table Block
- Must have exactly 4 columns in `column_settings`
- Must have at least 1 row (header)
- Must have at most 100 rows (1 header + 99 data)

### Header Row
- Must have exactly 4 cells
- Each cell must be `rich_text` with bold text
- Text must be in configured language

### Data Row
- Must have exactly 4 cells
- Column 1: Must contain exactly 1 emoji element
- Column 2: Must contain exactly 1 text element matching pattern `\d+d`
- Column 3: Must contain 2 elements (text + link) or be valid two-line format
- Column 4: Must contain user elements separated by newline text, or single dash "-" for no reviewers

### Translation Strings
- Must exist for both "en" and "ko" languages
- Must include all 7 required keys
- Truncation warning must include `{count}` placeholder

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| 0 PRs | Skip table, show empty state message (header + section block) |
| 1 PR | Show table with header + 1 data row |
| 100+ PRs | Truncate to 99 data rows (max_prs_total capped at 99), show truncation warning |
| No reviewers | Display "-" as plain text element in reviewers column |
| Missing Slack user ID | Fallback to `@github_username` as text element |
| PR title with special chars | Escape not needed in `link` element (Slack handles it) |
| Very long PR title | Slack will wrap text automatically in table cell |

---

## Entity Relationships

```
TeamMember
    ↓ (provides github_username → slack_user_id mapping)
PullRequest ────→ TableRow (data)
    ↑ (contains)
StalePR ────→ Sorted List ────→ TableBlock
                    ↓
            Truncation Logic
                    ↓
            Header Row + Data Rows
```

---

**Data Model Complete**: Ready for contract generation (Phase 1).
