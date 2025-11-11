# GitHub Search URL Contract

**Date**: 2025-11-11
**API**: GitHub Web UI Search
**Documentation**: https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests

## Overview

This contract defines the format for GitHub web search URLs used to display filtered pull requests in the browser. These URLs are generated programmatically and sent to users via Slack.

---

## URL Format

**Base URL**: `https://github.com/pulls`
**Query Parameter**: `q` (search query string)

**Complete Format**:
```
https://github.com/pulls?q={encoded_query}
```

**Example**:
```
https://github.com/pulls?q=is:pr+state:open+review-requested:alice+updated:<2024-10-15+archived:false+-is:draft
```

---

## Query Syntax

### Search Qualifiers

Multiple qualifiers are combined using `+` (plus sign) or space characters.

| Qualifier | Description | Example | Required |
|-----------|-------------|---------|----------|
| `is:pr` | Filter for pull requests | `is:pr` | ✅ Yes |
| `state:open` | Only open PRs | `state:open` | ✅ Yes |
| `review-requested:USER` | PRs requesting review from USER | `review-requested:alice` | ✅ Yes |
| `updated:<DATE` | Updated before DATE | `updated:<2024-10-15` | ✅ Yes |
| `archived:false` | Exclude archived repos | `archived:false` | ✅ Yes |
| `-is:draft` | Exclude draft PRs | `-is:draft` | ✅ Yes |

### Date Format
- **Format**: ISO 8601 (YYYY-MM-DD)
- **Operators**: `<`, `>`, `<=`, `>=`
- **Examples**:
  - `updated:<2024-10-15` - Updated before Oct 15, 2024
  - `updated:>=2024-11-01` - Updated on or after Nov 1, 2024

### Negation
- **Syntax**: `-` prefix before qualifier
- **Example**: `-is:draft` (exclude drafts)

---

## URL Encoding

### Requirements

1. **Space Handling**: Encode spaces as `+` (plus sign)
2. **Special Characters**: Encode `@`, `:`, `<`, `>` using percent-encoding
3. **Python Function**: Use `urllib.parse.quote_plus()`

### Encoding Rules

| Character | Encoded As | Note |
|-----------|------------|------|
| Space | `+` | query_plus encoding |
| `:` | `:` | Safe character, no encoding |
| `<` | `%3C` | Comparison operator |
| `>` | `%3E` | Comparison operator |
| `-` | `-` | Safe character, no encoding |
| `@` | `%40` | In usernames |

### Python Implementation

```python
from urllib.parse import quote_plus

def build_github_search_url(username: str, cutoff_date: str) -> str:
    """
    Build GitHub search URL for old PRs.

    Args:
        username: GitHub username
        cutoff_date: ISO date string (YYYY-MM-DD)

    Returns:
        Encoded GitHub search URL
    """
    # Build query string with qualifiers
    query = (
        f"is:pr "
        f"state:open "
        f"review-requested:{username} "
        f"updated:<{cutoff_date} "
        f"archived:false "
        f"-is:draft"
    )

    # Encode entire query (spaces become +)
    encoded_query = quote_plus(query)

    return f"https://github.com/pulls?q={encoded_query}"
```

---

## Validation

### Query Validation

1. **Username**: Must be non-empty, match GitHub username format
2. **Date**: Must be valid ISO 8601 date (YYYY-MM-DD)
3. **Length**: Final URL should not exceed 2000 characters (browser limit)

### Test Cases

```python
# Valid username
assert build_github_search_url("alice", "2024-10-15")
# → https://github.com/pulls?q=is:pr+state:open+review-requested:alice+updated:<2024-10-15+archived:false+-is:draft

# Username with special characters
assert build_github_search_url("user@org", "2024-10-15")
# → Properly encoded with %40

# Edge case: very long username (50 chars)
assert len(build_github_search_url("a" * 50, "2024-10-15")) < 2000
```

---

## Examples

### Example 1: Simple Username
```
Input:
  username = "alice"
  cutoff_date = "2024-10-15"

Output:
  https://github.com/pulls?q=is%3Apr+state%3Aopen+review-requested%3Aalice+updated%3A%3C2024-10-15+archived%3Afalse+-is%3Adraft
```

### Example 2: Username with Special Characters
```
Input:
  username = "user.name-123"
  cutoff_date = "2024-11-01"

Output:
  https://github.com/pulls?q=is%3Apr+state%3Aopen+review-requested%3Auser.name-123+updated%3A%3C2024-11-01+archived%3Afalse+-is%3Adraft
```

### Example 3: Organization Member
```
Input:
  username = "user@company"
  cutoff_date = "2024-09-30"

Output:
  https://github.com/pulls?q=is%3Apr+state%3Aopen+review-requested%3Auser%40company+updated%3A%3C2024-09-30+archived%3Afalse+-is%3Adraft
```

---

## Edge Cases

### URL Length Limit

**Problem**: Browser URL length limit (~2000 chars)
**Calculation**:
- Base URL: 24 chars (`https://github.com/pulls`)
- Query prefix: 3 chars (`?q=`)
- Fixed qualifiers: ~60 chars (encoded)
- Username: Max 39 chars (GitHub limit)
- Date: 10 chars (YYYY-MM-DD)
- **Total**: ~136 chars (well under 2000 limit)

**Verdict**: No length concerns for single-username URLs

### Special Usernames

| Case | Username | Handling |
|------|----------|----------|
| Hyphen | `user-name` | No encoding needed |
| Period | `user.name` | No encoding needed |
| Numbers | `user123` | No encoding needed |
| At sign | `user@org` | Encode as `%40` |
| Unicode | `user名前` | Encode with UTF-8 percent-encoding |

---

## Testing Strategy

### Unit Tests
```python
def test_build_github_search_url_basic():
    url = build_github_search_url("alice", "2024-10-15")
    assert "review-requested%3Aalice" in url
    assert "updated%3A%3C2024-10-15" in url

def test_build_github_search_url_special_chars():
    url = build_github_search_url("user@org", "2024-10-15")
    assert "user%40org" in url

def test_url_length_limit():
    url = build_github_search_url("a" * 39, "2024-10-15")
    assert len(url) < 2000
```

### Manual Tests
1. Generate URL for test user
2. Open in browser
3. Verify search results match expected criteria
4. Verify no 404 or parsing errors

---

## Error Handling

| Error Scenario | Detection | Handling |
|----------------|-----------|----------|
| Invalid username | Empty string | Log warning, skip user |
| Invalid date | Date parse error | Log error, use default |
| URL too long | len(url) > 2000 | Log error, truncate username |

---

## Dependencies

**Standard Library Only**:
- `urllib.parse.quote_plus()` - URL encoding

**No External Dependencies** ✅

---

## Implementation Module

**File**: `src/url_builder.py` (new module)

**Function Signature**:
```python
def build_old_pr_search_url(
    username: str,
    cutoff_date: date,
    org_name: str | None = None
) -> str:
    """
    Build GitHub search URL for old PRs.

    Args:
        username: GitHub username to search for
        cutoff_date: Date threshold (PRs updated before this are "old")
        org_name: Optional organization filter

    Returns:
        Fully encoded GitHub search URL

    Raises:
        ValueError: If username is empty or date is invalid
    """
```

---

## Future Enhancements

**Not in Scope** (document for future reference):
- Organization filter: `org:company-name`
- Repository filter: `repo:company/repo-name`
- Multiple usernames: Requires OR operator (complex)
- Saved searches: Requires GitHub account authentication
