---

description: "Task list for GitHub API Rate Limit Handling implementation"
---

# Tasks: GitHub API Rate Limit Handling

**Input**: Design documents from `/specs/003-github-rate-limit-handling/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, quickstart.md

**Tests**: Tests are MANDATORY per constitution (TDD cycle). Every user story MUST have tests written BEFORE implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single project structure: `src/`, `tests/` at repository root
- All Python modules in `src/`
- Tests split into `tests/unit/` and `tests/integration/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and configuration setup

- [X] T001 Add new environment variables to .env.example (MAX_PRS_TOTAL, MAX_RETRIES, RATE_LIMIT_WAIT_THRESHOLD, RETRY_BACKOFF_BASE, USE_GRAPHQL_BATCH)
- [X] T002 [P] Add RateLimitStatus dataclass to src/models.py
- [X] T003 [P] Add APICallMetrics dataclass to src/models.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Configuration and validation that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Add config fields to Config dataclass in src/config.py (max_prs_total, max_retries, rate_limit_wait_threshold, retry_backoff_base, use_graphql_batch)
- [X] T005 Implement config validation in src/config.py load_config() function (range checks for all new fields)
- [X] T006 Add team size validation (max 15 members) in src/config.py load_team_members() function
- [X] T007 Add APICallMetrics initialization to GitHubClient.__init__() in src/github_client.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Rate Limit Detection & Graceful Degradation (Priority: P1) 🎯 MVP

**Goal**: Detect GitHub API rate limits and either auto-wait (<5min reset) or fail fast (>5min reset) with clear messaging, preventing the app from getting stuck

**Independent Test**: Artificially reduce rate limit quota (via test token or mocked gh CLI responses) and verify the app detects limits, displays clear messages, and completes gracefully (waits if <5min, exits with error if >5min) without hanging

### Tests for User Story 1 (MANDATORY - TDD cycle) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T008 [P] [US1] Unit test for RateLimitStatus state transitions (normal → low → exhausted) in tests/unit/test_rate_limit.py
- [X] T009 [P] [US1] Unit test for config validation (range boundaries) in tests/unit/test_config.py
- [X] T010 [P] [US1] Integration test for rate limit detection with mocked gh CLI in tests/integration/test_rate_limit_detection.py
- [X] T011 [P] [US1] Integration test for auto-wait scenario (reset < threshold) in tests/integration/test_rate_limit_detection.py
- [X] T012 [P] [US1] Integration test for fail-fast scenario (reset > threshold) in tests/integration/test_rate_limit_detection.py
- [X] T013 [P] [US1] Integration test for inconsistent rate limit data handling in tests/integration/test_rate_limit_detection.py

### Implementation for User Story 1

- [X] T014 [US1] Implement check_rate_limit() method in src/github_client.py (calls gh api rate_limit, returns RateLimitStatus)
- [X] T015 [US1] Implement _should_proceed() decision logic in src/github_client.py (uses rate_limit_wait_threshold config)
- [X] T016 [US1] Implement _wait_for_reset() countdown logic in src/github_client.py (displays countdown, waits until reset)
- [X] T017 [US1] Add rate limit check before PR fetching in src/app.py main() function
- [X] T018 [US1] Add error handling for distant reset times (>1 hour) in src/github_client.py
- [X] T019 [US1] Add partial results handling for dry-run mode in src/app.py
- [X] T020 [US1] Add rate limit warning display (remaining < 100) in src/app.py

**Checkpoint**: At this point, User Story 1 should be fully functional - app detects rate limits and handles them gracefully

---

## Phase 4: User Story 2 - Smart Retry with Exponential Backoff (Priority: P2)

**Goal**: Automatically retry rate limit errors (HTTP 429) with exponential backoff (1s, 2s, 4s), distinguishing from network errors which fail immediately

**Independent Test**: Simulate HTTP 429 responses and verify system retries with correct intervals (1s, 2s, 4s), eventually succeeding or failing with clear messages. Verify network errors cause immediate failure without retry

### Tests for User Story 2 (MANDATORY - TDD cycle) ⚠️

