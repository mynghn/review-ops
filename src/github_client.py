"""GitHub API client for fetching pull requests and reviews."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, date

from github import Auth, Github

from models import APICallMetrics, PullRequest, RateLimitStatus

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

    def __init__(
        self,
        token: str,
        gh_search_limit: int = 100,
        max_retries: int = 3,
        retry_backoff_base: float = 1.0,
        use_graphql_batch: bool = True,
        api_call_delay: float = 2.0,
    ) -> None:
        """
        Initialize GitHub client with authentication token.

        Args:
            token: GitHub Personal Access Token with 'repo' and 'read:org' scopes
            gh_search_limit: Maximum number of PRs to return from each gh search query
                (default: 100)
            max_retries: Maximum retry attempts for rate limit errors (default: 3)
            retry_backoff_base: Base backoff duration for exponential retry (default: 1.0)
            use_graphql_batch: Enable GraphQL batch fetching for PR details (default: True)
            api_call_delay: Delay between API calls in seconds to prevent rate limits (default: 2.0)
        """
        auth = Auth.Token(token)
        self.client = Github(auth=auth)
        self.gh_search_limit = gh_search_limit
        self.max_retries = max_retries
        self.retry_backoff_base = retry_backoff_base
        self.use_graphql_batch = use_graphql_batch
        self.api_call_delay = api_call_delay
        self.metrics = APICallMetrics()
        self._pr_cache: dict[tuple[str, int], bool] = {}  # (repo, number) -> fetched

    def check_rate_limit(self) -> RateLimitStatus | None:
        """
        Check GitHub API rate limit and return status object.

        Uses gh API to check remaining rate limit and returns a RateLimitStatus object
        for decision-making. Returns None if rate limit check fails (non-fatal).

        Returns:
            RateLimitStatus with current quota info, or None if check failed
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

            # Strict validation: required fields must be present
            try:
                remaining = rate_data["remaining"]
                limit = rate_data["limit"]
                reset_timestamp = rate_data["reset"]
            except KeyError as e:
                raise ValueError(f"Missing required rate limit field: {e}") from e

            # Ensure non-negative remaining quota
            remaining = max(0, remaining)

            # Calculate wait time if exhausted
            current_time = datetime.now().timestamp()
            wait_seconds = max(0, int(reset_timestamp - current_time)) if remaining == 0 else None

            status = RateLimitStatus(
                remaining=remaining,
                limit=limit,
                reset_timestamp=reset_timestamp,
                is_exhausted=(remaining == 0),
                wait_seconds=wait_seconds,
            )

            logger.debug(f"GitHub API rate limit: {remaining}/{limit} remaining")

            if remaining < 100:
                reset_time = datetime.fromtimestamp(reset_timestamp)
                logger.warning(
                    f"⚠️  GitHub API rate limit is low: {remaining}/{limit} requests remaining. "
                    f"Resets at {reset_time.strftime('%Y-%m-%d %H:%M:%S')}. "
                    f"Consider running later or reducing MAX_PRS_TOTAL."
                )
            elif remaining < 500:
                logger.info(f"GitHub API rate limit: {remaining}/{limit} requests remaining")

            return status

        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
            KeyError,
        ) as e:
            # Non-fatal: Log debug message and continue
            logger.debug(f"Could not check rate limit (gh CLI may be unavailable): {e}")
            return None

    def _should_proceed(self, status: RateLimitStatus, threshold_seconds: int) -> bool:
        """
        Decide whether to proceed with API calls based on rate limit status.

        Args:
            status: Current rate limit status
            threshold_seconds: Maximum seconds to wait (from config)

        Returns:
            True if should proceed (auto-wait if needed), False if should fail fast
        """
        if not status.is_exhausted:
            return True

        if status.wait_seconds is None or status.wait_seconds <= 0:
            return True  # No wait needed

        if status.wait_seconds <= threshold_seconds:
            # Auto-wait scenario (reset < threshold)
            self._wait_for_reset(status)
            return True

        # Fail-fast scenario (reset > threshold)
        return False

    def _wait_for_reset(self, status: RateLimitStatus) -> None:
        """
        Wait for rate limit reset with countdown display.

        Args:
            status: Rate limit status with wait_seconds set
        """
        import time

        if status.wait_seconds is None or status.wait_seconds <= 0:
            return

        reset_time = datetime.fromtimestamp(status.reset_timestamp)
        logger.info(
            f"Rate limit exhausted. Waiting {status.wait_seconds}s until reset at "
            f"{reset_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Simple countdown without complexity
        remaining = status.wait_seconds
        while remaining > 0:
            if remaining % 30 == 0 or remaining <= 10:  # Log every 30s or final 10s
                logger.info(f"Waiting... {remaining}s remaining")
            time.sleep(1)
            remaining -= 1

        logger.info("Rate limit reset. Resuming operations.")

    def _classify_error(self, error: Exception) -> str:
        """
        Classify error type for retry decision.

        Args:
            error: Exception from subprocess call

        Returns:
            Error type: "primary_rate_limit", "secondary_rate_limit", "network", or "other"
        """
        if isinstance(error, subprocess.TimeoutExpired):
            return "network"

        if isinstance(error, subprocess.CalledProcessError):
            stderr = error.stderr if error.stderr else ""
            stderr_lower = stderr.lower()

            # Check for HTTP 403 secondary rate limit (requires longer wait)
            if "403" in stderr and "secondary rate limit" in stderr_lower:
                return "secondary_rate_limit"

            # Check for HTTP 429 primary rate limit (normal retry)
            if "429" in stderr or "rate limit" in stderr_lower:
                return "primary_rate_limit"

            # Check for network-related errors
            if any(
                term in stderr_lower
                for term in [
                    "timeout",
                    "connection refused",
                    "connection reset",
                    "dns",
                    "could not resolve",
                    "name resolution",
                    "unknown host",
                ]
            ):
                return "network"

        return "other"

    def _calculate_backoff(self, attempt: int, base: float) -> float:
        """
        Calculate exponential backoff wait time.

        Args:
            attempt: Retry attempt number (0-indexed)
            base: Base backoff duration in seconds

        Returns:
            Wait time in seconds (base * 2^attempt)
        """
        return base * (2**attempt)

    def _parse_retry_after(self, stderr: str) -> int | None:
        """
        Parse Retry-After header from gh CLI stderr.

        Args:
            stderr: Error output from gh CLI

        Returns:
            Retry-After seconds if found, None otherwise
        """
        import re

        # Look for "Retry-After: <seconds>" in stderr
        match = re.search(r"Retry-After:\s*(\d+)", stderr, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

    def _execute_gh_command(
        self,
        command: list[str],
        timeout: int = 30,
    ) -> subprocess.CompletedProcess:
        """
        Execute a GitHub CLI command with standard settings.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds

        Returns:
            Completed process result

        Raises:
            subprocess.CalledProcessError: If command fails
            subprocess.TimeoutExpired: If command times out
        """
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            env=os.environ,
            timeout=timeout,
        )

    def _retry_with_backoff(
        self,
        func: callable,
        max_retries: int,
        backoff_base: float,
    ) -> subprocess.CompletedProcess:
        """
        Execute a callable with retry logic for rate limit errors.

        Args:
            func: Callable to execute (e.g., lambda or function)
            max_retries: Maximum retry attempts
            backoff_base: Base backoff duration

        Returns:
            Result from the callable

        Raises:
            Exception: If callable fails after all retries
        """
        import time

        attempt = 0
        last_error = None

        while attempt <= max_retries:
            try:
                result = func()
                # Success!
                if attempt > 0:
                    logger.info(f"✓ Operation succeeded after {attempt} retry attempt(s)")
                return result

            except Exception as e:
                last_error = e
                error_type = self._classify_error(e)

                # Network errors and other errors don't retry
                if error_type in ["network", "other"]:
                    logger.debug(f"Error type '{error_type}' - not retrying")
                    raise

                # Rate limit errors retry (both primary and secondary)
                if (
                    error_type in ["primary_rate_limit", "secondary_rate_limit"]
                    and attempt < max_retries
                ):
                    self.metrics.retry_attempts += 1

                    # Check for Retry-After header
                    stderr = e.stderr if hasattr(e, "stderr") and e.stderr else ""
                    retry_after = self._parse_retry_after(stderr)

                    if retry_after:
                        wait_time = retry_after
                        logger.info(
                            f"Rate limit hit. Retry-After: {wait_time}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                    elif error_type == "secondary_rate_limit":
                        # Secondary rate limits require much longer waits (GitHub says "a few minutes")
                        # Use 60s base instead of configured base, with exponential backoff
                        wait_time = 60 * (2**attempt)  # 60s, 120s, 240s
                        logger.warning(
                            f"⚠️  Secondary rate limit hit. GitHub suggests waiting 'a few minutes'. "
                            f"Waiting {wait_time}s before retry (attempt {attempt + 1}/{max_retries})"
                        )
                    else:
                        # Primary rate limit uses configured backoff
                        wait_time = self._calculate_backoff(attempt, backoff_base)
                        logger.info(
                            f"Primary rate limit hit. Waiting {wait_time}s before retry "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )

                    time.sleep(wait_time)
                    attempt += 1
                    continue

                # Max retries exhausted
                if attempt >= max_retries:
                    self.metrics.failed_calls += 1
                    logger.error(f"Max retries ({max_retries}) exhausted")
                    raise

                attempt += 1

        # Should not reach here, but handle gracefully
        self.metrics.failed_calls += 1
        if last_error:
            raise last_error
        raise RuntimeError("Retry logic failed unexpectedly")

    def fetch_team_prs(self, org_name: str, team_usernames: set[str], updated_after: date) -> list[PullRequest]:
        """
        Fetch open PRs involving team members using a two-phase approach.

        Phase 1 - Search & Deduplicate:
        - Searches for PRs where
          - is in unarchived repos, is open, not a draft
          - is review required
          - has recent updates after {updated_after} date
          - team members are requested reviewers
        - Collects all PR keys (repo, number) across all searches
        - Automatically deduplicates using a set to avoid redundant fetches

        Phase 2 - Fetch Details:
        - Fetches complete details only for unique PRs
        - Each gh pr view call includes reviews, approvals, and status

        This two-phase approach is much more efficient than:
        - Iterating through all organization repos (slow for large orgs)
        - Fetching details before deduplication (wastes API calls)

        Args:
            org_name: Name of the GitHub organization
            team_usernames: Set of GitHub usernames to search for
            updated_after: Date to filter PRs updated after

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
        for username in team_usernames:
            logger.debug(f"  Searching for user: {username}")

            try:
                result = self._retry_with_backoff(
                    lambda: self._execute_gh_command(
                        [
                            "gh", "search", "prs",
                            "--owner", org_name,
                            "--archived=false",
                            "--state", "open",
                            "--draft=false",
                            "--review", "required",
                            "--review-requested", username,
                            "--updated", f">={updated_after.isoformat()}",
                            "--limit", str(self.gh_search_limit),
                            "--json", "number,repository",
                        ]
                    ),
                    max_retries=self.max_retries,
                    backoff_base=self.retry_backoff_base,
                )

                prs_data = json.loads(result.stdout)
                logger.debug(f"\tFound {len(prs_data)} PRs for {username}")

                # Collect PR keys (automatic deduplication via set)
                for pr_data in prs_data:
                    repo_full_name = pr_data["repository"]["nameWithOwner"]
                    pr_number = pr_data["number"]
                    pr_keys.add((repo_full_name, pr_number))

                # Add delay between API calls to prevent secondary rate limits
                if self.api_call_delay > 0:
                    import time

                    time.sleep(self.api_call_delay)
                    logger.debug(f"    Waited {self.api_call_delay}s to avoid rate limits")

            except subprocess.CalledProcessError as e:
                error_msg = (
                    f"gh search prs failed for {username}: {e.stderr}\n"
                    "Possible causes:\n"
                    "  - gh CLI not authenticated (run: gh auth login)\n"
                    "  - Invalid GitHub token (check GH_TOKEN in .env)\n"
                    "  - Network connectivity issues\n"
                    "  - GitHub API is down (check https://www.githubstatus.com/)"
                )
                logger.error(error_msg)
                raise ValueError(error_msg) from e
            except json.JSONDecodeError as e:
                error_msg = (
                    f"Failed to parse gh CLI output for {username}: {e}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg) from e

        logger.info(f"Found {len(pr_keys)} unique PR(s) across all searches")

        # Phase 2: Fetch details for unique PRs
        all_prs = []

        if self.use_graphql_batch:
            # GraphQL batch fetching strategy (reduces API calls by ~65%)
            logger.debug("Using GraphQL batch fetching for PR details")

            # Group PRs by repository for efficient batching
            prs_to_fetch = [
                {"repo": repo_full_name, "number": pr_number}
                for repo_full_name, pr_number in pr_keys
            ]
            grouped_prs = self._group_prs_by_repo(prs_to_fetch)

            # Fetch each repository's PRs in a single GraphQL batch query
            for repo_full_name, pr_numbers in grouped_prs.items():
                owner, repo = repo_full_name.split("/")
                batch_prs = self._fetch_pr_details_batch_graphql(owner, repo, pr_numbers)
                all_prs.extend(batch_prs)

        else:
            # REST API strategy (fallback, uses individual gh pr view calls)
            logger.debug("Using REST API for PR details (GraphQL disabled)")

            for repo_full_name, pr_number in pr_keys:
                pr_details = self._fetch_pr_details(repo_full_name, pr_number)
                if pr_details:
                    all_prs.append(pr_details)

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
            result = self._retry_with_backoff(
                lambda: self._execute_gh_command(
                    [
                        "gh", "pr", "view", str(pr_number),
                        "--repo", repo_full_name,
                        "--json", "number,title,author,url,createdAt,isDraft,"
                                  "reviewDecision,reviewRequests,latestReviews,baseRefName"
                    ]
                ),
                max_retries=self.max_retries,
                backoff_base=self.retry_backoff_base,
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
                1 for review in latest_reviews if review.get("state") == "APPROVED"
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

            logger.debug(
                f"  Fetched details for {repo_full_name}#{pr_number}: "
                f"{current_approvals} approvals, status={review_status}"
            )

            return pull_request

        except subprocess.CalledProcessError as e:
            logger.error(f"gh pr view failed for {repo_full_name}#{pr_number}: {e.stderr}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse gh pr view output for {repo_full_name}#{pr_number}: {e}")
            return None

    def _group_prs_by_repo(self, prs_to_fetch: list[dict]) -> dict[str, list[int]]:
        """
        Group PRs by repository for efficient batch fetching.

        Args:
            prs_to_fetch: List of dicts with 'repo' and 'number' keys

        Returns:
            Dict mapping repo (owner/name) to list of PR numbers
        """
        grouped: dict[str, list[int]] = {}
        for pr_info in prs_to_fetch:
            repo = pr_info["repo"]
            number = pr_info["number"]
            if repo not in grouped:
                grouped[repo] = []
            grouped[repo].append(number)
        return grouped

    def _build_graphql_batch_query(self, owner: str, repo: str, pr_numbers: list[int]) -> str:
        """
        Build GraphQL batch query for fetching multiple PRs from the same repository.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
            pr_numbers: List of PR numbers to fetch

        Returns:
            GraphQL query string
        """
        # Build aliased pullRequest fields for each PR number
        pr_fields = []
        for number in pr_numbers:
            alias = f"pr_{number}"
            pr_fields.append(f"""
                {alias}: pullRequest(number: {number}) {{
                    number
                    title
                    url
                    createdAt
                    isDraft
                    author {{
                        login
                    }}
                    reviewRequests(first: 100) {{
                        nodes {{
                            requestedReviewer {{
                                ... on User {{
                                    login
                                }}
                            }}
                        }}
                    }}
                    reviews(last: 100) {{
                        nodes {{
                            state
                            author {{
                                login
                            }}
                        }}
                    }}
                    reviewDecision
                    baseRefName
                }}
            """)

        query = f"""
        {{
            repository(owner: "{owner}", name: "{repo}") {{
                {"".join(pr_fields)}
            }}
        }}
        """
        return query

    def _fetch_pr_details_batch_graphql(
        self, owner: str, repo: str, pr_numbers: list[int]
    ) -> list[PullRequest]:
        """
        Fetch multiple PR details from the same repository using GraphQL batch query.

        This reduces API calls significantly compared to individual REST calls.
        For example, fetching 30 PRs takes 1 GraphQL call vs 30 REST calls (97% reduction).

        Args:
            owner: Repository owner
            repo: Repository name
            pr_numbers: List of PR numbers to fetch

        Returns:
            List of PullRequest objects (may be less than requested if some fail)
        """
        try:
            query = self._build_graphql_batch_query(owner, repo, pr_numbers)

            result = self._retry_with_backoff(
                lambda: self._execute_gh_command(
                    ["gh", "api", "graphql", "-f", f"query={query}"],
                    timeout=30,
                ),
                max_retries=self.max_retries,
                backoff_base=self.retry_backoff_base,
            )

            data = json.loads(result.stdout)
            repo_data = data.get("data", {}).get("repository", {})

            pull_requests = []
            repo_full_name = f"{owner}/{repo}"

            for number in pr_numbers:
                alias = f"pr_{number}"
                pr_data = repo_data.get(alias)

                if not pr_data:
                    logger.warning(f"No data returned for {repo_full_name}#{number} in batch query")
                    continue

                # Parse PR data (similar to _fetch_pr_details)
                try:
                    created_at = datetime.fromisoformat(pr_data["createdAt"].replace("Z", "+00:00"))

                    # For draft PRs, ready_at would be when marked as ready
                    # Since GraphQL doesn't easily expose this, use created_at
                    ready_at = created_at

                    # Extract reviewers from reviewRequests
                    review_requests = pr_data.get("reviewRequests", {}).get("nodes", [])
                    reviewers = [
                        req["requestedReviewer"]["login"]
                        for req in review_requests
                        if req.get("requestedReviewer", {}).get("login")
                    ]

                    # Count approvals from reviews
                    reviews = pr_data.get("reviews", {}).get("nodes", [])
                    # Get latest review per author
                    latest_reviews_by_author: dict[str, str] = {}
                    for review in reviews:
                        author_login = review.get("author", {}).get("login")
                        if author_login:
                            latest_reviews_by_author[author_login] = review.get("state", "")

                    current_approvals = sum(
                        1 for state in latest_reviews_by_author.values() if state == "APPROVED"
                    )

                    review_status = pr_data.get("reviewDecision") or None
                    base_branch = pr_data.get("baseRefName", "main")
                    repo_name = repo  # Use repo name directly

                    pull_request = PullRequest(
                        repo_name=repo_name,
                        number=pr_data["number"],
                        title=pr_data["title"],
                        author=pr_data["author"]["login"] if pr_data.get("author") else "ghost",
                        reviewers=reviewers,
                        url=pr_data["url"],
                        created_at=created_at,
                        ready_at=ready_at,
                        current_approvals=current_approvals,
                        review_status=review_status,
                        base_branch=base_branch,
                    )

                    pull_requests.append(pull_request)
                    logger.debug(
                        f"  Fetched {repo_full_name}#{number} via GraphQL: "
                        f"{current_approvals} approvals, status={review_status}"
                    )

                except (KeyError, ValueError) as e:
                    logger.warning(
                        f"Failed to parse PR {repo_full_name}#{number} from GraphQL: {e}"
                    )
                    continue

            # Update metrics
            self.metrics.graphql_calls += 1
            self.metrics.rest_detail_calls += len(pr_numbers)  # Track calls saved

            logger.debug(
                f"GraphQL batch: fetched {len(pull_requests)}/{len(pr_numbers)} PRs "
                f"from {repo_full_name}"
            )

            return pull_requests

        except subprocess.CalledProcessError as e:
            logger.error(f"GraphQL batch query failed for {repo_full_name}: {e.stderr}")
            self.metrics.failed_calls += 1
            return []
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse GraphQL response for {repo_full_name}: {e}")
            return []
