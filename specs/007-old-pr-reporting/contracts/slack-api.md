# Slack API Contract

**Date**: 2025-11-11
**API**: Slack Web API (chat.postMessage method)
**Documentation**: https://api.slack.com/methods/chat.postMessage

## Overview

This contract defines the integration with Slack's `chat.postMessage` method for posting messages and thread replies.

## Authentication

**Method**: Bot User OAuth Token
**Token Format**: `xoxb-*` (Bot token prefix)
**Required Scopes**:
- `chat:write` - Post messages to channels

**Token Source**: Slack App → OAuth & Permissions → Bot User OAuth Token

---

## Endpoint: chat.postMessage

**URL**: `https://slack.com/api/chat.postMessage`
**Method**: POST
**Content-Type**: `application/json`

### Request Headers
```http
Authorization: Bearer xoxb-your-bot-token
Content-Type: application/json
```

### Request Body (Main Board Message)
```json
{
  "channel": "C1234567890",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "[2025-11-11] Stale PR Board :help:"
      }
    },
    {
      "type": "table",
      "rows": [...]
    }
  ]
}
```

### Request Body (Thread Reply)
```json
{
  "channel": "C1234567890",
  "thread_ts": "1234567890.123456",
  "text": "⚠️ Too old PRs detected...",
  "mrkdwn": true
}
```

### Response (Success)
```json
{
  "ok": true,
  "channel": "C1234567890",
  "ts": "1234567890.123456",
  "message": {
    "text": "...",
    "blocks": [...]
  }
}
```

### Response (Error)
```json
{
  "ok": false,
  "error": "channel_not_found"
}
```

---

## Field Specifications

### channel (required)
- **Type**: string
- **Format**: Channel ID (starts with C for public, G for private)
- **Example**: "C1234567890"
- **Validation**: Must be valid channel where bot is a member

### blocks (optional)
- **Type**: array of block objects
- **Max**: 50 blocks per message
- **Usage**: Rich formatted messages (main board)
- **Alternative**: Use `text` field for simple messages

### text (required if blocks not provided)
- **Type**: string
- **Max Length**: 40,000 characters
- **Usage**: Fallback text, thread messages
- **Markdown**: Enabled with `mrkdwn: true`

### thread_ts (optional)
- **Type**: string
- **Format**: Message timestamp (e.g., "1234567890.123456")
- **Usage**: Post message as thread reply
- **Source**: `ts` field from parent message response

---

## Implementation

### Python SDK Usage

```python
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

client = WebClient(token=slack_bot_token)

try:
    # Post main board message
    response = client.chat_postMessage(
        channel=channel_id,
        blocks=blocks
    )

    # Extract timestamp for threading
    parent_ts = response["ts"]

    # Post thread reply
    client.chat_postMessage(
        channel=channel_id,
        thread_ts=parent_ts,
        text="⚠️ Too old PRs detected:\n• @alice: 3 PRs → [View on GitHub](url)"
    )

except SlackApiError as e:
    # Handle errors
    print(f"Error: {e.response['error']}")
```

---

## Error Handling

| Error Code | Description | Handling Strategy |
|------------|-------------|-------------------|
| `channel_not_found` | Invalid channel ID | Log error, exit with failure |
| `not_in_channel` | Bot not in channel | Log error with instructions to invite bot |
| `token_revoked` | Token invalidated | Log error with instructions to regenerate token |
| `invalid_auth` | Invalid token format | Validate token format in config.py |
| `rate_limited` | Too many requests | Retry with exponential backoff |

---

## Rate Limits

**Tier**: 1 request per second (default)
**Burst**: Up to 100 messages within 1 minute
**Strategy**: No rate limiting needed (max 2 messages per run: main board + thread)

---

## Testing

### Unit Tests
- Mock SlackApiError for error scenarios
- Verify request payload structure
- Test thread_ts parameter inclusion

### Integration Tests
- Use Slack test workspace
- Verify message posting with real API
- Verify thread reply appears under parent message
- Verify timestamp return value

---

## Dependencies

**Package**: `slack-sdk`
**Version**: `>=3.26.0` (latest stable as of 2024)
**Installation**: `pip install slack-sdk` or `uv add slack-sdk`

**Import**:
```python
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
```

---

## Migration from Webhooks

**Before** (Incoming Webhook):
```python
import requests
response = requests.post(webhook_url, json={"blocks": blocks})
# No timestamp returned, only "ok"
```

**After** (chat.postMessage):
```python
from slack_sdk import WebClient
client = WebClient(token=bot_token)
response = client.chat_postMessage(channel=channel_id, blocks=blocks)
parent_ts = response["ts"]  # Timestamp for threading
```

**Benefits**:
- ✅ Returns message timestamp for threading
- ✅ Better error messages
- ✅ Official SDK with type hints
- ✅ Automatic retry logic
- ✅ Rate limit handling
