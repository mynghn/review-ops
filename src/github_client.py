"""GitHub API client for fetching pull requests and reviews."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime

from github import Auth, Github

from models import PullRequest

logger = logging.getLogger(__name__)


class GitHubClient:
    """
    Client for interacting with GitHub API using a hybrid approach.

    This client uses GitHub CLI (gh) for efficient PR searching and detail fetching,
    while PyGithub provides authentication infrastructure. This hybrid approach offers:

    - Faster searches: gh CLI's search is optimized for large organizations
    - Fewer API calls: gh CLI batches multiple REST API calls into single commands
    - Better performance: Reduced round-trip time compared to individual REST calls
    - Rate limit efficiency: Each gh CLI command counts as fewer individual API calls

    The client requires 'gh' CLI to be installed and authenticated with the same token.
    """

    def __init__(self, token: str, gh_search_limit: int = 1000) -> None:
        """
        Initialize GitHub client with authentication token.

        Args:
            token: GitHub Personal Access Token with 'repo' and 'read:org' scopes
            gh_search_limit: Maximum number of PRs to return from each gh search query (default: 1000)
        """
        auth = Auth.Token(token)
        self.client = Github(auth=auth)
        self.gh_search_limit = gh_search_limit

    def check_rate_limit(self) -> None:
        """
        Check GitHub API rate limit and log warning if quota is low.

        Uses gh API to check remaining rate limit. Logs a warning if fewer than
        500 requests remain, as PR fetching can consume many API calls for large teams.

        This is a best-effort check and will not fail if gh CLI is unavailable.
        """
        try:
            result = subprocess.run(
                ["gh", "api", "rate_limit", "--jq", ".resources.core"],
                capture_output=True,
                text=True,
                check=True,
                env=os.environ,
                timeout=10,
            )

            rate_data = json.loads(result.stdout)
            remaining = rate_data.get("remaining", 0)
            limit = rate_data.get("limit", 5000)
            reset_timestamp = rate_data.get("reset", 0)

            logger.debug(f"GitHub API rate limit: {remaining}/{limit} remaining")

            if remaining < 500:
                reset_time = datetime.fromtimestamp(reset_timestamp)
                logger.warning(
                    f"⚠️  GitHub API rate limit is low: {remaining}/{limit} requests remaining. "
                    f"Resets at {reset_time.strftime('%Y-%m-%d %H:%M:%S')}. "
                    f"Consider running later or reducing GH_SEARCH_LIMIT."
                )
            elif remaining < 1000:
                logger.info(f"GitHub API rate limit: {remaining}/{limit} requests remaining")

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError) as e:
            # Non-fatal: Log debug message and continue
            logger.debug(f"Could not check rate limit (gh CLI may be unavailable): {e}")

    def fetch_team_prs(self, org_name: str, team_usernames: set[str]) -> list[PullRequest]:
        """
        Fetch open PRs involving team members using a two-phase approach.

        Phase 1 - Search & Deduplicate:
        - Searches for PRs where team members are authors or requested reviewers
        - Collects all PR keys (repo, number) across all searches
        - Automatically deduplicates using a set to avoid redundant fetches

        Phase 2 - Fetch Details:
        - Fetches complete details only for unique PRs
        - Each gh pr view call includes reviews, approvals, and status

        This two-phase approach is much more efficient than:
        - Iterating through all organization repos (slow for large orgs)
        - Fetching details before deduplication (wastes API calls)

        Note: 'reviewed-by' search is omitted as it's less relevant for staleness
        tracking and would add significant API overhead.

        Args:
            org_name: Name of the GitHub organization
            team_usernames: Set of GitHub usernames to search for

        Returns:
            List of PullRequest objects involving team members (drafts excluded)

        Raises:
            subprocess.CalledProcessError: If gh CLI command fails
            json.JSONDecodeError: If gh CLI output is malformed
        """
        # Check rate limit before making API calls
        self.check_rate_limit()

        # Phase 1: Collect all PR keys from searches (no detail fetching yet)
        pr_keys = set()  # Use set for automatic deduplication

        # Search types: author and review-requested
        # Note: Using flags instead of query strings for better reliability
        search_types = [
            ("author", "--author"),
            ("review-requested", "--review-requested"),
        ]

        for search_type_name, flag in search_types:
            logger.info(f"Searching PRs by {search_type_name}...")

            for username in team_usernames:
                logger.debug(f"  Searching for user: {username}")

                try:
                    result = subprocess.run(
                        [
                            "gh", "search", "prs",
                            "--owner", org_name,
                            flag, username,
                            "--state", "open",
                            "--limit", str(self.gh_search_limit),
                            "--json", "number,url,repository"
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                        env=os.environ,
                    )

                    prs_data = json.loads(result.stdout)
                    logger.debug(f"    Found {len(prs_data)} PRs for {username} ({search_type_name})")

                    # Collect PR keys (automatic deduplication via set)
                    for pr_data in prs_data:
                        repo_full_name = pr_data["repository"]["nameWithOwner"]
                        pr_number = pr_data["number"]
                        pr_keys.add((repo_full_name, pr_number))

                except subprocess.CalledProcessError as e:
                    error_msg = (
                        f"gh search prs failed for {username} ({search_type_name}): {e.stderr}\n"
                        "Possible causes:\n"
                        "  - gh CLI not authenticated (run: gh auth login)\n"
                        "  - Invalid GitHub token (check GH_TOKEN in .env)\n"
                        "  - Network connectivity issues\n"
                        "  - GitHub API is down (check https://www.githubstatus.com/)"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg) from e
                except json.JSONDecodeError as e:
                    error_msg = f"Failed to parse gh CLI output for {username} ({search_type_name}): {e}"
                    logger.error(error_msg)
                    raise ValueError(error_msg) from e

        logger.info(f"Found {len(pr_keys)} unique PR(s) across all searches")

        # Phase 2: Fetch details for each unique PR
        all_prs = []
        for repo_full_name, pr_number in pr_keys:
            pr_details = self._fetch_pr_details(repo_full_name, pr_number)
            if pr_details:
                # FR-008: Validate that PR still involves at least one team member
                # (author is team member OR any current reviewer is team member)
                is_team_pr = (
                    pr_details.author in team_usernames or
                    any(reviewer in team_usernames for reviewer in pr_details.reviewers)
                )

                if is_team_pr:
                    all_prs.append(pr_details)
                else:
                    logger.debug(
                        f"  Skipping PR {repo_full_name}#{pr_number}: "
                        f"no current team involvement "
                        f"(author={pr_details.author}, reviewers={pr_details.reviewers})"
                    )

        logger.info(f"Successfully fetched details for {len(all_prs)} PR(s)")
        return all_prs

    def _fetch_pr_details(self, repo_full_name: str, pr_number: int) -> PullRequest | None:
        """
        Fetch complete PR details using gh pr view.

        This replaces multiple PyGithub API calls with a single gh CLI call,
        fetching all needed data including reviewers, reviews, and review decision.

        Args:
            repo_full_name: Full repository name (e.g., 'owner/repo')
            pr_number: PR number

        Returns:
            PullRequest object or None if PR is a draft or fetch fails
        """
        try:
            result = subprocess.run(
                [
                    "gh", "pr", "view", str(pr_number),
                    "--repo", repo_full_name,
                    "--json", "number,title,author,url,createdAt,isDraft,"
                              "reviewDecision,reviewRequests,latestReviews,baseRefName"
                ],
                capture_output=True,
                text=True,
                check=True,
                env=os.environ,
            )

            pr_data = json.loads(result.stdout)

            # Skip drafts
            if pr_data.get("isDraft", False):
                logger.debug(f"  Skipping draft PR: {repo_full_name}#{pr_number}")
                return None

            # Extract data from gh CLI response
            created_at = datetime.fromisoformat(pr_data["createdAt"].replace("Z", "+00:00"))
            ready_at = created_at  # For non-draft PRs, use created_at

            # Extract requested reviewers (filter out team review requests)
            review_requests = pr_data.get("reviewRequests", [])
            reviewers = [req["login"] for req in review_requests if req.get("login")]

            # Count current approvals from latestReviews
            latest_reviews = pr_data.get("latestReviews", [])
            current_approvals = sum(
                1 for review in latest_reviews
                if review.get("state") == "APPROVED"
            )

            # Get review decision (normalize empty string to None)
            review_status = pr_data.get("reviewDecision") or None

            # Get base branch
            base_branch = pr_data.get("baseRefName", "main")

            # Extract repo name from repo_full_name (e.g., "owner/repo" -> "repo")
            repo_name = repo_full_name.split("/")[-1] if "/" in repo_full_name else repo_full_name

            pull_request = PullRequest(
                repo_name=repo_name,
                number=pr_data["number"],
                title=pr_data["title"],
                author=pr_data["author"]["login"] if pr_data["author"] else "ghost",
                reviewers=reviewers,
                url=pr_data["url"],
                created_at=created_at,
                ready_at=ready_at,
                current_approvals=current_approvals,
                review_status=review_status,
                base_branch=base_branch,
            )

            logger.debug(f"  Fetched details for {repo_full_name}#{pr_number}: "
                        f"{current_approvals} approvals, status={review_status}")

            return pull_request

        except subprocess.CalledProcessError as e:
            logger.error(f"gh pr view failed for {repo_full_name}#{pr_number}: {e.stderr}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse gh pr view output for {repo_full_name}#{pr_number}: {e}")
            return None
