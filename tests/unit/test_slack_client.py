"""Unit tests for SlackClient Block Kit functionality."""

from __future__ import annotations

from datetime import UTC, datetime, date
from unittest.mock import Mock, patch

import pytest

from models import PullRequest, StalePR, TeamMember
from slack_client import SlackClient


@pytest.fixture
def slack_client_en():
    """Create a Slack client with English language."""
    return SlackClient(webhook_url="https://hooks.slack.com/services/T00/B00/XXX", language="en")


@pytest.fixture
def slack_client_ko():
    """Create a Slack client with Korean language."""
    return SlackClient(webhook_url="https://hooks.slack.com/services/T00/B00/XXX", language="ko")


@pytest.fixture
def sample_stale_pr():
    """Create a sample stale PR."""
    pr = PullRequest(
        repo_name="review-ops",
        number=123,
        title="Fix authentication bug",
        author="johndoe",
        reviewers=["alice", "bob"],
        url="https://github.com/test-org/review-ops/pull/123",
        created_at=datetime(2025, 10, 17, 10, 0, 0, tzinfo=UTC),
        ready_at=datetime(2025, 10, 17, 10, 0, 0, tzinfo=UTC),
        current_approvals=0,
        review_status="REVIEW_REQUIRED",
        base_branch="main",
    )
    return StalePR(pr=pr, staleness_days=14.0)


@pytest.fixture
def sample_team():
    """Create sample team members."""
    return [
        TeamMember(github_username="alice", slack_user_id="U1234567890"),
        TeamMember(github_username="bob"),
        TeamMember(github_username="johndoe", slack_user_id="U9876543210"),
    ]


class TestSlackClientInitialization:
    """Tests for SlackClient initialization."""

    def test_initialization_with_language_en(self):
        """Test initialization with English language."""
        client = SlackClient(webhook_url="https://hooks.slack.com/test", language="en")
        assert client.language == "en"
        assert client.webhook_url == "https://hooks.slack.com/test"

    def test_initialization_with_language_ko(self):
        """Test initialization with Korean language."""
        client = SlackClient(webhook_url="https://hooks.slack.com/test", language="ko")
        assert client.language == "ko"

    def test_initialization_default_language(self):
        """Test initialization defaults to English."""
        client = SlackClient(webhook_url="https://hooks.slack.com/test")
        assert client.language == "en"

    def test_max_prs_total_default(self):
        """Test max_prs_total default is set correctly."""
        client = SlackClient(webhook_url="https://hooks.slack.com/services/TEST/TEST/TEST")
        assert client.max_prs_total == 30


class TestEscapeMrkdwn:
    """Tests for _escape_mrkdwn helper method."""

    def test_escape_ampersand(self, slack_client_en):
        """Test escaping ampersand character."""
        result = slack_client_en._escape_mrkdwn("Fix A & B")
        assert result == "Fix A &amp; B"

    def test_escape_less_than(self, slack_client_en):
        """Test escaping less-than character."""
        result = slack_client_en._escape_mrkdwn("Fix <script>")
        assert result == "Fix &lt;script&gt;"

    def test_escape_greater_than(self, slack_client_en):
        """Test escaping greater-than character."""
        result = slack_client_en._escape_mrkdwn("Fix >redirect")
        assert result == "Fix &gt;redirect"

    def test_escape_multiple_chars(self, slack_client_en):
        """Test escaping multiple special characters."""
        result = slack_client_en._escape_mrkdwn("Fix <tag> & <other>")
        assert result == "Fix &lt;tag&gt; &amp; &lt;other&gt;"


