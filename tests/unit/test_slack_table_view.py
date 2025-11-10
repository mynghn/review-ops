"""Unit tests for Slack table view implementation."""
from datetime import UTC, datetime

from models import GitHubTeamReviewRequest, PullRequest, StalePR, TeamMember
from slack_client import SlackClient


# Helper function to create mock PRs for testing
def create_mock_pr(
    repo_name="test-repo",
    number=123,
    title="Test PR Title",
    url="https://github.com/org/repo/pull/123",
    author="author1",
    reviewers=None,
    github_team_reviewers=None,
):
    """Create a mock PullRequest for testing."""
    if reviewers is None:
        reviewers = []
    if github_team_reviewers is None:
        github_team_reviewers = []
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
        github_team_reviewers=github_team_reviewers,
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
    assert len(header_row) == 5

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

    # Column 4: Author
    assert header_row[3]["elements"][0]["elements"][0]["text"] == "Author"
    assert header_row[3]["elements"][0]["elements"][0].get("style", {}).get("bold") is True

    # Column 5: Reviewers
    assert header_row[4]["elements"][0]["elements"][0]["text"] == "Review awaited"
    assert header_row[4]["elements"][0]["elements"][0].get("style", {}).get("bold") is True


def test_table_header_row_korean():
    """Test table header row has correct Korean column labels."""
    client = SlackClient(webhook_url="mock", language="ko", max_prs_total=30)

    # Test the method directly
    header_row = client._build_table_header_row()

    # Assert header cells with Korean labels
    assert len(header_row) == 5

    # Column 1: 신선도 (Staleness)
    assert header_row[0]["elements"][0]["elements"][0]["text"] == "신선도"
    assert header_row[0]["elements"][0]["elements"][0].get("style", {}).get("bold") is True

    # Column 2: 경과 (Age)
    assert header_row[1]["elements"][0]["elements"][0]["text"] == "경과"
    assert header_row[1]["elements"][0]["elements"][0].get("style", {}).get("bold") is True

    # Column 3: PR
    assert header_row[2]["elements"][0]["elements"][0]["text"] == "PR"
    assert header_row[2]["elements"][0]["elements"][0].get("style", {}).get("bold") is True

    # Column 4: Author
    assert header_row[3]["elements"][0]["elements"][0]["text"] == "Author"
    assert header_row[3]["elements"][0]["elements"][0].get("style", {}).get("bold") is True

    # Column 5: 리뷰 대기 중 (Review awaited)
    assert header_row[4]["elements"][0]["elements"][0]["text"] == "리뷰 대기 중"
    assert header_row[4]["elements"][0]["elements"][0].get("style", {}).get("bold") is True


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
        TeamMember(github_username="author1", slack_user_id="U11111"),
        TeamMember(github_username="reviewer1", slack_user_id="U12345"),
        TeamMember(github_username="reviewer2", slack_user_id="U67890"),
    ]

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, team_members)

    # Verify we have 5 columns
    assert len(data_row) == 5

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
    assert len(pr_cell_elements) == 3
    assert pr_cell_elements[2]["type"] == "link"
    assert pr_cell_elements[2]["text"] == "test-repo#123"
    assert pr_cell_elements[2]["url"] == "https://github.com/org/repo/pull/123"
    assert pr_cell_elements[1]["type"] == "text"
    assert pr_cell_elements[1]["text"] == "\n"
    assert pr_cell_elements[0]["type"] == "text"
    assert pr_cell_elements[0]["text"] == "Test PR Title"

    # Column 4: Author
    author_cell_elements = data_row[3]["elements"][0]["elements"]
    assert len(author_cell_elements) == 1
    assert author_cell_elements[0]["type"] == "user"
    assert author_cell_elements[0]["user_id"] == "U11111"

    # Column 5: Reviewers (user mentions separated by newlines)
    reviewer_cell_elements = data_row[4]["elements"][0]["elements"]
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

    # Reviewers column (now column 5) should have single dash
    reviewer_cell = data_row[4]["elements"][0]["elements"]
    assert len(reviewer_cell) == 1
    assert reviewer_cell[0]["type"] == "text"
    assert reviewer_cell[0]["text"] == "-"


