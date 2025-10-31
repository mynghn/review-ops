# Research & Technical Decisions

## Feature: UI Enhancements for Stale PR Board
**Branch**: 002-ui-enhance-on-stale-pr-board
**Date**: 2025-10-31

---

## 1. Slack Block Kit Integration

### Decision
Use **Slack Block Kit** with sections, dividers, and context blocks to replace plain text formatting.

### Rationale
- **Visual Hierarchy**: Block Kit provides native Slack UI components (sections, dividers, headers) that create clear visual separation between categories
- **Rich Formatting**: Supports mrkdwn text, emojis, and structured layouts without manual spacing hacks
- **Mobile Compatibility**: Block Kit renders consistently across desktop and mobile Slack clients
- **No Dependencies**: Block Kit is JSON-based; no additional Python libraries required beyond existing `requests`
- **Accessibility**: Block Kit includes automatic plain text fallback for accessibility tools

### Technical Specifications
- **Message Size Limits**:
  - Maximum blocks per message: 50 blocks
  - Maximum text length per text block: 3000 characters
  - Practical payload limit: ~50KB JSON (well within webhook limits)
- **Key Components**:
  - `header` block: Category titles with emoji (🤢 Rotten, 🧀 Aging, ✨ Fresh)
  - `section` block: PR information with mrkdwn formatting
  - `divider` block: Visual separation between categories
  - `context` block: Metadata (timestamps, author, review counts)