class TestBuildHeaderBlock:
    """Tests for _build_header_block method."""

    def test_header_rotten_en(self, slack_client_en):
        """Test English rotten header."""
        block = slack_client_en._build_header_block("rotten")
        assert block["type"] == "header"
        assert block["text"]["type"] == "plain_text"
        assert block["text"]["text"] == "🤢 Rotten PRs"
        assert block["text"]["emoji"] is True

    def test_header_rotten_ko(self, slack_client_ko):
        """Test Korean rotten header."""
        block = slack_client_ko._build_header_block("rotten")
        assert block["text"]["text"] == "🤢 PR 부패 중..."

    def test_header_aging_en(self, slack_client_en):
        """Test English aging header."""
        block = slack_client_en._build_header_block("aging")
        assert block["text"]["text"] == "🧀 Aging PRs"

    def test_header_aging_ko(self, slack_client_ko):
        """Test Korean aging header."""
        block = slack_client_ko._build_header_block("aging")
        assert block["text"]["text"] == "🧀 PR 숙성 중..."

    def test_header_fresh_en(self, slack_client_en):
        """Test English fresh header."""
        block = slack_client_en._build_header_block("fresh")
        assert block["text"]["text"] == "✨ Fresh PRs"

    def test_header_fresh_ko(self, slack_client_ko):
        """Test Korean fresh header."""
        block = slack_client_ko._build_header_block("fresh")
        assert block["text"]["text"] == "✨ 갓 태어난 PR"


class TestBuildPRSection:
    """Tests for _build_pr_section method."""

    def test_pr_section_structure(self, slack_client_en, sample_stale_pr, sample_team):
        """Test PR section has correct structure."""
        block = slack_client_en._build_pr_section(sample_stale_pr, sample_team)
        assert block["type"] == "section"
        assert block["text"]["type"] == "mrkdwn"
        assert "text" in block["text"]

    def test_pr_section_includes_title(self, slack_client_en, sample_stale_pr, sample_team):
        """Test PR section includes PR title."""
        block = slack_client_en._build_pr_section(sample_stale_pr, sample_team)
        text = block["text"]["text"]
        assert "Fix authentication bug" in text

    def test_pr_section_includes_url(self, slack_client_en, sample_stale_pr, sample_team):
        """Test PR section includes PR URL as link."""
        block = slack_client_en._build_pr_section(sample_stale_pr, sample_team)
        text = block["text"]["text"]
        assert "https://github.com/test-org/review-ops/pull/123" in text
        assert "review-ops#123" in text

    def test_pr_section_age_en(self, slack_client_en, sample_stale_pr, sample_team):
        """Test English age format."""
        block = slack_client_en._build_pr_section(sample_stale_pr, sample_team)
        text = block["text"]["text"]
        assert "14 days old" in text

    def test_pr_section_age_ko(self, slack_client_ko, sample_stale_pr, sample_team):
        """Test Korean age format."""
        block = slack_client_ko._build_pr_section(sample_stale_pr, sample_team)
        text = block["text"]["text"]
        assert "14일 묵음" in text
        assert "days old" not in text

    def test_pr_section_review_count_en(self, slack_client_en, sample_stale_pr, sample_team):
        """Test English review count format."""
        block = slack_client_en._build_pr_section(sample_stale_pr, sample_team)
        text = block["text"]["text"]
        assert "2 reviews pending" in text

    def test_pr_section_review_count_ko(self, slack_client_ko, sample_stale_pr, sample_team):
        """Test Korean review count format."""
        block = slack_client_ko._build_pr_section(sample_stale_pr, sample_team)
        text = block["text"]["text"]
        assert "리뷰 2개 대기중" in text
        assert "reviews pending" not in text

    def test_pr_section_author_mention_with_slack_id(
        self, slack_client_en, sample_stale_pr, sample_team
    ):
        """Test author mention uses Slack ID when available."""
        block = slack_client_en._build_pr_section(sample_stale_pr, sample_team)
        text = block["text"]["text"]
        assert "<@U9876543210>" in text  # johndoe's Slack ID

    def test_pr_section_escapes_title(self, slack_client_en, sample_team):
        """Test that PR title is escaped properly."""
        pr = PullRequest(
            repo_name="review-ops",
            number=456,
            title="Fix <script> & XSS",
            author="alice",
            reviewers=[],
            url="https://github.com/test-org/review-ops/pull/456",
            created_at=datetime(2025, 10, 20, 10, 0, 0, tzinfo=UTC),
            ready_at=datetime(2025, 10, 20, 10, 0, 0, tzinfo=UTC),
            current_approvals=0,
            review_status="REVIEW_REQUIRED",
            base_branch="main",
        )
        stale_pr = StalePR(pr=pr, staleness_days=5.0)

        block = slack_client_en._build_pr_section(stale_pr, sample_team)
        text = block["text"]["text"]
        assert "Fix &lt;script&gt; &amp; XSS" in text

    def test_pr_section_utf8_encoding_korean(self, slack_client_ko, sample_team):
        """Test that Korean characters are preserved correctly (UTF-8 encoding)."""
        pr = PullRequest(
            repo_name="review-ops",
            number=789,
            title="버그 수정: 인증 문제 해결",  # Korean: "Bug fix: Resolve auth issue"
            author="김철수",  # Korean name: "Kim Cheolsu"
            reviewers=["박영희", "이민수"],  # Korean names
            url="https://github.com/test-org/review-ops/pull/789",
            created_at=datetime(2025, 10, 20, 10, 0, 0, tzinfo=UTC),
            ready_at=datetime(2025, 10, 20, 10, 0, 0, tzinfo=UTC),
            current_approvals=0,
            review_status="REVIEW_REQUIRED",
            base_branch="main",
        )
        stale_pr = StalePR(pr=pr, staleness_days=7.0)

        block = slack_client_ko._build_pr_section(stale_pr, sample_team)
        text = block["text"]["text"]

        # Verify Korean characters are preserved without corruption
        assert "버그 수정: 인증 문제 해결" in text
        assert "@김철수" in text
        assert "7일 묵음" in text
        assert "리뷰 2개 대기중" in text

        # Ensure no encoding corruption (no question marks, no garbled text)
        assert "?" not in text or "?" in pr.title  # Only if originally in title

    def test_pr_section_utf8_mixed_korean_english(self, slack_client_ko, sample_team):
        """Test that mixed Korean and English content is handled correctly."""
        pr = PullRequest(
            repo_name="review-ops",
            number=999,
            title="Fix API 버그 in authentication flow",  # Mixed Korean/English
            author="johndoe",
            reviewers=["alice"],
            url="https://github.com/test-org/review-ops/pull/999",
            created_at=datetime(2025, 10, 20, 10, 0, 0, tzinfo=UTC),
            ready_at=datetime(2025, 10, 20, 10, 0, 0, tzinfo=UTC),
            current_approvals=0,
            review_status="REVIEW_REQUIRED",
            base_branch="main",
        )
        stale_pr = StalePR(pr=pr, staleness_days=3.0)

        block = slack_client_ko._build_pr_section(stale_pr, sample_team)
        text = block["text"]["text"]

        # Verify mixed content is preserved correctly
        assert "Fix API 버그 in authentication flow" in text
        assert "3일 묵음" in text  # Korean age format
        assert "리뷰 1개 대기중" in text  # Korean review count


