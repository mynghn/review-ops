"""Slack webhook client for sending notifications."""

from __future__ import annotations

import requests

from models import PullRequest, StalePR, TeamMember


class SlackClient:
    """Client for sending messages to Slack via webhooks."""

    def __init__(self, webhook_url: str, language: str = "en", max_prs_total: int = 30) -> None:
        """
        Initialize Slack client with webhook URL and language.

        Args:
            webhook_url: Slack incoming webhook URL
            language: Language code for message formatting ('en' or 'ko', default: 'en')
            max_prs_total: Total PRs to display across all categories (default: 30)
        """
        self.webhook_url = webhook_url
        self.language = language
        self.max_prs_total = max_prs_total

    def format_message(self, stale_prs: list[StalePR], team_members: list[TeamMember]) -> str:
        """
        Format stale PRs into a Slack message.

        Args:
            stale_prs: List of stale pull requests sorted by staleness
            team_members: List of team members for @mentions

        Returns:
            Formatted message string for Slack
        """
        if not stale_prs:
            return self._format_no_stale_prs_message()

        return self._format_stale_prs_message(stale_prs, team_members)

    def _format_no_stale_prs_message(self) -> str:
        """Format a celebratory message when there are no stale PRs."""
        return "🎉 Great news! No stale PRs found. The team is all caught up on code reviews!"

    def _format_stale_prs_message(
        self, stale_prs: list[StalePR], team_members: list[TeamMember]
    ) -> str:
        """
        Format stale PRs into a detailed message.

        Args:
            stale_prs: List of stale pull requests
            team_members: List of team members for @mentions

        Returns:
            Formatted message with PR details
        """
        # Create username to slack ID mapping
        username_to_slack_id = {
            member.github_username: member.slack_user_id
            for member in team_members
            if member.slack_user_id
        }

        lines = [
            f"📋 *Stale PR Report* - {len(stale_prs)} PRs need review\n",
        ]

        # Group by category
        by_category: dict[str, list[StalePR]] = {"rotten": [], "aging": [], "fresh": []}
        for stale_pr in stale_prs:
            by_category[stale_pr.category].append(stale_pr)

        # Add each category
        for category in ["rotten", "aging", "fresh"]:
            prs_in_category = by_category[category]
            if not prs_in_category:
                continue

            # Category header
            if category == "rotten":
                lines.append("\n🤢 *Rotten* (8+ days)")
            elif category == "aging":
                lines.append("\n🧀 *Aging* (4-7 days)")
            else:
                lines.append("\n✨ *Fresh* (1-3 days)")

            # Add each PR
            for stale_pr in prs_in_category:
                pr = stale_pr.pr
                days = int(stale_pr.staleness_days)

                # Format author mention
                author_mention = self._format_user_mention(pr.author, username_to_slack_id)

                # Format reviewers
                reviewer_mentions = [
                    self._format_user_mention(reviewer, username_to_slack_id)
                    for reviewer in pr.reviewers
                ]
                reviewers_str = ", ".join(reviewer_mentions) if reviewer_mentions else "none"

                # Format review status display
                review_status_display = self._format_review_status(
                    pr.review_status, pr.current_approvals
                )

                # Format PR line
                lines.append(
                    f"• <{pr.url}|{pr.repo_name}#{pr.number}> - {pr.title}\n"
                    f"  Author: {author_mention} | Reviewers: {reviewers_str}\n"
                    f"  Status: {review_status_display} | {days} day{'s' if days != 1 else ''} old"
                )

        return "\n".join(lines)

    def _format_review_status(self, review_status: str | None, current_approvals: int) -> str:
        """
        Format review status for display.

        Args:
            review_status: GitHub's review status
                (APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED, or None)
            current_approvals: Number of current approvals

        Returns:
            Formatted status string with emoji
        """
        if review_status == "APPROVED":
            plural = "s" if current_approvals != 1 else ""
            return f"✅ Approved ({current_approvals} approval{plural})"
        elif review_status == "CHANGES_REQUESTED":
            return "🔴 Changes requested"
        elif review_status == "REVIEW_REQUIRED":
            plural = "s" if current_approvals != 1 else ""
            return f"⏳ Review required ({current_approvals} approval{plural})"
        elif review_status is None:
            # Fallback when gh CLI unavailable or no review requirements
            if current_approvals > 0:
                return f"👀 {current_approvals} approval{'s' if current_approvals != 1 else ''}"
            return "⏳ Awaiting review"
        else:
            return f"❓ {review_status}"

    def _format_user_mention(
        self, github_username: str, username_to_slack_id: dict[str, str]
    ) -> str:
        """
        Format a user mention for Slack.

        Args:
            github_username: GitHub username
            username_to_slack_id: Mapping of GitHub username to Slack user ID

        Returns:
            Formatted mention (e.g., <@U1234567890> or @username)
        """
        slack_id = username_to_slack_id.get(github_username)
        if slack_id:
            return f"<@{slack_id}>"
        return f"@{github_username}"

    def send_message(self, message: str) -> None:
        """
        Send a message to Slack via webhook.

        Args:
            message: Text message to send

        Raises:
            Exception: If the webhook request fails
        """
        payload = {"text": message}
        response = requests.post(self.webhook_url, json=payload, timeout=10)

        if response.status_code != 200:
            msg = f"Failed to send Slack message: {response.status_code} - {response.text}"
            raise Exception(msg)

    # Block Kit formatting methods

    def post_stale_pr_summary(
        self, stale_prs: list[StalePR], team_members: list[TeamMember]
    ) -> None:
        """
        Post a Block Kit formatted stale PR summary to Slack.

        Args:
            stale_prs: List of stale pull requests sorted by staleness
            team_members: List of team members for @mentions

        Raises:
            Exception: If the webhook request fails
        """
        # Group PRs by category
        by_category: dict[str, list[StalePR]] = {"rotten": [], "aging": [], "fresh": []}
        for stale_pr in stale_prs:
            by_category[stale_pr.category].append(stale_pr)

        # Build blocks
        blocks = self.build_blocks(by_category, team_members)

        # Send to Slack
        payload = {"blocks": blocks}
        response = requests.post(self.webhook_url, json=payload, timeout=10)

        if response.status_code != 200:
            msg = f"Failed to send Slack message: {response.status_code} - {response.text}"
            raise Exception(msg)

    def _allocate_pr_display(
        self, by_category: dict[str, list[StalePR]]
    ) -> tuple[dict[str, list[StalePR]], int]:
        """
        Allocate PRs from total budget, prioritizing staleness (rotten → aging → fresh).

        Args:
            by_category: Dict mapping category to full PR lists

        Returns:
            Tuple of (allocated dict, total truncated count)
        """
        remaining = self.max_prs_total
        total_original = sum(len(prs) for prs in by_category.values())

        # Allocate in priority order: rotten → aging → fresh
        # Initialize all categories to ensure keys exist
        allocated = {"rotten": [], "aging": [], "fresh": []}
        for category in ["rotten", "aging", "fresh"]:
            prs = by_category.get(category, [])
            allocated[category] = prs[:remaining]
            remaining -= len(allocated[category])
            if remaining <= 0:
                break

        total_allocated = sum(len(prs) for prs in allocated.values())
        total_truncated = max(0, total_original - total_allocated)

        return allocated, total_truncated

    def build_blocks(
        self, by_category: dict[str, list[StalePR]], team_members: list[TeamMember]
    ) -> list[dict]:
        """
        Construct Block Kit blocks with table format.

        Public API for building Block Kit message blocks without sending.
        Useful for dry-run mode, testing, and custom integrations.

        Args:
            by_category: Dictionary mapping category names to lists of StalePRs
            team_members: List of team members for @mentions

        Returns:
            List of Block Kit block dictionaries ready for Slack API
        """
        # Flatten and sort all PRs by staleness descending (stalest first)
        all_prs = []
        for category in ["rotten", "aging", "fresh"]:
            all_prs.extend(by_category.get(category, []))

        all_prs.sort(key=lambda pr: pr.staleness_days, reverse=True)

        # Handle empty state
        if not all_prs:
            return self._build_empty_state_blocks()

        # Truncate to display limit (cap at 99 data rows + 1 header = 100 total)
        display_limit = min(self.max_prs_total, 99)
        displayed_prs = all_prs[:display_limit]
        truncated_count = len(all_prs) - len(displayed_prs)

        # Build blocks
        blocks = []

        # Add header block
        blocks.append(self._build_board_header_block())

        # Build table block
        table_rows = [self._build_table_header_row()]
        for stale_pr in displayed_prs:
            table_rows.append(self._build_table_data_row(stale_pr, team_members))

        table_block = {
            "type": "table",
            "column_settings": [
                {"align": "center"},  # Staleness
                {"align": "center"},  # Age
                {"align": "left"},  # PR
                {"align": "center"},  # Author
                {"align": "left"},  # Reviewers
            ],
            "rows": table_rows,
        }
        blocks.append(table_block)

        # Add truncation warning if needed
        if truncated_count > 0:
            blocks.append(self._build_truncation_warning(truncated_count))

        return blocks

    def _build_category_blocks(
        self, category: str, prs: list[StalePR], team_members: list[TeamMember]
    ) -> list[dict]:
        """
        Build blocks for a single category (pre-allocated, no truncation).

        Args:
            category: Category name ('rotten', 'aging', or 'fresh')
            prs: List of PRs in this category (already allocated from budget)
            team_members: List of team members for @mentions

        Returns:
            List of blocks for this category
        """
        blocks = []

        # Add header block
        blocks.append(self._build_header_block(category))

        # Add PR sections (already allocated, no further truncation)
        for stale_pr in prs:
            blocks.append(self._build_pr_section(stale_pr, team_members))

        return blocks

    def _build_header_block(self, category: str) -> dict:
        """
        Create header block for a category (language-aware).

        Args:
            category: Category name ('rotten', 'aging', or 'fresh')

        Returns:
            Block Kit header block dictionary
        """
        if category == "rotten":
            text = "🤢 PR 부패 중..." if self.language == "ko" else "🤢 Rotten PRs"
        elif category == "aging":
            text = "🧀 PR 숙성 중..." if self.language == "ko" else "🧀 Aging PRs"
        else:  # fresh
            text = "✨ 갓 태어난 PR" if self.language == "ko" else "✨ Fresh PRs"

        return {"type": "header", "text": {"type": "plain_text", "text": text, "emoji": True}}

    def _build_pr_section(self, stale_pr: StalePR, team_members: list[TeamMember]) -> dict:
        """
        Create section block for a single PR with mrkdwn formatting.

        Args:
            stale_pr: The stale PR to format
            team_members: List of team members for @mentions

        Returns:
            Block Kit section block dictionary
        """
        pr = stale_pr.pr
        days = int(stale_pr.staleness_days)

        # Create username to slack ID mapping
        username_to_slack_id = {
            member.github_username: member.slack_user_id
            for member in team_members
            if member.slack_user_id
        }

        # Format author mention
        author_mention = self._format_user_mention(pr.author, username_to_slack_id)

        # Format age string (language-aware)
        age_text = f"{days}일 묵음" if self.language == "ko" else f"{days} days old"

        # Format review count (language-aware)
        review_count = len(pr.reviewers)
        if self.language == "ko":
            review_text = f"리뷰 {review_count}개 대기중"
        else:
            review_text = f"{review_count} review{'s' if review_count != 1 else ''} pending"

        # Build mrkdwn text
        escaped_title = self._escape_mrkdwn(pr.title)
        text = (
            f"*<{pr.url}|{pr.repo_name}#{pr.number}: {escaped_title}>*\n"
            f":bust_in_silhouette: {author_mention} • "
            f":clock3: {age_text} • "
            f":eyes: {review_text}"
        )

        return {"type": "section", "text": {"type": "mrkdwn", "text": text}}

    def _build_truncation_warning(self, count: int) -> dict:
        """
        Create context block warning about truncated PRs.

        Args:
            count: Number of PRs not shown

        Returns:
            Block Kit context block dictionary
        """
        if self.language == "ko":
            warning_text = f"⚠️ +{count}개 더 있음. 전체 목록은 GitHub에서 확인하세요."
        else:
            plural = "s" if count != 1 else ""
            warning_text = (
                f"⚠️ +{count} more PR{plural} not shown. "
                "Check GitHub for full list."
            )

        return {"type": "context", "elements": [{"type": "mrkdwn", "text": warning_text}]}

    def _build_empty_state_blocks(self) -> list[dict]:
        """
        Create "all clear" Block Kit message when no PRs exist.

        Returns:
            List of blocks for empty state message
        """
        messages = {
            "en": "🎉 All clear! No PRs need review",
            "ko": "🎉 리뷰 대기 중인 PR이 없습니다",
        }

        return [
            self._build_board_header_block(),
            {"type": "section", "text": {"type": "mrkdwn", "text": messages[self.language]}},
        ]

    def _build_board_header_block(self) -> dict:
        """
        Build header block with board title.

        Returns:
            Block Kit header block dictionary
        """
        titles = {
            "en": ":calendar: Code Review Board",
            "ko": ":calendar: 코드 리뷰 현황판",
        }
        return {
            "type": "header",
            "text": {"type": "plain_text", "text": titles[self.language], "emoji": True},
        }

    def _escape_mrkdwn(self, text: str) -> str:
        """
        Escape special characters to prevent unintended mrkdwn formatting.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for mrkdwn
        """
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text

    # Table View Helper Methods

    def _build_table_header_row(self) -> list[dict]:
        """
        Build table header row with bilingual column labels.

        Returns:
            List of 5 rich_text cells with bold column headers
        """
        headers = {
            "en": ["Staleness", "Age", "PR", "Author", "Reviewers"],
            "ko": ["숙성도", "경과", "PR", "Author", "리뷰어"],
        }

        header_texts = headers[self.language]

        return [
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [{"type": "text", "text": text, "style": {"bold": True}}],
                    }
                ],
            }
            for text in header_texts
        ]

    def _build_table_data_row(
        self, stale_pr: StalePR, team_members: list[TeamMember]
    ) -> list[dict]:
        """
        Build table data row for a single PR.

        Args:
            stale_pr: The stale PR to format
            team_members: List of team members for Slack user ID mapping

        Returns:
            List of 5 rich_text cells representing one table row
        """
        pr = stale_pr.pr

        # Create username to slack ID mapping
        username_to_slack_id = {
            member.github_username: member.slack_user_id
            for member in team_members
            if member.slack_user_id
        }

        # Column 1: Staleness emoji
        emoji_name = self._get_staleness_emoji(stale_pr.category)
        col_staleness = self._build_rich_text_cell([{"type": "emoji", "name": emoji_name}])

        # Column 2: Age
        age_text = f"{int(stale_pr.staleness_days)}d"
        col_age = self._build_rich_text_cell([{"type": "text", "text": age_text}])

        # Column 3: PR details (repo#number + link)
        pr_elements = [
            {"type": "text", "text": f"{pr.repo_name}#{pr.number}\n"},
            {"type": "link", "text": pr.title, "url": pr.url},
        ]
        col_pr = self._build_rich_text_cell(pr_elements)

        # Column 4: Author
        author_slack_id = username_to_slack_id.get(pr.author)
        if author_slack_id:
            author_elements = [{"type": "user", "user_id": author_slack_id}]
        else:
            author_elements = [{"type": "text", "text": f"@{pr.author}"}]
        col_author = self._build_rich_text_cell(author_elements)

        # Column 5: Reviewers (including GitHub teams)
        reviewer_elements = self._build_reviewer_elements(pr, team_members)
        col_reviewers = self._build_rich_text_cell(reviewer_elements)

        return [col_staleness, col_age, col_pr, col_author, col_reviewers]

    def _get_staleness_emoji(self, category: str) -> str:
        """
        Map category to Slack emoji name.

        Args:
            category: Category name ('rotten', 'aging', or 'fresh')

        Returns:
            Slack emoji name (e.g., 'nauseated_face')
        """
        emoji_map = {
            "rotten": "nauseated_face",
            "aging": "cheese_wedge",
            "fresh": "sparkles",
        }
        return emoji_map[category]

    def _build_rich_text_cell(self, elements: list[dict]) -> dict:
        """
        Wrap elements in rich_text cell structure for table cells.

        Args:
            elements: List of rich_text_section elements (text, emoji, link, user)

        Returns:
            Rich text cell dictionary
        """
        return {
            "type": "rich_text",
            "elements": [{"type": "rich_text_section", "elements": elements}],
        }

    def _build_reviewer_elements(
        self, pr: PullRequest, team_members: list[TeamMember]
    ) -> list[dict]:
        """
        Build reviewer elements with user mentions separated by newlines.
        GitHub teams are shown first with format "team-name: @user1 @user2",
        followed by remaining individual reviewers (with deduplication).

        Args:
            pr: PullRequest object with reviewers and github_team_reviewers
            team_members: List of team members for Slack user ID mapping

        Returns:
            List of elements (user mentions + newlines, or single dash if empty)
        """
        # Collect all reviewers to display
        all_reviewer_usernames = set()  # For deduplication
        elements = []

        username_to_slack_id = {
            member.github_username: member.slack_user_id
            for member in team_members
            if member.slack_user_id
        }

        def add_user_mention(username: str) -> None:
            """Helper to add a user mention element."""
            slack_id = username_to_slack_id.get(username)
            if slack_id:
                elements.append({"type": "user", "user_id": slack_id})
            else:
                # Fallback to @username if no Slack ID
                elements.append({"type": "text", "text": f"@{username}"})

        # First, collect GitHub team members for deduplication
        for github_team in pr.github_team_reviewers:
            all_reviewer_usernames.update(github_team.members)

        # Calculate remaining individual reviewers after deduplication
        remaining_reviewers = [r for r in pr.reviewers if r not in all_reviewer_usernames]

        # Now display GitHub teams with their members
        for i, github_team in enumerate(pr.github_team_reviewers):
            # Add team name prefix with @ and opening parenthesis
            elements.append({"type": "text", "text": f"@{github_team.team_name} ("})

            # Add team members
            if github_team.members:
                for j, member in enumerate(github_team.members):
                    add_user_mention(member)

                    # Add comma+space between team members (but not after the last one)
                    if j < len(github_team.members) - 1:
                        elements.append({"type": "text", "text": ", "})

                # Close parenthesis after members
                elements.append({"type": "text", "text": ")"})
            else:
                # Empty team or failed to fetch members - close with "no members)"
                elements.append({"type": "text", "text": "no members)"})

            # Add newline after each team (if there are more teams or remaining reviewers)
            if i < len(pr.github_team_reviewers) - 1 or remaining_reviewers:
                elements.append({"type": "text", "text": "\n"})

        for i, reviewer in enumerate(remaining_reviewers):
            add_user_mention(reviewer)

            # Add newline between reviewers (but not after the last one)
            if i < len(remaining_reviewers) - 1:
                elements.append({"type": "text", "text": "\n"})

        # If no reviewers at all, show dash
        if not elements:
            return [{"type": "text", "text": "-"}]

        return elements
