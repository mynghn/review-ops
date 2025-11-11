"""Unit tests for URL builder functions."""

from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs, unquote_plus, urlparse

import pytest

from url_builder import build_old_pr_search_url


class TestBuildOldPRSearchURL:
    """Tests for build_old_pr_search_url function."""

    def test_basic_url_generation(self):
        """Test basic URL generation with simple username."""
        url = build_old_pr_search_url("alice", date(2024, 10, 15))

        # Parse URL to check structure
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "github.com"
        assert parsed.path == "/pulls"

        # Decode query string
        query_params = parse_qs(parsed.query)
        query = unquote_plus(query_params["q"][0])

        # Verify all required components
        assert "is:pr" in query
        assert "state:open" in query
        assert "review-requested:alice" in query
        assert "updated:<2024-10-15" in query
        assert "archived:false" in query
        assert "-is:draft" in query

    def test_special_character_encoding(self):
        """Test URL generation with special characters in username."""
        url = build_old_pr_search_url("user@org", date(2024, 10, 15))

        # @ should be encoded
        assert "%40" in url or "user@org" in unquote_plus(url)

        # Decode and verify
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        query = unquote_plus(query_params["q"][0])
        assert "review-requested:user@org" in query

    def test_hyphen_period_in_username(self):
        """Test username with hyphens and periods."""
        url = build_old_pr_search_url("user.name-123", date(2024, 10, 15))

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        query = unquote_plus(query_params["q"][0])

        assert "review-requested:user.name-123" in query

    def test_empty_username_validation(self):
        """Test error handling for empty username."""
        with pytest.raises(ValueError, match="Username cannot be empty"):
            build_old_pr_search_url("", date(2024, 10, 15))

        with pytest.raises(ValueError, match="Username cannot be empty"):
            build_old_pr_search_url("   ", date(2024, 10, 15))

    def test_invalid_date_type_validation(self):
        """Test error handling for invalid date type."""
        with pytest.raises(ValueError, match="must be a date object"):
            build_old_pr_search_url("alice", "2024-10-15")  # type: ignore

        with pytest.raises(ValueError, match="must be a date object"):
            build_old_pr_search_url("alice", 20241015)  # type: ignore

    def test_url_length_validation(self):
        """Test URL length stays within browser limits."""
        # Maximum GitHub username length is 39 characters
        long_username = "a" * 39
        url = build_old_pr_search_url(long_username, date(2024, 10, 15))

        # Browser limit is ~2000 characters
        assert len(url) < 2000

    def test_date_format_variations(self):
        """Test various date inputs."""
        # Recent date
        url1 = build_old_pr_search_url("alice", date(2024, 11, 11))
        assert "2024-11-11" in url1

        # Older date
        url2 = build_old_pr_search_url("alice", date(2020, 1, 1))
        assert "2020-01-01" in url2

        # Edge case: leap year
        url3 = build_old_pr_search_url("alice", date(2024, 2, 29))
        assert "2024-02-29" in url3

    def test_url_decoding_verification(self):
        """Test that generated URLs can be decoded and parsed."""
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

    def test_state_open_filter(self):
        """Test that state:open filter is present to exclude closed PRs."""
        url = build_old_pr_search_url("alice", date(2024, 10, 15))

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        query = unquote_plus(query_params["q"][0])

        # Verify state:open explicitly excludes closed PRs
        assert "state:open" in query

    def test_archived_false_filter(self):
        """Test that archived:false filter is present."""
        url = build_old_pr_search_url("alice", date(2024, 10, 15))

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        query = unquote_plus(query_params["q"][0])

        assert "archived:false" in query

    def test_draft_exclusion_filter(self):
        """Test that -is:draft filter is present."""
        url = build_old_pr_search_url("alice", date(2024, 10, 15))

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        query = unquote_plus(query_params["q"][0])

        assert "-is:draft" in query
