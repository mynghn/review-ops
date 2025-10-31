# Implementation Quickstart

## Feature: UI Enhancements for Stale PR Board
**Branch**: 002-ui-enhance-on-stale-pr-board
**Estimated Time**: 3-5 hours
**Priority**: P1 (Block Kit) → P2 (Korean) → P3 (Config)

---

## Prerequisites

- ✅ Python 3.12 installed
- ✅ Existing `src/slack_client.py` with webhook posting
- ✅ Existing `src/config.py` for environment variables
- ✅ pytest test infrastructure in place
- ✅ Slack workspace with incoming webhook URL

---

## Implementation Order

### Phase 1: Block Kit Formatting (P1)
1. Add Block Kit builder methods to `SlackClient`
2. Update tests to validate Block Kit JSON
3. Manual verification in Slack workspace

### Phase 2: Korean Language Support (P2)
4. Add `LANGUAGE` env var to config
5. Add language parameter to `SlackClient`
6. Add inline conditionals for Korean strings
7. Expand tests for Korean encoding

### Phase 3: Configuration (P3)
8. Document `LANGUAGE` env var in `.env.example`
9. Update README with language configuration

---

## Step-by-Step Implementation

### Step 1: Add Language Config (5 min)

**File**: `src/config.py`

```python
# Add after existing config variables
LANGUAGE = os.getenv('LANGUAGE', 'en')
SUPPORTED_LANGUAGES = ['en', 'ko']

if LANGUAGE not in SUPPORTED_LANGUAGES:
    raise ValueError(
        f"Invalid LANGUAGE={LANGUAGE}. "
        f"Supported values: {', '.join(SUPPORTED_LANGUAGES)}"
    )
```

**Why First**: Fail fast on startup if config invalid, before any Slack calls.

---

### Step 2: Update SlackClient Constructor (10 min)

**File**: `src/slack_client.py`

```python
class SlackClient:
    MAX_PRS_PER_CATEGORY = 15

    def __init__(self, webhook_url: str, language: str = 'en'):
        self.webhook_url = webhook_url
        self.language = language
```

**Test**:
```python
def test_slack_client_initialization():
    client = SlackClient(webhook_url=TEST_URL, language='ko')
    assert client.language == 'ko'
```

---

### Step 3: Add mrkdwn Escaping Helper (15 min)

**File**: `src/slack_client.py`

```python
def _escape_mrkdwn(self, text: str) -> str:
    """Escapes special characters to prevent unintended mrkdwn formatting"""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    return text
```

**Test**:
```python
def test_escape_mrkdwn():
    client = SlackClient(webhook_url=TEST_URL)
    result = client._escape_mrkdwn("Fix <script> & XSS")
    assert result == "Fix &lt;script&gt; &amp; XSS"
```

**Why Early**: Needed by PR section builder, foundational utility.

---

### Step 4: Implement Header Block Builder (20 min)

**File**: `src/slack_client.py`

```python
def _build_header_block(self, category: str) -> dict:
    """Creates header block for a category (language-aware)"""
    if category == 'rotten':
        text = "🤢 PR 부패 중..." if self.language == 'ko' else "🤢 Rotten PRs"
    elif category == 'aging':
        text = "🧀 PR 숙성 중..." if self.language == 'ko' else "🧀 Aging PRs"
    else:  # fresh
        text = "✨ 갓 태어난 PR" if self.language == 'ko' else "✨ Fresh PRs"

    return {
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": text,
            "emoji": True
        }
    }
```

**Tests** (2 languages × 3 categories = 6 tests):
```python
def test_header_block_rotten_en():
    client = SlackClient(webhook_url=TEST_URL, language='en')
    block = client._build_header_block('rotten')
    assert block['type'] == 'header'
    assert block['text']['text'] == '🤢 Rotten PRs'

def test_header_block_rotten_ko():
    client = SlackClient(webhook_url=TEST_URL, language='ko')
    block = client._build_header_block('rotten')
    assert block['text']['text'] == '🤢 PR 부패 중...'

# ... repeat for 'aging' and 'fresh' categories
```

