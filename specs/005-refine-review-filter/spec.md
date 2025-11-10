# Feature Specification: Refine Review-Needed PR Criteria

**Feature Branch**: `005-refine-review-filter`
**Created**: 2025-11-10
**Status**: Draft
**Input**: User description: "Let's redefine the condition of `review-needed` PR. Current implementation is `review:required`, but I'd like to also search for `review:none` PRs. And in addition to that, for PRs that require reviews from multiple users or certain group of users, I'd like to filter out `review:required` PRs that do not have any team member in its review waiting list. I'd like to also omit already review submitted github user from the final reviewer column so that it represents reviewers that are awaited."

## Clarifications

### Session 2025-11-10

- Q: When GitHub API rate limits are exceeded during the dual search queries (`review:none` and `review:required`), how should the system behave? → A: Retry with existing logic, but fail fast with clear error/warning if any search ultimately fails after all retries are exhausted (no silent partial results)
- Q: When expanding GitHub team memberships to check for team member presence (FR-007), should there be a limit on team size or number of teams processed? → A: Set a maximum team size limit (e.g., 100 members); if a team exceeds this, skip expansion and include the PR by default (fail-safe approach with logging)
- Q: When a search query fails after all retries are exhausted, where should the error/warning message be delivered? → A: Log to console/file only (no Slack notification sent if any search fails)
- Q: Should the team member presence filtering (checking if at least one team member is in `reviewRequests`) apply to both `review:none` and `review:required` PRs, or only to `review:required` PRs? → A: Apply team member filtering only to `review:required` PRs; include all `review:none` PRs where team members are requested reviewers (since review:none searches already constrain to PRs with team member reviewers, filtering would be redundant)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Include Review-Required PRs (Priority: P1)

Team members receive notifications for PRs in both states: those with no reviews yet (`review:none`) and those with some reviews but requiring additional approvals (`review:required`), ensuring that PRs needing team attention are not missed regardless of their review status.

**Why this priority**: This is the core enhancement - expanding the search criteria from only `review:none` to include `review:required` PRs. This ensures PRs that have received partial reviews but still need team member approval are captured in the board.

**Independent Test**: Can be fully tested by creating PRs with different review states (no reviews, 1 approval but 2 required, etc.) and verifying that both `review:none` and `review:required` PRs appear in the notification when team members are requested reviewers.

**Acceptance Scenarios**:

1. **Given** a PR with no reviews submitted (review:none) and a team member as requested reviewer, **When** fetching team PRs, **Then** the PR is included in the results
2. **Given** a PR with 1 approval but requiring 2 approvals (review:required) and a team member as requested reviewer, **When** fetching team PRs, **Then** the PR is included in the results
3. **Given** a PR with all required approvals (review:approved), **When** fetching team PRs, **Then** the PR is excluded from results

---

### User Story 2 - Display Current Requested Reviewers (Priority: P2)

The reviewer column displays only reviewers who currently appear in GitHub's requested reviewers list, which automatically excludes reviewers who have completed their review (unless re-requested by the PR author). This allows team members to see at a glance who still needs to take action.

**Why this priority**: Clarifies that the system should use GitHub's current `reviewRequests` field as the source of truth for pending reviewers. GitHub automatically removes reviewers from this list after they submit reviews (unless re-requested), so we get correct behavior by default.

**Independent Test**: Can be tested by creating a PR with 3 requested reviewers where 1 has approved (not re-requested) and 2 have not reviewed, then verifying only the 2 pending reviewers appear in the reviewer column. Also test that re-requested reviewers appear even after submitting a review.

**Acceptance Scenarios**:

1. **Given** a PR with requested reviewers [user_a, user_b, user_c] where user_a has approved and NOT been re-requested, **When** displaying the PR, **Then** the reviewer column shows only [user_b, user_c] (GitHub removes user_a from reviewRequests)
2. **Given** a PR with requested reviewers [user_a, user_b] where user_a has approved and BEEN re-requested, **When** displaying the PR, **Then** the reviewer column shows [user_a, user_b] (GitHub re-adds user_a to reviewRequests)
3. **Given** a PR with requested reviewers [user_a] where user_a has submitted "CHANGES_REQUESTED" and NOT been re-requested, **When** displaying the PR, **Then** the reviewer column shows empty "-" (GitHub removes user_a from reviewRequests after their review)
4. **Given** a PR with a GitHub team as requested reviewer, **When** displaying the PR, **Then** the reviewer column shows the team name (not expanded member list)

---

### User Story 3 - Filter Review-Required PRs by Team Member Presence (Priority: P3)

