# URL Builder Interface

**Date**: 2025-11-11
**Module**: `src/url_builder.py` (new)
**Purpose**: Generate GitHub search URLs for old PR reporting

## Overview

This module provides utility functions to generate properly encoded GitHub search URLs. It encapsulates URL construction logic to ensure consistency and correct encoding across the application.

---

## Public API

### Function: build_old_pr_search_url

```python
def build_old_pr_search_url(
    username: str,
    cutoff_date: date,
) -> str:
    """
    Build GitHub search URL for old PRs awaiting review from a specific user.

    Generates a URL to https://github.com/pulls with search filters for:
    - Open pull requests
    - Review requested from username
    - Updated before cutoff_date
    - Excluding archived repositories and drafts

    Args:
        username: GitHub username to search for (e.g., "alice", "user@org")
        cutoff_date: Date threshold - PRs updated before this are considered "old"

    Returns:
        Fully encoded GitHub search URL (https://github.com/pulls?q=...)

    Raises:
        ValueError: If username is empty or cutoff_date is invalid

    Example:
        >>> from datetime import date
        >>> url = build_old_pr_search_url("alice", date(2024, 10, 15))
        >>> print(url)
        https://github.com/pulls?q=is%3Apr+state%3Aopen+...
    """
```

---

## Implementation Details

### Query Construction

The function builds a search query with the following qualifiers:

```python
query = (
    f"is:pr "                           # Filter for pull requests
    f"state:open "                      # Only open PRs
    f"review-requested:{username} "     # Review requested from user
    f"updated:<{cutoff_date.isoformat()} "  # Updated before cutoff
    f"archived:false "                  # Exclude archived repos
    f"-is:draft"                        # Exclude draft PRs
)
```

### Encoding Strategy

1. Use `urllib.parse.quote_plus()` to encode the entire query string
2. Spaces are converted to `+` for readability
3. Special characters (`:`, `<`, `@`) are percent-encoded
4. Date is converted to ISO format (YYYY-MM-DD)

### Error Handling

```python
if not username or not username.strip():
    raise ValueError("Username cannot be empty")

if not isinstance(cutoff_date, date):
    raise ValueError(f"cutoff_date must be a date object, got {type(cutoff_date)}")

# Additional validation
if len(username) > 39:  # GitHub username limit
    logger.warning(f"Username '{username}' exceeds 39 characters")
```

---

## Usage Examples

### Example 1: Basic Usage

```python
from datetime import date
from url_builder import build_old_pr_search_url

cutoff = date(2024, 10, 15)
url = build_old_pr_search_url("alice", cutoff)

# Result: https://github.com/pulls?q=is%3Apr+state%3Aopen+review-requested%3Aalice+updated%3A%3C2024-10-15+archived%3Afalse+-is%3Adraft
```

### Example 2: Integration with App Logic

```python
from datetime import date, timedelta
from config import load_config
from url_builder import build_old_pr_search_url

config = load_config()
cutoff_date = date.today() - timedelta(days=config.gh_search_window_size)

# Generate URLs for each team member with old PRs
for member in team_members:
    old_pr_count = count_old_prs(member.github_username, cutoff_date)
    if old_pr_count > 0:
        url = build_old_pr_search_url(member.github_username, cutoff_date)
        print(f"{member.github_username}: {old_pr_count} old PRs → {url}")
```

### Example 3: Error Handling

```python
try:
    url = build_old_pr_search_url("", date.today())
except ValueError as e:
    logger.error(f"Invalid username: {e}")

try:
    url = build_old_pr_search_url("alice", "2024-10-15")  # Wrong type
except ValueError as e:
    logger.error(f"Invalid date type: {e}")
```

---

## Testing

### Unit Tests

