"""Slack webhook client for sending notifications."""

from __future__ import annotations

import requests

from models import StalePR, TeamMember


class SlackClient:
    """Client for sending messages to Slack via webhooks."""

    def __init__(self, webhook_url: str) -> None:
        """
        Initialize Slack client with webhook URL.

        Args:
            webhook_url: Slack incoming webhook URL
        """
        self.webhook_url = webhook_url

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
                review_status_display = self._format_review_status(pr.review_status, pr.current_approvals)

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
            review_status: GitHub's review status (APPROVED, CHANGES_REQUESTED, REVIEW_REQUIRED, or None)
            current_approvals: Number of current approvals

        Returns:
            Formatted status string with emoji
        """
        if review_status == "APPROVED":
            return f"✅ Approved ({current_approvals} approval{'s' if current_approvals != 1 else ''})"
        elif review_status == "CHANGES_REQUESTED":
            return "🔴 Changes requested"
        elif review_status == "REVIEW_REQUIRED":
            return f"⏳ Review required ({current_approvals} approval{'s' if current_approvals != 1 else ''})"
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