class TestBuildTruncationWarning:
    """Tests for _build_truncation_warning method."""

    def test_truncation_warning_structure(self, slack_client_en):
        """Test truncation warning has correct structure."""
        block = slack_client_en._build_truncation_warning(5)
        assert block["type"] == "context"
        assert "elements" in block
        assert len(block["elements"]) == 1
        assert block["elements"][0]["type"] == "mrkdwn"

    def test_truncation_warning_en_single(self, slack_client_en):
        """Test English truncation warning for 1 PR."""
        block = slack_client_en._build_truncation_warning(1)
        text = block["elements"][0]["text"]
        assert "+1 more PR not shown" in text
        assert "GitHub" in text

    def test_truncation_warning_en_multiple(self, slack_client_en):
        """Test English truncation warning for multiple PRs."""
        block = slack_client_en._build_truncation_warning(10)
        text = block["elements"][0]["text"]
        assert "+10 more PRs not shown" in text

    def test_truncation_warning_ko(self, slack_client_ko):
        """Test Korean truncation warning."""
        block = slack_client_ko._build_truncation_warning(5)
        text = block["elements"][0]["text"]
        assert "+5개 더 있음" in text
        assert "GitHub에서 확인하세요" in text


class TestBuildStalenessLegendBlock:
    """Tests for _build_staleness_legend_block method."""

    def test_staleness_legend_structure(self, slack_client_en):
        """Test staleness legend has correct structure."""
        block = slack_client_en._build_staleness_legend_block()
        assert block["type"] == "context"
        assert "elements" in block
        assert len(block["elements"]) == 3

    def test_staleness_legend_elements_are_plain_text(self, slack_client_en):
        """Test all legend elements are plain_text with emoji enabled."""
        block = slack_client_en._build_staleness_legend_block()
        for element in block["elements"]:
            assert element["type"] == "plain_text"
            assert element["emoji"] is True

    def test_staleness_legend_en(self, slack_client_en):
        """Test English staleness legend content."""
        block = slack_client_en._build_staleness_legend_block()
        texts = [elem["text"] for elem in block["elements"]]

        assert ":nauseated_face: Rotten (8d~)" in texts
        assert ":cheese_wedge: Aging (4~7d)" in texts
        assert ":sparkles: Fresh (~3d)" in texts

        # Verify order: worst to best (rotten -> aging -> fresh)
        assert texts[0] == ":nauseated_face: Rotten (8d~)"
        assert texts[1] == ":cheese_wedge: Aging (4~7d)"
        assert texts[2] == ":sparkles: Fresh (~3d)"

    def test_staleness_legend_ko(self, slack_client_ko):
        """Test Korean staleness legend content."""
        block = slack_client_ko._build_staleness_legend_block()
        texts = [elem["text"] for elem in block["elements"]]

        assert ":nauseated_face: 부패 중.. (8d~)" in texts
        assert ":cheese_wedge: 숙성 중.. (4~7d)" in texts
        assert ":sparkles: 신규 (~3d)" in texts

        # Verify order: worst to best (rotten -> aging -> fresh)
        assert texts[0] == ":nauseated_face: 부패 중.. (8d~)"
        assert texts[1] == ":cheese_wedge: 숙성 중.. (4~7d)"
        assert texts[2] == ":sparkles: 신규 (~3d)"


