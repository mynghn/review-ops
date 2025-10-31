# Slack Webhook Contract

**Feature**: Stale PR Board
**Date**: 2025-10-31
**Purpose**: Document Slack Block Kit message structure, formatting, and size constraints

This document defines the contract between the application and Slack's Incoming Webhooks API, using Block Kit for rich message formatting.

## Webhook Setup

**URL Format**: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX`

**Method**: `POST`

**Headers**:
```
Content-Type: application/json
```

**Authentication**: None (webhook URL contains authentication token)

## Message Structure

### Stale PRs Found Message

**Payload Format**:
```json
{
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "🔔 Stale PR Board",
        "emoji": true
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "<@U1234567890> <@U0987654321>\n\n*5 PRs need review:*\n🤢 Rotten (8+ days): 2\n🧀 Aging (4-7 days): 2\n✨ Fresh (1-3 days): 1"
      }
    },
    {
      "type": "divider"
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*🤢 Rotten (8+ days)*"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "🤢 *<https://github.com/org/repo/pull/123|repo#123>*\n_Fix critical bug in authentication_\nAuthor: <@U1234567890> | Reviewers: <@U0987654321>, <@UABCDEFGHIJ> | 8 days | Approvals: 0/2"
      }
    },
    {
      "type": "divider"
    },
    {
      "type": "context",
      "elements": [
        {
          "type": "mrkdwn",
          "text": "🤖 Generated at 2025-10-31 14:30:00 UTC"
        }
      ]
    }
  ]
}
```

### No Stale PRs Message (Celebratory)

**Payload Format**:
```json
{
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "🎉 All Caught Up!",
        "emoji": true
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "Great job team! All open PRs have sufficient approvals or are being actively reviewed. No stale PRs found."
      }
    },
    {
      "type": "context",
      "elements": [
        {
          "type": "mrkdwn",
          "text": "🤖 Generated at 2025-10-31 14:30:00 UTC"
        }
      ]
    }
  ]
}
```

## Block Types

### 1. Header Block

**Purpose**: Main message title

**Structure**:
```json
{
  "type": "header",
  "text": {
    "type": "plain_text",
    "text": "🔔 Stale PR Board",
    "emoji": true
  }
}
```

**Constraints**:
- `text.type` must be `plain_text` (not `mrkdwn`)
- Maximum length: 150 characters
- Use `emoji: true` to render emojis

---

### 2. Section Block

**Purpose**: Main content blocks (summary, category headers, PR rows)

**Structure with Markdown**:
```json
{
  "type": "section",
  "text": {
    "type": "mrkdwn",
    "text": "*Bold text* and _italic text_\n<https://example.com|Link>"
  }
}
```

**Markdown Formatting**:
- `*bold*` → **bold**
- `_italic_` → _italic_
- `~strike~` → ~~strike~~
- `` `code` `` → `code`
- `<url|text>` → clickable link
- `<@USER_ID>` → user mention
- `\n` → line break

**Constraints**:
- Maximum text length: 3,000 characters
- Nested formatting not supported (e.g., `*bold _italic_*` doesn't work)

---

### 3. Divider Block

**Purpose**: Visual separator between sections

**Structure**:
```json
{
  "type": "divider"
}
```

**Constraints**:
- No additional properties
- Renders as horizontal line

---

### 4. Context Block

**Purpose**: Footer or secondary information

**Structure**:
```json
{
  "type": "context",
  "elements": [
    {
      "type": "mrkdwn",
      "text": "🤖 Generated at 2025-10-31 14:30:00 UTC"
    }
  ]
}
```

**Constraints**:
- Maximum 10 elements
- Each element max 2,000 characters
- Renders in smaller, gray text

---

## Formatting Guidelines

### User Mentions

**Format**: `<@USER_ID>`

**User ID Format**: `U` + 10 alphanumeric characters (e.g., `U1234567890`)

**Finding User IDs**:
1. Slack UI: Click user profile → "..." → "Copy member ID"
2. Slack API: `users.list` or `users.lookupByEmail` endpoints
3. Configuration: Store in `team_members.json` with `slack_user_id` field

**Fallback** (if no Slack ID):
```python
def format_mention(username: str, slack_user_id: str | None) -> str:
    """Format user mention with fallback."""
    if slack_user_id:
        return f"<@{slack_user_id}>"
    else:
        return f"@{username}"  # Plain text, not clickable
```

**Example**:
```
Author: <@U1234567890>  # Renders as clickable @alice
Author: @bob            # Renders as plain text @bob
```

---

### Clickable Links

**Format**: `<URL|Link Text>`

**GitHub PR Link**:
```python
pr_link = f"<{pr.url}|{pr.repo_name}#{pr.number}>"
# Renders as: repo#123 (clickable, links to GitHub)
```

**Constraints**:
- URL must be fully qualified (include `https://`)
- Link text can include special characters
- Maximum URL length: 3,000 characters

