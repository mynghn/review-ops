# Feature Specification: Stale PR Board

**Feature Branch**: `001-stale-pr-board`
**Created**: 2025-10-31
**Status**: Draft
**Input**: User description: "Build an application -more of a script- that helps a dev team to do their code-reviews in time, by 1) fetching all the GitHub PRs made by or review-requested to any one of them 2) and sorting them by their staleness of not getting approved since the creation 3) and finally present the sorted in staleness descending order list of PRs with proper visualized UI that triggers interest and attention for them to eventually do code review for stale PRs. Final UI could be any form, but as a MVP, sending aesthetically intriguing slack message when run would be fine."

## Clarifications

### Session 2025-10-31

- Q: How should the system securely store and access GitHub tokens and Slack webhook URLs? → A: Environment variables via .env file (gitignored)
- Q: How should the system handle repositories with no branch protection rules (no required approvals configured)? → A: Default to requiring 1 approval
- Q: What should the system do when GitHub API rate limits are hit during repository scanning? → A: Print error to console with rate limit reset time, allow user to retry manually (no Slack notification)
- Q: When no stale PRs are found (all PRs are sufficiently approved or none exist), should the system still send a Slack notification? → A: Send a pleasing/celebratory message that celebrates the team's success
- Q: How should the system handle team member usernames that don't exist on GitHub? → A: GitHub API will return no PRs for non-existent users; system logs warning but continues processing other team members
- Q: How should the system handle PR approval state changes that happen during script execution (race conditions)? → A: Accept eventual consistency; snapshot data at query time reflects state at that moment (no real-time synchronization)
- Q: How should the system handle PRs with complex approval requirements (CODEOWNERS, required reviewers)? → A: Trust GitHub's mergeable state API and branch protection rules to determine if PR has sufficient approval; system does not reimplement complex approval logic
- Q: How should the system handle PRs where the team member is both author and requested reviewer? → A: Include the PR in results (matches filter criteria); this is a valid scenario where team member should be aware of the PR
- Q: How does the system handle PRs in repositories the authenticated user doesn't have access to? → A: Skip inaccessible repositories with a warning logged to console; continue processing accessible repositories (partial results acceptable)
- Q: What if the Slack webhook URL is invalid or Slack API returns an error? → A: Print error to console with webhook response details and exit with non-zero exit code; do not proceed with subsequent notifications
- Q: How does the system handle very large organizations (100+ repositories)? → A: System processes all repositories sequentially; performance validated in SC-007 (deferred); no pagination limits for MVP
- Q: What happens when a PR has never been marked "Ready for Review" (remains in draft)? → A: Draft PRs (ready_at = null) are excluded entirely from stale PR calculations; staleness measurement starts only when PR transitions to ready state

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Stale PR Detection & Notification (Priority: P1)

A development team lead runs a command-line tool that identifies all open pull requests across their GitHub organization that involve team members (as authors or requested reviewers) and currently lack sufficient approval. The tool calculates how long each PR has been waiting for approval and sends a prioritized list to their Slack channel, highlighting the most neglected PRs that need immediate attention.

**Why this priority**: This is the MVP that delivers the core value proposition - helping teams identify and act on stale PRs. It provides the essential feedback loop to improve code review response times without requiring complex UI or configuration.

**Independent Test**: Can be fully tested by configuring a team list, running the script against a GitHub organization with known PRs in various states, and verifying the Slack message contains the correct PRs sorted by staleness (most stale first), with PRs that have sufficient approval excluded.

**Acceptance Scenarios**:

1. **Given** a configuration file with 3 team member GitHub usernames and a GitHub organization with 5 open PRs (2 created by team members, 2 with team members as requested reviewers, 1 unrelated), **When** the script is executed, **Then** the script identifies exactly 4 PRs involving team members and posts them to Slack sorted by staleness.

2. **Given** a PR that was marked "Ready for Review" 5 days ago and has never been approved, **When** the staleness calculation runs, **Then** the PR shows staleness of 5 days.