class TestBuildBlocks:
    """Tests for build_blocks method."""

    def test_build_blocks_empty_categories_en(self, slack_client_en, sample_team):
        """Test building blocks with empty categories returns 'all clear' message in English."""
        by_category = {"rotten": [], "aging": [], "fresh": []}
        blocks = slack_client_en.build_blocks(by_category, sample_team)

        # Should return "all clear" message with header + section (table view format)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "header"
        assert blocks[0]["text"]["text"] == f":help: {date.today().isoformat()} Stale PR Board"
        assert blocks[1]["type"] == "section"
        assert "🎉 All clear! No PRs need review" in blocks[1]["text"]["text"]

    def test_build_blocks_empty_categories_ko(self, slack_client_ko, sample_team):
        """Test building blocks with empty categories returns 'all clear' message in Korean."""
        by_category = {"rotten": [], "aging": [], "fresh": []}
        blocks = slack_client_ko.build_blocks(by_category, sample_team)

        # Should return Korean "all clear" message (table view format)
        assert len(blocks) == 2
        assert blocks[0]["type"] == "header"
        assert blocks[0]["text"]["text"] == f":help: {date.today().isoformat()} 리뷰가 필요한 PR들"
        assert blocks[1]["type"] == "section"
        assert "🎉 리뷰 대기 중인 PR이 없습니다" in blocks[1]["text"]["text"]

    def test_build_blocks_single_category(self, slack_client_en, sample_stale_pr, sample_team):
        """Test building blocks with single category (table view format)."""
        by_category = {"rotten": [sample_stale_pr], "aging": [], "fresh": []}
        blocks = slack_client_en.build_blocks(by_category, sample_team)

        # Should have board header + legend + table (table view format)
        assert len(blocks) == 3
        assert blocks[0]["type"] == "header"
        assert blocks[0]["text"]["text"] == f":help: {date.today().isoformat()} Stale PR Board"
        assert blocks[1]["type"] == "context"
        assert blocks[2]["type"] == "table"
        # Table should have 1 header row + 1 data row
        assert len(blocks[2]["rows"]) == 2

    def test_build_blocks_multiple_categories(self, slack_client_en, sample_stale_pr, sample_team):
        """Test building blocks with multiple categories (table view format)."""
        by_category = {
            "rotten": [sample_stale_pr],
            "aging": [sample_stale_pr],
            "fresh": [sample_stale_pr],
        }
        blocks = slack_client_en.build_blocks(by_category, sample_team)

        # Should have: board header + legend + table (all PRs in single table)
        assert len(blocks) == 3
        assert blocks[0]["type"] == "header"
        assert blocks[1]["type"] == "context"
        assert blocks[2]["type"] == "table"
        # Table should have 1 header row + 3 data rows
        assert len(blocks[2]["rows"]) == 4

    def test_build_blocks_skips_empty_categories(
        self, slack_client_en, sample_stale_pr, sample_team
    ):
        """Test that empty categories are skipped (table view format)."""
        by_category = {"rotten": [], "aging": [sample_stale_pr], "fresh": []}
        blocks = slack_client_en.build_blocks(by_category, sample_team)

        # Should have board header + legend + table with single PR
        assert len(blocks) == 3
        assert blocks[0]["type"] == "header"
        assert blocks[0]["text"]["text"] == f":help: {date.today().isoformat()} Stale PR Board"
        assert blocks[1]["type"] == "context"
        assert blocks[2]["type"] == "table"
        assert len(blocks[2]["rows"]) == 2  # 1 header + 1 data row