---

### Step 5: Implement PR Section Builder (30 min)

**File**: `src/slack_client.py`

```python
def _build_pr_section(self, pr) -> dict:
    """Creates section block for a single PR with mrkdwn formatting"""
    # Format age string
    age_text = (
        f"{pr.days_old}일 묵음"
        if self.language == 'ko'
        else f"{pr.days_old} days old"
    )

    # Format review count string
    review_text = (
        f"리뷰 {pr.review_count}개 대기중"
        if self.language == 'ko'
        else f"{pr.review_count} reviews pending"
    )

    # Build mrkdwn text
    escaped_title = self._escape_mrkdwn(pr.title)
    text = (
        f"*<{pr.url}|PR #{pr.number}: {escaped_title}>*\n"
        f":bust_in_silhouette: @{pr.author} • "
        f":clock3: {age_text} • "
        f":eyes: {review_text}"
    )

    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text
        }
    }
```

**Test Fixtures**:
```python
@pytest.fixture
def sample_pr():
    """Sample PR for testing"""
    return PullRequest(
        number=123,
        title="Fix authentication bug",
        author="johndoe",
        url="https://github.com/org/repo/pull/123",
        days_old=14,
        review_count=3
    )
```

**Tests**:
```python
def test_pr_section_english(sample_pr):
    client = SlackClient(webhook_url=TEST_URL, language='en')
    block = client._build_pr_section(sample_pr)

    assert block['type'] == 'section'
    assert 'PR #123: Fix authentication bug' in block['text']['text']
    assert '14 days old' in block['text']['text']
    assert '3 reviews pending' in block['text']['text']

def test_pr_section_korean(sample_pr):
    client = SlackClient(webhook_url=TEST_URL, language='ko')
    block = client._build_pr_section(sample_pr)

    assert '14일 묵음' in block['text']['text']
    assert '리뷰 3개 대기중' in block['text']['text']

def test_pr_section_escapes_special_chars():
    pr = PullRequest(title="Fix <script> & XSS", ...)
    client = SlackClient(webhook_url=TEST_URL)
    block = client._build_pr_section(pr)

    assert '&lt;script&gt;' in block['text']['text']
    assert '&amp;' in block['text']['text']
```

---

### Step 6: Implement Truncation Warning Builder (15 min)

**File**: `src/slack_client.py`

```python
def _build_truncation_warning(self, count: int) -> dict:
    """Creates context block warning about truncated PRs"""
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

**Tests**:
```python
def test_truncation_warning_english():
    client = SlackClient(webhook_url=TEST_URL, language='en')
    block = client._build_truncation_warning(5)

    assert block['type'] == 'context'
    assert '+5 more PRs' in block['elements'][0]['text']

def test_truncation_warning_korean():
    client = SlackClient(webhook_url=TEST_URL, language='ko')
    block = client._build_truncation_warning(5)

    assert '+5개 더 있음' in block['elements'][0]['text']
```

---

### Step 7: Implement Category Blocks Builder (30 min)

**File**: `src/slack_client.py`

```python
def _build_category_blocks(self, category: str, prs: list) -> list[dict]:
    """Builds blocks for a single category with truncation logic"""
    if not prs:
        return []  # Skip empty categories

    blocks = [self._build_header_block(category)]

    # Truncate to max limit
    displayed_prs = prs[:self.MAX_PRS_PER_CATEGORY]
    for pr in displayed_prs:
        blocks.append(self._build_pr_section(pr))

    # Add truncation warning if needed
    if len(prs) > self.MAX_PRS_PER_CATEGORY:
        remaining = len(prs) - self.MAX_PRS_PER_CATEGORY
        blocks.append(self._build_truncation_warning(remaining))

    return blocks