```python
# tests/unit/test_url_builder.py

from datetime import date
import pytest
from url_builder import build_old_pr_search_url


def test_build_old_pr_search_url_basic():
    """Test basic URL generation with simple username."""
    url = build_old_pr_search_url("alice", date(2024, 10, 15))

    assert url.startswith("https://github.com/pulls?q=")
    assert "review-requested%3Aalice" in url
    assert "updated%3A%3C2024-10-15" in url
    assert "is%3Apr" in url
    assert "state%3Aopen" in url
    assert "archived%3Afalse" in url
    assert "-is%3Adraft" in url


def test_build_old_pr_search_url_special_characters():
    """Test URL generation with special characters in username."""
    url = build_old_pr_search_url("user@org", date(2024, 10, 15))

    # @ should be encoded as %40
    assert "user%40org" in url


def test_build_old_pr_search_url_hyphen_period():
    """Test username with hyphens and periods."""
    url = build_old_pr_search_url("user.name-123", date(2024, 10, 15))

    # Hyphens and periods should not be encoded
    assert "user.name-123" in url


def test_build_old_pr_search_url_empty_username():
    """Test error handling for empty username."""
    with pytest.raises(ValueError, match="Username cannot be empty"):
        build_old_pr_search_url("", date(2024, 10, 15))


def test_build_old_pr_search_url_invalid_date_type():
    """Test error handling for invalid date type."""
    with pytest.raises(ValueError, match="must be a date object"):
        build_old_pr_search_url("alice", "2024-10-15")


def test_build_old_pr_search_url_length():
    """Test URL length stays within browser limits."""
    # Maximum GitHub username length is 39 characters
    long_username = "a" * 39
    url = build_old_pr_search_url(long_username, date(2024, 10, 15))

    # Browser limit is ~2000 characters
    assert len(url) < 2000


def test_build_old_pr_search_url_date_formats():
    """Test various date inputs."""
    # Recent date
    url1 = build_old_pr_search_url("alice", date(2024, 11, 11))
    assert "2024-11-11" in url1

    # Older date
    url2 = build_old_pr_search_url("alice", date(2020, 1, 1))
    assert "2020-01-01" in url2


def test_build_old_pr_search_url_decoding():
    """Test that generated URLs can be decoded and parsed."""
    from urllib.parse import urlparse, parse_qs, unquote_plus

    url = build_old_pr_search_url("alice", date(2024, 10, 15))

    parsed = urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "github.com"
    assert parsed.path == "/pulls"

    query_params = parse_qs(parsed.query)
    assert "q" in query_params

    query = unquote_plus(query_params["q"][0])
    assert "is:pr" in query
    assert "review-requested:alice" in query
    assert "updated:<2024-10-15" in query
```

---

## Dependencies

**Standard Library**:
- `urllib.parse` - URL encoding (`quote_plus`)
- `datetime` - Date handling (`date` type)
- `logging` - Warning/error logging

**No External Dependencies** ✅

---

## Module Structure

```python
# src/url_builder.py

"""GitHub search URL generation utilities."""

from __future__ import annotations

import logging
from datetime import date
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


def build_old_pr_search_url(
    username: str,
    cutoff_date: date,
) -> str:
    """
    Build GitHub search URL for old PRs.

    [Full docstring as specified in Public API section]
    """
    # Validation
    if not username or not username.strip():
        raise ValueError("Username cannot be empty")

    if not isinstance(cutoff_date, date):
        raise ValueError(
            f"cutoff_date must be a date object, got {type(cutoff_date).__name__}"
        )

    # Warn for unusually long usernames
    if len(username) > 39:
        logger.warning(
            f"Username '{username}' exceeds GitHub's 39-character limit. "
            "URL may not work correctly."
        )

    # Build query string
    query = (
        f"is:pr "
        f"state:open "
        f"review-requested:{username} "
        f"updated:<{cutoff_date.isoformat()} "
        f"archived:false "
        f"-is:draft"
    )

    # Encode query
    encoded_query = quote_plus(query)

    # Build final URL
    url = f"https://github.com/pulls?q={encoded_query}"

    logger.debug(f"Generated GitHub search URL for {username}: {url}")

    return url
```

---

## Integration Points

### In `app.py`

```python
from url_builder import build_old_pr_search_url

# Calculate cutoff date
cutoff_date = date.today() - timedelta(days=config.gh_search_window_size)

# Generate OldPRReport instances
old_pr_reports = []
for member in team_members:
    old_pr_count = len(old_prs_by_member[member.github_username])
    if old_pr_count > 0:
        url = build_old_pr_search_url(member.github_username, cutoff_date)
        old_pr_reports.append(
            OldPRReport(
                github_username=member.github_username,
                pr_count=old_pr_count,
                github_search_url=url,
            )
        )
```

### In Tests

```python
from url_builder import build_old_pr_search_url

# Mock URL generation in integration tests
def test_old_pr_workflow(mocker):
    mock_url = mocker.patch('url_builder.build_old_pr_search_url')
    mock_url.return_value = "https://github.com/pulls?q=mocked"

    # Test workflow...
```

---

## Performance

**Computational Complexity**: O(1) - constant time
**Memory Usage**: O(n) where n is username length
**Typical Execution Time**: < 1ms per URL

**Optimization Notes**:
- No I/O operations
- String concatenation is fast for small strings
- URL encoding is a simple character mapping

---

## Future Enhancements

**Not in Scope** (potential future additions):

1. **Organization filter**: Add optional `org_name` parameter
   ```python
   def build_old_pr_search_url(
       username: str,
       cutoff_date: date,
       org_name: str | None = None,
   ) -> str:
       if org_name:
           query += f"org:{org_name} "
   ```

2. **Repository filter**: Filter by specific repos
3. **Multiple usernames**: Support OR queries (requires different syntax)
4. **Query builder class**: For more complex queries (currently not needed)
