"""GitHub API client for fetching pull requests and reviews."""

from __future__ import annotations

import json
import os
import subprocess

from github import Auth, Github, GithubException, Repository
from github.PullRequest import PullRequest as GithubPR

from models import PullRequest


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self, token: str) -> None:
        """
        Initialize GitHub client with authentication token.

        Args:
            token: GitHub Personal Access Token with 'repo' and 'read:org' scopes
        """
        auth = Auth.Token(token)
        self.client = Github(auth=auth)

    def fetch_organization_repos(self, org_name: str) -> list[Repository.Repository]:
        """
        Fetch all repositories for a GitHub organization.

        Args:
            org_name: Name of the GitHub organization

        Returns:
            List of Repository objects

        Raises:
            GithubException: If organization not found or access denied
        """
        org = self.client.get_organization(org_name)
        return list(org.get_repos(type="all"))

    def fetch_team_prs(self, org_name: str, team_usernames: set[str]) -> list[PullRequest]:
        """
        Fetch open PRs involving team members using gh CLI search.

        This is much more efficient than iterating through all organization repos.
        Searches for PRs where team members are authors or requested reviewers.

        Note: reviewed-by is omitted as it's less relevant for staleness tracking.

        Args:
            org_name: Name of the GitHub organization
            team_usernames: Set of GitHub usernames to search for

        Returns:
            List of PullRequest objects involving team members
        """
        import logging
        from datetime import datetime
        logger = logging.getLogger(__name__)

        all_prs = []
        seen_pr_keys = set()  # Deduplicate by (repo, number)

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
                            "--limit", "1000",
                            "--json", "number,url,repository"
                        ],
                        capture_output=True,
                        text=True,
                        check=True,
                        env=os.environ,
                    )

                    prs_data = json.loads(result.stdout)
                    logger.debug(f"    Found {len(prs_data)} PRs for {username} ({search_type_name})")

                    for pr_data in prs_data:
                        repo_full_name = pr_data["repository"]["nameWithOwner"]
                        pr_number = pr_data["number"]
                        pr_key = (repo_full_name, pr_number)

                        # Skip if we've already processed this PR
                        if pr_key in seen_pr_keys:
                            continue
                        seen_pr_keys.add(pr_key)

                        # Fetch full PR details using gh pr view
                        # This replaces multiple PyGithub API calls with a single gh CLI call
                        pr_details = self._fetch_pr_details(repo_full_name, pr_number)

                        if pr_details:
                            all_prs.append(pr_details)

                except subprocess.CalledProcessError as e:
                    logger.error(f"gh search prs failed for {username} ({search_type_name}): {e.stderr}")
                    raise
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse gh CLI output: {e}")
                    raise

        logger.info(f"Total unique PRs found: {len(all_prs)}")
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
        import logging
        from datetime import datetime
        logger = logging.getLogger(__name__)

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

    def fetch_open_prs(self, repo: Repository.Repository) -> list[PullRequest]:
        """
        Fetch all open pull requests from a repository, excluding drafts.

        Args:
            repo: Repository object to fetch PRs from

        Returns:
            List of PullRequest objects (drafts excluded)
        """
        github_prs = repo.get_pulls(state="open", sort="created")
        pull_requests = []

        for github_pr in github_prs:
            # Skip draft PRs
            if github_pr.draft:
                continue

            # Get review status from gh CLI
            repo_full_name = repo.full_name
            review_status = self.get_review_status(repo_full_name, github_pr.number)

            # Count current approvals (still useful for display)
            current_approvals = self.count_current_approvals(github_pr)

            # Extract reviewer usernames
            reviewers = [reviewer.login for reviewer in github_pr.requested_reviewers]

            # Determine ready_at time (for MVP, use created_at since we can't easily get ready time)
            ready_at = github_pr.created_at if not github_pr.draft else None

            pr = PullRequest(
                repo_name=repo.name,
                number=github_pr.number,
                title=github_pr.title,
                author=github_pr.user.login,
                reviewers=reviewers,
                url=github_pr.html_url,
                created_at=github_pr.created_at,
                ready_at=ready_at,
                current_approvals=current_approvals,
                review_status=review_status,
                base_branch=github_pr.base.ref,
            )
            pull_requests.append(pr)

        return pull_requests

    def get_review_status(self, repo_full_name: str, pr_number: int) -> str | None:
        """
        Get PR review status using gh CLI.

        The review status reflects GitHub's computed review state based on
        branch protection rules, including required approvals, CODEOWNERS, and
        required reviewers.

        Args:
            repo_full_name: Full repository name (e.g., 'owner/repo')
            pr_number: PR number

        Returns:
            One of: 'APPROVED', 'CHANGES_REQUESTED', 'REVIEW_REQUIRED', or None
            None indicates no review requirements configured or gh CLI unavailable
        """
        try:
            result = subprocess.run(
                ["gh", "pr", "view", str(pr_number),
                 "--repo", repo_full_name,
                 "--json", "reviewDecision"],
                capture_output=True,
                text=True,
                check=True,
                env=os.environ,
            )
            data = json.loads(result.stdout)
            return data.get("reviewDecision") or None
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
            # Fall back gracefully if gh CLI unavailable or fails
            return None

    def count_current_approvals(self, pr: GithubPR) -> int:
        """
        Count the number of current valid approvals for a PR.

        Only the latest review from each user is considered.
        Only reviews with state='APPROVED' count as approvals.

        Args:
            pr: GitHub PullRequest object

        Returns:
            Number of current valid approvals
        """
        reviews = pr.get_reviews()

        # Track latest review per user
        latest_reviews: dict[str, object] = {}

        for review in reviews:
            user = review.user.login
            if (
                user not in latest_reviews
                or review.submitted_at > latest_reviews[user].submitted_at
            ):
                latest_reviews[user] = review

        # Count approvals from latest reviews
        approval_count = sum(
            1 for review in latest_reviews.values() if review.state == "APPROVED"
        )

        return approval_count