# === Tests for GitHub Team Review Requests ===


def test_github_team_reviewers_display():
    """Test GitHub team reviewers are displayed with team name and members."""
    client = SlackClient(webhook_url="mock", language="en", max_prs_total=30)

    # Create GitHub team with members
    github_team = GitHubTeamReviewRequest(
        team_name="Backend Team",
        team_slug="backend-team",
        members=["alice", "bob"],
    )

    # Create mock PR with GitHub team reviewer
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        reviewers=[],  # No individual reviewers
        github_team_reviewers=[github_team],
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0)

    team_members = [
        TeamMember(github_username="alice", slack_user_id="U11111"),
        TeamMember(github_username="bob", slack_user_id="U22222"),
    ]

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, team_members)

    # Reviewers column (now column 5) should show team name with members
    reviewer_cell = data_row[4]["elements"][0]["elements"]

    # Should have: "@Backend Team" + "(" + user(alice) + ", " + user(bob) + ")"
    assert reviewer_cell[0]["type"] == "text"
    assert reviewer_cell[0]["text"] == "@Backend Team"

    assert reviewer_cell[1]["type"] == "text"
    assert reviewer_cell[1]["text"] == "("

    assert reviewer_cell[2]["type"] == "user"
    assert reviewer_cell[2]["user_id"] == "U11111"

    assert reviewer_cell[3]["type"] == "text"
    assert reviewer_cell[3]["text"] == ", "

    assert reviewer_cell[4]["type"] == "user"
    assert reviewer_cell[4]["user_id"] == "U22222"

    assert reviewer_cell[5]["type"] == "text"
    assert reviewer_cell[5]["text"] == ")"


def test_github_team_and_individual_reviewers_with_deduplication():
    """Test mixed GitHub team and individual reviewers with deduplication."""
    client = SlackClient(webhook_url="mock", language="en", max_prs_total=30)

    # Create GitHub team with members alice and bob
    github_team = GitHubTeamReviewRequest(
        team_name="Backend Team",
        team_slug="backend-team",
        members=["alice", "bob"],
    )

    # Create mock PR with both GitHub team and individual reviewers
    # alice is in team AND individually requested - should deduplicate
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        reviewers=["alice", "charlie"],  # alice is duplicate, charlie is not in team
        github_team_reviewers=[github_team],
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0)

    team_members = [
        TeamMember(github_username="alice", slack_user_id="U11111"),
        TeamMember(github_username="bob", slack_user_id="U22222"),
        TeamMember(github_username="charlie", slack_user_id="U33333"),
    ]

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, team_members)

    # Reviewers column (now column 5) should show: @Backend Team (alice, bob), newline, then charlie
    reviewer_cell = data_row[4]["elements"][0]["elements"]

    # Verify team section: "@Backend Team" + "(" + alice + ", " + bob + ")"
    assert reviewer_cell[0]["text"] == "@Backend Team"
    assert reviewer_cell[1]["text"] == "("
    assert reviewer_cell[2]["user_id"] == "U11111"  # alice
    assert reviewer_cell[3]["text"] == ", "
    assert reviewer_cell[4]["user_id"] == "U22222"  # bob
    assert reviewer_cell[5]["text"] == ")"

    # Newline before individual reviewers
    assert reviewer_cell[6]["text"] == "\n"

    # Only charlie should be shown (alice is deduplicated)
    assert reviewer_cell[7]["user_id"] == "U33333"  # charlie
    assert len(reviewer_cell) == 8  # No more elements