class TestPostStalePRSummary:
    """Tests for post_stale_pr_summary method."""

    def test_post_stale_pr_summary_success(self, slack_client_en, sample_stale_pr, sample_team):
        """Test successful posting of stale PR summary."""
        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            slack_client_en.post_stale_pr_summary([sample_stale_pr], sample_team)

            # Verify request was made
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == slack_client_en.webhook_url
            assert "blocks" in call_args[1]["json"]

    def test_post_stale_pr_summary_failure(self, slack_client_en, sample_stale_pr, sample_team):
        """Test handling of failed posting."""
        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "invalid_payload"
            mock_post.return_value = mock_response

            with pytest.raises(Exception, match="Failed to send Slack message"):
                slack_client_en.post_stale_pr_summary([sample_stale_pr], sample_team)

    def test_post_stale_pr_summary_groups_by_category(
        self, slack_client_en, sample_team
    ):
        """Test that PRs are correctly displayed in table view format."""
        pr_rotten = PullRequest(
            repo_name="repo",
            number=1,
            title="Rotten",
            author="alice",
            reviewers=[],
            url="https://github.com/test/repo/pull/1",
            created_at=datetime(2025, 10, 1, 10, 0, 0, tzinfo=UTC),
            ready_at=datetime(2025, 10, 1, 10, 0, 0, tzinfo=UTC),
            current_approvals=0,
            review_status=None,
            base_branch="main",
        )
        pr_fresh = PullRequest(
            repo_name="repo",
            number=2,
            title="Fresh",
            author="bob",
            reviewers=[],
            url="https://github.com/test/repo/pull/2",
            created_at=datetime(2025, 10, 29, 10, 0, 0, tzinfo=UTC),
            ready_at=datetime(2025, 10, 29, 10, 0, 0, tzinfo=UTC),
            current_approvals=0,
            review_status=None,
            base_branch="main",
        )

        stale_prs = [
            StalePR(pr=pr_rotten, staleness_days=10.0),  # rotten (8+)
            StalePR(pr=pr_fresh, staleness_days=2.0),  # fresh (1-3)
        ]

        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            slack_client_en.post_stale_pr_summary(stale_prs, sample_team)

            # Verify blocks were sent with table format
            call_args = mock_post.call_args
            blocks = call_args[1]["json"]["blocks"]

            # Should have board header + legend + table
            assert len(blocks) == 3
            assert blocks[0]["type"] == "header"
            assert blocks[0]["text"]["text"] == f":help: {date.today().isoformat()} Stale PR Board"
            assert blocks[1]["type"] == "context"
            assert blocks[2]["type"] == "table"
            # Table should have 1 header + 2 data rows (sorted by staleness descending)
            assert len(blocks[2]["rows"]) == 3


