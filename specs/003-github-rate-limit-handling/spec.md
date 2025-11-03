# Feature Specification: GitHub API Rate Limit Handling

**Feature Branch**: `003-github-rate-limit-handling`
**Created**: 2025-10-31
**Status**: Draft
**Input**: User description: "Let's handle GitHub API rate limit with more effort. Current version of app gets stucked in rate limits for 5 member team configuration. Consider rate limits during GitHub API calls or even optimize quota usage by squashing requests or removing useless calls, if possible."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rate Limit Detection & Graceful Degradation (Priority: P1)

When the application encounters GitHub API rate limits during a scheduled run for a 5-member team, the system detects the limit status, informs the user about the situation, and either waits until the limit resets (if <5 minutes) or fails fast with clear error messaging (if >5 minutes) instead of crashing or getting stuck.

**Why this priority**: This is the most critical issue - the current app gets "stuck" and fails completely when hitting rate limits, making it unusable for even small teams. Fixing this provides immediate value by ensuring the app always completes its run successfully.

**Independent Test**: Can be fully tested by artificially reducing the rate limit quota (via test token or simulation) and verifying the app detects the limit, displays clear messages, and completes gracefully without hanging or crashing.

**Acceptance Scenarios**:

1. **Given** the application starts with low rate limit remaining (< 100 requests), **When** the user runs the stale PR board, **Then** the system displays a warning message indicating the rate limit is low and may affect results
2. **Given** the application encounters rate limit exhaustion mid-run with reset <5 minutes away, **When** the system detects this, **Then** it waits with a countdown message and automatically resumes after reset
3. **Given** the application encounters rate limit exhaustion mid-run with reset >5 minutes away, **When** running in normal mode, **Then** the system logs a clear error message and exits with non-zero status without sending Slack message
4. **Given** the application encounters rate limit exhaustion mid-run with reset >5 minutes away, **When** running in dry-run mode, **Then** the system displays partial results with a warning showing what was fetched and what reset time is
5. **Given** the rate limit reset time is >1 hour away, **When** the app detects rate limit exhaustion, **Then** the system immediately exits with error indicating abnormal rate limit state and suggesting investigation

---

### User Story 2 - Smart Retry with Exponential Backoff (Priority: P2)

When GitHub API calls fail specifically due to rate limiting (HTTP 429), the system automatically retries failed requests with increasing wait times between attempts, ensuring successful completion without requiring manual re-runs. Network errors fail immediately without retry.

**Why this priority**: Automatic retry for rate limit errors significantly improves reliability by handling predictable GitHub API throttling gracefully. Network errors fail fast since they're unlikely to resolve within seconds, letting the next scheduled run handle them.

**Independent Test**: Can be tested by simulating rate limit errors (HTTP 429) and verifying the system retries with correct backoff intervals (1s, 2s, 4s) and eventually succeeds or provides clear failure messages after exhausting retries. Can also verify that network errors cause immediate failure without retry attempts.

**Acceptance Scenarios**:

1. **Given** a GitHub API call fails with rate limit error (HTTP 429), **When** the system processes the error, **Then** it waits for the recommended retry-after duration and automatically retries the request
2. **Given** a GitHub API call fails with rate limit error (HTTP 429), **When** the retry mechanism activates, **Then** the system waits 1 second before the first retry, 2 seconds before the second retry, and 4 seconds before the third retry
3. **Given** a GitHub API call fails with rate limit error after 3 retry attempts, **When** all retries are exhausted, **Then** the system logs the specific error, continues with remaining PRs, and reports the failure in the final summary
4. **Given** the rate limit resets during a retry wait period, **When** the wait completes, **Then** the system successfully fetches the data and continues normal operation
5. **Given** a GitHub API call fails with network error (timeout, connection refused, DNS failure), **When** the error is detected, **Then** the system immediately logs the error and exits without retry attempts

---

### User Story 3 - API Call Optimization via Deduplication (Priority: P3)

The application minimizes GitHub API quota usage by eliminating redundant API calls within a single run through in-memory deduplication, ensuring each unique PR is fetched exactly once even when it appears in multiple team members' search results.

**Why this priority**: While P1 and P2 handle rate limits reactively, this proactively reduces API usage to prevent hitting limits in the first place. This is lower priority because the app should work reliably before being optimized.

**Independent Test**: Can be tested by running the app with team members who share common PRs and verifying: (1) each unique PR is fetched only once, (2) in-memory tracking prevents redundant fetches, and (3) overall API usage decreases by 30-50% compared to naive implementation.

**Acceptance Scenarios**:

1. **Given** the application performs a search for team member PRs, **When** multiple team members are authors or reviewers of the same PR, **Then** the PR is fetched exactly once and reused for all relevant team members
2. **Given** the application needs to check PR details, **When** the PR was already fetched in the current run, **Then** the system reuses the in-memory PR data instead of re-fetching
3. **Given** the application completes a run, **When** calculating total API usage, **Then** the system logs the number of API calls made and compares it to the theoretical maximum without deduplication (showing optimization percentage)
4. **Given** the application encounters the same PR URL multiple times, **When** tracking fetched PRs, **Then** the system uses the PR URL as the unique identifier for deduplication

---

### Edge Cases

- What happens when gh CLI commands time out instead of returning rate limit errors?

## Clarifications

### Session 2025-10-31