```

**Tests**:
```python
def test_category_blocks_no_prs():
    """Empty categories should return empty list"""
    client = SlackClient(webhook_url=TEST_URL)
    blocks = client._build_category_blocks('rotten', [])
    assert blocks == []

def test_category_blocks_under_limit():
    """Categories with <15 PRs should not truncate"""
    client = SlackClient(webhook_url=TEST_URL)
    prs = [create_test_pr(i) for i in range(10)]
    blocks = client._build_category_blocks('rotten', prs)

    assert len(blocks) == 11  # 1 header + 10 sections
    assert blocks[0]['type'] == 'header'
    assert all(b['type'] == 'section' for b in blocks[1:])

def test_category_blocks_over_limit():
    """Categories with >15 PRs should truncate and show warning"""
    client = SlackClient(webhook_url=TEST_URL)
    prs = [create_test_pr(i) for i in range(20)]
    blocks = client._build_category_blocks('rotten', prs)

    assert len(blocks) == 17  # 1 header + 15 sections + 1 context
    assert blocks[0]['type'] == 'header'
    assert blocks[-1]['type'] == 'context'
    assert '+5' in blocks[-1]['elements'][0]['text']
```

---

### Step 8: Implement Full Blocks Builder (20 min)

**File**: `src/slack_client.py`

```python
def _build_blocks(self, categorized_prs: dict) -> list[dict]:
    """Constructs complete list of Block Kit blocks for all categories"""
    blocks = []

    for category in ['rotten', 'aging', 'fresh']:
        prs = categorized_prs.get(category, [])
        category_blocks = self._build_category_blocks(category, prs)

        if category_blocks:  # Only add non-empty categories
            blocks.extend(category_blocks)
            blocks.append({"type": "divider"})

    # Remove last divider if blocks exist
    if blocks and blocks[-1]['type'] == 'divider':
        blocks.pop()

    return blocks
```

**Tests**:
```python
def test_build_blocks_all_categories():
    """Test full block structure with all categories"""
    client = SlackClient(webhook_url=TEST_URL)
    categorized_prs = {
        'rotten': [create_test_pr(1), create_test_pr(2)],
        'aging': [create_test_pr(3)],
        'fresh': [create_test_pr(4)]
    }

    blocks = client._build_blocks(categorized_prs)

    # Check structure: header, sections, divider, header, section, divider, header, section
    header_count = sum(1 for b in blocks if b['type'] == 'header')
    section_count = sum(1 for b in blocks if b['type'] == 'section')
    divider_count = sum(1 for b in blocks if b['type'] == 'divider')

    assert header_count == 3  # One per category
    assert section_count == 4  # Total PRs
    assert divider_count == 2  # Between categories (not after last)

def test_build_blocks_empty_categories():
    """Empty categories should be skipped"""
    client = SlackClient(webhook_url=TEST_URL)
    categorized_prs = {
        'rotten': [create_test_pr(1)],
        'aging': [],  # Empty
        'fresh': [create_test_pr(2)]
    }

    blocks = client._build_blocks(categorized_prs)

    header_count = sum(1 for b in blocks if b['type'] == 'header')
    assert header_count == 2  # Only rotten and fresh
