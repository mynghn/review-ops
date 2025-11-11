# Research: Too Old PRs Reporting

**Date**: 2025-11-11
**Branch**: 007-old-pr-reporting

## Overview

This document captures research findings for implementing "too old PR" reporting functionality. Three main technical areas required investigation:

1. GitHub search URL format and query parameters
2. Slack webhook threading capabilities
3. URL encoding best practices for Python

## Research Areas

### 1. GitHub Search URL Format

**Question**: What is the exact format for `https://github.com/pulls` search URLs with filters?

**Research Sources**:
- GitHub Docs: "Searching issues and pull requests"
- GitHub Docs: "Filtering and searching issues and pull requests"
- Stack Overflow: "Github: Find PRs where user is a reviewer"

**Findings**:

GitHub's `/pulls` page accepts a query parameter `q` containing space-separated (or `+`-separated) search qualifiers:

```
https://github.com/pulls?q=is:pr+state:open+review-requested:USERNAME+updated:<YYYY-MM-DD
```

**Key Search Qualifiers**:
- `is:pr` - Filter for pull requests (not issues)
- `state:open` - Only open PRs
- `review-requested:USERNAME` - PRs where USERNAME is requested as reviewer
- `updated:<YYYY-MM-DD` - PRs last updated before specified date
- `updated:>=YYYY-MM-DD` - PRs last updated on or after specified date
- `archived:false` - Exclude archived repositories
- `-is:draft` - Exclude draft PRs

**Query Syntax**:
- Multiple qualifiers separated by `+` or space characters
- Date format: ISO 8601 (YYYY-MM-DD)
- Comparison operators: `<`, `>`, `<=`, `>=`
- Negation: `-` prefix (e.g., `-is:draft`)

**Example Query**:
```
is:pr state:open review-requested:alice updated:<2024-10-15 archived:false -is:draft
```

**Decision**: Use this format for generating GitHub search URLs, encoding spaces as `+` for readability.

**Rationale**: Official GitHub format, widely documented, supports all required filters (state, review-requested, updated date).

**Alternatives Considered**:
- Using GitHub API search endpoint: Rejected (requires authentication, client-side complexity)
- Using org-specific search: Rejected (less flexible, harder to maintain)

---

### 2. Slack Webhook Threading

**Question**: Can incoming webhooks return message timestamps for thread replies?

**Research Sources**:
- Slack API Docs: "Sending messages using incoming webhooks"
- Stack Overflow: "Where do I get thread_ts to start a Slack thread with an incoming webhook?"
- GitHub Issue: "Is there a way to get the ts in the response when sending a message via webhook?"

**Findings**:

**Problem**: Incoming webhooks do NOT return message timestamps. Webhook POST requests only return plaintext "ok" without any message metadata.

**Thread Posting Requirements**:
- To post a threaded reply, you need the parent message's `ts` (timestamp) value
- Use `thread_ts` parameter in the webhook payload to specify parent message
- Example: `{"text": "Reply message", "thread_ts": "1234567890.123456"}`

**Options to Retrieve Message Timestamp**:

A. **Use chat.postMessage API** (instead of webhooks)
   - Requires OAuth token (bot token or user token)
   - Returns message timestamp directly in response
   - Requires additional Slack app setup
   - **Pros**: Clean, direct, reliable
   - **Cons**: More complex setup, requires OAuth permissions

B. **Use conversations.history API** (after webhook post)
   - Fetch recent channel history to find posted message
   - Requires OAuth token with `channels:history` permission
   - Match message by timestamp range or content
   - **Pros**: Works with existing webhook
   - **Cons**: Requires additional API call, OAuth setup, potential race conditions

C. **Use Events API**
   - Subscribe to `message.channels` event
   - Receive webhook callback with message timestamp
   - Requires public webhook endpoint
   - **Pros**: Real-time, reliable
   - **Cons**: Infrastructure complexity, requires public endpoint

D. **Skip threading entirely**
   - Post old PR report as separate standalone message
   - **Pros**: Simplest implementation
   - **Cons**: Violates feature requirement (FR-003)

**Decision**: Use **Option A: chat.postMessage API** for both main board and thread posting.

**Rationale**:
- Simplest technical solution (single API, no race conditions)
- Most reliable (timestamp guaranteed in response)
- Clean separation of concerns (one API for all posting)
- Minimal code changes (replace webhook with API client)
- Slack Bot Token easy to obtain via Slack App setup

**Alternatives Rejected**:
- **Option B (conversations.history)**: Adds complexity with race conditions, requires matching logic
- **Option C (Events API)**: Too complex, requires infrastructure changes
- **Option D (No threading)**: Violates requirements

**Implementation Impact**:
- Replace `requests.post(webhook_url)` with Slack SDK `chat.postMessage` method
- Add new environment variable: `SLACK_BOT_TOKEN` (instead of `SLACK_WEBHOOK_URL`)
- Update configuration validation and documentation
- Return message timestamp from `post_stale_pr_summary()` method

---

### 3. URL Encoding Best Practices

**Question**: How should we encode GitHub search URLs in Python?

**Research Sources**:
- Python Docs: urllib.parse module
- ProxiesAPI: "Encoding URLs with urllib quote"
- Stack Overflow: "How can I percent-encode URL parameters in Python?"

**Findings**:

**Key Functions**:
- `urllib.parse.quote()` - Encodes characters to %XX format, spaces become `%20`
- `urllib.parse.quote_plus()` - Like quote(), but spaces become `+` (HTML form encoding)
- `urllib.parse.urlencode()` - Encodes dict of key-value pairs to query string

**Best Practices**:
1. Always encode user-generated content (usernames, dates)
2. Use `quote_plus()` for query parameters to encode spaces as `+`
3. Don't double-encode already-encoded URLs
4. Use `safe` parameter to preserve specific characters (e.g., `:` in qualifiers)
5. Validate URL length (browser limit ~2000 chars, GitHub search limit unknown)

**Example**:
```python
from urllib.parse import quote_plus

username = "user@org"
date = "2024-01-01"
query = f"is:pr state:open review-requested:{quote_plus(username)} updated:<{date}"
url = f"https://github.com/pulls?q={quote_plus(query)}"
```

**Decision**: Use `urllib.parse.quote_plus()` for encoding the complete query string.

**Rationale**:
- Handles spaces as `+` (more readable than `%20`)
- Standard Python library (no dependencies)
- Handles all special characters in usernames (e.g., `.`, `-`, `@`)
- Consistent with GitHub's query format

**Alternatives Considered**:
- `quote()` with manual space replacement: Rejected (less idiomatic)
- `urlencode()` with dict: Rejected (doesn't fit GitHub's query syntax)
- Manual encoding: Rejected (error-prone, misses edge cases)

---

## Summary of Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| GitHub URLs | Use `/pulls?q=` format with search qualifiers | Official format, supports all filters |
| Slack API | Replace webhooks with `chat.postMessage` | Only way to get message timestamp reliably |
| URL Encoding | Use `urllib.parse.quote_plus()` | Standard library, handles all edge cases |

## Open Questions

None - All technical unknowns have been resolved through research.

## Next Steps

1. Phase 1: Design data models (OldPRReport, updated Config)
2. Phase 1: Design contracts (Slack API integration, URL builder)
3. Phase 1: Update quickstart with Slack Bot Token setup