def test_multiple_github_teams():
    """Test multiple GitHub teams are displayed correctly."""
    client = SlackClient(webhook_url="mock", language="en", max_prs_total=30)

    # Create two GitHub teams
    team1 = GitHubTeamReviewRequest(
        team_name="Backend Team",
        team_slug="backend-team",
        members=["alice"],
    )
    team2 = GitHubTeamReviewRequest(
        team_name="Frontend Team",
        team_slug="frontend-team",
        members=["bob"],
    )

    # Create mock PR with multiple GitHub teams
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        reviewers=[],
        github_team_reviewers=[team1, team2],
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0)

    team_members = [
        TeamMember(github_username="alice", slack_user_id="U11111"),
        TeamMember(github_username="bob", slack_user_id="U22222"),
    ]

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, team_members)

    # Reviewers column (now column 5) should show both teams separated by newline
    reviewer_cell = data_row[4]["elements"][0]["elements"]

    # Team 1: "@Backend Team" + "(" + alice + ")"
    assert reviewer_cell[0]["text"] == "@Backend Team"
    assert reviewer_cell[1]["text"] == "("
    assert reviewer_cell[2]["user_id"] == "U11111"
    assert reviewer_cell[3]["text"] == ")"

    # Newline between teams
    assert reviewer_cell[4]["text"] == "\n"

    # Team 2: "@Frontend Team" + "(" + bob + ")"
    assert reviewer_cell[5]["text"] == "@Frontend Team"
    assert reviewer_cell[6]["text"] == "("
    assert reviewer_cell[7]["user_id"] == "U22222"
    assert reviewer_cell[8]["text"] == ")"


def test_github_team_with_empty_members():
    """Test GitHub team with no members shows appropriate message."""
    client = SlackClient(webhook_url="mock", language="en", max_prs_total=30)

    # Create GitHub team with empty members (API fetch failed)
    github_team = GitHubTeamReviewRequest(
        team_name="Backend Team",
        team_slug="backend-team",
        members=[],  # Empty - fetch failed
    )

    # Create mock PR with GitHub team reviewer
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        reviewers=[],
        github_team_reviewers=[github_team],
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0)

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, [])

    # Reviewers column (now column 5) should show team name with "(no members)"
    reviewer_cell = data_row[4]["elements"][0]["elements"]

    assert reviewer_cell[0]["text"] == "@Backend Team"
    assert reviewer_cell[1]["text"] == "("
    assert reviewer_cell[2]["text"] == "no members)"


def test_github_team_with_no_slack_ids():
    """Test GitHub team members without Slack IDs fall back to @username."""
    client = SlackClient(webhook_url="mock", language="en", max_prs_total=30)

    # Create GitHub team with members
    github_team = GitHubTeamReviewRequest(
        team_name="Backend Team",
        team_slug="backend-team",
        members=["alice", "bob"],
    )

    # Create mock PR with GitHub team reviewer
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        reviewers=[],
        github_team_reviewers=[github_team],
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0)

    # No team members with Slack IDs - should fall back to @username
    team_members = []

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, team_members)

    # Reviewers column (now column 5) should show team name with @usernames
    reviewer_cell = data_row[4]["elements"][0]["elements"]

    assert reviewer_cell[0]["text"] == "@Backend Team"
    assert reviewer_cell[1]["text"] == "("
    assert reviewer_cell[2]["text"] == "@alice"
    assert reviewer_cell[3]["text"] == ", "
    assert reviewer_cell[4]["text"] == "@bob"
    assert reviewer_cell[5]["text"] == ")"