**Example**:
```
<https://github.com/org/repo/pull/123|repo#123>
```

---

### Emojis

**Staleness Category Emojis**:
- Fresh (1-3 days): ✨ (`:sparkles:`)
- Aging (4-7 days): 🧀 (`:cheese:`)
- Rotten (8+ days): 🤢 (`:nauseated_face:`)

**Other Emojis**:
- Message header: 🔔 (`:bell:`)
- Bot indicator: 🤖 (`:robot:`)
- Celebration: 🎉 (`:tada:`)

**Usage**:
```json
{
  "type": "plain_text",
  "text": "🔔 Stale PR Board",
  "emoji": true
}
```

---

### Multi-line Text

**Line Breaks**: Use `\n` for line breaks

**Example**:
```python
text = (
    f"{emoji} *<{pr.url}|{pr.repo_name}#{pr.number}>*\n"
    f"_{pr.title}_\n"
    f"Author: {author_mention} | Reviewers: {reviewer_mentions} | "
    f"{staleness} days | Approvals: {current}/{required}"
)
```

**Renders as**:
```
🤢 repo#123
Fix critical bug
Author: @alice | Reviewers: @bob, @charlie | 8 days | Approvals: 0/2
```

---

## Size Constraints

### Message Limits

| Constraint | Limit | Notes |
|------------|-------|-------|
| **Total message size** | 40,000 characters | Entire JSON payload |
| **Blocks per message** | 50 blocks | All block types combined |
| **Text in section block** | 3,000 characters | Per `text` field |
| **Text in context element** | 2,000 characters | Per element |
| **Header text** | 150 characters | Plain text only |
| **Elements in context** | 10 elements | Per context block |

### Handling Large PR Lists

**Strategy 1: Truncation**
```python
MAX_PRS_PER_MESSAGE = 40

if len(stale_prs) > MAX_PRS_PER_MESSAGE:
    displayed_prs = stale_prs[:MAX_PRS_PER_MESSAGE]
    remaining = len(stale_prs) - MAX_PRS_PER_MESSAGE

    # Add truncation notice
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"_...and {remaining} more stale PRs_"
        }
    })
```

**Strategy 2: Multiple Messages** (future enhancement):
```python
# Split into multiple webhook calls
for batch in chunked(stale_prs, MAX_PRS_PER_MESSAGE):
    send_message(format_message(batch))
```

**MVP Approach**: Assume ≤40 stale PRs (reasonable for most teams)

---

## PR Row Format

**Template**:
```
{emoji} *<{pr_url}|{repo}#{number}>*
_{title}_
Author: {author_mention} | Reviewers: {reviewer_mentions} | {staleness} days | Approvals: {current}/{required}
```

**Example**:
```
🤢 *<https://github.com/org/repo/pull/123|repo#123>*
_Fix critical bug in authentication_
Author: <@U1234567890> | Reviewers: <@U0987654321>, <@UABCDEFGHIJ> | 8 days | Approvals: 0/2
```

**Python Implementation**:
```python
def format_pr_row(pr: StalePR, team: list[TeamMember]) -> str:
    """Format a single PR row for Slack."""
    # Format author mention
    author_mention = get_slack_mention(pr.pr.author, team)

    # Format reviewer mentions
    reviewer_mentions = ", ".join(
        get_slack_mention(reviewer, team)
        for reviewer in pr.pr.reviewers
    )

    # Format staleness (integer days for display)
    staleness_display = int(pr.staleness_days)

    return (
        f"{pr.emoji} *<{pr.pr.url}|{pr.pr.repo_name}#{pr.pr.number}>*\n"
        f"_{pr.pr.title}_\n"
        f"Author: {author_mention} | "
        f"Reviewers: {reviewer_mentions} | "
        f"{staleness_display} days | "
        f"Approvals: {pr.pr.current_approvals}/{pr.pr.required_approvals}"
    )
```

---

## Message Grouping

**Strategy**: Group by staleness category, display most stale first

**Structure**:
```
1. Header: "🔔 Stale PR Board"
2. Summary: @mentions + counts by category
3. Divider
4. Category: "🤢 Rotten (8+ days)"
5. PR rows (most stale within category first)
6. Divider
7. Category: "🧀 Aging (4-7 days)"
8. PR rows
9. Divider
10. Category: "✨ Fresh (1-3 days)"
11. PR rows
12. Context: Generation timestamp
```

