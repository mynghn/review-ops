# Quickstart: Table View UI Implementation

**Feature**: Table View UI for Stale PR Board
**Date**: 2025-11-10
**Target Audience**: Developers implementing the table view feature

## Overview

This guide helps you implement the table view UI in `SlackClient` by replacing the current category-based Block Kit format with a single sorted table. The implementation follows a Test-Driven Development (TDD) approach.

---

## Prerequisites

Before starting:

- [x] Read [research.md](./research.md) for technical background
- [x] Review [data-model.md](./data-model.md) for structure definitions
- [x] Examine [contracts/](./contracts/) for expected output format
- [x] Understand existing `SlackClient` code in [src/slack_client.py](../../../src/slack_client.py)

---

## Implementation Roadmap

### Phase 0: Setup (15 minutes)

1. **Create feature branch** (if not already on it):
   ```bash
   git checkout 004-table-view-ui
   ```

2. **Review current implementation**:
   - Open [src/slack_client.py:242-290](../../../src/slack_client.py#L242-L290)
   - Identify `build_blocks()` method (this will be replaced)
   - Note existing bilingual support pattern in `_build_header_block()` and other methods

3. **Set up test file**:
   ```bash
   # Create new test file for table view tests
   touch tests/unit/test_slack_table_view.py
   ```

### Phase 1: Test-Driven Development (2 hours)

**Step 1.1: Write Header Row Test** (15 min)

Create test for table header generation:

```python
# tests/unit/test_slack_table_view.py
import pytest
from slack_client import SlackClient
from models import StalePR, PullRequest, TeamMember

def test_table_header_row_english():
    """Test table header row has correct English column labels."""
    client = SlackClient(webhook_url="mock", language="en", max_prs_total=30)

    # Build empty table (just header)
    blocks = client.build_blocks({"rotten": [], "aging": [], "fresh": []}, [])

    # Extract table block
    table_block = next(b for b in blocks if b["type"] == "table")
    header_row = table_block["rows"][0]

    # Assert header cells
    assert len(header_row) == 4
    assert header_row[0]["elements"][0]["elements"][0]["text"] == "Staleness"
    assert header_row[1]["elements"][0]["elements"][0]["text"] == "Age"
    assert header_row[2]["elements"][0]["elements"][0]["text"] == "PR"
    assert header_row[3]["elements"][0]["elements"][0]["text"] == "Reviewers"

    # Assert bold styling
    for cell in header_row:
        assert cell["elements"][0]["elements"][0].get("style", {}).get("bold") is True

def test_table_header_row_korean():
    """Test table header row has correct Korean column labels."""
    client = SlackClient(webhook_url="mock", language="ko", max_prs_total=30)

    blocks = client.build_blocks({"rotten": [], "aging": [], "fresh": []}, [])
    table_block = next(b for b in blocks if b["type"] == "table")
    header_row = table_block["rows"][0]

    assert header_row[0]["elements"][0]["elements"][0]["text"] == "신선도"
    assert header_row[1]["elements"][0]["elements"][0]["text"] == "경과"
    assert header_row[2]["elements"][0]["elements"][0]["text"] == "PR"
    assert header_row[3]["elements"][0]["elements"][0]["text"] == "리뷰어"
```

**Run tests (should fail)**:
```bash
uv run pytest tests/unit/test_slack_table_view.py -v
```

**Step 1.2: Implement Header Row Generation** (30 min)

Add new method to `SlackClient`:

```python
# src/slack_client.py

def _build_table_header_row(self) -> list[dict]:
    """
    Build table header row with bilingual column labels.

    Returns:
        List of 4 rich_text cells with bold column headers
    """
    headers = {
        "en": ["Staleness", "Age", "PR", "Reviewers"],
        "ko": ["신선도", "경과", "PR", "리뷰어"]
    }

    header_texts = headers[self.language]

    return [
        {
            "type": "rich_text",
            "elements": [
                {
                    "type": "rich_text_section",
                    "elements": [
                        {
                            "type": "text",
                            "text": text,
                            "style": {"bold": True}
                        }
                    ]
                }
            ]
        }
        for text in header_texts
    ]
```

**Run tests (should pass)**:
```bash
uv run pytest tests/unit/test_slack_table_view.py::test_table_header_row_english -v
uv run pytest tests/unit/test_slack_table_view.py::test_table_header_row_korean -v
```

**Step 1.3: Write Data Row Tests** (30 min)

Add tests for PR data rows:

```python
def test_table_data_row_structure():
    """Test data row has correct cell structure for a single PR."""
    client = SlackClient(webhook_url="mock", language="en", max_prs_total=30)

    # Create mock PR
    pr = PullRequest(
        repo_name="test-repo",
        number=123,
        title="Test PR Title",
        url="https://github.com/org/repo/pull/123",
        author="author1",
        reviewers=["reviewer1", "reviewer2"],
        review_status=None,
        current_approvals=0,
        created_at="2025-01-01T00:00:00Z"
    )
    stale_pr = StalePR(pr=pr, staleness_days=12.0, category="rotten")

    team_members = [
        TeamMember(github_username="reviewer1", slack_user_id="U12345"),
        TeamMember(github_username="reviewer2", slack_user_id="U67890")
    ]

    blocks = client.build_blocks({"rotten": [stale_pr], "aging": [], "fresh": []}, team_members)
    table_block = next(b for b in blocks if b["type"] == "table")
    data_row = table_block["rows"][1]  # First data row after header

    # Column 1: Staleness emoji
    assert data_row[0]["elements"][0]["elements"][0]["type"] == "emoji"
    assert data_row[0]["elements"][0]["elements"][0]["name"] == "nauseated_face"

    # Column 2: Age
    assert data_row[1]["elements"][0]["elements"][0]["type"] == "text"
    assert data_row[1]["elements"][0]["elements"][0]["text"] == "12d"

    # Column 3: PR details (repo#number + link)
    pr_cell_elements = data_row[2]["elements"][0]["elements"]
    assert pr_cell_elements[0]["type"] == "text"
    assert pr_cell_elements[0]["text"] == "test-repo#123\n"
    assert pr_cell_elements[1]["type"] == "link"
    assert pr_cell_elements[1]["text"] == "Test PR Title"
    assert pr_cell_elements[1]["url"] == "https://github.com/org/repo/pull/123"

    # Column 4: Reviewers (user mentions separated by newlines)
    reviewer_cell_elements = data_row[3]["elements"][0]["elements"]
    assert reviewer_cell_elements[0]["type"] == "user"
    assert reviewer_cell_elements[0]["user_id"] == "U12345"
    assert reviewer_cell_elements[1]["type"] == "text"
    assert reviewer_cell_elements[1]["text"] == "\n"
    assert reviewer_cell_elements[2]["type"] == "user"
    assert reviewer_cell_elements[2]["user_id"] == "U67890"

def test_table_no_reviewers():
    """Test data row displays dash when PR has no reviewers."""
    client = SlackClient(webhook_url="mock", language="en", max_prs_total=30)

    pr = PullRequest(
        repo_name="test-repo", number=123, title="Test PR",
        url="https://github.com/org/repo/pull/123",
        author="author1", reviewers=[],  # No reviewers
        review_status=None, current_approvals=0,
        created_at="2025-01-01T00:00:00Z"
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0, category="aging")

    blocks = client.build_blocks({"rotten": [], "aging": [stale_pr], "fresh": []}, [])
    table_block = next(b for b in blocks if b["type"] == "table")
    data_row = table_block["rows"][1]

    # Reviewers column should have single dash
    reviewer_cell = data_row[3]["elements"][0]["elements"]
    assert len(reviewer_cell) == 1
    assert reviewer_cell[0]["type"] == "text"
    assert reviewer_cell[0]["text"] == "-"
```

**Run tests (should fail)**:
```bash
uv run pytest tests/unit/test_slack_table_view.py -v
```

**Step 1.4: Implement Data Row Generation** (45 min)

Add helper methods to `SlackClient`:

```python
# src/slack_client.py

def _build_table_data_row(self, stale_pr: StalePR, team_members: list[TeamMember]) -> list[dict]:
    """
    Build table data row for a single PR.

    Args:
        stale_pr: The stale PR to format
        team_members: List of team members for Slack user ID mapping

    Returns:
        List of 4 rich_text cells representing one table row
    """
    pr = stale_pr.pr

    # Column 1: Staleness emoji
    emoji_name = self._get_staleness_emoji(stale_pr.category)
    col_staleness = self._build_rich_text_cell([{"type": "emoji", "name": emoji_name}])

    # Column 2: Age
    age_text = f"{int(stale_pr.staleness_days)}d"
    col_age = self._build_rich_text_cell([{"type": "text", "text": age_text}])

    # Column 3: PR details
    pr_elements = [
        {"type": "text", "text": f"{pr.repo_name}#{pr.number}\n"},
        {"type": "link", "text": pr.title, "url": pr.url}
    ]
    col_pr = self._build_rich_text_cell(pr_elements)

    # Column 4: Reviewers
    reviewer_elements = self._build_reviewer_elements(pr.reviewers, team_members)
    col_reviewers = self._build_rich_text_cell(reviewer_elements)

    return [col_staleness, col_age, col_pr, col_reviewers]

def _get_staleness_emoji(self, category: str) -> str:
    """Map category to Slack emoji name."""
    emoji_map = {
        "rotten": "nauseated_face",
        "aging": "cheese_wedge",
        "fresh": "sparkles"
    }
    return emoji_map[category]

def _build_rich_text_cell(self, elements: list[dict]) -> dict:
    """Wrap elements in rich_text cell structure."""
    return {
        "type": "rich_text",
        "elements": [
            {
                "type": "rich_text_section",
                "elements": elements
            }
        ]
    }

def _build_reviewer_elements(self, reviewers: list[str], team_members: list[TeamMember]) -> list[dict]:
    """
    Build reviewer elements with user mentions separated by newlines.

    Args:
        reviewers: List of GitHub usernames
        team_members: List of team members for Slack user ID mapping

    Returns:
        List of elements (user mentions + newlines, or single dash if empty)
    """
    if not reviewers:
        return [{"type": "text", "text": "-"}]

    username_to_slack_id = {
        member.github_username: member.slack_user_id
        for member in team_members
        if member.slack_user_id
    }

    elements = []
    for i, reviewer in enumerate(reviewers):
        slack_id = username_to_slack_id.get(reviewer)
        if slack_id:
            elements.append({"type": "user", "user_id": slack_id})
        else:
            # Fallback to @username if no Slack ID
            elements.append({"type": "text", "text": f"@{reviewer}"})

        # Add newline between reviewers (but not after the last one)
        if i < len(reviewers) - 1:
            elements.append({"type": "text", "text": "\n"})

    return elements
```

**Run tests (should pass)**:
```bash
uv run pytest tests/unit/test_slack_table_view.py -v
```

### Phase 2: Replace build_blocks() (1 hour)

**Step 2.1: Write Integration Test** (15 min)

```python
def test_build_blocks_table_format():
    """Test build_blocks returns table format instead of category sections."""
    client = SlackClient(webhook_url="mock", language="en", max_prs_total=30)

    # Create PRs across all categories
    pr1 = create_stale_pr(days=12, category="rotten", repo="repo1", number=1)
    pr2 = create_stale_pr(days=5, category="aging", repo="repo2", number=2)
    pr3 = create_stale_pr(days=2, category="fresh", repo="repo3", number=3)

    by_category = {
        "rotten": [pr1],
        "aging": [pr2],
        "fresh": [pr3]
    }

    blocks = client.build_blocks(by_category, [])

    # Should have: header block + table block
    assert len(blocks) == 2
    assert blocks[0]["type"] == "header"
    assert blocks[1]["type"] == "table"

    # Table should have 4 rows (1 header + 3 data)
    table_rows = blocks[1]["rows"]
    assert len(table_rows) == 4

    # Table should have correct column settings
    assert blocks[1]["column_settings"] == [
        {"align": "center"},
        {"align": "center"},
        {"align": "left"},
        {"align": "left"}
    ]

    # Data rows should be sorted by staleness descending (stalest first)
    # Row 1: 12d (rotten), Row 2: 5d (aging), Row 3: 2d (fresh)
    assert table_rows[1][1]["elements"][0]["elements"][0]["text"] == "12d"
    assert table_rows[2][1]["elements"][0]["elements"][0]["text"] == "5d"
    assert table_rows[3][1]["elements"][0]["elements"][0]["text"] == "2d"
```

**Step 2.2: Rewrite build_blocks()** (30 min)

Replace the existing `build_blocks()` method:

```python
# src/slack_client.py

def build_blocks(
    self, by_category: dict[str, list[StalePR]], team_members: list[TeamMember]
) -> list[dict]:
    """
    Construct Block Kit blocks with table format.

    Args:
        by_category: Dictionary mapping category names to lists of StalePRs
        team_members: List of team members for @mentions

    Returns:
        List of Block Kit block dictionaries ready for Slack API
    """
    # Flatten and sort all PRs by staleness descending
    all_prs = []
    for category in ["rotten", "aging", "fresh"]:
        all_prs.extend(by_category.get(category, []))

    all_prs.sort(key=lambda pr: pr.staleness_days, reverse=True)

    # Handle empty state
    if not all_prs:
        return self._build_empty_state_blocks()

    # Truncate to display limit
    display_limit = min(self.max_prs_total, 99)  # Cap at 99 (100 - 1 header row)
    displayed_prs = all_prs[:display_limit]
    truncated_count = len(all_prs) - len(displayed_prs)

    # Build blocks
    blocks = []

    # Add header block
    blocks.append(self._build_board_header_block())

    # Build table block
    table_rows = [self._build_table_header_row()]
    for stale_pr in displayed_prs:
        table_rows.append(self._build_table_data_row(stale_pr, team_members))

    table_block = {
        "type": "table",
        "column_settings": [
            {"align": "center"},  # Staleness
            {"align": "center"},  # Age
            {"align": "left"},    # PR
            {"align": "left"}     # Reviewers
        ],
        "rows": table_rows
    }
    blocks.append(table_block)

    # Add truncation warning if needed
    if truncated_count > 0:
        blocks.append(self._build_truncation_warning(truncated_count))

    return blocks

def _build_board_header_block(self) -> dict:
    """Build header block with board title."""
    today = date.today().isoformat()
    titles = {
        "en": f":help: {today} Stale PR Board",
        "ko": f":help: {today} 리뷰가 필요한 PR들"
    }
    return {
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": titles[self.language],
            "emoji": True
        }
    }
```

**Step 2.3: Update Empty State** (15 min)

Update `_build_empty_state_blocks()` to match new format:

```python
def _build_empty_state_blocks(self) -> list[dict]:
    """
    Create "all clear" Block Kit message when no PRs exist.

    Returns:
        List of blocks for empty state message
    """
    messages = {
        "en": "🎉 All clear! No PRs need review",
        "ko": "🎉 리뷰 대기 중인 PR이 없습니다"
    }

    return [
        self._build_board_header_block(),
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": messages[self.language]
            }
        }
    ]
```

**Run all tests**:
```bash
uv run pytest tests/unit/test_slack_table_view.py -v
```

### Phase 3: Update Existing Tests (30 min)

1. **Run existing test suite**:
   ```bash
   uv run pytest tests/ -v
   ```

2. **Update failing tests**:
   - Find tests that expect old category-based format
   - Update assertions to expect table format
   - Update test fixtures if needed

3. **Add edge case tests**:
   - Test with 0 PRs (empty state)
   - Test with 1 PR (minimal table)
   - Test with 100+ PRs (truncation)
   - Test with missing Slack IDs (fallback to @username)

### Phase 4: Manual Testing (30 min)

1. **Test with dry-run mode**:
   ```bash
   uv run python src/app.py --dry-run
   ```

2. **Verify output**:
   - Check table structure matches contract examples
   - Verify bilingual support (set `LANGUAGE=ko`)
   - Verify sorting (stalest PRs first)
   - Verify truncation warning appears when needed

3. **Test with real Slack**:
   ```bash
   # Remove --dry-run flag
   uv run python src/app.py
   ```
   - Check message rendering in Slack desktop
   - Check message rendering in Slack mobile
   - Verify emojis display correctly
   - Verify links are clickable
   - Verify user mentions work

---

## Troubleshooting

### Issue: Tests fail with "KeyError: 'table'"

**Cause**: `build_blocks()` is not returning a table block

**Solution**: Verify `build_blocks()` adds the table block to the returned list

### Issue: Slack API returns "invalid_blocks" error

**Cause**: Table structure doesn't match Slack Block Kit specification

**Solution**:
1. Validate against [contract examples](./contracts/)
2. Use Slack Block Kit Builder: https://app.slack.com/block-kit-builder
3. Check for missing required fields in rich_text cells

### Issue: User mentions don't work

**Cause**: Slack user IDs not in `team_members.json`

**Solution**:
1. Check `team_members.json` has correct Slack user IDs
2. Verify fallback to `@username` works when Slack ID missing

### Issue: Korean translation not showing

**Cause**: `LANGUAGE` environment variable not set

**Solution**:
```bash
export LANGUAGE=ko
uv run python src/app.py --dry-run
```

---

## Checklist

Before marking the feature complete:

- [ ] All unit tests pass (`pytest tests/unit/`)
- [ ] All integration tests pass (`pytest tests/integration/`)
- [ ] Code coverage ≥73% (existing baseline)
- [ ] Dry-run output matches contract examples
- [ ] Bilingual support works (EN and KO)
- [ ] Empty state displays correctly
- [ ] Truncation warning appears when >30 PRs
- [ ] Manual testing in Slack successful (desktop + mobile)
- [ ] No performance degradation (<1s for 30 PRs)
- [ ] Documentation updated (CLAUDE.md)

---

## Next Steps

After implementation:
1. Run `/speckit.tasks` to generate task breakdown
2. Execute tasks using `/speckit.implement`
3. Create PR with changes
4. Request code review

---

## Resources

- [Slack Block Kit API Docs](https://api.slack.com/reference/block-kit/blocks#table)
- [Research Findings](./research.md)
- [Data Model](./data-model.md)
- [Contract Examples](./contracts/)
- [Feature Spec](./spec.md)
