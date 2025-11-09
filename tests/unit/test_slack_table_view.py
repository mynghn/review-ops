"""Unit tests for Slack table view implementation."""
import pytest
from datetime import datetime, UTC
from slack_client import SlackClient
from models import StalePR, PullRequest, TeamMember


# Helper function to create mock PRs for testing
def create_mock_pr(
    repo_name="test-repo",
    number=123,
    title="Test PR Title",
    url="https://github.com/org/repo/pull/123",
    author="author1",
    reviewers=None,
):
    """Create a mock PullRequest for testing."""
    if reviewers is None:
        reviewers = []
    return PullRequest(
        repo_name=repo_name,
        number=number,
        title=title,
        url=url,
        author=author,
        reviewers=reviewers,
        review_status=None,
        current_approvals=0,
        created_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        base_branch="main",
    )


def create_mock_stale_pr(
    days=5.0,
    repo="test-repo",
    number=123,
    title="Test PR",
    reviewers=None,
):
    """Create a mock StalePR for testing."""
    pr = create_mock_pr(
        repo_name=repo,
        number=number,
        title=title,
        url=f"https://github.com/org/{repo}/pull/{number}",
        reviewers=reviewers or [],
    )
    return StalePR(pr=pr, staleness_days=days)


# === Tests for Header Row (TDD: Write tests FIRST) ===


def test_table_header_row_english():
    """Test table header row has correct English column labels."""
    client = SlackClient(webhook_url="mock", language="en", max_prs_total=30)

    # Build with empty categories to get minimal blocks (header + empty state)
    blocks = client.build_blocks({"rotten": [], "aging": [], "fresh": []}, [])

    # Find table block (should exist if any PRs, or check header method directly)
    # Since empty returns empty state, let's test the method directly
    header_row = client._build_table_header_row()

    # Assert header cells
    assert len(header_row) == 4

    # Column 1: Staleness
    assert header_row[0]["type"] == "rich_text"
    assert header_row[0]["elements"][0]["type"] == "rich_text_section"
    assert header_row[0]["elements"][0]["elements"][0]["type"] == "text"
    assert header_row[0]["elements"][0]["elements"][0]["text"] == "Staleness"
    assert header_row[0]["elements"][0]["elements"][0].get("style", {}).get("bold") is True

    # Column 2: Age
    assert header_row[1]["elements"][0]["elements"][0]["text"] == "Age"
    assert header_row[1]["elements"][0]["elements"][0].get("style", {}).get("bold") is True

    # Column 3: PR
    assert header_row[2]["elements"][0]["elements"][0]["text"] == "PR"
    assert header_row[2]["elements"][0]["elements"][0].get("style", {}).get("bold") is True

    # Column 4: Reviewers
    assert header_row[3]["elements"][0]["elements"][0]["text"] == "Reviewers"
    assert header_row[3]["elements"][0]["elements"][0].get("style", {}).get("bold") is True


def test_table_header_row_korean():
    """Test table header row has correct Korean column labels."""
    client = SlackClient(webhook_url="mock", language="ko", max_prs_total=30)

    # Test the method directly
    header_row = client._build_table_header_row()

    # Assert header cells with Korean labels
    assert len(header_row) == 4

    # Column 1: 숙성도 (Staleness)
    assert header_row[0]["elements"][0]["elements"][0]["text"] == "숙성도"
    assert header_row[0]["elements"][0]["elements"][0].get("style", {}).get("bold") is True

    # Column 2: 경과 (Age)
    assert header_row[1]["elements"][0]["elements"][0]["text"] == "경과"
    assert header_row[1]["elements"][0]["elements"][0].get("style", {}).get("bold") is True

    # Column 3: PR
    assert header_row[2]["elements"][0]["elements"][0]["text"] == "PR"
    assert header_row[2]["elements"][0]["elements"][0].get("style", {}).get("bold") is True

    # Column 4: 리뷰어 (Reviewers)
    assert header_row[3]["elements"][0]["elements"][0]["text"] == "리뷰어"
    assert header_row[3]["elements"][0]["elements"][0].get("style", {}).get("bold") is True


# === Tests for Data Row (TDD: Write tests FIRST) ===


def test_table_data_row_structure():
    """Test data row has correct cell structure for a single PR."""
    client = SlackClient(webhook_url="mock", language="en", max_prs_total=30)

    # Create mock PR with reviewers
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR Title",
        url="https://github.com/org/repo/pull/123",
        author="author1",
        reviewers=["reviewer1", "reviewer2"],
    )
    stale_pr = StalePR(pr=pr, staleness_days=12.0)  # 12 days -> "rotten" category

    team_members = [
        TeamMember(github_username="reviewer1", slack_user_id="U12345"),
        TeamMember(github_username="reviewer2", slack_user_id="U67890"),
    ]

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, team_members)

    # Verify we have 4 columns
    assert len(data_row) == 4

    # Column 1: Staleness emoji
    assert data_row[0]["type"] == "rich_text"
    assert data_row[0]["elements"][0]["type"] == "rich_text_section"
    assert data_row[0]["elements"][0]["elements"][0]["type"] == "emoji"
    assert data_row[0]["elements"][0]["elements"][0]["name"] == "nauseated_face"

    # Column 2: Age
    assert data_row[1]["elements"][0]["elements"][0]["type"] == "text"
    assert data_row[1]["elements"][0]["elements"][0]["text"] == "12d"

    # Column 3: PR details (repo#number + link)
    pr_cell_elements = data_row[2]["elements"][0]["elements"]
    assert len(pr_cell_elements) == 2
    assert pr_cell_elements[0]["type"] == "text"
    assert pr_cell_elements[0]["text"] == "test-repo#123\n"
    assert pr_cell_elements[1]["type"] == "link"
    assert pr_cell_elements[1]["text"] == "Test PR Title"
    assert pr_cell_elements[1]["url"] == "https://github.com/org/repo/pull/123"

    # Column 4: Reviewers (user mentions separated by newlines)
    reviewer_cell_elements = data_row[3]["elements"][0]["elements"]
    assert len(reviewer_cell_elements) == 3  # user1, newline, user2
    assert reviewer_cell_elements[0]["type"] == "user"
    assert reviewer_cell_elements[0]["user_id"] == "U12345"
    assert reviewer_cell_elements[1]["type"] == "text"
    assert reviewer_cell_elements[1]["text"] == "\n"
    assert reviewer_cell_elements[2]["type"] == "user"
    assert reviewer_cell_elements[2]["user_id"] == "U67890"


def test_table_no_reviewers():
    """Test data row displays dash when PR has no reviewers."""
    client = SlackClient(webhook_url="mock", language="en", max_prs_total=30)

    # Create mock PR with no reviewers
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        url="https://github.com/org/repo/pull/123",
        reviewers=[],
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0)  # 5 days -> "aging" category

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, [])

    # Reviewers column should have single dash
    reviewer_cell = data_row[3]["elements"][0]["elements"]
    assert len(reviewer_cell) == 1
    assert reviewer_cell[0]["type"] == "text"
    assert reviewer_cell[0]["text"] == "-"