- **Mrkdwn Escaping Rules**:
  - Escape `*`, `_`, `~` in PR titles to prevent unintended formatting
  - Use `<url|text>` syntax for clickable links
  - Special characters: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`

### Alternatives Considered
1. **Plain text with Unicode box-drawing** - Rejected: poor mobile rendering, accessibility issues
2. **Slack Attachments API (legacy)** - Rejected: deprecated in favor of Block Kit
3. **Third-party Slack SDK** - Rejected: unnecessary dependency for simple webhook posting

### Implementation Notes
```python
# Example Block Kit structure
{
    "blocks": [
        {"type": "header", "text": {"type": "plain_text", "text": "🤢 Rotten PRs"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": "*PR Title* by @author\n:clock: 14 days old"}},
        {"type": "divider"},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": "Total: 5 PRs"}]}
    ]
}
```

---

## 2. Korean Language Support

### Decision
Use **inline conditional expressions** for language-specific strings with language selection via `LANGUAGE` environment variable.

### Rationale
- **Maximum Simplicity**: Direct if/else is simpler than dict lookup abstraction for just 2 languages
- **Zero Dependencies**: No additional packages (gettext, babel, etc.)
- **Zero Abstractions**: No translation keys, no helper methods, no unnecessary indirection
- **Cultural Fit**: Allows Korean translations to use witty, informal tone appropriate for team culture
- **Readable**: Strings appear directly in context where they're used
- **Constitution Aligned**: Follows "Simplicity First" principle - no unnecessary abstractions

### Technical Specifications
- **Language Codes**: `en` (English), `ko` (Korean), default to `en`
- **Configuration**: `LANGUAGE` env var in `.env`, validated at startup
- **String Pattern**:
  ```python
  # Category headers
  rotten_header = "🤢 PR 부패 중..." if self.language == 'ko' else "🤢 Rotten PRs"
  aging_header = "🧀 PR 숙성 중..." if self.language == 'ko' else "🧀 Aging PRs"
  fresh_header = "✨ 갓 태어난 PR" if self.language == 'ko' else "✨ Fresh PRs"

  # Dynamic strings with f-strings
  age_text = f"{days}일 묵음" if self.language == 'ko' else f"{days} days old"
  review_text = f"리뷰 {count}개 대기중" if self.language == 'ko' else f"{count} reviews pending"
  truncation = f"⚠️ +{count}개 더 있음" if self.language == 'ko' else f"⚠️ +{count} more PRs"
  ```

- **String Inventory** (complete list):
  1. Category headers: Rotten, Aging, Fresh (3 strings)
  2. Age expressions: days/weeks old (2 strings)
  3. Review count: pending reviews (1 string)
  4. Truncation warning (1 string)
  5. Empty state: "No PRs" (1 string)
  **Total: ~10 strings** - too few to justify abstraction layer

- **Witty Korean Phrases**:
  - Rotten: "PR 부패 중..." (PR rotting... - ongoing decay, slightly dramatic)
  - Aging: "PR 숙성 중..." (PR aging... - like wine/cheese, positive spin)
  - Fresh: "갓 태어난 PR" (freshly born PR - warm, welcoming)

### Korean-Specific Considerations
1. **No Pluralization**: Korean doesn't have plural forms (e.g., "PR 1개" vs "PR 5개" uses same structure)
2. **Particle Handling**: Avoid grammatical particles (은/는/이/가) that require complex logic
3. **Technical Terms**: Keep English for "PR", "review", "branch" (standard in Korean dev teams)
4. **Emoji Compatibility**: All emojis (🤢🧀✨) render correctly in Korean Slack clients

### Alternatives Considered
1. **Translation dictionary** - Rejected: unnecessary abstraction for 10 strings, violates simplicity principle
2. **GNU gettext** - Rejected: overkill for 2 languages, requires .po/.mo files
3. **External JSON translation files** - Rejected: adds file I/O overhead, complicates deployment

### Implementation Notes
```python
# In config.py
LANGUAGE = os.getenv('LANGUAGE', 'en')
if LANGUAGE not in ['en', 'ko']:
    raise ValueError(f"Unsupported language: {LANGUAGE}")

# In slack_client.py (example usage)
def _format_category_header(self, category: str) -> dict:
    if category == 'rotten':
        text = "🤢 PR 부패 중..." if self.language == 'ko' else "🤢 Rotten PRs"
    elif category == 'aging':
        text = "🧀 PR 숙성 중..." if self.language == 'ko' else "🧀 Aging PRs"
    else:  # fresh
        text = "✨ 갓 태어난 PR" if self.language == 'ko' else "✨ Fresh PRs"

    return {"type": "header", "text": {"type": "plain_text", "text": text}}
```

---

## 3. Message Truncation Strategy

### Decision
Implement **per-category soft limit of 50 PRs** with graceful truncation and "X more PRs" indicator.

### Rationale
- **Readability**: 50 PRs per category fits comfortably within Slack's UX without overwhelming users
- **Size Safety**: Even with max 50 PRs × 3 categories = 150 PRs, Block Kit stays under 50-block limit (3-4 blocks per category section)
- **User Feedback**: Shows truncated count so users know there are more PRs to check on GitHub
- **Performance**: Avoids serializing hundreds of PR blocks unnecessarily

### Technical Specifications
- **Soft Limit**: 50 PRs per category (Rotten, Aging, Fresh)
- **Truncation Message**: Append context block: "⚠️ +X more PRs not shown. Check GitHub for full list."
- **Block Count Calculation**:
  - 1 header block per category
  - 1 section block per PR (title, author, age, reviews)
  - 1 divider between categories
  - 1 context block for truncation warning (if needed)
  - Total worst case: (1 header + 50 sections + 1 truncation) × 3 categories + 2 dividers = ~156 blocks
  - **Adjustment**: Reduce limit to 15 PRs per category to stay under 50 blocks total → (1 + 15 + 1) × 3 + 2 = 53 blocks
- **Final Safe Limit**: **15 PRs per category** (45 PRs total max displayed)

### Alternatives Considered
1. **No truncation** - Rejected: risk of hitting message size limits with large backlogs
2. **Pagination with buttons** - Rejected: requires response URLs and state management (out of scope)
3. **Dynamic truncation based on text length** - Rejected: too complex, 15 PR limit is simpler

### Implementation Notes
```python
def _format_category_blocks(self, prs: List[PR], category: str) -> List[dict]:
    blocks = [{"type": "header", "text": {"type": "plain_text", "text": self._translate(f'category_{category}')}}]

    displayed_prs = prs[:15]  # Truncate to 15
    for pr in displayed_prs:
        blocks.append(self._format_pr_section(pr))

    if len(prs) > 15:
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": self._translate('truncation_warning', count=len(prs) - 15)}]
        })

    return blocks
