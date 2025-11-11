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

    # Check URL length (browser limit ~2000 chars)
    if len(url) > 2000:
        raise ValueError(
            f"Generated URL exceeds browser limit (2000 chars): {len(url)} chars. "
            f"Consider shortening username or using different search criteria."
        )

    logger.debug(f"Generated GitHub search URL for {username}: {url}")

    return url