def test_github_team_with_complete_deduplication():
    """Test GitHub team where all individual reviewers are already in team (no trailing newline)."""
    client = SlackClient(webhook_url="mock", language="en", max_prs_total=30)

    # Create GitHub team with members alice and bob
    github_team = GitHubTeamReviewRequest(
        team_name="Backend Team",
        team_slug="backend-team",
        members=["alice", "bob"],
    )

    # Create mock PR where individual reviewers are all in the team (complete deduplication)
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        reviewers=["alice", "bob"],  # Both are in the team - will be deduplicated
        github_team_reviewers=[github_team],
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0)

    team_members = [
        TeamMember(github_username="alice", slack_user_id="U11111"),
        TeamMember(github_username="bob", slack_user_id="U22222"),
    ]

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, team_members)

    # Reviewers column (now column 5) should show only team
    # (no trailing newline, no duplicate reviewers)
    reviewer_cell = data_row[4]["elements"][0]["elements"]

    # Should have: "@Backend Team" + "(" + user(alice) + ", " + user(bob) + ")"
    # NO trailing newline since all reviewers were deduplicated
    assert reviewer_cell[0]["text"] == "@Backend Team"
    assert reviewer_cell[1]["text"] == "("
    assert reviewer_cell[2]["user_id"] == "U11111"
    assert reviewer_cell[3]["text"] == ", "
    assert reviewer_cell[4]["user_id"] == "U22222"
    assert reviewer_cell[5]["text"] == ")"
    assert len(reviewer_cell) == 6  # No extra elements (no trailing newline, no duplicates)


# === Tests for Non-Team Member Filtering ===


def test_reviewer_filtering_disabled_shows_all_reviewers():
    """Test that with filtering disabled (default), all reviewers are shown."""
    client = SlackClient(
        webhook_url="mock", language="en", max_prs_total=30, show_non_team_reviewers=True
    )

    # Create mock PR with team and non-team reviewers
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        reviewers=["team_member", "non_team_member"],
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0)

    # Only team_member is in team_members.json
    team_members = [
        TeamMember(github_username="team_member", slack_user_id="U11111"),
    ]

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, team_members)

    # Reviewers column should show BOTH reviewers
    reviewer_cell = data_row[4]["elements"][0]["elements"]

    # Should have: team_member mention + newline + @non_team_member (fallback)
    assert reviewer_cell[0]["type"] == "user"
    assert reviewer_cell[0]["user_id"] == "U11111"  # team_member
    assert reviewer_cell[1]["text"] == "\n"
    assert reviewer_cell[2]["text"] == "@non_team_member"  # fallback for non-team member


def test_reviewer_filtering_enabled_filters_individual_reviewers():
    """Test that with filtering enabled, only team members are shown."""
    client = SlackClient(
        webhook_url="mock", language="en", max_prs_total=30, show_non_team_reviewers=False
    )

    # Create mock PR with team and non-team reviewers
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        reviewers=["team_member", "non_team_member"],
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0)

    # Only team_member is in team_members.json
    team_members = [
        TeamMember(github_username="team_member", slack_user_id="U11111"),
    ]

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, team_members)

    # Reviewers column should show ONLY team_member
    reviewer_cell = data_row[4]["elements"][0]["elements"]

    # Should have: only team_member mention (no non_team_member)
    assert len(reviewer_cell) == 1
    assert reviewer_cell[0]["type"] == "user"
    assert reviewer_cell[0]["user_id"] == "U11111"  # team_member


def test_reviewer_filtering_enabled_filters_github_team_members():
    """Test that with filtering enabled, GitHub team members are filtered."""
    client = SlackClient(
        webhook_url="mock", language="en", max_prs_total=30, show_non_team_reviewers=False
    )

    # Create GitHub team with team and non-team members
    github_team = GitHubTeamReviewRequest(
        team_name="Backend Team",
        team_slug="backend-team",
        members=["team_member", "non_team_member"],
    )

    # Create mock PR with GitHub team reviewer
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        reviewers=[],
        github_team_reviewers=[github_team],
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0)

    # Only team_member is in team_members.json
    team_members = [
        TeamMember(github_username="team_member", slack_user_id="U11111"),
    ]

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, team_members)

    # Reviewers column should show only team_member in the team
    reviewer_cell = data_row[4]["elements"][0]["elements"]

    # Should have: "@Backend Team" + "(" + team_member + ")" (no non_team_member)
    assert reviewer_cell[0]["text"] == "@Backend Team"
    assert reviewer_cell[1]["text"] == "("
    assert reviewer_cell[2]["user_id"] == "U11111"  # team_member only
    assert reviewer_cell[3]["text"] == ")"
    assert len(reviewer_cell) == 4