```

---

## 4. Testing Strategy

### Decision
Use **pytest with mocked Slack webhooks** and **real Block Kit JSON validation**.

### Rationale
- **Existing Infrastructure**: Project already uses pytest, pytest-mock, pytest-cov
- **External Service Isolation**: Mocking webhooks prevents actual Slack API calls during CI
- **Block Kit Validation**: Test actual JSON structure to catch formatting errors
- **Korean Encoding**: Validate UTF-8 encoding in test assertions
- **Fast Feedback**: Unit tests run in <1s without network I/O

### Technical Specifications
- **Test Pyramid**:
  - **Unit Tests**: Translation lookup, Block Kit block generation, truncation logic
  - **Integration Tests**: Full message formatting with mocked webhook POST
  - **No E2E Tests**: Manual verification in Slack workspace (one-time visual QA)

- **Mock Strategy**:
  ```python
  @pytest.fixture
  def mock_webhook(mocker):
      return mocker.patch('requests.post', return_value=MockResponse(200, 'ok'))

  def test_block_kit_message(mock_webhook):
      client = SlackClient(language='en')
      client.post_stale_pr_summary(prs_by_category)

      call_args = mock_webhook.call_args
      payload = json.loads(call_args[1]['data'])

      assert 'blocks' in payload
      assert payload['blocks'][0]['type'] == 'header'
      assert '🤢' in payload['blocks'][0]['text']['text']
  ```

- **Korean Test Cases**:
  - Verify Korean characters don't get mangled (UTF-8 encoding)
  - Check witty phrases appear in correct contexts
  - Validate mrkdwn formatting works with Korean text

- **Block Kit Validation**:
  - Assert block types (`header`, `section`, `divider`, `context`)
  - Check text field structure (`plain_text` vs `mrkdwn`)
  - Verify block count stays under 50
  - Test truncation message appears when limit exceeded

### Alternatives Considered
1. **Slack API SDK testing tools** - Rejected: no official Python testing tools for Block Kit
2. **VCR cassette recording** - Rejected: requires initial real API call, complicates setup
3. **Schema validation library** - Rejected: overkill, manual assertions are sufficient

### Implementation Notes
```python
# tests/integration/test_slack_client.py
class TestBlockKitFormatting:
    def test_rotten_category_header(self, mock_webhook):
        # Test header block generation

    def test_pr_section_formatting(self, mock_webhook):
        # Test PR detail blocks

    def test_truncation_at_15_prs(self, mock_webhook):
        # Test truncation warning appears

    def test_korean_translation(self, mock_webhook):
        # Test Korean text in blocks
```

---

## 5. Performance & Size Management

### Decision
**Pre-calculate block counts** and apply hard 15 PR/category limit before serialization.

### Rationale
- **Predictable Size**: 15 PR limit guarantees <50 blocks, <50KB payload
- **No Retry Logic**: Avoids complexity of try-catch-truncate-retry pattern
- **Fast Execution**: No JSON size measurement needed, simple list slicing
- **User Feedback**: Truncation message explains why some PRs aren't shown

### Technical Specifications
- Block count formula: `(1 header + N sections + 1 truncation) × 3 categories + 2 dividers`
- With N=15: `(1 + 15 + 1) × 3 + 2 = 53 blocks` (within 50-block limit with small buffer)
- Payload size estimate: ~50 bytes/block × 53 blocks = ~2.7KB (well within limits)

### Alternatives Considered
1. **Dynamic size calculation** - Rejected: premature optimization
2. **Compression** - Rejected: Slack webhook doesn't support gzip
3. **Split into multiple messages** - Rejected: loses unified view, complicates code

---

## 6. Error Handling

### Decision
**Preserve existing webhook error handling**; add language config validation at startup.

### Rationale
- **Already Robust**: Existing code handles webhook failures (FR-019 in spec)
- **Fail Fast**: Invalid language config should error immediately at app startup
- **Block Kit Errors**: Slack API validates Block Kit JSON and returns 400 errors (existing error handling applies)

### Technical Specifications
- **Startup Validation**:
  ```python
  # In config.py
  SUPPORTED_LANGUAGES = ['en', 'ko']
  LANGUAGE = os.getenv('LANGUAGE', 'en')
  if LANGUAGE not in SUPPORTED_LANGUAGES:
      raise ValueError(f"Invalid LANGUAGE={LANGUAGE}. Must be one of: {SUPPORTED_LANGUAGES}")
  ```
- **Webhook Errors**: Existing try-except in slack_client.py catches and logs failures
- **Malformed Block Kit**: Slack returns 400 with validation error → logged, re-raised (no silent failures)

### No New Error Handling
- No new try-except blocks needed
- Language lookup errors prevented by startup validation
- Block Kit errors surface through existing webhook error path

---

## Summary

All Phase 0 research complete. Key decisions:

| Area | Decision | Rationale |
|------|----------|-----------|
| **Slack Formatting** | Block Kit (sections, dividers, context) | Native UI, mobile-friendly, no deps |
| **Translations** | Dict-based with f-strings | Simple, zero deps, maintainable |
| **Truncation** | 15 PRs per category (45 total) | Stays under 50-block limit, predictable |
| **Testing** | Pytest with mocked webhooks | Fast, existing infra, Block Kit JSON validation |
| **Language Config** | LANGUAGE env var (en/ko) | Simple, validated at startup |

**Ready for Phase 1**: Design artifacts (data model, contracts, quickstart)