- [X] T021 [P] [US2] Integration test for exponential backoff retry logic in tests/integration/test_retry_logic.py
- [X] T022 [P] [US2] Integration test for Retry-After header handling in tests/integration/test_retry_logic.py
- [X] T023 [P] [US2] Integration test for max retries exhaustion in tests/integration/test_retry_logic.py
- [X] T024 [P] [US2] Integration test for network error fail-fast behavior in tests/integration/test_retry_logic.py
- [X] T025 [P] [US2] Integration test for error classification (rate limit vs network vs other) in tests/integration/test_retry_logic.py

### Implementation for User Story 2

- [X] T026 [US2] Implement _classify_error() method in src/github_client.py (distinguishes HTTP 429, network errors, other errors)
- [X] T027 [US2] Implement _calculate_backoff() method in src/github_client.py (exponential backoff formula with configurable base)
- [X] T028 [US2] Implement _parse_retry_after() method in src/github_client.py (extracts Retry-After from stderr)
- [X] T029 [US2] Implement _retry_with_backoff() wrapper in src/github_client.py (wraps gh CLI calls, handles retries)
- [X] T030 [US2] Update all gh CLI subprocess calls in fetch_team_prs() to use retry wrapper in src/github_client.py
- [X] T031 [US2] Add retry attempt tracking to APICallMetrics in src/github_client.py
- [X] T032 [US2] Add detailed retry logging (attempt number, wait time) in src/github_client.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - rate limit detection + automatic retry for transient errors

---

## Phase 5: User Story 3 - API Call Optimization via Deduplication (Priority: P3)

**Goal**: Minimize API quota usage by eliminating redundant PR fetches through in-memory deduplication and GraphQL batch fetching, reducing API calls by 30%+

**Independent Test**: Run with team members who share common PRs and verify: (1) each unique PR fetched once, (2) in-memory tracking prevents redundant fetches, (3) overall API usage decreases by 30-50% (compare metrics output with/without optimization)

### Tests for User Story 3 (MANDATORY - TDD cycle) ⚠️

- [X] T033 [P] [US3] Integration test for PR deduplication (same PR, multiple members) in tests/integration/test_graphql_batch.py
- [X] T034 [P] [US3] Integration test for GraphQL batch query construction in tests/integration/test_graphql_batch.py
- [X] T035 [P] [US3] Integration test for GraphQL batch fetching (grouped by repo) in tests/integration/test_graphql_batch.py
- [X] T036 [P] [US3] Integration test for GraphQL feature flag fallback in tests/integration/test_graphql_batch.py
- [X] T037 [P] [US3] Unit test for API metrics calculation (optimization_rate, success_rate) in tests/unit/test_api_metrics.py
- [X] T038 [P] [US3] Unit test for SlackClient PR allocation logic (priority-based) in tests/unit/test_slack_client.py

### Implementation for User Story 3

- [X] T039 [P] [US3] Add PR deduplication tracking (in-memory dict) to GitHubClient.__init__() in src/github_client.py
- [X] T040 [P] [US3] Modify SlackClient to accept max_prs_total in constructor in src/slack_client.py
- [X] T041 [US3] Implement _allocate_pr_display() priority-based allocation in src/slack_client.py
- [X] T042 [US3] Update truncation logic to use total limit in src/slack_client.py
- [X] T043 [US3] Implement _group_prs_by_repo() helper in src/github_client.py
- [X] T044 [US3] Implement _build_graphql_batch_query() method in src/github_client.py
- [X] T045 [US3] Implement _fetch_pr_details_batch_graphql() method in src/github_client.py
- [X] T046 [US3] Add deduplication check before PR fetch in fetch_team_prs() in src/github_client.py
- [X] T047 [US3] Update APICallMetrics tracking (search_calls, rest_detail_calls, graphql_calls) in src/github_client.py
- [X] T048 [US3] Add GraphQL/REST strategy selection based on use_graphql_batch flag in src/github_client.py
- [X] T049 [US3] Update app.py to pass max_prs_total to SlackClient in src/app.py
- [X] T050 [US3] Add API metrics logging at end of run in src/app.py

