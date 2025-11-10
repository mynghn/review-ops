# Tasks: Refine Review-Needed PR Criteria

**Input**: Design documents from `/specs/005-refine-review-filter/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Tests are MANDATORY per constitution (TDD cycle). Every user story MUST have tests written BEFORE implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and verification

- [X] T001 Verify Python 3.12 and pytest are available
- [X] T002 Verify gh CLI is installed and authenticated
- [X] T003 Review existing github_client.py structure (lines 425-881)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create helper method _search_prs_by_review_status in src/github_client.py to execute single search query with review status parameter
- [X] T005 Add unit test for _search_prs_by_review_status method in tests/unit/test_github_client.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Include Review-Required PRs (Priority: P1) 🎯 MVP

**Goal**: Expand PR search criteria to include both `review:none` and `review:required` PRs with proper deduplication

**Independent Test**: Create PRs with different review states and verify both `review:none` and `review:required` PRs appear in results without duplication

### Tests for User Story 1 (MANDATORY - TDD cycle) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [P] [US1] Write unit test for dual search execution in tests/unit/test_github_client.py to verify both review:none and review:required searches execute
- [X] T007 [P] [US1] Write unit test for PR deduplication in tests/unit/test_github_client.py to verify PRs appearing in both searches are only fetched once
- [X] T008 [P] [US1] Write unit test for search metadata tracking in tests/unit/test_github_client.py to verify pr_search_metadata dictionary records which searches found each PR
- [X] T009 [P] [US1] Write unit test for empty search results in tests/unit/test_github_client.py to verify handling when either search returns no results

### Implementation for User Story 1

- [X] T010 [US1] Modify fetch_team_prs method in src/github_client.py to initialize pr_search_metadata dictionary for tracking search origins
- [X] T011 [US1] Update fetch_team_prs method in src/github_client.py to execute dual searches (review:none and review:required) using _search_prs_by_review_status helper
- [X] T012 [US1] Update fetch_team_prs method in src/github_client.py to track search origin in pr_search_metadata for each PR key found
- [X] T013 [US1] Verify PR deduplication works correctly with existing pr_keys set in fetch_team_prs method
- [X] T014 [US1] Run tests T006-T009 to verify dual search and deduplication implementation

**Checkpoint**: At this point, User Story 1 should be fully functional - both review:none and review:required PRs are fetched without duplication

---

## Phase 4: User Story 2 - Display Current Requested Reviewers (Priority: P2)

**Goal**: Display only reviewers who currently appear in GitHub's requested reviewers list (reviewRequests field)

**Independent Test**: Create PR with 3 requested reviewers where 1 has approved (not re-requested), verify only 2 pending reviewers appear in display

**Note**: This functionality ALREADY EXISTS in the codebase. The system already uses the reviewRequests field from PullRequest model. This phase adds tests to verify existing behavior.

### Tests for User Story 2 (MANDATORY - TDD cycle) ⚠️

- [X] T015 [P] [US2] Write unit test in tests/unit/test_github_client.py to verify reviewers list comes from reviewRequests field
- [X] T016 [P] [US2] Write unit test in tests/unit/test_slack_client.py to verify reviewer column displays reviewers from PullRequest.reviewers list
- [X] T017 [P] [US2] Write unit test in tests/unit/test_slack_client.py to verify empty reviewRequests displays as "-" in reviewer column

### Implementation for User Story 2

- [X] T018 [US2] Verify existing PullRequest model in src/models.py correctly populates reviewers field from GitHub reviewRequests
- [X] T019 [US2] Verify existing SlackClient in src/slack_client.py correctly displays reviewers from PullRequest.reviewers
- [X] T020 [US2] Run tests T015-T017 to verify reviewer display works correctly
- [X] T021 [US2] Document reviewRequests behavior in code comments if not already present

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - PRs are fetched with dual search, and only current pending reviewers are displayed

---

## Phase 5: User Story 3 - Filter Review-Required PRs by Team Member Presence (Priority: P3)

**Goal**: Filter review:required PRs to include only those where at least one team member appears in reviewRequests, preventing notifications for PRs where team review obligation is fulfilled

**Independent Test**: Create review:required PR where team members have already reviewed and are not in reviewRequests, verify it does not appear in notification

### Tests for User Story 3 (MANDATORY - TDD cycle) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T022 [P] [US3] Write unit test in tests/unit/test_github_client_filtering.py to verify review:required PR with team member in reviewers is included
- [X] T023 [P] [US3] Write unit test in tests/unit/test_github_client_filtering.py to verify review:required PR without team members in reviewers is excluded
- [X] T024 [P] [US3] Write unit test in tests/unit/test_github_client_filtering.py to verify review:none PR without team members in reviewers is included (no filtering applied)
- [X] T025 [P] [US3] Write unit test in tests/unit/test_github_client_filtering.py to verify case-insensitive username comparison (Alice matches alice)
- [X] T026 [P] [US3] Write unit test in tests/unit/test_github_client_filtering.py to verify empty reviewRequests list causes PR exclusion

### Implementation for User Story 3

- [X] T027 [US3] Create _filter_by_team_member_presence method in src/github_client.py to check if team members are in reviewers or github_team_reviewers
- [X] T028 [US3] Implement case-insensitive username comparison logic in _filter_by_team_member_presence method using lowercased username sets
- [X] T029 [US3] Update fetch_team_prs method in src/github_client.py to call _filter_by_team_member_presence after detail fetching
- [X] T030 [US3] Ensure filtering applies ONLY to PRs marked as "review:required" in pr_search_metadata, not to "review:none" PRs
- [X] T031 [US3] Add debug logging in _filter_by_team_member_presence to log when PRs are excluded due to no team members
- [X] T032 [US3] Run tests T022-T026 to verify filtering implementation

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work - PRs are fetched with dual search, filtered by team member presence, and display correct reviewers

---

## Phase 6: User Story 4 - Handle GitHub Team Review Requests (Priority: P3)

**Goal**: For PRs with GitHub teams as requested reviewers, correctly identify whether any team members are in the review waiting list by expanding team membership with 100-member size limit

**Independent Test**: Create PR with GitHub team as requested reviewer, verify team membership is expanded for filtering and PR appears only if tracked team members are part of the requested team

### Tests for User Story 4 (MANDATORY - TDD cycle) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T033 [P] [US4] Write unit test in tests/unit/test_github_client_filtering.py to verify review:required PR with team member in github_team_reviewers.members is included
- [X] T034 [P] [US4] Write unit test in tests/unit/test_github_client_filtering.py to verify review:required PR with GitHub team containing no tracked team members is excluded
- [X] T035 [P] [US4] Write unit test in tests/unit/test_github_client.py to verify team size check for oversized teams (>100 members)
- [X] T036 [P] [US4] Write unit test in tests/unit/test_github_client.py to verify fail-safe inclusion when team expansion fails or size exceeds limit
- [X] T037 [P] [US4] Write unit test in tests/unit/test_slack_client.py to verify GitHub team name (not expanded members) displays in reviewer column

### Implementation for User Story 4

- [X] T038 [US4] Create _fetch_github_team_members_with_limit method in src/github_client.py that checks team size before expansion
- [X] T039 [US4] Implement team size check using gh api /orgs/{org}/teams/{team_slug} to get members_count in _fetch_github_team_members_with_limit
- [X] T040 [US4] Add logic to skip expansion and return None when team size exceeds 100 members (fail-safe signal)
- [X] T041 [US4] Add warning log when team size exceeds limit in _fetch_github_team_members_with_limit
- [X] T042 [US4] Update _filter_by_team_member_presence method in src/github_client.py to handle None members (fail-safe inclusion)
- [X] T043 [US4] Update existing team expansion calls to use _fetch_github_team_members_with_limit instead of _fetch_github_team_members
- [X] T044 [US4] Run tests T033-T037 to verify GitHub team handling implementation
- [X] T045 [US4] Verify existing SlackClient correctly displays GitHub team names (not expanded members) in reviewer column

**Checkpoint**: All user stories should now be independently functional - complete dual search, filtering, team expansion, and correct display

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T046 [P] Add observability logging in src/github_client.py to log count of PRs from review:none vs review:required searches (FR-012)
- [X] T047 [P] Add observability logging in src/github_client.py to log deduplication statistics (PRs in both searches)
- [X] T048 [P] Add observability logging in src/github_client.py to log filtering statistics (PRs excluded by team member filtering)
- [X] T049 [P] Add error handling in src/github_client.py to fail fast with clear error if either search fails after retries (FR-011)
- [X] T050 [P] Write integration test in tests/integration/ to verify rate limit handling works with dual searches
- [X] T051 [P] Write integration test in tests/integration/ to verify API call delay between searches
- [X] T052 Run complete test suite with pytest to verify all functionality
- [X] T053 Update CLAUDE.md with dual search behavior and team member filtering logic
- [ ] T054 Manual testing following quickstart.md validation scenarios
- [ ] T055 Verify total execution time is under 30 seconds for typical workload (15 members, 30 PRs)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P2): Can start after Foundational - Independent (just verifying existing behavior)
  - User Story 3 (P3): Depends on User Story 1 (needs dual search to exist before filtering)
  - User Story 4 (P3): Depends on User Story 3 (needs filtering logic to integrate team expansion)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

```
Foundational (Phase 2)
    ↓
