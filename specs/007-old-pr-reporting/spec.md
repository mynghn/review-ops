# Feature Specification: Too Old PRs Reporting

**Feature Branch**: `007-old-pr-reporting`
**Created**: 2025-11-11
**Status**: Draft
**Input**: User description: "Let's add too old PRs reporting functionality to the stale PR board app. It restricts PR search with recent updates upto configured days (e.g. 30 days). Send additional in-thread message if there are too old review-requested PRs for each team members. Message should contain GitHub web link to the PR search page for each members."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Recent PRs on Main Board (Priority: P1)

Team members viewing the Slack stale PR board see only PRs that have been updated within the configured time window (e.g., last 30 days). This keeps the main board focused on actionable review requests and prevents it from being cluttered with very old PRs that may have been abandoned or are stale.

**Why this priority**: This is the core value of the feature - keeping the main board actionable and focused. Without this, the board becomes overwhelming with historical PRs.

**Independent Test**: Can be fully tested by configuring a 30-day threshold, creating PRs with various update dates, and verifying only recent PRs appear on the main board. Delivers immediate value by improving board relevance.

**Acceptance Scenarios**:

1. **Given** the age threshold is configured to 30 days and there are PRs updated 20 days ago, **When** the stale PR board is generated, **Then** those PRs appear on the main board message
2. **Given** the age threshold is configured to 30 days and there are PRs with review requests updated 35 days ago, **When** the stale PR board is generated, **Then** those PRs do NOT appear on the main board message
3. **Given** no age threshold is configured, **When** the stale PR board is generated, **Then** all PRs appear on the main board regardless of update date (backward compatible behavior)

---

### User Story 2 - Discover Too Old PRs via Thread Message (Priority: P2)

Team members can check the thread reply to the main board message to discover if any team members have review-requested PRs older than the configured threshold. The thread message lists each team member who has old PRs using a simple bulleted format with emoji (⚠️), username mention, count, and a GitHub search link to view those specific PRs (e.g., "⚠️ @alice: 3 old PRs → [View on GitHub](link)").

**Why this priority**: This provides visibility into potentially abandoned PRs without cluttering the main board. It's a supplementary alert mechanism.

**Independent Test**: Can be tested independently by configuring a threshold, creating old PRs for specific team members, and verifying the thread message contains correct links and counts. Delivers value by surfacing old PRs that need attention or cleanup.

**Acceptance Scenarios**:

1. **Given** the age threshold is 30 days and team member Alice has 2 PRs with review requests updated 35 days ago, **When** the stale PR board is posted, **Then** a thread reply is posted listing Alice with count "2" and a GitHub search link
2. **Given** the age threshold is 30 days and no team members have PRs older than 30 days, **When** the stale PR board is posted, **Then** no thread reply is posted
3. **Given** the age threshold is 30 days and multiple team members (Alice, Bob, Charlie) have old PRs, **When** the thread reply is posted, **Then** the message lists all team members with their counts and individual GitHub search links
4. **Given** a team member clicks on the GitHub search link in the thread, **When** GitHub opens, **Then** the search results show only that team member's PRs with review requests older than the threshold

---

### User Story 3 - Configure Age Threshold (Priority: P3)

Administrators can configure the age threshold (in days) that defines what constitutes a "too old" PR. This threshold determines which PRs are excluded from the main board and reported in the thread.

**Why this priority**: Configuration flexibility is important but not critical for initial value delivery. A reasonable default (e.g., 30 days) can be used initially.

**Independent Test**: Can be tested by setting different threshold values (15, 30, 60 days) and verifying the main board and thread messages reflect the configured threshold. Delivers value by adapting to different team workflows.

**Acceptance Scenarios**:

1. **Given** the age threshold is set to 30 days, **When** the application runs, **Then** PRs updated more than 30 days ago are excluded from main board and reported in thread
2. **Given** the age threshold is set to 15 days, **When** the application runs, **Then** PRs updated more than 15 days ago are excluded from main board and reported in thread
3. **Given** the age threshold configuration is invalid or missing, **When** the application runs, **Then** all PRs appear on main board with no thread message (backward compatible default behavior)

---

## Clarifications

### Session 2025-11-11

- Q: How should the system determine which team members to include in the thread message? → A: Fetch old PRs first to count them, then only include team members with count > 0
- Q: Should archived or closed PRs be included in the "too old" count? → A: Exclude archived and closed PRs (only count open PRs)
- Q: Should the age threshold calculation use calendar days or business days? → A: Use calendar days (simpler, consistent with GitHub API --updated filter)
- Q: What environment variable should be used for the age threshold? → A: Use existing GH_SEARCH_WINDOW_SIZE (no new variable needed)
- Q: What format should the thread message use? → A: Simple bulleted text list with emoji and links (lightweight, scannable)

