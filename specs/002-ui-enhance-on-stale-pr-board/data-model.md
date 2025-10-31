# Data Model

## Feature: UI Enhancements for Stale PR Board
**Branch**: 002-ui-enhance-on-stale-pr-board
**Date**: 2025-10-31

---

## Overview

This document defines the data structures and entities for implementing Block Kit formatting and Korean language support in the stale PR board.

**Key Changes**:
- Transform plain text Slack messages into Block Kit JSON structures
- Add language configuration for EN/KO string pairs
- Implement truncation logic for large PR lists

**No New Entities**: This feature enhances existing `SlackClient` class, no new domain models needed.

---

## 1. Block Kit Message Structure

### BlockKitMessage (Conceptual)

Not a Python class - this is the **JSON structure** sent to Slack webhook.

```json
{
  "blocks": [
    {
      "type": "header",
      "text": {"type": "plain_text", "text": "🤢 Rotten PRs"}
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*<https://github.com/org/repo/pull/123|PR #123: Fix authentication bug>*\n:bust_in_silhouette: @johndoe • :clock3: 14 days old • :eyes: 3 reviews pending"
      }
    },
    {
      "type": "context",
      "elements": [
        {"type": "mrkdwn", "text": "⚠️ +5 more PRs not shown"}
      ]
    },
    {
      "type": "divider"
    },
    {
      "type": "header",
      "text": {"type": "plain_text", "text": "🧀 Aging PRs"}
    }
  ]
}
```

### Block Types Used

| Block Type | Purpose | Max per Message | Text Type |
|------------|---------|-----------------|-----------|
| `header` | Category titles (Rotten/Aging/Fresh) | 50 | `plain_text` |
| `section` | PR details (title, author, age, reviews) | 50 | `mrkdwn` |
| `context` | Truncation warning, metadata | 50 | `mrkdwn` |
| `divider` | Visual separation between categories | 50 | N/A |

### Block Count Calculation

```
Blocks per Category = 1 header + N sections + [0 or 1 truncation context]
Total Blocks = (Blocks per Category × 3 categories) + 2 dividers

With 15 PR limit:
= (1 + 15 + 1) × 3 + 2
= 53 blocks (within 50-block limit with buffer)
```

---

## 2. Enhanced SlackClient Class

### Existing Class Structure

```python
class SlackClient:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def post_message(self, text: str) -> bool:
        """Posts plain text message (DEPRECATED after this feature)"""
        # ... existing implementation
```

### Enhanced Class Structure

```python
class SlackClient:
    def __init__(self, webhook_url: str, language: str = 'en'):
        self.webhook_url = webhook_url
        self.language = language  # NEW: 'en' or 'ko'

    def post_stale_pr_summary(self, categorized_prs: dict) -> bool:
        """Posts Block Kit formatted PR summary with language support"""
        blocks = self._build_blocks(categorized_prs)
        payload = {"blocks": blocks}
        # ... POST to webhook

    def _build_blocks(self, categorized_prs: dict) -> list[dict]:
        """Constructs Block Kit blocks for all categories"""
        blocks = []
        for category in ['rotten', 'aging', 'fresh']:
            prs = categorized_prs.get(category, [])
            blocks.extend(self._build_category_blocks(category, prs))
            blocks.append({"type": "divider"})
        return blocks[:-1]  # Remove last divider

    def _build_category_blocks(self, category: str, prs: list) -> list[dict]:
        """Builds blocks for a single category with truncation"""
        blocks = [self._build_header_block(category)]

        displayed_prs = prs[:15]  # Truncate to 15
        for pr in displayed_prs:
            blocks.append(self._build_pr_section(pr))

        if len(prs) > 15:
            blocks.append(self._build_truncation_warning(len(prs) - 15))

        return blocks

    def _build_header_block(self, category: str) -> dict:
        """Creates header block with category name in selected language"""
        # Returns: {"type": "header", "text": {...}}

    def _build_pr_section(self, pr: PullRequest) -> dict:
        """Creates section block for a single PR with mrkdwn formatting"""
        # Returns: {"type": "section", "text": {...}}

    def _build_truncation_warning(self, count: int) -> dict:
        """Creates context block warning about truncated PRs"""
        # Returns: {"type": "context", "elements": [...]}

    def _escape_mrkdwn(self, text: str) -> str:
        """Escapes special mrkdwn characters in PR titles"""
        # Escapes: *, _, ~, <, >, &
```

### Key Attributes

| Attribute | Type | Purpose | Default |
|-----------|------|---------|---------|
| `webhook_url` | `str` | Slack incoming webhook URL | (required) |
| `language` | `str` | Language code ('en' or 'ko') | `'en'` |

### Key Methods

| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `post_stale_pr_summary` | `categorized_prs: dict` | `bool` | Main entry point, posts Block Kit message |
| `_build_blocks` | `categorized_prs: dict` | `list[dict]` | Assembles all blocks for all categories |
| `_build_category_blocks` | `category: str, prs: list` | `list[dict]` | Builds blocks for one category with truncation |
| `_build_header_block` | `category: str` | `dict` | Creates header block (language-aware) |
| `_build_pr_section` | `pr: PullRequest` | `dict` | Creates section block for single PR |
| `_build_truncation_warning` | `count: int` | `dict` | Creates truncation warning (language-aware) |
| `_escape_mrkdwn` | `text: str` | `str` | Escapes special mrkdwn characters |

