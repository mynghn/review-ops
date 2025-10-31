# SlackClient Interface Contract

## Feature: UI Enhancements for Stale PR Board
**Class**: `SlackClient`
**Module**: `src/slack_client.py`

---

## Class Overview

Enhanced `SlackClient` class with Block Kit formatting and language support for stale PR board messages.

**Key Changes**:
- Add `language` parameter to constructor
- Replace plain text formatting with Block Kit blocks
- Add private helper methods for block construction

---

## Constructor

### `__init__(webhook_url: str, language: str = 'en')`

Initialize SlackClient with webhook URL and language preference.

**Parameters**:
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `webhook_url` | `str` | Yes | - | Slack incoming webhook URL |
| `language` | `str` | No | `'en'` | Language code ('en' or 'ko') |

**Raises**:
- `ValueError` - if `language` not in `['en', 'ko']` (validated in config.py, not constructor)

**Example**:
```python
from config import SLACK_WEBHOOK_URL, LANGUAGE

client = SlackClient(webhook_url=SLACK_WEBHOOK_URL, language=LANGUAGE)
```

**Notes**:
- Language validation happens at app startup (config.py), not in constructor
- Invalid language raises error before SlackClient instantiation

---

## Public Methods

### `post_stale_pr_summary(categorized_prs: dict[str, list[PullRequest]]) -> bool`

Posts Block Kit formatted summary of stale PRs to Slack.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `categorized_prs` | `dict[str, list[PullRequest]]` | Yes | Dictionary with keys: 'rotten', 'aging', 'fresh' |

**Returns**:
| Type | Description |
|------|-------------|
| `bool` | `True` if message posted successfully, `False` otherwise |

**Example**:
```python
categorized_prs = {
    'rotten': [pr1, pr2],
    'aging': [pr3],
    'fresh': [pr4, pr5, pr6]
}

success = client.post_stale_pr_summary(categorized_prs)
if not success:
    logger.error("Failed to post Slack message")
```

**Expected Input Structure**:
```python
{
    'rotten': [PullRequest(...)],  # 10+ days old
    'aging': [PullRequest(...)],   # 5-9 days old
    'fresh': [PullRequest(...)]    # 0-4 days old
}
```

**Behavior**:
- Builds Block Kit blocks for all categories
- Truncates each category to 15 PRs max
- Adds truncation warning if PRs exceed limit
- POSTs JSON payload to webhook URL
- Logs errors if webhook fails

**Error Handling**:
- Catches `requests.RequestException` and logs error
- Returns `False` on failure, `True` on success (200 OK)
- Slack API errors (400 Bad Request) logged with response body

---

## Private Methods

### `_build_blocks(categorized_prs: dict[str, list[PullRequest]]) -> list[dict]`

Constructs complete list of Block Kit blocks for all categories.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `categorized_prs` | `dict[str, list[PullRequest]]` | Categorized PR dictionary |

**Returns**:
| Type | Description |
|------|-------------|
| `list[dict]` | List of Block Kit block objects (JSON-serializable dicts) |

**Block Structure**:
```python
[
    {"type": "header", ...},      # Rotten category header
    {"type": "section", ...},     # PR 1
    {"type": "section", ...},     # PR 2
    {"type": "context", ...},     # Truncation warning (if needed)
    {"type": "divider"},          # Visual separator
    {"type": "header", ...},      # Aging category header
    # ...
]
```

**Notes**:
- Iterates through categories in order: rotten, aging, fresh
- Adds divider between categories (not after last category)
- Skips empty categories (no header if no PRs)

---

### `_build_category_blocks(category: str, prs: list[PullRequest]) -> list[dict]`

Builds Block Kit blocks for a single category with truncation logic.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `category` | `str` | Category name ('rotten', 'aging', or 'fresh') |
| `prs` | `list[PullRequest]` | List of PRs in this category |

**Returns**:
| Type | Description |
|------|-------------|
| `list[dict]` | List of blocks: 1 header + N sections (max 15) + optional truncation |