---

### Edge Cases

- **URL Length Limit**: GitHub search URLs have browser limit (~2000 chars). Mitigation: Raise ValueError in url_builder.py if URL exceeds limit. Display error in dry-run mode; skip team member in thread message with warning log in production mode.
- **Empty Old PR List**: When no team members have old PRs, skip thread posting entirely (tested in T065).
- **Invalid Date Configuration**: When GH_SEARCH_WINDOW_SIZE is invalid, fall back to no age filtering (backward compatible, tested in T056).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST restrict PR search to only include PRs updated within the configured age threshold (e.g., 30 days)
- **FR-001a**: System MUST exclude archived and closed PRs from both main board and old PR reporting (only open PRs are considered)
- **FR-002**: System MUST identify PRs with review requests that are older than the configured age threshold
- **FR-002a**: System MUST fetch old PRs and count them per team member to determine who should be included in the thread message
- **FR-003**: System MUST post an in-thread reply message when one or more team members have old PRs
- **FR-004**: System MUST generate a GitHub search URL for each team member showing their old PRs
- **FR-005**: System MUST include the count of old PRs for each team member in the thread message
- **FR-006**: System MUST use existing `GH_SEARCH_WINDOW_SIZE` environment variable to determine the age threshold (no new environment variable needed)
- **FR-006a**: Age threshold MUST use calendar days (not business days) for consistency with GitHub API date filtering
- **FR-007**: System MUST use PR last updated date (not creation date) to determine age
- **FR-008**: System MUST only include team members with at least one old PR in the thread message
- **FR-009**: System MUST format the thread message as a simple bulleted text list with emoji (⚠️), username mentions, count, and GitHub search links in bilingual format (EN/KO)
- **FR-010**: System MUST handle missing or invalid age threshold configuration by using default behavior (no age filtering)
- **FR-011**: GitHub search URLs MUST filter by the team member's username, state:open, and last updated date older than threshold
- **FR-012**: System MUST preserve existing stale PR board functionality when age threshold is not configured

### Key Entities

- **Age Threshold Configuration**: Number of days that defines the cutoff for "too old" PRs. Derived from existing `GH_SEARCH_WINDOW_SIZE` environment variable. PRs with last update older than this are excluded from main board.
- **Old PR Report Entry**: Represents a team member with old PRs, containing: team member GitHub username, count of old PRs, and GitHub search URL to view those PRs.
- **PR Update Date**: The last updated timestamp of a PR, used to determine if it exceeds the age threshold.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Main board displays only PRs updated within the configured age threshold (e.g., 0% of PRs older than 30 days appear on main board when threshold is set to 30 days)
- **SC-002**: Thread message is posted within 5 seconds of main board message when old PRs are detected
- **SC-003**: GitHub search links in thread message return accurate results (100% of links show only the specified team member's old PRs)
- **SC-004**: Team members can identify old PRs requiring action in under 30 seconds using the thread message
- **SC-005**: Configuration changes take effect on next run without requiring code changes
- **SC-006**: Existing users see no change in behavior when age threshold is not configured (100% backward compatibility)

## Assumptions

- The "last updated" date of a PR is available via GitHub API (assumed to be the `updated_at` field)
- Team members want to see old PRs reported separately rather than not at all
- Existing `GH_SEARCH_WINDOW_SIZE` environment variable can be reused to define the age threshold (default: 30 days)
- Age threshold uses calendar days (not business days) for simplicity and consistency with GitHub API `--updated` filtering
- GitHub search URLs can be constructed using query parameters for username and updated date filters
- Slack chat.postMessage API must be used instead of webhooks (webhooks do not support thread replies or return message timestamps per research findings)
- The main board message posting will return a timestamp (ts) from Slack chat.postMessage API for thread reply targeting
- **BREAKING CHANGE**: Requires migration from SLACK_WEBHOOK_URL to SLACK_BOT_TOKEN + SLACK_CHANNEL_ID configuration
- Team members listed in `team_members.json` are the only ones whose old PRs should be reported

## Dependencies

- GitHub API must provide PR last updated dates (available via `updated_at` field)
- Slack chat.postMessage API (requires bot token with chat:write scope)
- Main board posting must use chat.postMessage API to return message timestamp for threading
- **BREAKING CHANGE**: Existing webhook-based deployments must migrate to Slack Bot API (see quickstart.md for migration guide)
- Existing PR fetching logic from `github_client.py`
- Existing team member configuration from `team_members.json`

## Out of Scope

- Automatic cleanup or closing of old PRs
- Email notifications for old PRs
- Historical tracking of old PR trends over time
- Custom age thresholds per team member or repository
- Integration with PR review reminders or nudges
- Displaying old PRs in the main board with a special indicator (they are excluded entirely)