When a PR requires reviews from multiple users or GitHub teams, the system only includes `review:required` PRs where at least one team member appears in the current requested reviewers list, preventing notifications for PRs where the team's review obligation is already fulfilled.

**Why this priority**: This filtering logic prevents false positives - PRs that technically need more reviews but not from our team. This improves signal-to-noise ratio but can be implemented after the basic dual-search functionality.

**Independent Test**: Can be tested by creating a `review:required` PR where team members have already reviewed and are not re-requested (removed from reviewRequests), and verifying it does not appear in the notification.

**Acceptance Scenarios**:

1. **Given** a review:required PR with reviewRequests [user_a, user_b, team_member_c] where team_member_c is the only team member, **When** fetching team PRs, **Then** the PR is included
2. **Given** a review:required PR with reviewRequests [user_a, user_b] where neither are team members, **When** fetching team PRs, **Then** the PR is excluded
3. **Given** a review:required PR with a GitHub team in reviewRequests and at least one team member in that team, **When** fetching team PRs, **Then** the PR is included
4. **Given** a review:required PR where team members have already reviewed and are NOT in reviewRequests (not re-requested), **When** fetching team PRs, **Then** the PR is excluded

---

### User Story 4 - Handle GitHub Team Review Requests (Priority: P3)

For PRs with GitHub teams as requested reviewers, the system correctly identifies whether any team members are in the review waiting list by expanding team membership, ensuring team-based review requests are properly filtered.

**Why this priority**: Handles the specific case of GitHub team review requests, which requires additional API calls to expand team membership. Important for completeness but can be deferred after individual user filtering works.

**Independent Test**: Can be tested by creating a PR with a GitHub team as requested reviewer, verifying that team membership is expanded for filtering purposes, and confirming the PR appears only if team members from our tracked team are part of the requested team.

**Acceptance Scenarios**:

1. **Given** a review:required PR with a GitHub team in reviewRequests, **When** the GitHub team contains team members, **Then** the PR is included
2. **Given** a review:required PR with a GitHub team in reviewRequests, **When** the GitHub team contains no team members, **Then** the PR is excluded
3. **Given** a review:required PR with both individual and team reviewers in reviewRequests, **When** at least one team member exists in either list, **Then** the PR is included
4. **Given** a PR with a GitHub team in reviewRequests, **When** displaying reviewers, **Then** the team name is shown (not expanded member list)

---

### Edge Cases