3. **Given** a PR that was marked "Ready for Review" 10 days ago, received approval after 2 days, then lost approval due to new commits 3 days ago, **When** the staleness calculation runs, **Then** the PR shows staleness of 3 days (time since approval was lost).

4. **Given** a PR that was marked "Ready for Review" 7 days ago and received sufficient approval 1 day ago (currently approved), **When** the script filters PRs, **Then** this PR is excluded from the Slack message as it has current approval.

5. **Given** a PR in draft status for 10 days that was marked "Ready for Review" 2 days ago, **When** the staleness calculation runs, **Then** the PR shows staleness of 2 days (draft time is not counted).

6. **Given** a repository with branch protection requiring 2 approvals and a PR with only 1 approval for 4 days, **When** the script checks approval status, **Then** the PR is identified as lacking sufficient approval and shows 4 days staleness.

7. **Given** 10 PRs with varying staleness from 1 to 10 days, **When** the Slack message is generated, **Then** PRs are ordered with the 10-day stale PR at the top and the 1-day stale PR at the bottom.

8. **Given** a team configuration with usernames ["alice", "bob", "charlie"] and a GitHub org with 20 repositories, **When** the script runs, **Then** it successfully queries all repositories and returns results within reasonable time (under 2 minutes for typical org sizes).

9. **Given** a GitHub organization where all open PRs involving team members currently have sufficient approvals (or no open PRs exist), **When** the script executes, **Then** a pleasing/celebratory Slack message is sent confirming no stale PRs were found and celebrating the team's success in keeping reviews current.

---

### User Story 2 - Enhanced Slack UI with PR Context (Priority: P2)

A development team receives a rich, visually engaging Slack message that not only lists stale PRs but also provides key context for each PR including repository name, PR title, author, URL, current vs required approval count, and visual indicators (color coding, icons) that make it easy to quickly scan and prioritize which PRs to review first.

**Why this priority**: While P1 delivers the core functionality, P2 enhances team engagement by making the information more scannable and actionable. Visual cues and context help reviewers make faster decisions about which PRs to tackle first and provide direct links to jump into reviews.

**Independent Test**: Can be fully tested by running the script with the enhanced formatting enabled and verifying the Slack message uses Block Kit or message attachments with properly formatted fields, colors based on staleness severity, and clickable PR links that open directly to the GitHub PR page.

**Acceptance Scenarios**:

1. **Given** 5 stale PRs with staleness ranging from 1 to 10 days, **When** the enhanced Slack message is generated, **Then** each PR displays as a card showing repository name, PR number and title, author username, staleness days, current approval count vs required count, and a clickable PR URL.

2. **Given** a PR with 8 days staleness (critical), **When** the message is rendered, **Then** the PR card has a red/warning color indicator to signal urgency.

3. **Given** a PR with 2 days staleness (moderate), **When** the message is rendered, **Then** the PR card has a yellow/caution color indicator.

4. **Given** a PR requiring 2 approvals with 1 current approval, **When** the message is rendered, **Then** the approval status shows "1/2 approvals" or similar clear progress indicator.

5. **Given** a Slack message with 15 stale PRs, **When** the message is posted, **Then** the formatting remains readable and well-organized without exceeding Slack's message size limits.

---

### User Story 3 - Configurable Staleness Scoring (Priority: P3)

A development team can customize how staleness is calculated by configuring weights or rules for different scenarios, such as giving higher priority to PRs from certain repositories, adjusting staleness based on PR size or complexity, or applying different thresholds for "critical" vs "moderate" staleness.

**Why this priority**: This extends the tool's flexibility for teams with specific workflows or priorities. However, it's not essential for the initial value delivery and adds complexity that should be validated through usage of P1 and P2 first.

**Independent Test**: Can be fully tested by creating a configuration with custom scoring rules (e.g., "PRs in 'critical-services' repo get 2x staleness weight"), running the script, and verifying that PRs are sorted according to the adjusted scoring rather than pure time-based staleness.