User Story 1 (P1) - Dual Search + Deduplication
    ↓
User Story 2 (P2) - Display Reviewers (Independent, can run in parallel with US3)
    ↓
User Story 3 (P3) - Filter by Team Member Presence
    ↓
User Story 4 (P3) - Handle GitHub Team Expansion
    ↓
Polish (Phase 7)
```

### Within Each User Story

1. Tests MUST be written and FAIL before implementation (TDD cycle)
2. Tests marked [P] can run in parallel (different test files)
3. Implementation tasks follow test completion
4. Story complete and verified before moving to next priority

### Parallel Opportunities

- **Phase 1 (Setup)**: All 3 tasks can run in parallel (different verification activities)
- **Phase 2 (Foundational)**: T004 and T005 must run sequentially (test depends on method)
- **Phase 3 (US1) Tests**: T006-T009 can all run in parallel (different test scenarios)
- **Phase 4 (US2) Tests**: T015-T017 can all run in parallel (different files)
- **Phase 5 (US3) Tests**: T022-T026 can all run in parallel (different test scenarios)
- **Phase 6 (US4) Tests**: T033-T037 can all run in parallel (different test scenarios)
- **Phase 7 (Polish)**: T046-T051 can all run in parallel (different concerns)

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all tests for User Story 1 together (TDD):
Task T006: "Write unit test for dual search execution"
Task T007: "Write unit test for PR deduplication"
Task T008: "Write unit test for search metadata tracking"
Task T009: "Write unit test for empty search results"

# Then sequentially implement:
Task T010 → T011 → T012 → T013 → T014 (run tests)
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - creates helper method)
3. Complete Phase 3: User Story 1 (Dual search with deduplication)
4. Complete Phase 4: User Story 2 (Verify reviewer display)
5. **STOP and VALIDATE**: Test dual search works, reviewers display correctly
6. Deploy/demo if ready

**MVP Delivers**: PRs with both review:none and review:required states appear in notifications with correct pending reviewers displayed

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Basic dual search working
3. Add User Story 2 → Test independently → Correct reviewer display
4. Add User Story 3 → Test independently → Smart filtering active
5. Add User Story 4 → Test independently → Complete GitHub team support
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (blocking for US3)
   - Developer B: User Story 2 (independent, can run in parallel)
3. After US1 completes:
   - Developer A: User Story 3 (builds on US1)
4. After US3 completes:
   - Developer A: User Story 4 (builds on US3)
5. Stories integrate sequentially for this feature due to dependencies

---

## Notes

- [P] tasks = different files/concerns, no dependencies
- [Story] label maps task to specific user story for traceability
- TDD cycle is mandatory: Write tests → Verify failure → Implement → Verify success
- Each user story should be independently testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- User Story 1 is the MVP - delivers core dual search functionality
- User Story 3 depends on US1, User Story 4 depends on US3
- Total estimated implementation time: ~4 days (per plan.md constitution check)

---

## Task Summary

- **Total Tasks**: 55
- **Phase 1 (Setup)**: 3 tasks
- **Phase 2 (Foundational)**: 2 tasks
- **Phase 3 (User Story 1 - P1)**: 9 tasks (4 tests, 5 implementation)
- **Phase 4 (User Story 2 - P2)**: 7 tasks (3 tests, 4 implementation)
- **Phase 5 (User Story 3 - P3)**: 11 tasks (5 tests, 6 implementation)
- **Phase 6 (User Story 4 - P3)**: 13 tasks (5 tests, 8 implementation)
- **Phase 7 (Polish)**: 10 tasks

**Parallel Opportunities Identified**: 23 tasks marked [P] can run in parallel within their phases

**Independent Test Criteria**:
- US1: Create PRs with different review states, verify both appear without duplication
- US2: Create PR with reviewers who have/haven't reviewed, verify only pending shown
- US3: Create review:required PR with/without team members, verify filtering works
- US4: Create PR with GitHub team reviewers, verify team expansion and filtering

**Suggested MVP Scope**: User Stories 1 + 2 (Phases 1-4) - delivers dual search with correct reviewer display
