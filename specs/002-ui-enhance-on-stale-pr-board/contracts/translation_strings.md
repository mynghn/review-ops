# Translation Strings Contract

## Feature: UI Enhancements for Stale PR Board
**Languages**: English (en), Korean (ko)
**Implementation**: Inline conditionals (no translation dictionary)

---

## Complete String Inventory

### 1. Category Headers (3 pairs)

| Context | English (en) | Korean (ko) | Notes |
|---------|--------------|-------------|-------|
| Rotten category header | `🤢 Rotten PRs` | `🤢 PR 부패 중...` | Ongoing decay, slightly dramatic |
| Aging category header | `🧀 Aging PRs` | `🧀 PR 숙성 중...` | Like wine/cheese, positive spin |
| Fresh category header | `✨ Fresh PRs` | `✨ 갓 태어난 PR` | Freshly born, warm and welcoming |

**Implementation Pattern**:
```python
if category == 'rotten':
    header = "🤢 PR 부패 중..." if self.language == 'ko' else "🤢 Rotten PRs"
elif category == 'aging':
    header = "🧀 PR 숙성 중..." if self.language == 'ko' else "🧀 Aging PRs"
else:  # fresh
    header = "✨ 갓 태어난 PR" if self.language == 'ko' else "✨ Fresh PRs"
```

---

### 2. Age Expressions (2 pairs)

| Context | English (en) | Korean (ko) | Variables |
|---------|--------------|-------------|-----------|
| Days old | `{days} days old` | `{days}일 묵음` | `days: int` |
| Weeks old (optional) | `{weeks} weeks old` | `{weeks}주 묵음` | `weeks: int` |

**Implementation Pattern**:
```python
age_text = f"{days}일 묵음" if self.language == 'ko' else f"{days} days old"
```

