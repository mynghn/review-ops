# Quickstart: Too Old PRs Reporting

**Date**: 2025-11-11
**Branch**: 007-old-pr-reporting
**Time to Complete**: ~10 minutes

## Overview

This quickstart guide helps you set up "too old PR" reporting functionality. The feature adds thread replies to the Stale PR Board when team members have review-requested PRs older than the configured threshold.

**What's New**:
- Main board shows only recent PRs (updated within `GH_SEARCH_WINDOW_SIZE` days)
- Thread reply lists team members with old PRs
- Each team member gets a clickable GitHub search link

---

## Prerequisites

**Existing Setup** (must already be configured):
- Python 3.12+ installed
- `uv` package manager installed
- GitHub Personal Access Token (`GH_TOKEN`)
- `team_members.json` configured
- Existing Stale PR Board working

**New Requirements**:
- Slack Bot Token (replaces webhook URL)
- Slack channel ID where bot will post

---

## Step 1: Create Slack App

### 1.1 Create New App

1. Go to https://api.slack.com/apps
2. Click "Create New App"
3. Select "From scratch"
4. App Name: "Review Ops Bot" (or your preference)
5. Select your workspace
6. Click "Create App"

### 1.2 Add Bot Permissions

1. In app settings, go to "OAuth & Permissions"
2. Scroll to "Scopes" → "Bot Token Scopes"
3. Click "Add an OAuth Scope"
4. Add: `chat:write` (required to post messages)
5. Save changes

### 1.3 Install App to Workspace