**Checkpoint**: All user stories should now be independently functional - rate limit detection + retry + optimization

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T051 [P] Add derived properties to RateLimitStatus (reset_time, should_wait) in src/models.py
- [X] T052 [P] Add derived metrics to APICallMetrics (total_api_points, optimization_rate, success_rate) in src/models.py
- [X] T053 [P] Update .env.example with detailed comments for all new variables
- [X] T054 [P] Verify all error messages are clear and actionable across all modules
- [X] T055 [P] Add DEBUG-level logging for troubleshooting in src/github_client.py and src/app.py
- [X] T056 Run full integration tests with real gh CLI (against test repo) to validate end-to-end flow
- [X] T057 Run quickstart.md validation (test all documented scenarios)
- [X] T058 Update CLAUDE.md via .specify/scripts/bash/update-agent-context.sh

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1 rate limit detection but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Works with US1/US2 but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- US1: Models/config → detection logic → wait logic → app integration
- US2: Error classification → backoff calculation → retry wrapper → integration
- US3: Deduplication setup → GraphQL query building → batch fetching → metrics

### Parallel Opportunities

- Phase 1 (Setup): T002 and T003 can run in parallel (different entities in same file, no conflicts)
- US1 Tests: T008-T013 can all run in parallel (different test files/functions)
- US2 Tests: T021-T025 can all run in parallel (different test files/functions)
- US3 Tests: T033-T038 can all run in parallel (different test files/functions)
- US3 Implementation: T039 and T040 can run in parallel (different files)
- Phase 6 (Polish): T051, T052, T053, T054, T055 can all run in parallel (different files or non-conflicting sections)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task T008: "Unit test for RateLimitStatus state transitions in tests/unit/test_rate_limit.py"
Task T009: "Unit test for config validation in tests/unit/test_config.py"
Task T010: "Integration test for rate limit detection in tests/integration/test_rate_limit_detection.py"
Task T011: "Integration test for auto-wait scenario in tests/integration/test_rate_limit_detection.py"
Task T012: "Integration test for fail-fast scenario in tests/integration/test_rate_limit_detection.py"
Task T013: "Integration test for inconsistent data handling in tests/integration/test_rate_limit_detection.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T007) - CRITICAL checkpoint
3. Complete Phase 3: User Story 1 (T008-T020)
4. **STOP and VALIDATE**: Test User Story 1 independently with quickstart scenarios
5. Deploy/demo if ready - app now handles rate limits gracefully

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **Deploy/Demo (MVP!)**
   - App now prevents getting stuck on rate limits
3. Add User Story 2 → Test independently → Deploy/Demo
   - App now automatically recovers from transient rate limit errors
4. Add User Story 3 → Test independently → Deploy/Demo
   - App now minimizes API usage through optimization
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers after Foundational phase completes:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (P1) - Critical path
   - Developer B: User Story 2 (P2) - Can start independently
   - Developer C: User Story 3 (P3) - Can start independently
3. Stories complete and integrate independently

---

## Task Summary

- **Total tasks**: 58
- **Phase 1 (Setup)**: 3 tasks
- **Phase 2 (Foundational)**: 4 tasks
- **Phase 3 (US1)**: 13 tasks (6 tests + 7 implementation)
- **Phase 4 (US2)**: 12 tasks (5 tests + 7 implementation)
- **Phase 5 (US3)**: 18 tasks (6 tests + 12 implementation)
- **Phase 6 (Polish)**: 8 tasks

**Parallel opportunities**: 32 tasks marked [P] can run in parallel

**MVP scope** (recommended first delivery): Phases 1-3 (20 tasks) delivers User Story 1, solving the critical "app gets stuck" problem

**Independent test criteria**:
- US1: App completes gracefully under rate limit conditions (no hanging)
- US2: App automatically recovers from HTTP 429 errors
- US3: API usage reduced by 30%+ (verify via metrics logging)

---

## Notes

- [P] tasks = different files or non-conflicting sections, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD cycle)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All tasks follow strict checkbox format: `- [ ] [ID] [P?] [Story?] Description with file path`