**Acceptance Scenarios**:

1. **Given** a configuration that doubles staleness weight for PRs in repositories tagged as "critical", **When** a critical repo PR with 3 days staleness is compared to a normal repo PR with 5 days staleness, **Then** the critical PR (effective staleness 6 days) appears higher in the list.

2. **Given** a configuration with staleness thresholds (1-3 days = low, 4-7 days = medium, 8+ days = high), **When** the scoring system evaluates PRs, **Then** PRs are categorized and displayed within severity groups.

3. **Given** a custom scoring rule based on PR label (e.g., "urgent" label adds +5 days to staleness score), **When** an "urgent" PR with 2 days actual staleness is scored, **Then** it displays with effective 7 days staleness and is sorted accordingly.

---

### Edge Cases

- When GitHub API rate limits are hit, system prints error to console with rate limit reset time and exits, allowing user to manually retry after the reset window (no Slack notification sent)
- How does the system handle PRs in repositories the authenticated user doesn't have access to?
- Repositories with no branch protection rules default to requiring 1 approval (PRs with 0 approvals are considered stale, PRs with 1+ approvals are considered sufficiently approved)
- How does the system handle team member usernames that don't exist on GitHub?
- What happens when a PR has never been marked "Ready for Review" (remains in draft)?
- How does the system handle PR approval state changes that happen during script execution?
- What if the Slack webhook URL is invalid or Slack API returns an error?
- How does the system handle very large organizations (100+ repositories)?
- What happens when a PR has complex approval requirements (CODEOWNERS, required reviewers)?
- How does the system handle PRs where the team member is both author and requested reviewer?

## Requirements *(mandatory)*

### Functional Requirements

#### Configuration & Setup
- **FR-001**: System MUST load configuration from a file specifying team member GitHub usernames (array of strings)
- **FR-002**: System MUST load GitHub organization name from configuration
- **FR-003**: System MUST load GitHub authentication token from environment variables (using .env file for local development, gitignored to prevent credential leakage)
- **FR-004**: System MUST load Slack webhook URL from environment variables (using .env file for local development, gitignored to prevent credential leakage)
- **FR-005**: System MUST validate all required configuration values are present before execution

#### GitHub Integration
- **FR-006**: System MUST query all repositories in the specified GitHub organization
- **FR-007**: System MUST fetch all open pull requests across all organization repositories
- **FR-008**: System MUST filter PRs to include only those where at least one team member is the author OR is in the requested reviewers list
- **FR-009**: System MUST determine if a PR is in "Ready for Review" state (not draft)
- **FR-010**: System MUST identify when a PR was marked "Ready for Review" using the GitHub API's `ready_at` timestamp field (null for draft PRs, set when transitioning to ready state). For MVP, this avoids complex timeline API parsing while meeting staleness calculation needs.
- **FR-011**: System MUST check each PR's current approval status against the repository's approval requirements (defaulting to 1 required approval for repositories without branch protection rules)
- **FR-012**: System MUST exclude PRs that currently have sufficient approvals based on repository branch protection rules (or the default of 1 approval if no rules exist)

#### Staleness Calculation
- **FR-013**: System MUST calculate staleness as time elapsed from the most recent of: "PR marked Ready for Review" OR "PR lost approval status" to current time
- **FR-014**: System MUST track approval loss events by detecting when a PR had approvals that were subsequently dismissed or invalidated
- **FR-015**: System MUST track approval loss events when new commits are pushed to a PR after approval (if repository settings invalidate approvals on new commits)
- **FR-016**: System MUST express staleness in hours for PRs waiting less than 24 hours (e.g., "3 hours", "23 hours") and in days for PRs waiting 1+ day (e.g., "2 days", "5 days"). Implementation must format the float staleness_days value appropriately for display.

