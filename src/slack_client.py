"""Slack webhook client for sending notifications."""

from __future__ import annotations

import requests

from models import StalePR, TeamMember


class SlackClient:
    """Client for sending messages to Slack via webhooks."""

    MAX_PRS_PER_CATEGORY = 15
    """Maximum number of PRs to display per category before truncation"""

    def __init__(self, webhook_url: str, language: str = "en") -> None:
        """
        Initialize Slack client with webhook URL and language.

        Args:
            webhook_url: Slack incoming webhook URL
            language: Language code for message formatting ('en' or 'ko', default: 'en')
        """
        self.webhook_url = webhook_url
        self.language = language

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

    def build_blocks(
        self, by_category: dict[str, list[StalePR]], team_members: list[TeamMember]
    ) -> list[dict]:
        """
        Construct Block Kit blocks for all categories.

        Public API for building Block Kit message blocks without sending.
        Useful for dry-run mode, testing, and custom integrations.

        Args:
            by_category: Dictionary mapping category names to lists of StalePRs
            team_members: List of team members for @mentions

        Returns:
            List of Block Kit block dictionaries ready for Slack API
        """
        blocks = []

        # Add blocks for each category (rotten, aging, fresh)
        for category in ["rotten", "aging", "fresh"]:
            prs_in_category = by_category.get(category, [])
            if not prs_in_category:
                continue  # Skip empty categories

            # Add category blocks
            category_blocks = self._build_category_blocks(
                category, prs_in_category, team_members
            )
            blocks.extend(category_blocks)

            # Add divider after each category (except the last one)
            blocks.append({"type": "divider"})

        # Remove trailing divider if exists
        if blocks and blocks[-1].get("type") == "divider":
            blocks.pop()

        # If no blocks were created (all categories empty), return "all clear" message
        if not blocks:
            blocks = self._build_empty_state_blocks()

        return blocks

    def _build_category_blocks(
        self, category: str, prs: list[StalePR], team_members: list[TeamMember]
    ) -> list[dict]:
        """
        Build blocks for a single category with truncation.

        Args:
            category: Category name ('rotten', 'aging', or 'fresh')
            prs: List of PRs in this category
            team_members: List of team members for @mentions

        Returns:
            List of blocks for this category
        """
        blocks = []

        # Add header block
        blocks.append(self._build_header_block(category))

        # Add PR sections (truncate to MAX_PRS_PER_CATEGORY)
        displayed_prs = prs[: self.MAX_PRS_PER_CATEGORY]
        for stale_pr in displayed_prs:
            blocks.append(self._build_pr_section(stale_pr, team_members))

        # Add truncation warning if needed
        if len(prs) > self.MAX_PRS_PER_CATEGORY:
            truncated_count = len(prs) - self.MAX_PRS_PER_CATEGORY
            blocks.append(self._build_truncation_warning(truncated_count))

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
        if self.language == "ko":
            header_text = "🎉 모든 PR 리뷰 완료!"
            message_text = (
                "축하합니다! 리뷰 대기 중인 PR이 없습니다. "
                "팀이 모든 코드 리뷰를 완료했습니다!"
            )
        else:
            header_text = "🎉 All Clear!"
            message_text = (
                "Great news! No stale PRs found. "
                "The team is all caught up on code reviews!"
            )

        return [
            {"type": "header", "text": {"type": "plain_text", "text": header_text, "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": message_text}},
        ]

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