---

## 3. Language Configuration

### LanguageConfig (Conceptual)

Not a separate class - language is a **single string attribute** on `SlackClient`.

### Validation

```python
# In config.py
LANGUAGE = os.getenv('LANGUAGE', 'en')
SUPPORTED_LANGUAGES = ['en', 'ko']

if LANGUAGE not in SUPPORTED_LANGUAGES:
    raise ValueError(f"Invalid LANGUAGE={LANGUAGE}. Supported: {SUPPORTED_LANGUAGES}")
```

### String Pairs

All language-specific strings use inline conditionals:

```python
# Example from _build_header_block
if category == 'rotten':
    text = "🤢 PR 부패 중..." if self.language == 'ko' else "🤢 Rotten PRs"
elif category == 'aging':
    text = "🧀 PR 숙성 중..." if self.language == 'ko' else "🧀 Aging PRs"
else:  # fresh
    text = "✨ 갓 태어난 PR" if self.language == 'ko' else "✨ Fresh PRs"
```

**Complete String Inventory**:
1. Category headers: Rotten, Aging, Fresh (3 pairs)
2. Age format: "{days} days old" → "{days}일 묵음" (1 pair)
3. Review count: "{count} reviews pending" → "리뷰 {count}개 대기중" (1 pair)
4. Truncation: "+{count} more PRs" → "+{count}개 더 있음" (1 pair)
5. Empty category: "No PRs in this category" → "이 카테고리에 PR 없음" (1 pair)

**Total: 7 string pairs** (14 strings total)

---

## 4. Existing PullRequest Model (No Changes)

The existing `PullRequest` model (from `models.py` or similar) remains unchanged:

```python
@dataclass
class PullRequest:
    number: int
    title: str
    author: str
    url: str
    created_at: datetime
    days_old: int
    review_count: int
    # ... other fields
```

**No modifications needed** - Block Kit formatting consumes existing fields.

---

## 5. Truncation Logic

### Per-Category Limit

```python
MAX_PRS_PER_CATEGORY = 15

def _build_category_blocks(self, category: str, prs: list) -> list[dict]:
    blocks = [self._build_header_block(category)]

    # Truncate to max limit
    displayed_prs = prs[:MAX_PRS_PER_CATEGORY]

    for pr in displayed_prs:
        blocks.append(self._build_pr_section(pr))

    # Show truncation warning if needed
    if len(prs) > MAX_PRS_PER_CATEGORY:
        remaining = len(prs) - MAX_PRS_PER_CATEGORY
        blocks.append(self._build_truncation_warning(remaining))

    return blocks
```

### Truncation Warning Format

```python
def _build_truncation_warning(self, count: int) -> dict:
    warning_text = (
        f"⚠️ +{count}개 더 있음. 전체 목록은 GitHub에서 확인하세요."
        if self.language == 'ko'
        else f"⚠️ +{count} more PRs not shown. Check GitHub for full list."
    )

    return {
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": warning_text}
        ]
    }
```

---

## 6. Mrkdwn Escaping

### Special Characters

Slack mrkdwn uses these characters for formatting:
- `*` - bold
- `_` - italic
- `~` - strikethrough
- `` ` `` - inline code
- `&`, `<`, `>` - HTML entities

### Escaping Strategy

```python
def _escape_mrkdwn(self, text: str) -> str:
    """Escapes special characters to prevent unintended formatting"""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    # Don't escape *, _, ~ if we want to allow user formatting in PR titles
    return text
```

**Decision**: Escape only HTML entities (`&<>`), allow `*_~` for intentional formatting in PR titles.

---

## 7. Data Flow

```
app.py
  → fetch PRs from GitHub (existing)
  → categorize by staleness (existing)
  → SlackClient.post_stale_pr_summary(categorized_prs) [NEW]
      → _build_blocks(categorized_prs)
          → for each category:
              → _build_category_blocks(category, prs)
                  → _build_header_block(category) [language-aware]
                  → for each PR (max 15):
                      → _build_pr_section(pr)
                  → if truncated: _build_truncation_warning(count) [language-aware]
              → add divider
      → POST {"blocks": blocks} to webhook
```

---

## 8. No New Database/Storage

**No changes to storage layer**:
- Team members still loaded from `team_members.json`
- PRs fetched from GitHub API (no caching)
- Language config from environment variable
- Slack webhook URL from `.env`

**Stateless operation**: No persistence of Block Kit messages or translation state.

---

## Summary

### Modified Entities
- ✅ `SlackClient` class - add `language` attribute and Block Kit builder methods

### New Entities
- ❌ None - no new classes or data models

### Configuration Changes
- ✅ Add `LANGUAGE` env var to `.env` and `config.py`

### Data Structures
- ✅ Block Kit JSON structure (documented above)
- ✅ 7 string pairs for EN/KO (inline conditionals)

**Simplicity maintained**: No unnecessary abstractions, enhance existing code only.