**Truncation Logic**:
```python
MAX_PRS_PER_CATEGORY = 15

displayed_prs = prs[:MAX_PRS_PER_CATEGORY]
if len(prs) > MAX_PRS_PER_CATEGORY:
    # Add truncation warning
```

**Example Output** (3 PRs, no truncation):
```python
[
    {"type": "header", "text": {"type": "plain_text", "text": "🤢 Rotten PRs"}},
    {"type": "section", "text": {"type": "mrkdwn", "text": "..."}},  # PR 1
    {"type": "section", "text": {"type": "mrkdwn", "text": "..."}},  # PR 2
    {"type": "section", "text": {"type": "mrkdwn", "text": "..."}}   # PR 3
]
```

---

### `_build_header_block(category: str) -> dict`

Creates header block for a category (language-aware).

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `category` | `str` | Category name ('rotten', 'aging', or 'fresh') |

**Returns**:
| Type | Description |
|------|-------------|
| `dict` | Block Kit header block |

**Return Structure**:
```python
{
    "type": "header",
    "text": {
        "type": "plain_text",
        "text": "🤢 Rotten PRs",  # or Korean equivalent
        "emoji": True
    }
}
```

**Language Mapping**:
| Category | English | Korean |
|----------|---------|--------|
| `'rotten'` | `🤢 Rotten PRs` | `🤢 PR 부패 중...` |
| `'aging'` | `🧀 Aging PRs` | `🧀 PR 숙성 중...` |
| `'fresh'` | `✨ Fresh PRs` | `✨ 갓 태어난 PR` |

---

### `_build_pr_section(pr: PullRequest) -> dict`

Creates section block for a single PR with mrkdwn formatting.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `pr` | `PullRequest` | Pull request object with all required fields |

**Returns**:
| Type | Description |
|------|-------------|
| `dict` | Block Kit section block with PR details |

**Required PR Fields**:
- `pr.number: int` - PR number
- `pr.title: str` - PR title (will be escaped)
- `pr.url: str` - Full GitHub PR URL
- `pr.author: str` - GitHub username
- `pr.days_old: int` - Age in days
- `pr.review_count: int` - Number of pending reviews

**Return Structure**:
```python
{
    "type": "section",
    "text": {
        "type": "mrkdwn",
        "text": (
            "*<https://github.com/org/repo/pull/123|PR #123: Fix bug>*\n"
            ":bust_in_silhouette: @johndoe • :clock3: 14 days old • :eyes: 3 reviews pending"
        )
    }
}
```

**Formatting Rules**:
- PR title: bold with clickable link `*<url|text>*`
- Author: username with @ prefix
- Age: language-aware format (days only)
- Reviews: language-aware count format
- Separators: ` • ` (bullet with spaces)

---

### `_build_truncation_warning(count: int) -> dict`

Creates context block warning about truncated PRs (language-aware).

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `count` | `int` | Number of PRs not shown due to truncation |

**Returns**:
| Type | Description |
|------|-------------|
| `dict` | Block Kit context block with warning message |

**Return Structure**:
```python
{
    "type": "context",
    "elements": [
        {
            "type": "mrkdwn",
            "text": "⚠️ +5 more PRs not shown. Check GitHub for full list."
        }
    ]
}
```

**Language Mapping**:
| Language | Format |
|----------|--------|
| English | `⚠️ +{count} more PRs not shown. Check GitHub for full list.` |
| Korean | `⚠️ +{count}개 더 있음. 전체 목록은 GitHub에서 확인하세요.` |

---

### `_escape_mrkdwn(text: str) -> str`

Escapes special characters in text to prevent unintended mrkdwn formatting.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| `text` | `str` | Raw text (e.g., PR title) |

**Returns**:
| Type | Description |
|------|-------------|
| `str` | Escaped text safe for mrkdwn blocks |

**Escape Rules**:
| Character | Escaped To | Reason |
|-----------|------------|--------|
| `&` | `&amp;` | HTML entity |
| `<` | `&lt;` | HTML entity, prevents malformed links |
| `>` | `&gt;` | HTML entity, prevents malformed links |