#### Sorting & Filtering
- **FR-017**: System MUST sort filtered PRs by staleness in descending order (most stale first)
- **FR-018**: System MUST handle PRs with identical staleness by applying a secondary sort by PR creation date (oldest first)

#### Slack Notification (P1)
- **FR-019**: System MUST format the sorted PR list as a Slack message with basic text formatting
- **FR-020**: System MUST include in each PR entry: repository name, PR number, PR title, staleness value
- **FR-021**: System MUST send the formatted message to the configured Slack webhook URL
- **FR-022**: System MUST handle Slack API response and report success or failure to the user
- **FR-023**: System MUST send a pleasing/celebratory Slack message when no stale PRs are found, confirming the check completed successfully with all PRs sufficiently approved

#### Enhanced Slack UI (P2)
- **FR-024**: System MUST format PRs as Slack Block Kit blocks or message attachments for rich visual presentation
- **FR-025**: System MUST include in each enhanced PR entry: repository name, PR number, PR title, author username, clickable PR URL, staleness value, approval progress (current vs required)
- **FR-026**: System MUST apply color coding to PR entries based on staleness severity thresholds
- **FR-027**: System MUST ensure the Slack message respects Slack's formatting and size constraints (40,000 characters max, 50 blocks max). When approaching limits, truncate the PR list with a footer message indicating "... and N more PRs" to maintain deliverability.

#### Configurable Scoring (P3)
- **FR-028**: System MUST support loading optional staleness scoring rules from configuration
- **FR-029**: System MUST apply configured staleness weights or multipliers when scoring rules are defined
- **FR-030**: System MUST sort PRs by adjusted staleness score when custom scoring is enabled
- **FR-031**: System MUST document available scoring rule types in configuration schema

#### Error Handling
- **FR-032**: System MUST handle GitHub API errors by logging the error details, displaying a clear user-facing message indicating the failure reason, and exiting with appropriate non-zero exit code
- **FR-033**: System MUST handle GitHub API rate limiting by printing an error message to console that includes the rate limit reset time, then exiting to allow the user to manually retry after the reset window (no Slack notification for rate limit errors)
- **FR-034**: System MUST handle missing configuration values with clear error messages
- **FR-035**: System MUST handle network failures when communicating with GitHub or Slack APIs
- **FR-036**: System MUST continue processing remaining PRs if individual PR data retrieval fails (with logging)

### Key Entities

- **Team Member Configuration**: A list of GitHub usernames representing the development team for which to track PRs. Includes: github_username (string), slack_user_id (string, optional - for @mentions in Slack messages).

- **Pull Request**: Represents an open GitHub pull request. Includes: repository name, PR number, PR title, author username, list of requested reviewer usernames, created_at timestamp, ready_at timestamp (null if draft), approval status (sufficient or insufficient), current approval count, required approval count, base_branch (target branch), URL to PR.

- **Approval Event**: Represents a change in a PR's approval status. Includes: PR identifier, timestamp of event, event type (approved, approval-dismissed, approval-invalidated), resulting approval status. *Note: This is a conceptual entity derived from GitHub API responses; not persisted as a dataclass in the implementation. Used transiently during staleness calculation.*

- **Staleness Score**: The calculated priority value for a PR based on time without sufficient approval. Includes: PR identifier, base staleness in days, effective staleness (if custom scoring applied), staleness category (low/medium/high based on thresholds).

- **Configuration**: System settings and credentials. Includes: team member usernames list, GitHub organization name, GitHub authentication token, Slack webhook URL, log_level (string, default: "INFO"), api_timeout (integer, default: 30 seconds), optional staleness scoring rules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Team members can execute the script and receive a Slack notification with the stale PR list within 2 minutes for organizations with up to 50 repositories.

- **SC-002**: The staleness calculation accurately reflects the time since "Ready for Review" or "Approval Lost" events with less than 1 hour margin of error (accounting for API data freshness). *(Validated through unit tests T026-T030 and integration tests T040-T044)*