def test_reviewer_filtering_enabled_skips_empty_github_teams():
    """Test that GitHub teams with no team members after filtering are skipped entirely."""
    client = SlackClient(
        webhook_url="mock", language="en", max_prs_total=30, show_non_team_reviewers=False
    )

    # Create GitHub team with only non-team members
    github_team = GitHubTeamReviewRequest(
        team_name="Backend Team",
        team_slug="backend-team",
        members=["non_team_member1", "non_team_member2"],
    )

    # Create mock PR with GitHub team reviewer
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        reviewers=[],
        github_team_reviewers=[github_team],
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0)

    # team_members.json has different users (not in the team)
    team_members = [
        TeamMember(github_username="other_team_member", slack_user_id="U11111"),
    ]

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, team_members)

    # Reviewers column should show dash (team is completely filtered out)
    reviewer_cell = data_row[4]["elements"][0]["elements"]

    assert len(reviewer_cell) == 1
    assert reviewer_cell[0]["text"] == "-"


def test_reviewer_filtering_enabled_all_reviewers_filtered():
    """Test that when all reviewers are filtered out, dash is displayed."""
    client = SlackClient(
        webhook_url="mock", language="en", max_prs_total=30, show_non_team_reviewers=False
    )

    # Create mock PR with only non-team reviewers
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        reviewers=["non_team_member1", "non_team_member2"],
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0)

    # team_members.json has different users
    team_members = [
        TeamMember(github_username="other_team_member", slack_user_id="U11111"),
    ]

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, team_members)

    # Reviewers column should show dash
    reviewer_cell = data_row[4]["elements"][0]["elements"]

    assert len(reviewer_cell) == 1
    assert reviewer_cell[0]["text"] == "-"


def test_reviewer_filtering_enabled_mixed_team_and_github_teams():
    """Test filtering with both GitHub teams and individual reviewers."""
    client = SlackClient(
        webhook_url="mock", language="en", max_prs_total=30, show_non_team_reviewers=False
    )

    # Create GitHub team with mixed members
    github_team = GitHubTeamReviewRequest(
        team_name="Backend Team",
        team_slug="backend-team",
        members=["alice", "non_team_member"],
    )

    # Create mock PR with GitHub team and individual reviewers
    pr = create_mock_pr(
        repo_name="test-repo",
        number=123,
        title="Test PR",
        reviewers=["bob", "another_non_team_member"],
        github_team_reviewers=[github_team],
    )
    stale_pr = StalePR(pr=pr, staleness_days=5.0)

    # Only alice and bob are team members
    team_members = [
        TeamMember(github_username="alice", slack_user_id="U11111"),
        TeamMember(github_username="bob", slack_user_id="U22222"),
    ]

    # Test the method directly
    data_row = client._build_table_data_row(stale_pr, team_members)

    # Reviewers column should show: @Backend Team (alice) + newline + bob
    reviewer_cell = data_row[4]["elements"][0]["elements"]

    # Team section: "@Backend Team" + "(" + alice + ")" (non_team_member filtered out)
    assert reviewer_cell[0]["text"] == "@Backend Team"
    assert reviewer_cell[1]["text"] == "("
    assert reviewer_cell[2]["user_id"] == "U11111"  # alice
    assert reviewer_cell[3]["text"] == ")"

    # Newline before individual reviewers
    assert reviewer_cell[4]["text"] == "\n"

    # Only bob shown (another_non_team_member filtered out, alice deduplicated)
    assert reviewer_cell[5]["user_id"] == "U22222"  # bob
    assert len(reviewer_cell) == 6