1. In app settings, go to "Install App"
2. Click "Install to Workspace"
3. Review permissions and click "Allow"
4. Copy the "Bot User OAuth Token" (starts with `xoxb-`)
5. Save this token securely (you'll need it for `.env`)

### 1.4 Invite Bot to Channel

1. Open Slack app/web
2. Go to the channel where you want PR reports
3. Type: `/invite @Review Ops Bot`
4. Confirm invitation

### 1.5 Get Channel ID

1. In Slack, right-click the channel name
2. Select "View channel details"
3. Scroll down to find "Channel ID" (starts with `C` for public or `G` for private)
4. Copy this ID (you'll need it for `.env`)

---

## Step 2: Update Configuration

### 2.1 Update `.env` File

**Remove old webhook configuration**:
```bash
# Remove this line:
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

**Add new bot token configuration**:
```bash
# Slack Bot Token (from Step 1.3)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here

# Slack Channel ID (from Step 1.5)
SLACK_CHANNEL_ID=C1234567890
```

**Complete `.env` Example**:
```bash
# GitHub Configuration
GH_TOKEN=ghp_your_github_token
GITHUB_ORG=your-org-name

# Slack Configuration (NEW FORMAT)
SLACK_BOT_TOKEN=xoxb-1234567890-1234567890123-abcdefghijklmnopqrstuvwx
SLACK_CHANNEL_ID=C1234567890

# Optional: PR Age Threshold (default: 30 days)
GH_SEARCH_WINDOW_SIZE=30

# Optional: Language (default: en)
LANGUAGE=en

# Optional: Rate Limiting
MAX_PRS_TOTAL=30
RATE_LIMIT_WAIT_THRESHOLD=300

# Optional: Reviewer Display
SHOW_NON_TEAM_REVIEWERS=true

# Optional: Holiday Calendar (default: US)
HOLIDAYS_COUNTRY=US
```

### 2.2 Validate Token Format

Run quick validation:
```bash
# Check bot token starts with xoxb-
echo $SLACK_BOT_TOKEN | grep '^xoxb-' && echo "✅ Valid bot token format"

# Check channel ID starts with C or G
echo $SLACK_CHANNEL_ID | grep '^[CG]' && echo "✅ Valid channel ID format"
```

---

## Step 3: Install Dependencies

### 3.1 Add Slack SDK

```bash
# Using uv (recommended)
uv add slack-sdk

# Or using pip
pip install slack-sdk
```

### 3.2 Verify Installation

```bash
uv pip list | grep slack-sdk
# Should show: slack-sdk  3.26.0 (or later)
```

---

## Step 4: Test Configuration

### 4.1 Dry Run Test

Run the app in dry-run mode to verify configuration:

```bash
uv run python src/app.py --dry-run
```

**Expected Output**:
```
Starting Stale PR Board (DRY RUN MODE - no Slack sending)
Loaded 5 team members
Checking GitHub API rate limit...
Searching for open PRs involving team members in: your-org
Found 10 open PRs involving team members
Stale PRs found: 8

DRY RUN MODE - Block Kit JSON Payload
============================================================
{
  "blocks": [
    ...
  ]
}
============================================================

✅ Dry run completed - Block Kit JSON printed above
```

### 4.2 Verify Configuration Loaded

Check the log output for:
- ✅ No errors about missing `SLACK_BOT_TOKEN`
- ✅ No errors about missing `SLACK_CHANNEL_ID`
- ✅ No warnings about deprecated `SLACK_WEBHOOK_URL`

---

## Step 5: Run Production Test

### 5.1 First Production Run

```bash
# Run without --dry-run to post to Slack
uv run python src/app.py
```

**Expected Slack Message**:
1. Main board message appears in channel
2. If old PRs exist, thread reply appears under main message
3. Thread lists team members with old PRs
4. Each member has clickable GitHub search link

**Example Thread Message**:
```
⚠️ Too old PRs detected (updated >30 days ago):

• @alice: 3 PRs → View on GitHub
• @bob: 1 PR → View on GitHub
```

### 5.2 Verify Thread Functionality

1. Check that thread reply appears under main message (not as separate message)
2. Click GitHub links to verify they show correct PRs
3. Verify links filter by username and date threshold

---

## Step 6: Troubleshooting

### Error: "not_in_channel"

**Symptom**: `SlackApiError: not_in_channel`

**Solution**:
```bash
# Invite bot to channel
/invite @Review Ops Bot
```

### Error: "invalid_auth"

**Symptom**: `SlackApiError: invalid_auth`

**Causes**:
- Bot token expired or revoked
- Wrong token format (should start with `xoxb-`)

**Solution**:
1. Go to Slack App settings → "OAuth & Permissions"
2. Regenerate token if needed
3. Update `.env` with new token

### Error: "channel_not_found"

**Symptom**: `SlackApiError: channel_not_found`

**Causes**:
- Invalid channel ID
- Bot not installed to workspace

**Solution**:
1. Verify channel ID format (starts with `C` or `G`)
2. Reinstall bot to workspace if needed

### No Thread Reply Appears

**Possible Causes**:
- No team members have old PRs (expected behavior)
- Threshold too low (all PRs are recent)

**Solution**:
```bash
# Check logs for:
"No old PRs found - skipping thread reply"

# Adjust threshold if needed:
GH_SEARCH_WINDOW_SIZE=60  # Try 60 days
```

### Thread Appears as Separate Message

**Symptom**: Thread reply posts as new message instead of reply

**Causes**:
- Main message timestamp not captured
- Threading logic error

**Solution**:
1. Check logs for message timestamp: `"Posted main board, ts=1234567890.123456"`
2. Verify `post_stale_pr_summary()` returns timestamp
3. Verify `post_thread_reply()` uses `thread_ts` parameter

---

## Step 7: Verify Old PR Filtering

### 7.1 Test Different Thresholds

```bash
# Test with 15-day threshold
GH_SEARCH_WINDOW_SIZE=15 uv run python src/app.py --dry-run

# Test with 60-day threshold
GH_SEARCH_WINDOW_SIZE=60 uv run python src/app.py --dry-run
```

### 7.2 Verify GitHub Links

1. Copy GitHub link from thread message
2. Open in browser
3. Verify search shows:
   - Only PRs for that specific user
   - Only PRs updated before threshold date
   - Only open, non-draft, non-archived PRs

**Example Search Results**:
```
is:pr state:open review-requested:alice updated:<2024-10-15 archived:false -is:draft
```

---

## Step 8: Bilingual Testing (Optional)

If using Korean language:

```bash
# Test Korean language
LANGUAGE=ko uv run python src/app.py --dry-run
```

**Expected Korean Thread Message**:
```
⚠️ 오래된 PR 발견 (30일 이상 지남):

• @alice: 3개 → GitHub에서 보기
• @bob: 1개 → GitHub에서 보기
```

---

## Common Workflow

### Daily Usage

```bash
# Manual run (development)
uv run python src/app.py

# Cron job (production)
0 9 * * * cd /path/to/review-ops && uv run python src/app.py
```

### Adjusting Threshold

```bash
# Edit .env
GH_SEARCH_WINDOW_SIZE=45  # Change from 30 to 45 days

# Run to see effect
uv run python src/app.py --dry-run
```

---

## Migration from Webhooks

If you previously used `SLACK_WEBHOOK_URL`:

**Before** (.env):
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00/B00/XXX
```

**After** (.env):
```bash
SLACK_BOT_TOKEN=xoxb-1234567890-1234567890123-abcdefghijklmnopqrstuvwx
SLACK_CHANNEL_ID=C1234567890
```

**Benefits of Migration**:
- ✅ Thread replies now supported
- ✅ Better error messages
- ✅ More reliable posting
- ✅ Official Slack SDK

---

## Next Steps

1. ✅ Set up scheduled runs (cron job or GitHub Actions)
2. ✅ Monitor thread replies for old PRs
3. ✅ Adjust `GH_SEARCH_WINDOW_SIZE` based on team workflow
4. ✅ Use GitHub links to investigate old PRs

---

## Getting Help

**Logs**:
```bash
# Enable debug logging
LOG_LEVEL=DEBUG uv run python src/app.py --dry-run
```

**Common Issues**:
- Check `.env` file for correct token format
- Verify bot is invited to channel
- Verify bot has `chat:write` permission
- Check GitHub API rate limits

**Documentation**:
- Slack API: https://api.slack.com/methods/chat.postMessage
- GitHub Search: https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests
