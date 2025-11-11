"""Staleness calculation logic for pull requests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import holidays

from models import PullRequest


def _count_business_days(start: datetime, end: datetime, country: str) -> float:
    """
    Count business days between two datetimes, excluding weekends and holidays.

    Business days are Monday-Friday, excluding holidays defined by the country's
    holiday calendar. Fractional days are calculated proportionally.

    Args:
        start: Start datetime (timezone-aware)
        end: End datetime (timezone-aware)
        country: Country code for holiday calendar (e.g., 'US', 'KR')

    Returns:
        Number of business days as a float (e.g., 1.5 for 1 day + 12 hours)

    Examples:
        - Monday 9am to Tuesday 9am = 1.0 business days
        - Friday 5pm to Monday 9am = 0.0 business days (weekend)
        - Monday 9am to Monday 9pm = 0.5 business days (12 hours / 24 hours)
        - Wednesday (holiday) 9am to Thursday 9am = 0.0 business days
    """
    # Get the holiday calendar for the country
    country_holidays = holidays.country_holidays(country)

    # If the time span is very short (< 1 hour), return 0
    if (end - start).total_seconds() < 3600:
        return 0.0

    # Start from the beginning of the start date for day counting
    current_date = start.date()
    end_date = end.date()

    business_days = 0.0

    # Special case: if start and end are on the same day
    if current_date == end_date:
        # Check if it's a weekend or holiday
        if current_date.weekday() >= 5:  # Saturday or Sunday
            return 0.0
        if current_date in country_holidays:
            return 0.0
        # Calculate fractional day
        total_seconds = (end - start).total_seconds()
        return total_seconds / 86400  # 86400 seconds in a day

    # Handle fractional day at the start
    start_of_next_day = datetime.combine(
        current_date + timedelta(days=1), datetime.min.time(), tzinfo=start.tzinfo
    )
    if current_date.weekday() < 5 and current_date not in country_holidays:
        # It's a business day, count the fraction
        remaining_seconds = (start_of_next_day - start).total_seconds()
        business_days += remaining_seconds / 86400
    current_date += timedelta(days=1)

    # Count full days in between
    while current_date < end_date:
        # Check if it's a weekday and not a holiday
        if current_date.weekday() < 5 and current_date not in country_holidays:
            business_days += 1.0
        current_date += timedelta(days=1)

    # Handle fractional day at the end
    if current_date.weekday() < 5 and current_date not in country_holidays:
        start_of_end_day = datetime.combine(
            end_date, datetime.min.time(), tzinfo=end.tzinfo
        )
        elapsed_seconds = (end - start_of_end_day).total_seconds()
        business_days += elapsed_seconds / 86400

    return business_days


def calculate_staleness(pr: PullRequest, country: str) -> float | None:
    """
    Calculate staleness in business days for a pull request.

    A PR is considered stale if it lacks sufficient approvals.
    Staleness is calculated from the time the PR was ready for review,
    counting only business days (Monday-Friday, excluding holidays).

    Args:
        pr: The pull request to calculate staleness for
        country: Country code for holiday calendar (e.g., 'US', 'KR')

    Returns:
        Number of business days the PR has been stale, or None if:
        - PR is a draft (ready_at is None)
        - PR has sufficient approvals (current_approvals >= required_approvals)

    Notes:
        - Draft PRs are excluded from staleness calculation
        - PRs with sufficient approval are not considered stale
        - Staleness counts only business days (Mon-Fri, excluding holidays)
        - Weekends and holidays are excluded from the count
        - Returns fractional business days (e.g., 1.5 for 1 day + 12 business hours)
    """
    # Skip draft PRs
    if pr.is_draft:
        return None

    # Skip PRs with sufficient approval
    if pr.has_sufficient_approval:
        return None

    # Calculate staleness from ready_at time
    if pr.ready_at is None:
        # This shouldn't happen as is_draft checks ready_at, but handle defensively
        return None

    now = datetime.now(UTC)
    staleness_business_days = _count_business_days(pr.ready_at, now, country)

    return staleness_business_days