**Not Escaped** (intentional):
- `*` - Allow bold formatting in PR titles
- `_` - Allow italic formatting
- `~` - Allow strikethrough
- `` ` `` - Allow inline code

**Example**:
```python
title = "Fix <script> tag handling & XSS"
escaped = self._escape_mrkdwn(title)
# Result: "Fix &lt;script&gt; tag handling &amp; XSS"
```

---

## Constants

### `MAX_PRS_PER_CATEGORY`

Maximum number of PRs displayed per category before truncation.

```python
MAX_PRS_PER_CATEGORY = 15
```

**Rationale**:
- Keeps message under 50-block Slack limit
- (1 header + 15 sections + 1 truncation) × 3 categories + 2 dividers = 53 blocks
- Provides comfortable buffer

---

## Attributes

### Instance Attributes

| Attribute | Type | Visibility | Description |
|-----------|------|------------|-------------|
| `webhook_url` | `str` | Public | Slack incoming webhook URL |
| `language` | `str` | Public | Language code ('en' or 'ko') |

**No Hidden State**:
- No caching of blocks or messages
- No persistent connections
- Stateless operation (each method call independent)

---

## Error Handling

### Webhook POST Failures

```python
try:
    response = requests.post(
        self.webhook_url,
        json=payload,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    response.raise_for_status()
    return True
except requests.RequestException as e:
    logger.error(f"Failed to post to Slack: {e}")
    if hasattr(e, 'response') and e.response is not None:
        logger.error(f"Response body: {e.response.text}")
    return False
```

**Error Scenarios**:
| Status Code | Cause | Handling |
|-------------|-------|----------|
| 400 | Invalid Block Kit JSON | Log error with response body, return False |
| 404 | Webhook URL not found | Log error, return False |
| 500 | Slack server error | Log error, return False |
| Timeout | Network issue | Log error, return False |

---

## Testing Interface

### Test Fixtures

```python
@pytest.fixture
def slack_client_en():
    """English SlackClient for testing"""
    return SlackClient(webhook_url=TEST_WEBHOOK_URL, language='en')

@pytest.fixture
def slack_client_ko():
    """Korean SlackClient for testing"""
    return SlackClient(webhook_url=TEST_WEBHOOK_URL, language='ko')

@pytest.fixture
def mock_webhook(mocker):
    """Mock requests.post to avoid real Slack calls"""
    return mocker.patch('requests.post', return_value=MockResponse(200, 'ok'))
```

### Test Coverage Requirements

| Method | Coverage Requirement |
|--------|---------------------|
| `post_stale_pr_summary` | Success, failure, webhook error scenarios |
| `_build_blocks` | Empty categories, mixed categories, all categories |
| `_build_category_blocks` | No PRs, <15 PRs, >15 PRs (truncation) |
| `_build_header_block` | All 3 categories × 2 languages = 6 tests |
| `_build_pr_section` | Various PR data, special chars in title |
| `_build_truncation_warning` | Various counts × 2 languages |
| `_escape_mrkdwn` | Special chars (&, <, >), Unicode (Korean) |

---

## Backward Compatibility

### Deprecated Methods (if any exist)

If old `post_message(text: str)` method exists:

```python
@deprecated("Use post_stale_pr_summary() instead")
def post_message(self, text: str) -> bool:
    """Legacy plain text posting (DEPRECATED)"""
    # ... existing implementation
```

**Migration Path**:
- Keep old method temporarily for other use cases
- Use `post_stale_pr_summary()` for PR board feature
- Remove old method in future release if unused

---

## Summary

### New Interface Components
- ✅ `language` constructor parameter
- ✅ `post_stale_pr_summary()` public method (Block Kit)
- ✅ 5 private helper methods for Block Kit construction

### Modified Components
- ✅ `__init__()` - add language parameter

### Unchanged Components
- ✅ `webhook_url` attribute and validation
- ✅ Error handling patterns (try-except, logging)
- ✅ Request timeout settings

**Zero Breaking Changes**: New feature adds methods, doesn't modify existing ones.