class TestTruncation:
    """Tests for truncation functionality."""

    def test_truncation_applies_at_limit(self, slack_client_en, sample_team):
        """Test that truncation applies at max_prs_total (table view format)."""
        # Create 20 PRs (more than limit of 10)
        prs = []
        for i in range(20):
            pr = PullRequest(
                repo_name="repo",
                number=i,
                title=f"PR {i}",
                author="alice",
                reviewers=[],
                url=f"https://github.com/test/repo/pull/{i}",
                created_at=datetime(2025, 10, 20, 10, 0, 0, tzinfo=UTC),
                ready_at=datetime(2025, 10, 20, 10, 0, 0, tzinfo=UTC),
                current_approvals=0,
                review_status=None,
                base_branch="main",
            )
            prs.append(StalePR(pr=pr, staleness_days=5.0))

        by_category = {"aging": prs, "rotten": [], "fresh": []}

        # Test with max_prs_total=10 to trigger truncation
        slack_client_limited = SlackClient(
            webhook_url="https://hooks.slack.com/test",
            language="en",
            max_prs_total=10
        )
        blocks = slack_client_limited.build_blocks(by_category, sample_team)

        # Should have: board header + legend + table + truncation warning
        assert len(blocks) == 4
        assert blocks[0]["type"] == "header"
        assert blocks[1]["type"] == "context"  # legend
        assert blocks[2]["type"] == "table"

        # Table should have 11 rows: 1 header + 10 data rows (truncated)
        assert len(blocks[2]["rows"]) == 11

        # Find context block (truncation warning)
        assert blocks[3]["type"] == "context"
        warning_text = blocks[3]["elements"][0]["text"]
        assert "+10" in warning_text  # 20 - 10 = 10