```

---

### Step 9: Implement Main Public Method (20 min)

**File**: `src/slack_client.py`

```python
def post_stale_pr_summary(self, categorized_prs: dict) -> bool:
    """Posts Block Kit formatted summary of stale PRs to Slack"""
    try:
        blocks = self._build_blocks(categorized_prs)

        payload = {"blocks": blocks}

        response = requests.post(
            self.webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        response.raise_for_status()

        logger.info(f"Posted stale PR summary to Slack ({len(blocks)} blocks)")
        return True

    except requests.RequestException as e:
        logger.error(f"Failed to post to Slack: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response body: {e.response.text}")
        return False
```

**Tests**:
```python
def test_post_stale_pr_summary_success(mock_webhook):
    """Test successful webhook POST"""
    client = SlackClient(webhook_url=TEST_URL)
    categorized_prs = {
        'rotten': [create_test_pr(1)],
        'aging': [],
        'fresh': [create_test_pr(2)]
    }

    result = client.post_stale_pr_summary(categorized_prs)

    assert result is True
    assert mock_webhook.called
    call_args = mock_webhook.call_args
    payload = call_args[1]['json']
    assert 'blocks' in payload

def test_post_stale_pr_summary_webhook_failure(mocker):
    """Test webhook failure handling"""
    mocker.patch('requests.post', side_effect=requests.RequestException("Network error"))

    client = SlackClient(webhook_url=TEST_URL)
    result = client.post_stale_pr_summary({'rotten': [], 'aging': [], 'fresh': []})

    assert result is False
```

---

### Step 10: Update App Entry Point (10 min)

**File**: `src/app.py`

```python
# Update SlackClient initialization
from config import SLACK_WEBHOOK_URL, LANGUAGE

slack_client = SlackClient(
    webhook_url=SLACK_WEBHOOK_URL,
    language=LANGUAGE
)

# Update message posting call
categorized_prs = {
    'rotten': rotten_prs,
    'aging': aging_prs,
    'fresh': fresh_prs
}

success = slack_client.post_stale_pr_summary(categorized_prs)
if not success:
    logger.error("Failed to post stale PR summary to Slack")
```

---

### Step 11: Add Environment Variable Documentation (5 min)

**File**: `.env.example`

```bash
# Existing variables...

# Language for Slack messages (en or ko)
# Default: en
LANGUAGE=en
```

**File**: `README.md` (if exists, add section)

```markdown
### Configuration

#### Language Support

Set the `LANGUAGE` environment variable to control message language:
- `en` (English) - default
- `ko` (Korean) - Korean translations with witty expressions

Example:
\```bash
LANGUAGE=ko python src/app.py
\```
```

---

### Step 12: Manual Verification in Slack (10 min)

1. **Set English language**:
   ```bash
   export LANGUAGE=en
   python src/app.py
   ```
   - Check Slack: Verify Block Kit formatting (headers, sections, dividers)
   - Verify English strings: "Rotten PRs", "days old", "reviews pending"

2. **Set Korean language**:
   ```bash
   export LANGUAGE=ko
   python src/app.py
   ```
   - Check Slack: Verify Korean strings: "PR 부패 중...", "PR 숙성 중...", "갓 태어난 PR", "일 묵음", "리뷰 개 대기중"
   - Verify no encoding issues (no question marks or garbled text)

3. **Test truncation** (if >15 PRs in any category):
   - Verify truncation warning appears
   - Verify count is correct
   - Verify message stays under Slack limits

---

## Testing Checklist

### Unit Tests
- [x] Config validation (valid/invalid languages)
- [x] SlackClient initialization
- [x] `_escape_mrkdwn()` with special chars
- [x] `_build_header_block()` for all categories × 2 languages (6 tests)
- [x] `_build_pr_section()` with EN/KO, special chars
- [x] `_build_truncation_warning()` with EN/KO
- [x] `_build_category_blocks()` with 0, <15, >15 PRs
- [x] `_build_blocks()` with various category combinations

### Integration Tests
- [x] `post_stale_pr_summary()` with mocked webhook (success)
- [x] `post_stale_pr_summary()` with mocked webhook (failure)
- [x] End-to-end with real PR data (mocked webhook)
- [x] Block Kit JSON structure validation
- [x] Korean UTF-8 encoding validation

### Manual Tests
- [ ] Visual verification in Slack (English)
- [ ] Visual verification in Slack (Korean)
- [ ] Truncation warning display (if applicable)
- [ ] Mobile Slack client rendering
- [ ] Link clickability
- [ ] Emoji rendering

---

## Common Pitfalls

### 1. Korean Encoding Issues
**Problem**: Korean characters display as question marks
**Solution**: Ensure all files saved with UTF-8 encoding
```python
# Verify encoding in test
assert '썩은' in text  # Should not raise UnicodeError
```

### 2. Block Kit Limit Exceeded
**Problem**: Slack returns 400 "blocks too large"
**Solution**: Verify `MAX_PRS_PER_CATEGORY = 15` is enforced
```python
assert len(displayed_prs) <= self.MAX_PRS_PER_CATEGORY
```

### 3. Mrkdwn Formatting Broken
**Problem**: PR titles with `<` or `>` break links
**Solution**: Ensure `_escape_mrkdwn()` is called on titles
```python
escaped_title = self._escape_mrkdwn(pr.title)
```

### 4. Last Divider Not Removed
**Problem**: Message ends with divider (visual clutter)
**Solution**: Pop last divider in `_build_blocks()`
```python
if blocks and blocks[-1]['type'] == 'divider':
    blocks.pop()
```

### 5. Empty Categories Show Headers
**Problem**: Headers displayed even with 0 PRs
**Solution**: Return empty list from `_build_category_blocks()` if no PRs
```python
if not prs:
    return []
```

---

## Performance Notes

- **No performance impact**: Block Kit construction is O(n) where n = number of PRs
- **Truncation reduces load**: Max 45 PRs processed (15 × 3 categories)
- **Network same**: Single webhook POST (same as before)
- **Memory**: Negligible (JSON blocks ~5-10KB)

---

## Rollback Plan

If Block Kit causes issues:

1. **Revert to plain text**: Keep old `post_message()` method
2. **Feature flag**: Add `USE_BLOCK_KIT` env var
3. **Conditional logic**:
   ```python
   if USE_BLOCK_KIT:
       client.post_stale_pr_summary(categorized_prs)
   else:
       client.post_message(legacy_format)
   ```

**No data loss risk**: Read-only feature (no database changes)

---

## Post-Implementation

### Documentation Updates
- [x] Update `CLAUDE.md` (via agent context script)
- [ ] Update README with language config
- [ ] Add example screenshots to docs (optional)

### Monitoring
- Monitor Slack webhook error logs for first week
- Check for Korean encoding issues in production
- Verify no 400 errors from Slack API

### Future Enhancements (Out of Scope)
- Additional languages (Japanese, Chinese)
- Interactive buttons (approve/dismiss PR)
- Customizable emoji per category
- Dynamic truncation limits

---

## Estimated Timeline

| Task | Time | Cumulative |
|------|------|------------|
| Steps 1-3: Config + constructor + escaping | 30 min | 0:30 |
| Step 4: Header builder + tests | 20 min | 0:50 |
| Step 5: PR section builder + tests | 30 min | 1:20 |
| Step 6: Truncation builder + tests | 15 min | 1:35 |
| Step 7: Category builder + tests | 30 min | 2:05 |
| Step 8: Full blocks builder + tests | 20 min | 2:25 |
| Step 9: Public method + tests | 20 min | 2:45 |
| Step 10: App integration | 10 min | 2:55 |
| Step 11: Documentation | 5 min | 3:00 |
| Step 12: Manual verification | 10 min | 3:10 |
| **Total** | **~3 hours** | |

**Buffer for debugging**: +1-2 hours → **Total: 4-5 hours**

---

## Success Criteria

✅ **Functional**:
- Block Kit messages display in Slack with visual hierarchy
- Korean messages display correctly with no encoding issues
- Truncation works when >15 PRs per category
- Links are clickable, emojis render correctly

✅ **Quality**:
- 100% test coverage on new methods
- No failing tests in CI
- No linting errors

✅ **Constitution**:
- No unnecessary abstractions (inline conditionals, not translation dict)
- Small scope (3-5 hours as estimated)
- TDD approach followed (tests written alongside code)

**Ready to ship!** 🚀