**Notes**:
- Korean "묵음" = aged/stale (neutral tone)
- No plural handling needed (Korean doesn't pluralize)
- Use days-only format for simplicity (weeks optional for very old PRs)

---

### 3. Review Count (1 pair)

| Context | English (en) | Korean (ko) | Variables |
|---------|--------------|-------------|-----------|
| Pending reviews | `{count} reviews pending` | `리뷰 {count}개 대기중` | `count: int` |

**Implementation Pattern**:
```python
review_text = f"리뷰 {count}개 대기중" if self.language == 'ko' else f"{count} reviews pending"
```

**Notes**:
- "리뷰" (review) kept in English transliteration (standard in Korean dev teams)
- "개" = counter for items (always used, even for count=1)
- "대기중" = waiting/pending

---

### 4. Truncation Warning (1 pair)

| Context | English (en) | Korean (ko) | Variables |
|---------|--------------|-------------|-----------|
| More PRs indicator | `⚠️ +{count} more PRs not shown. Check GitHub for full list.` | `⚠️ +{count}개 더 있음. 전체 목록은 GitHub에서 확인하세요.` | `count: int` |

**Implementation Pattern**:
```python
warning = (
    f"⚠️ +{count}개 더 있음. 전체 목록은 GitHub에서 확인하세요."
    if self.language == 'ko'
    else f"⚠️ +{count} more PRs not shown. Check GitHub for full list."
)
```

**Notes**:
- "더 있음" = more exist (informal but professional)
- "GitHub" kept in English (proper noun)
- "확인하세요" = please check (polite imperative)

---

### 5. Empty Category (1 pair)

| Context | English (en) | Korean (ko) | Variables |
|---------|--------------|-------------|-----------|
| No PRs in category | `No PRs in this category` | `이 카테고리에 PR 없음` | None |

**Implementation Pattern**:
```python
empty_text = "이 카테고리에 PR 없음" if self.language == 'ko' else "No PRs in this category"
```

**Notes**:
- May not be displayed if empty categories are skipped
- Korean omits articles ("the") and uses informal but clear style

---

### 6. PR Section Format (composite string)

| Component | English (en) | Korean (ko) |
|-----------|--------------|-------------|
| Author prefix | `:bust_in_silhouette:` (emoji only) | `:bust_in_silhouette:` (emoji only) |
| Age prefix | `:clock3:` (emoji only) | `:clock3:` (emoji only) |
| Review prefix | `:eyes:` (emoji only) | `:eyes:` (emoji only) |
| Separator | ` • ` | ` • ` (same) |

**Full PR Section Format**:

English:
```
*<https://github.com/org/repo/pull/123|PR #123: Fix authentication bug>*
:bust_in_silhouette: @johndoe • :clock3: 14 days old • :eyes: 3 reviews pending
```

Korean:
```
*<https://github.com/org/repo/pull/123|PR #123: Fix authentication bug>*
:bust_in_silhouette: @johndoe • :clock3: 14일 묵음 • :eyes: 리뷰 3개 대기중
```

**Implementation Pattern**:
```python
age_str = f"{pr.days_old}일 묵음" if self.language == 'ko' else f"{pr.days_old} days old"
review_str = f"리뷰 {pr.review_count}개 대기중" if self.language == 'ko' else f"{pr.review_count} reviews pending"

text = (
    f"*<{pr.url}|PR #{pr.number}: {self._escape_mrkdwn(pr.title)}>*\n"
    f":bust_in_silhouette: @{pr.author} • :clock3: {age_str} • :eyes: {review_str}"
)
```

**Notes**:
- PR title remains in original language (not translated)
- Author username remains unchanged
- Only age and review count strings are translated

---

## Translation Guidelines

### Tone & Formality
- **English**: Professional, concise, informative
- **Korean**:
  - Informal but respectful (반말 적절히 사용)
  - Witty where appropriate (e.g., "숙성중" for aging)
  - Direct and clear (no overly formal grammar)

### Technical Terms
Keep these in English (standard practice in Korean dev teams):
- PR (not "풀 리퀘스트")
- GitHub (not "깃허브")
- review (as "리뷰" - Korean transliteration)

### Avoid
- ❌ Grammatical particles (은/는/이/가) that require context-sensitive logic
- ❌ Honorifics (formal 존댓말 like 합니다/습니다)
- ❌ Complex sentence structures requiring word order changes
- ❌ Slang or overly casual language

### Emoji Usage
- ✅ Same emojis for both languages
- ✅ Emojis render consistently in all Slack clients
- ✅ No need for emoji translations

---

## Configuration

### Environment Variable
```bash
# In .env
LANGUAGE=en  # or 'ko'
```

### Validation (in config.py)
```python
LANGUAGE = os.getenv('LANGUAGE', 'en')
SUPPORTED_LANGUAGES = ['en', 'ko']

if LANGUAGE not in SUPPORTED_LANGUAGES:
    raise ValueError(
        f"Invalid LANGUAGE={LANGUAGE}. "
        f"Supported values: {', '.join(SUPPORTED_LANGUAGES)}"
    )
```

### SlackClient Initialization
```python
# In app.py
from config import LANGUAGE

slack_client = SlackClient(
    webhook_url=SLACK_WEBHOOK_URL,
    language=LANGUAGE
)
```

---

## Testing

### Korean Encoding Tests
```python
def test_korean_header_encoding():
    """Ensure Korean characters don't get mangled"""
    client = SlackClient(webhook_url=TEST_URL, language='ko')
    blocks = client._build_blocks({'rotten': [], 'aging': [], 'fresh': []})

    header = blocks[0]
    assert header['text']['text'] == "🤢 PR 부패 중..."
    assert '?' not in header['text']['text']  # No encoding errors

def test_korean_age_format():
    """Test Korean age string formatting"""
    client = SlackClient(webhook_url=TEST_URL, language='ko')
    pr = create_test_pr(days_old=14)

    section = client._build_pr_section(pr)
    text = section['text']['text']

    assert '14일 묵음' in text
    assert 'days old' not in text
```

### Bilingual Test Coverage
Every formatted string should have tests for both languages:
- ✅ Header blocks (3 categories × 2 languages = 6 tests)
- ✅ Age strings (1 × 2 = 2 tests)
- ✅ Review count strings (1 × 2 = 2 tests)
- ✅ Truncation warnings (1 × 2 = 2 tests)

---

## Summary

| Category | String Count | Variables | Implementation |
|----------|--------------|-----------|----------------|
| Category headers | 3 pairs (6 strings) | None | Inline conditionals |
| Age expressions | 1-2 pairs (2-4 strings) | `days`, `weeks` | f-string + conditional |
| Review count | 1 pair (2 strings) | `count` | f-string + conditional |
| Truncation warning | 1 pair (2 strings) | `count` | f-string + conditional |
| Empty state | 1 pair (2 strings) | None | Inline conditionals |
| **Total** | **7 pairs (14 strings)** | | **No translation dict** |

**Philosophy**: Too few strings to justify abstraction. Inline conditionals keep code simple and readable.