class TestPRAllocationLogic:
    """Tests for priority-based PR allocation logic."""

    def test_allocate_pr_display_prioritizes_staleness(self):
        """Test that PRs are allocated by staleness priority: rotten > aging > fresh."""
        # Create PRs for each category
        rotten_prs = []
        for i in range(15):
            pr = PullRequest(
                repo_name="repo",
                number=i,
                title=f"Rotten PR {i}",
                author="alice",
                reviewers=[],
                url=f"https://github.com/test/repo/pull/{i}",
                created_at=datetime(2025, 10, 1, 10, 0, 0, tzinfo=UTC),
                ready_at=datetime(2025, 10, 1, 10, 0, 0, tzinfo=UTC),
                current_approvals=0,
                review_status=None,
                base_branch="main",
            )
            rotten_prs.append(StalePR(pr=pr, staleness_days=15.0))

        aging_prs = []
        for i in range(100, 115):  # 15 PRs
            pr = PullRequest(
                repo_name="repo",
                number=i,
                title=f"Aging PR {i}",
                author="bob",
                reviewers=[],
                url=f"https://github.com/test/repo/pull/{i}",
                created_at=datetime(2025, 10, 15, 10, 0, 0, tzinfo=UTC),
                ready_at=datetime(2025, 10, 15, 10, 0, 0, tzinfo=UTC),
                current_approvals=0,
                review_status=None,
                base_branch="main",
            )
            aging_prs.append(StalePR(pr=pr, staleness_days=5.0))

        fresh_prs = []
        for i in range(200, 215):  # 15 PRs
            pr = PullRequest(
                repo_name="repo",
                number=i,
                title=f"Fresh PR {i}",
                author="charlie",
                reviewers=[],
                url=f"https://github.com/test/repo/pull/{i}",
                created_at=datetime(2025, 10, 29, 10, 0, 0, tzinfo=UTC),
                ready_at=datetime(2025, 10, 29, 10, 0, 0, tzinfo=UTC),
                current_approvals=0,
                review_status=None,
                base_branch="main",
            )
            fresh_prs.append(StalePR(pr=pr, staleness_days=1.0))

        by_category = {"rotten": rotten_prs, "aging": aging_prs, "fresh": fresh_prs}

        # Test with max_prs_total=20 (less than 45 total PRs)
        client = SlackClient(
            webhook_url="https://hooks.slack.com/test", language="en", max_prs_total=20
        )

        allocated, truncated_count = client._allocate_pr_display(by_category)

        # Should show all 15 rotten PRs (highest priority)
        assert len(allocated["rotten"]) == 15

        # Should show 5 aging PRs (remaining budget: 20 - 15 = 5)
        assert len(allocated["aging"]) == 5

        # Should show 0 fresh PRs (budget exhausted)
        assert len(allocated["fresh"]) == 0

        # Should have truncated 25 PRs (45 total - 20 displayed)
        assert truncated_count == 25

    def test_allocate_pr_display_with_enough_budget(self):
        """Test allocation when budget is sufficient for all PRs."""
        # Create small number of PRs
        rotten_prs = []
        for i in range(5):
            pr = PullRequest(
                repo_name="repo",
                number=i,
                title=f"Rotten PR {i}",
                author="alice",
                reviewers=[],
                url=f"https://github.com/test/repo/pull/{i}",
                created_at=datetime(2025, 10, 1, 10, 0, 0, tzinfo=UTC),
                ready_at=datetime(2025, 10, 1, 10, 0, 0, tzinfo=UTC),
                current_approvals=0,
                review_status=None,
                base_branch="main",
            )
            rotten_prs.append(StalePR(pr=pr, staleness_days=15.0))

        aging_prs = []
        for i in range(100, 110):  # 10 PRs
            pr = PullRequest(
                repo_name="repo",
                number=i,
                title=f"Aging PR {i}",
                author="bob",
                reviewers=[],
                url=f"https://github.com/test/repo/pull/{i}",
                created_at=datetime(2025, 10, 15, 10, 0, 0, tzinfo=UTC),
                ready_at=datetime(2025, 10, 15, 10, 0, 0, tzinfo=UTC),
                current_approvals=0,
                review_status=None,
                base_branch="main",
            )
            aging_prs.append(StalePR(pr=pr, staleness_days=5.0))

        fresh_prs = []
        for i in range(200, 205):  # 5 PRs
            pr = PullRequest(
                repo_name="repo",
                number=i,
                title=f"Fresh PR {i}",
                author="charlie",
                reviewers=[],
                url=f"https://github.com/test/repo/pull/{i}",
                created_at=datetime(2025, 10, 29, 10, 0, 0, tzinfo=UTC),
                ready_at=datetime(2025, 10, 29, 10, 0, 0, tzinfo=UTC),
                current_approvals=0,
                review_status=None,
                base_branch="main",
            )
            fresh_prs.append(StalePR(pr=pr, staleness_days=1.0))

        by_category = {"rotten": rotten_prs, "aging": aging_prs, "fresh": fresh_prs}

        # Test with max_prs_total=30 (more than 20 total PRs)
        client = SlackClient(
            webhook_url="https://hooks.slack.com/test", language="en", max_prs_total=30
        )

        allocated, truncated_count = client._allocate_pr_display(by_category)

        # Should show all PRs (budget sufficient)
        assert len(allocated["rotten"]) == 5
        assert len(allocated["aging"]) == 10
        assert len(allocated["fresh"]) == 5

        # No truncation
        assert truncated_count == 0

    def test_allocate_pr_display_empty_categories(self):
        """Test allocation with empty categories."""
        rotten_prs = []
        aging_prs = []
        for i in range(25):
            pr = PullRequest(
                repo_name="repo",
                number=i,
                title=f"Aging PR {i}",
                author="bob",
                reviewers=[],
                url=f"https://github.com/test/repo/pull/{i}",
                created_at=datetime(2025, 10, 15, 10, 0, 0, tzinfo=UTC),
                ready_at=datetime(2025, 10, 15, 10, 0, 0, tzinfo=UTC),
                current_approvals=0,
                review_status=None,
                base_branch="main",
            )
            aging_prs.append(StalePR(pr=pr, staleness_days=5.0))

        fresh_prs = []

        by_category = {"rotten": rotten_prs, "aging": aging_prs, "fresh": fresh_prs}

        # Test with max_prs_total=20
        client = SlackClient(
            webhook_url="https://hooks.slack.com/test", language="en", max_prs_total=20
        )

        allocated, truncated_count = client._allocate_pr_display(by_category)

        # Rotten is empty, so full budget goes to aging
        assert len(allocated["rotten"]) == 0
        assert len(allocated["aging"]) == 20
        assert len(allocated["fresh"]) == 0

        # Should have truncated 5 aging PRs (25 - 20)
        assert truncated_count == 5