- What happens when a PR has `review:required` but the reviewRequests list is empty? (Exclude the PR - no one is actively waiting for review)
- What happens when a PR transitions from `review:none` to `review:required` during processing? (PR will be captured by whichever search query runs, no duplicate due to deduplication logic)
- What happens when a team member is part of multiple GitHub teams in reviewRequests? (PR is included as long as any team contains the team member)
- What happens when GitHub team membership API call fails? (Fall back to showing the team request without expansion, PR is included to avoid missing notifications)
- What happens when all originally requested reviewers have submitted reviews and none have been re-requested? (reviewRequests is empty, reviewer column shows "-", PR is excluded from `review:required` search)
- What happens when a reviewer dismisses their own review? (GitHub determines reviewRequests behavior, system uses current state)
- What happens when PR author requests review from new reviewers after initial reviews submitted? (New reviewers appear in reviewRequests, PR may be included if they are team members)
- What happens when GitHub API rate limits are exceeded during dual search queries? (Apply existing retry logic to both searches; if either search fails after all retries exhausted, log error to console/file and do not send Slack notification - prevents misleading partial notifications)
- What happens when a GitHub team in reviewRequests exceeds the maximum team size limit (e.g., 100 members)? (Skip expansion for that team, include the PR by default to avoid missing notifications, and log the occurrence for monitoring)
- Does team member presence filtering apply to both `review:none` and `review:required` PRs? (No, filtering only applies to `review:required` PRs; `review:none` PRs are included if team members are requested reviewers, since the search query already constrains to those PRs)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST search for PRs with both `review:none` AND `review:required` status when fetching team PRs
- **FR-002**: System MUST execute separate search queries for each review status (`review:none` and `review:required`) and merge results with deduplication
- **FR-003**: System MUST filter `review:required` PRs (and ONLY `review:required` PRs, not `review:none` PRs) to include only those where at least one team member appears in the current `reviewRequests` field (GitHub's source of truth for pending reviewers)
- **FR-004**: System MUST use GitHub's `reviewRequests` field as the authoritative source for determining which reviewers are currently awaited
- **FR-005**: System MUST display only reviewers from the `reviewRequests` field in the reviewer column, which automatically handles review submissions and re-requests
- **FR-006**: System MUST check both individual user reviewers and GitHub team reviewers in `reviewRequests` when determining team member presence for `review:required` PR filtering
- **FR-007**: System MUST expand GitHub team memberships to check if any team members are part of teams in `reviewRequests` for `review:required` PR filtering purposes; if a team exceeds maximum size limit (100 members), system MUST skip expansion, include the PR by default (fail-safe), and log the occurrence
- **FR-008**: System MUST display GitHub team names (not expanded members) in the reviewer column when a team appears in `reviewRequests`
- **FR-009**: System MUST exclude PRs where review status is `APPROVED` (all required reviews obtained)
- **FR-010**: System MUST preserve existing deduplication logic to handle PRs appearing in multiple search results
- **FR-011**: System MUST maintain existing rate limit handling and retry logic for the additional search queries; if either search fails after all retries are exhausted, system MUST log the error to console/file and NOT send any Slack notification (prevents misleading partial notifications)
- **FR-012**: System MUST log the count of PRs fetched from each search query (`review:none` vs `review:required`) for observability
- **FR-013**: Team member presence check MUST be case-insensitive when comparing GitHub usernames
- **FR-014**: System MUST display "-" in the reviewer column when `reviewRequests` field is empty

### Key Entities

- **ReviewStatus**: Enum representing PR review state - `none` (no reviews yet), `required` (some reviews submitted, more needed), `approved` (all reviews obtained)
- **ReviewRequest**: Entry in GitHub's `reviewRequests` field representing a reviewer (individual or team) currently awaited for review
- **GitHubTeamReviewRequest**: GitHub team with expanded member list (already exists in codebase)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Team receives notifications for 100% of PRs where team members appear in the `reviewRequests` field, regardless of whether the PR has `review:none` or `review:required` status
- **SC-002**: False positive rate for `review:required` PRs (PRs shown where team is not in `reviewRequests`) is reduced to 0%
- **SC-003**: Reviewer column accuracy rate is 100% - only reviewers currently in `reviewRequests` are displayed, automatically handling review submissions and re-requests
- **SC-004**: PR deduplication ensures each PR appears exactly once in the notification, even if captured by multiple search queries
- **SC-005**: Total API call time for PR fetching increases by no more than 50% compared to current implementation (acceptable trade-off for improved coverage)
- **SC-006**: Team members can identify within 3 seconds who still needs to review by scanning the reviewer column

## Dependencies & Constraints

### Dependencies

- GitHub CLI (`gh`) must support `--review required` search filter
- Existing `gh search prs` command syntax remains compatible with additional review filter values
- GitHub API team membership endpoint remains accessible for expanding team review requests
- PR detail fetching must include `reviewRequests` field to determine current pending reviewers
- Existing `PullRequest` and `GitHubTeamReviewRequest` data models support storing requested reviewers

### Constraints

- GitHub search API has separate rate limits for search queries vs detail fetches (must account for additional search queries)
- `review:required` PRs include those with `CHANGES_REQUESTED` reviews, which may or may not need team member attention
- GitHub team membership API calls add latency proportional to number of team-based review requests
- Deduplication must happen before detail fetching to avoid redundant API calls
- System behavior depends on GitHub's automatic management of `reviewRequests` field (removes reviewers after review, re-adds on re-request)
- Maximum team size limit (100 members) prevents unbounded API calls for very large GitHub teams; oversized teams trigger fail-safe inclusion with logging

## Assumptions

- The `--review required` flag in `gh search prs` returns PRs where review decision is not yet approved (at least one more review needed)
- Team member usernames in `team_members.json` exactly match GitHub usernames (case-insensitive)
- A PR should be shown if ANY team member is in `reviewRequests`, not requiring ALL team members to be pending reviewers
- GitHub automatically removes reviewers from `reviewRequests` after they submit a review (unless dismissal settings differ)
- GitHub automatically re-adds reviewers to `reviewRequests` when the PR author uses the "re-request review" feature
- The current codebase already uses `reviewRequests` field for displaying reviewers, so this behavior is preserved
- The performance impact of doubling search queries (one per review status) is acceptable given the improved PR coverage
- GitHub team review requests are expanded to individual members for filtering purposes (for `review:required` PRs only), but the display still shows the team name
- For display purposes, if `reviewRequests` is empty, showing "-" in reviewer column is acceptable
- `review:none` PRs do not require team member presence filtering since the search query already constrains results to PRs where team members are requested reviewers
