"""Main application entry point for the Stale PR Board."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime, timedelta

from config import load_config, load_team_members
from github_client import GitHubClient
from models import StalePR
from slack_client import SlackClient
from staleness import calculate_staleness
from url_builder import build_old_pr_search_url


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
        # In dry-run mode, provide dummy Slack credentials if not set
        if args.dry_run and not os.getenv("SLACK_BOT_TOKEN"):
            os.environ["SLACK_BOT_TOKEN"] = "xoxb-DUMMY-DRYRUN-MODE"
        if args.dry_run and not os.getenv("SLACK_CHANNEL_ID"):
            os.environ["SLACK_CHANNEL_ID"] = "C0000000000"

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
        slack_client = SlackClient(
            bot_token=config.slack_bot_token,
            channel_id=config.slack_channel_id,
            language=config.language,
            max_prs_total=config.max_prs_total,
            show_non_team_reviewers=config.show_non_team_reviewers,
        )

        # Check rate limit before making API calls
        logger.info("Checking GitHub API rate limit...")
        rate_limit_status = github_client.check_rate_limit()

        if rate_limit_status:
            # Warn if quota is low (< 100)
            if rate_limit_status.remaining < 100:
                logger.warning(
                    f"⚠️  Low GitHub API quota: "
                    f"{rate_limit_status.remaining}/{rate_limit_status.limit} remaining"
                )

            # Check if we should proceed based on rate limit
            if (
                rate_limit_status.is_exhausted
                and not github_client._should_proceed(
                    rate_limit_status, config.rate_limit_wait_threshold
                )
            ):
                # Fail fast scenario - reset time too distant
                reset_time = datetime.fromtimestamp(rate_limit_status.reset_timestamp)
                wait_hours = (
                    rate_limit_status.wait_seconds / 3600 if rate_limit_status.wait_seconds else 0
                )

                error_msg = (
                    f"GitHub API rate limit exhausted. "
                    f"Reset in {wait_hours:.1f} hours at "
                    f"{reset_time.strftime('%Y-%m-%d %H:%M:%S')}. "
                    f"This exceeds the configured wait threshold of "
                    f"{config.rate_limit_wait_threshold}s. "
                    f"Please try again later or increase RATE_LIMIT_WAIT_THRESHOLD."
                )

                if args.dry_run:
                    # In dry-run mode, show partial results if available
                    logger.warning(f"⚠️  {error_msg}")
                    logger.warning("Dry-run mode: would have failed here. Exiting.")
                    return 1
                else:
                    logger.error(f"❌ {error_msg}")
                    return 1

        # Fetch PRs involving team members using GitHub Search API
        logger.info(f"Searching for open PRs involving team members in: {config.github_org}")
        team_usernames = {member.github_username for member in team_members}
        team_prs = github_client.fetch_team_prs(
            org_name=config.github_org,
            team_usernames=team_usernames,
            updated_after=date.today() - timedelta(days=config.gh_search_window_size),
        )
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
            staleness_days = calculate_staleness(pr, config.holidays_country)
            if staleness_days is not None:
                stale_prs.append(StalePR(pr=pr, staleness_days=staleness_days))

        logger.info(f"Stale PRs found: {len(stale_prs)}")

        # Sort by staleness (most stale first)
        stale_prs.sort(key=lambda s: s.staleness_days, reverse=True)

        # Format and send Slack message
        if args.dry_run:
            # Dry run mode: Build Block Kit JSON for testing
            logger.info("Building Block Kit payload (dry-run mode)")

            # Group PRs by category (same logic as production)
            by_category: dict[str, list[StalePR]] = {"rotten": [], "aging": [], "fresh": []}
            for stale_pr in stale_prs:
                by_category[stale_pr.category].append(stale_pr)

            # Build blocks using public API
            blocks = slack_client.build_blocks(by_category, team_members)
            payload = {"blocks": blocks}

            # Pretty-print JSON with UTF-8 support
            import json

            json_output = json.dumps(payload, indent=2, ensure_ascii=False)

            print("\n" + "=" * 80)
            print("DRY RUN MODE - Block Kit JSON Payload")
            print("=" * 80)
            print(json_output)
            print("=" * 80)
            print(f"\nℹ️  Block count: {len(blocks)}/50 (max limit)")
            print(f"ℹ️  Payload size: {len(json_output):,} bytes")
            print(f"ℹ️  Language: {config.language}")
            print(
                f"ℹ️  PRs by category: "
                f"Rotten={len(by_category['rotten'])}, "
                f"Aging={len(by_category['aging'])}, "
                f"Fresh={len(by_category['fresh'])}"
            )
            print("\n🔗 Test visually: https://app.slack.com/block-kit-builder")
            print("💡 Tip: Copy JSON above and paste into Block Kit Builder")
            print("=" * 80 + "\n")
            logger.info("✅ Dry run completed - Block Kit JSON printed above")
        else:
            # Normal mode: send Block Kit formatted message to Slack
            logger.info("Sending Block Kit formatted Slack notification")
            message_ts = slack_client.post_stale_pr_summary(stale_prs, team_members)
            logger.info(f"✅ Slack notification sent successfully (ts={message_ts})")

            # Post old PR report as a single thread reply
            logger.info("Counting old PRs per team member")
            cutoff_date = date.today() - timedelta(days=config.gh_search_window_size)

            # Fetch counts of old PRs for each team member
            team_usernames = {member.github_username for member in team_members}
            old_pr_counts = github_client.count_old_prs_by_member(
                org_name=config.github_org,
                team_usernames=team_usernames,
                updated_before=cutoff_date,
            )

            # Generate GitHub search URLs only for members with old PRs
            old_pr_data = []  # List of (TeamMember, pr_count, url)
            for member in team_members:
                if member.github_username in old_pr_counts:
                    count = old_pr_counts[member.github_username]
                    try:
                        url = build_old_pr_search_url(
                            username=member.github_username,
                            cutoff_date=cutoff_date,
                        )
                        old_pr_data.append((member, count, url))
                        logger.debug(
                            f"  Generated old PR URL for {member.github_username} ({count} PRs)"
                        )
                    except ValueError as e:
                        logger.warning(
                            f"  Failed to generate URL for {member.github_username}: {e}"
                        )
                        continue

            # Post single thread message if there are members with old PRs
            if old_pr_data:
                logger.info(f"Posting old PR thread reply for {len(old_pr_data)} team member(s)")
                slack_client.post_old_pr_thread(
                    thread_ts=message_ts,
                    old_pr_data=old_pr_data,
                    cutoff_date=cutoff_date,
                )
                logger.info("✅ Old PR report posted successfully")
            else:
                logger.info("No old PRs found - skipping thread reply")

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

        # Log API metrics
        metrics = github_client.metrics
        logger.info("API Metrics:")
        logger.info(f"  Search calls: {metrics.search_calls}")
        if github_client.use_graphql_batch:
            logger.info(f"  GraphQL batch calls: {metrics.graphql_calls}")
            logger.info(f"  REST calls avoided: {metrics.rest_detail_calls}")
            if metrics.graphql_calls > 0:
                optimization_rate = (
                    metrics.rest_detail_calls / (metrics.rest_detail_calls + metrics.graphql_calls)
                ) * 100
                logger.info(f"  Optimization rate: {optimization_rate:.1f}%")
        else:
            logger.info(f"  REST detail calls: {metrics.rest_detail_calls}")
        logger.info(f"  Retry attempts: {metrics.retry_attempts}")
        logger.info(f"  Failed calls: {metrics.failed_calls}")
        if metrics.search_calls + metrics.graphql_calls + metrics.rest_detail_calls > 0:
            total_calls = metrics.search_calls + metrics.graphql_calls + metrics.rest_detail_calls
            success_rate = (
                (total_calls - metrics.failed_calls) / total_calls
            ) * 100
            logger.info(f"  Success rate: {success_rate:.1f}%")

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
