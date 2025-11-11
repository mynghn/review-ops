# Data Model: Too Old PRs Reporting

**Date**: 2025-11-11
**Branch**: 007-old-pr-reporting

## Overview

This document defines the data models required for "too old PR" reporting functionality. The feature introduces minimal new entities while leveraging existing models.

## New Entities

### OldPRReport

Represents a team member with old PRs requiring attention.

**Fields**:
- `github_username: str` - GitHub username of the team member
- `pr_count: int` - Number of old PRs for this team member
- `github_search_url: str` - Pre-generated GitHub search URL to view old PRs

**Validation Rules**:
- `github_username`: Must be non-empty string, matching existing TeamMember username
- `pr_count`: Must be positive integer (> 0)
- `github_search_url`: Must be valid URL starting with `https://github.com/pulls?q=`

**Usage**:
- Created during old PR search phase
- Passed to Slack client for thread message formatting
- Sorted by pr_count (descending) before display

**Lifecycle**:
1. App fetches old PRs from GitHub
2. Groups by team member and counts
3. Generates GitHub search URLs
4. Creates OldPRReport instances (only for members with count > 0)
5. Passes to Slack client for thread posting
6. Discarded after thread posted (stateless, no persistence)

**Example**:
```python
@dataclass
class OldPRReport:
    github_username: str
    pr_count: int
    github_search_url: str
```

---

## Modified Entities

### Config (models.py)

**Changes**:
- **ADD**: `slack_bot_token: str` - Slack Bot User OAuth Token for chat.postMessage API
- **ADD**: `slack_channel_id: str` - Target Slack channel ID for posting messages
- **REMOVE**: `slack_webhook_url: str` - No longer needed (replaced by bot token)

**Rationale**: Research shows incoming webhooks can't return message timestamps. Migration to chat.postMessage API requires bot token and explicit channel ID.

**Validation Rules** (config.py):
- `slack_bot_token`: Must start with `xoxb-` (bot token prefix)
- `slack_channel_id`: Must start with `C` (public channel) or `G` (private channel)

**Environment Variables**:
- `SLACK_BOT_TOKEN` - Bot User OAuth Token (replace SLACK_WEBHOOK_URL)
- `SLACK_CHANNEL_ID` - Target channel ID for posting

**Backward Compatibility**: Breaking change - existing users must update .env configuration.

**Migration Path**:
1. Create Slack App in workspace
2. Enable chat:write permission
3. Install app to workspace
4. Copy Bot User OAuth Token (starts with xoxb-)
5. Get channel ID from Slack (right-click channel → View channel details)
6. Update .env file with new variables

**Example**:
```python
@dataclass
class Config:
    # ... existing fields ...
    slack_bot_token: str  # NEW
    slack_channel_id: str  # NEW
    # slack_webhook_url removed
```

---

### SlackClient (slack_client.py)

**Changes**:
- **MODIFY**: `__init__()` - Accept `bot_token` and `channel_id` instead of `webhook_url`
- **MODIFY**: `post_stale_pr_summary()` - Return message timestamp (ts) for threading
- **ADD**: `post_thread_reply()` - New method to post thread replies using parent ts

**Updated Constructor**:
```python
def __init__(
    self,
    bot_token: str,
    channel_id: str,
    language: str = "en",
    max_prs_total: int = 30,
    show_non_team_reviewers: bool = True,
) -> None:
    """Initialize Slack client with bot token and channel ID."""
    from slack_sdk import WebClient
    self.client = WebClient(token=bot_token)
    self.channel_id = channel_id
    # ... rest unchanged ...
```

**New Return Type**:
```python
def post_stale_pr_summary(
    self, stale_prs: list[StalePR], team_members: list[TeamMember]
) -> str:
    """
    Post Block Kit formatted stale PR summary to Slack.

    Returns:
        Message timestamp (ts) for threading
    """
```

**New Method**:
```python
def post_thread_reply(
    self,
    thread_ts: str,
    old_pr_reports: list[OldPRReport],
    team_members: list[TeamMember],
) -> None:
    """
    Post old PR report as thread reply.

    Args:
        thread_ts: Parent message timestamp to reply to
        old_pr_reports: List of team members with old PRs
        team_members: Team member list for Slack mentions
    """
```

---

## Unchanged Entities

The following entities remain unchanged:

- **TeamMember** - No changes needed
- **PullRequest** - No changes needed
- **StalePR** - No changes needed
- **RateLimitStatus** - No changes needed
- **APICallMetrics** - No changes needed
- **GitHubTeamReviewRequest** - No changes needed

---

## Data Flow

### Main Board Posting (Existing, Modified)
```
app.py:
  1. Fetch PRs (filtered by updated >= threshold)
  2. Calculate staleness
  3. Group by category
     ↓
slack_client.post_stale_pr_summary():
  4. Build Block Kit blocks
  5. Post via chat.postMessage
  6. Return message timestamp (ts)
     ↓
app.py:
  7. Store ts for thread posting
```

### Thread Reply Posting (New)
```
app.py:
  1. Fetch old PRs (filtered by updated < threshold)
  2. Group by team member
  3. Count PRs per member
  4. Generate GitHub search URLs
  5. Create OldPRReport instances (only count > 0)
     ↓
slack_client.post_thread_reply():
  6. Format thread message (bilingual)
  7. Post via chat.postMessage with thread_ts
```

---

## State Transitions

### OldPRReport Lifecycle

```
[Nonexistent]
    ↓ (old PRs found for team member)
[Created with count, URL]
    ↓ (passed to Slack client)
[Formatted to Slack message]
    ↓ (thread posted successfully)
[Discarded] (no persistence)
```

**Terminal States**:
- Posted successfully (normal flow)
- Error during posting (exception raised, logged)

---

## Relationships

```
Config
  ├── slack_bot_token (used by SlackClient)
  ├── slack_channel_id (used by SlackClient)
  └── gh_search_window_size (determines threshold)

OldPRReport
  ├── github_username (FK to TeamMember.github_username)
  └── github_search_url (generated URL)

SlackClient
  ├── posts main board → returns ts
  └── posts thread reply (uses ts)

TeamMember
  └── referenced by OldPRReport
```

---

## Validation Summary

| Entity | Field | Validation |
|--------|-------|------------|
| OldPRReport | github_username | Non-empty string, exists in team_members |
| OldPRReport | pr_count | Positive integer (> 0) |
| OldPRReport | github_search_url | Valid URL, starts with https://github.com/pulls |
| Config | slack_bot_token | Starts with "xoxb-" |
| Config | slack_channel_id | Starts with "C" or "G" |

---

## Migration Impact

**Breaking Changes**:
- Config model changes (add bot_token/channel_id, remove webhook_url)
- SlackClient constructor signature change
- post_stale_pr_summary() now returns timestamp

**Migration Steps**:
1. Update Config dataclass in models.py
2. Update config.py validation
3. Update SlackClient in slack_client.py (add slack-sdk dependency)
4. Update app.py to handle timestamp return
5. Update tests to use bot_token/channel_id
6. Update documentation (README, .env.example)

**Rollback Strategy**:
- Keep webhook_url support as optional fallback (if bot_token not provided)
- Log deprecation warning for webhook_url usage
- Remove webhook_url in future release (v2.0)