**Python Implementation**:
```python
def build_message_blocks(stale_prs: list[StalePR], team: list[TeamMember]) -> list[dict]:
    """Build Slack Block Kit message blocks."""
    blocks = []

    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": "🔔 Stale PR Board",
            "emoji": True
        }
    })

    # Group by category
    by_category = defaultdict(list)
    for stale_pr in stale_prs:
        by_category[stale_pr.category].append(stale_pr)

    # Count by category
    rotten_count = len(by_category["rotten"])
    aging_count = len(by_category["aging"])
    fresh_count = len(by_category["fresh"])

    # Get unique authors for mentions
    authors = {pr.pr.author for pr in stale_prs}
    mentions = " ".join(get_slack_mention(author, team) for author in authors)

    # Summary section
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                f"{mentions}\n\n"
                f"*{len(stale_prs)} PRs need review:*\n"
                f"🤢 Rotten (8+ days): {rotten_count}\n"
                f"🧀 Aging (4-7 days): {aging_count}\n"
                f"✨ Fresh (1-3 days): {fresh_count}"
            )
        }
    })

    # Add categories in order: rotten → aging → fresh
    for category, emoji, label in [
        ("rotten", "🤢", "Rotten (8+ days)"),
        ("aging", "🧀", "Aging (4-7 days)"),
        ("fresh", "✨", "Fresh (1-3 days)")
    ]:
        prs = by_category[category]
        if not prs:
            continue

        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{emoji} {label}*"
            }
        })

        # Sort by staleness within category (most stale first)
        prs.sort(key=lambda p: p.staleness_days, reverse=True)

        for pr in prs:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": format_pr_row(pr, team)
                }
            })

    # Footer
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": f"🤖 Generated at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        }]
    })

    return blocks
```

---

## Sending Messages

**Python Implementation**:
```python
import requests
from typing import NoReturn

def send_slack_message(webhook_url: str, blocks: list[dict]) -> None:
    """Send Block Kit message to Slack webhook."""
    payload = {"blocks": blocks}

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise Exception(
            f"Slack webhook failed: {response.status_code} {response.text}"
        ) from e
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error sending to Slack: {e}") from e
```

**Response Codes**:
- `200 OK`: Message sent successfully (response body: `"ok"`)
- `400 Bad Request`: Invalid payload format
- `404 Not Found`: Invalid webhook URL
- `500 Internal Server Error`: Slack server error (retry once)

---

## Error Handling

### Invalid Webhook URL
```python
if not webhook_url.startswith("https://hooks.slack.com/"):
    raise ValueError("SLACK_WEBHOOK_URL must be a valid Slack webhook URL")
```

### Network Timeout
```python
try:
    response = requests.post(webhook_url, json=payload, timeout=10)
except requests.exceptions.Timeout:
    print("WARNING: Slack notification timed out", file=sys.stderr)
    # Continue execution (notification failed but don't crash)
```

### Invalid Payload
```python
if response.status_code == 400:
    print(f"ERROR: Invalid Slack message format: {response.text}", file=sys.stderr)
    # Log error, investigate payload structure
```

---

## Testing Strategy

**Unit Tests**: Test block generation without actual webhook calls

**Integration Tests**: Mock `requests.post` to verify payload structure

**Manual Testing**: Use real webhook URL to test in Slack channel

**Example Test**:
```python
def test_format_stale_pr_message():
    """Test Slack message formatting."""
    stale_prs = [
        StalePR(pr=sample_pr, staleness_days=8.5),
        StalePR(pr=sample_pr2, staleness_days=3.2)
    ]

    blocks = build_message_blocks(stale_prs, team)

    # Verify structure
    assert blocks[0]["type"] == "header"
    assert "🔔 Stale PR Board" in blocks[0]["text"]["text"]

    # Verify PR rows
    pr_sections = [b for b in blocks if b["type"] == "section"]
    assert len(pr_sections) >= 2  # At least summary + 2 PRs

    # Verify size constraints
    payload = json.dumps({"blocks": blocks})
    assert len(payload) < 40000, "Message exceeds size limit"
    assert len(blocks) <= 50, "Too many blocks"
```

---

## Slack Block Kit Resources

**Official Documentation**:
- Block Kit Builder: https://api.slack.com/block-kit/building
- Block Reference: https://api.slack.com/reference/block-kit/blocks
- Formatting Reference: https://api.slack.com/reference/surfaces/formatting

**Interactive Builder**:
- https://app.slack.com/block-kit-builder

**User ID Lookup**:
- https://api.slack.com/methods/users.lookupByEmail

---

## Next Steps

With this Slack webhook contract defined:
1. Implement `SlackClient` in `src/review_ops/slack_client.py`
2. Implement message formatting functions
3. Write unit tests for block generation
4. Write integration tests with mocked webhook calls
5. Manual testing with real Slack channel
