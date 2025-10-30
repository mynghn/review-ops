"""Main application entry point for the Stale PR Board."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from config import load_config, load_team_members
from github_client import GitHubClient
from models import StalePR
from slack_client import SlackClient
from staleness import calculate_staleness


def setup_logging(log_level: str) -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    """
    Main entry point for the stale PR detection application.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Detect stale PRs and notify via Slack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print message to console instead of sending to Slack (no webhook needed)",
    )
    args = parser.parse_args()

    try:
        # In dry-run mode, provide a dummy Slack webhook URL if not set
        if args.dry_run and not os.getenv("SLACK_WEBHOOK_URL"):
            os.environ["SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/services/DUMMY/DRYRUN/MODE"

        # Load configuration
        config = load_config()
        setup_logging(config.log_level)
        logger = logging.getLogger(__name__)

        if args.dry_run:
            logger.info("Starting Stale PR Board (DRY RUN MODE - no Slack sending)")
        else:
            logger.info("Starting Stale PR Board")
        logger.debug(f"Configuration: org={config.github_org}, log_level={config.log_level}")

        # Load team members
        team_members = load_team_members()
        logger.info(f"Loaded {len(team_members)} team members")

        # DEBUG: Print team members
        if args.dry_run:
            print("\n" + "=" * 80)
            print("DEBUG: Team members being searched:")
            print("=" * 80)
            for member in team_members:
                print(f"  - {member.github_username}")
            print("=" * 80 + "\n")

        # Initialize clients
        github_client = GitHubClient(token=config.github_token)
        slack_client = SlackClient(webhook_url=config.slack_webhook_url)

        # Fetch PRs involving team members using GitHub Search API
        logger.info(f"Searching for open PRs involving team members in: {config.github_org}")
        team_usernames = {member.github_username for member in team_members}
        team_prs = github_client.fetch_team_prs(config.github_org, team_usernames)
        logger.info(f"Found {len(team_prs)} open PRs involving team members")

        # DEBUG: Print all PRs found
        if args.dry_run and team_prs:
            print("\n" + "=" * 80)
            print("DEBUG: All open PRs found involving team members:")
            print("=" * 80)
            for pr in team_prs:
                print(f"  {pr.repo_name}#{pr.number}: {pr.title}")
                print(f"    Author: {pr.author}")
                print(f"    Reviewers: {pr.reviewers}")
                print(f"    Status: {pr.review_status}")
            print("=" * 80 + "\n")

        # Calculate staleness
        stale_prs: list[StalePR] = []
        for pr in team_prs:
            staleness_days = calculate_staleness(pr)
            if staleness_days is not None:
                stale_prs.append(StalePR(pr=pr, staleness_days=staleness_days))

        logger.info(f"Stale PRs found: {len(stale_prs)}")

        # Sort by staleness (most stale first)
        stale_prs.sort(key=lambda s: s.staleness_days, reverse=True)

        # Format and send Slack message
        message = slack_client.format_message(stale_prs, team_members)
        logger.debug(f"Slack message length: {len(message)} characters")

        if args.dry_run:
            # Dry run mode: print to console instead of sending
            print("\n" + "=" * 80)
            print("DRY RUN MODE - Message that would be sent to Slack:")
            print("=" * 80)
            print(message)
            print("=" * 80 + "\n")
            logger.info("✅ Dry run completed - message printed above")
        else:
            # Normal mode: send to Slack
            logger.info("Sending Slack notification")
            slack_client.send_message(message)
            logger.info("✅ Slack notification sent successfully")

        # Summary
        if stale_prs:
            by_category = {"rotten": 0, "aging": 0, "fresh": 0}
            for stale_pr in stale_prs:
                by_category[stale_pr.category] += 1

            logger.info("Summary:")
            logger.info(f"  🤢 Rotten (8+ days): {by_category['rotten']}")
            logger.info(f"  🧀 Aging (4-7 days): {by_category['aging']}")
            logger.info(f"  ✨ Fresh (1-3 days): {by_category['fresh']}")
        else:
            logger.info("🎉 No stale PRs found!")

        return 0

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user", file=sys.stderr)
        return 130

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