- Q: Cache Storage Mechanism - The spec mentions caching PR data but doesn't specify where/how this cache is stored, which fundamentally affects the implementation architecture. → A: No persistent cache needed - simple in-memory deduplication only (track already-fetched PRs within a single run, discard on exit)
- Q: Distant Rate Limit Reset Time - What happens when the rate limit reset time is in the distant future (> 1 hour)? → A: Exit immediately with error indicating abnormal rate limit state and suggesting investigation (no partial results, no Slack message, clear error showing distant reset time)
- Q: Partial Results Behavior - What does "complete with partial results" mean when rate limit reset is >5 minutes? → A: Fail fast with error in normal run (no Slack message sent). Show partial results with warning only in dry-run mode (for debugging)
- Q: Large Team Scalability - How does the system handle very large organizations where even optimized calls exceed rate limits? → A: Document team size limit (e.g., 15 members max) and fail gracefully if exceeded
- Q: Inconsistent Rate Limit Data - How does the system handle GitHub API returning inconsistent rate limit data? → A: Use most conservative value and log warning (safe, maintains availability)
- Q: Intermittent Network Connectivity During Retries - How does the system behave when network connectivity is intermittent during retry attempts? → A: Fail immediately on network errors (no retry, strict fast-fail)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST check GitHub API rate limit status before initiating any PR search operations
- **FR-002**: System MUST display clear warning messages to users when remaining rate limit quota is below 100 requests
- **FR-003**: System MUST detect rate limit exhaustion (HTTP 429 responses or zero remaining quota) during API operations
- **FR-004**: System MUST handle inconsistent rate limit data by using the most conservative value and logging a warning. Algorithm: `remaining = min(remaining_values)`, `reset_time = min(reset_timestamps)` where multiple rate limit responses are received within a single operation
- **FR-005**: System MUST wait and automatically retry when rate limit resets within 5 minutes
- **FR-006**: System MUST fail fast and exit with error (no Slack message) when rate limit resets beyond 5 minutes in normal mode
- **FR-007**: System MUST display partial results with warning when rate limit resets beyond 5 minutes in dry-run mode only
- **FR-008**: System MUST implement exponential backoff retry logic for rate limit errors (HTTP 429) with intervals of 1s, 2s, 4s
- **FR-009**: System MUST respect GitHub's `Retry-After` header when present in rate limit responses, using the maximum of the header value and exponential backoff time: `wait_time = max(retry_after_seconds, exponential_backoff_seconds)`
- **FR-010**: System MUST limit retry attempts to 3 per rate limit error to prevent infinite loops
- **FR-011**: System MUST log detailed error information when retries are exhausted, including rate limit status and error messages
- **FR-012**: System MUST fail immediately without retry when encountering network errors (timeout, connection refused, DNS failure, etc.)
- **FR-013**: System MUST track fetched PR URLs in memory during a single run to enable deduplication
- **FR-014**: System MUST reuse in-memory PR data within a single run to avoid redundant fetches when the same PR appears multiple times
- **FR-015**: System MUST log total API call count and optimization metrics at the end of each run
- **FR-016**: System MUST provide configuration options for retry behavior (max attempts, backoff multiplier) and rate limit wait behavior (wait threshold determining auto-wait vs fail-fast cutoff) for rate limit errors only
- **FR-017**: System MUST validate team size at startup and fail with clear error message if team members exceed 15 (recommended maximum for rate limit compliance)
- **FR-018**: System MUST distinguish between rate limit errors (retryable with backoff), network errors (fail fast), and other API failures for appropriate handling, logging the error type and applied strategy for each failure
- **FR-019**: System MUST immediately exit with error when rate limit reset time is more than 1 hour in the future, indicating an abnormal rate limit state that requires investigation (no partial results, no Slack message, clear error indicating the distant reset time)

### Key Entities

- **RateLimitStatus**: Represents current GitHub API rate limit state including remaining quota, total limit, reset timestamp, and whether retry is recommended. Uses conservative values when rate limit data is inconsistent (lowest remaining quota, earliest reset time).
- **RetryPolicy**: Configuration for retry behavior for rate limit errors only, including max attempts, backoff intervals, timeout thresholds, and whether to respect Retry-After headers. Network errors fail immediately without retry.
- **PRDeduplicationTracker**: In-memory dictionary mapping PR URLs to fetched PR data within a single run, enabling reuse and preventing redundant API calls
- **APICallMetrics**: Tracking information for API usage including total calls made, calls saved by deduplication, retry count for rate limit errors, and success/failure rates. Optimization percentage calculated as: `(theoretical_calls - actual_calls) / theoretical_calls × 100` where theoretical_calls assumes no deduplication or batching

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Application successfully completes PR fetching for a 5-member team without crashing or getting stuck, even when starting with low rate limits (< 200 remaining)
- **SC-002**: Users see clear status messages about rate limit state, including remaining quota and reset time, at least once during each run
- **SC-003**: When rate limit is exhausted and resets within 5 minutes, application automatically waits and resumes, completing within 7 minutes total (including wait time)
- **SC-004**: When rate limit is exhausted and resets beyond 5 minutes in normal mode, application fails fast and exits with error within 5 seconds without sending Slack message
- **SC-005**: When rate limit is exhausted and resets beyond 5 minutes in dry-run mode, application displays partial results with warning within 5 seconds showing reset time
- **SC-006**: Rate limit errors (HTTP 429) are automatically recovered through retry logic, with 95%+ success rate for rate limit errors when reset times are reasonable
- **SC-007**: API call deduplication reduces total GitHub API calls by at least 30% within a single run when team members share common PRs (measured by comparing actual calls vs. theoretical maximum without deduplication: baseline = search_calls × team_size + individual_REST_calls_per_PR × total_unique_PRs). Note: GraphQL batch fetching alone can achieve up to 65% savings for PR detail calls, while deduplication provides additional savings for search phase; 30% is the minimum combined requirement
- **SC-008**: Users can configure retry behavior through environment variables without modifying code
- **SC-009**: Application logs include clear metrics showing: total API calls, calls saved by deduplication, retry attempts, and final rate limit status