- **SC-003**: The system correctly identifies and excludes PRs that currently have sufficient approval according to repository-specific rules, with 100% accuracy in filtering.

- **SC-004**: The Slack message is delivered successfully to the configured channel 95% of the time (allowing for transient network issues). *(Validated through integration tests T045-T048 and real-world testing T104)*

- **SC-005**: Team code review response time improves by at least 30% (measured as average time from PR ready-to-review to first approval) after 2 weeks of regular stale PR board usage. *(Deferred to post-MVP: Baseline measurement and tracking mechanism to be implemented after initial deployment)*

- **SC-006**: The sorted PR list prioritization is perceived as accurate by 80% of team members (validated through Slack poll or Google Form survey after 2 weeks of usage). *(Deferred to post-MVP: Survey mechanism to be implemented after initial deployment)*

- **SC-007**: The system handles organizations with up to 100 repositories and 200 open PRs without requiring more than 3 minutes execution time. *(Deferred to post-MVP: Formal performance benchmarking to be conducted after P1 implementation; informal testing during development sufficient for MVP)*

- **SC-008**: Error messages for common issues (missing config, invalid credentials, API errors) are clear enough that team members can self-resolve 90% of issues without developer support. *(Validated through unit tests T031-T035, error handling tasks T044/T056/T065, and manual testing T107)*

## Assumptions

The following assumptions have been made to provide reasonable defaults where specifications were not explicit:

1. **Execution Model**: The script is executed manually on-demand (via command line) rather than running on a schedule or continuously. Future iterations could add scheduled execution, but P1 focuses on the simplest invocation model.

2. **GitHub Authentication**: A GitHub Personal Access Token (classic or fine-grained) with appropriate scopes (`repo:read`, `org:read`) is used for authentication. The token is loaded from environment variables via a .env file (gitignored) for local development, ensuring credentials are never committed to version control.

3. **Slack Integration Method**: A Slack incoming webhook URL is used to post messages. This is the simplest integration method requiring no OAuth or app installation, suitable for MVP.

4. **Approval Status Source**: GitHub's PR review API and mergeable state information are trusted to accurately reflect whether a PR meets repository approval requirements. The system does not reimplement approval rule parsing from branch protection settings.

5. **Approval Loss Detection**: Approval loss is detected by examining PR review timeline events for "review dismissed" events and checking if new commits invalidate previous approvals based on repository settings. The GitHub API provides this information through review state changes.

6. **Draft PR Handling**: PRs that have never left draft status are excluded entirely from the stale PR list, as "Ready for Review" is the starting point for staleness calculation.

7. **Configuration Format**: Configuration is stored in a JSON file (e.g., `config.json`) for simplicity. Future iterations could support YAML or environment-only configuration.

8. **Staleness Thresholds (P2)**: For color coding in enhanced UI, reasonable defaults are: 1-3 days (green/low), 4-7 days (yellow/medium), 8+ days (red/high). These can be configurable in P3.

9. **API Rate Limits**: For a typical small-to-medium organization (up to 100 repos), GitHub API rate limits (5000 requests/hour for authenticated users) are sufficient. If rate limiting becomes an issue, the script reports the error and the team can retry after the reset window.

10. **Repository Access**: The authenticated GitHub user has read access to all repositories in the organization. If some repositories are inaccessible, those are skipped with a warning logged.

11. **Approval Progress Calculation (P2)**: "Current approval count" is the number of unique approving reviews that are currently valid (not dismissed, not invalidated by new commits). "Required approval count" is derived from branch protection rules for the PR's target branch.

12. **Timezone Handling**: All timestamps are compared in UTC to ensure consistent staleness calculations regardless of where the script is executed.

13. **Success Criteria Measurement Deferral**: SC-005 (response time improvement), SC-006 (team perception survey), and SC-007 (performance benchmarking) require longitudinal data collection and measurement infrastructure that is deferred to post-MVP. MVP focuses on delivering core functionality; measurement mechanisms will be added after initial deployment and usage validation.
