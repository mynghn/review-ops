# Tasks: Too Old PRs Reporting

**Input**: Design documents from `/specs/007-old-pr-reporting/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are MANDATORY per constitution (TDD cycle). Every user story MUST have tests written BEFORE implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single project structure: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency updates

- [ ] T001 Add slack-sdk dependency to pyproject.toml (>=3.26.0)
- [ ] T002 Install dependencies using uv sync or uv add slack-sdk
- [ ] T003 [P] Update .env.example with new Slack configuration variables (SLACK_BOT_TOKEN, SLACK_CHANNEL_ID)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure changes that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: This includes breaking changes to Slack API integration. No user story work can begin until this phase is complete.

- [ ] T004 [P] Update Config model in src/models.py to add slack_bot_token and slack_channel_id fields
- [ ] T005 [P] Update Config model in src/models.py to remove deprecated slack_webhook_url field
- [ ] T006 Update config.py to validate slack_bot_token format (must start with 'xoxb-')
- [ ] T007 Update config.py to validate slack_channel_id format (must start with 'C' or 'G')
- [ ] T008 [P] Update SlackClient.__init__() in src/slack_client.py to accept bot_token and channel_id parameters
- [ ] T009 [P] Replace requests-based webhook posting with slack_sdk.WebClient in src/slack_client.py
- [ ] T010 Update post_stale_pr_summary() in src/slack_client.py to return message timestamp (ts)
- [ ] T011 Update app.py to pass bot_token and channel_id to SlackClient constructor
- [ ] T012 Update app.py to capture and store timestamp from post_stale_pr_summary()
- [ ] T013 [P] Update existing SlackClient tests in tests/unit/test_slack_client.py for new constructor signature

**Checkpoint**: Slack API migration complete - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View Recent PRs on Main Board (Priority: P1) 🎯 MVP

**Goal**: Restrict main board to show only PRs updated within configured time window (GH_SEARCH_WINDOW_SIZE)

**Independent Test**: Configure 30-day threshold, create PRs with various update dates (20 days old, 35 days old), verify only PRs updated within 30 days appear on main board

### Tests for User Story 1 (MANDATORY - TDD cycle) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T014 [P] [US1] Add unit test for PR date filtering in tests/unit/test_github_client.py (test PRs updated within threshold are included)
- [ ] T015 [P] [US1] Add unit test for PR exclusion in tests/unit/test_github_client.py (test PRs updated before threshold are excluded)

### Implementation for User Story 1

- [ ] T016 [US1] Add updated_after parameter to fetch_prs() method in src/github_client.py
- [ ] T017 [US1] Update GitHub API search query in src/github_client.py to include `updated:>=date state:open` filters (exclude closed/archived PRs per FR-001a)
- [ ] T018 [US1] Calculate cutoff date in src/app.py using GH_SEARCH_WINDOW_SIZE configuration
- [ ] T019 [US1] Pass cutoff date to fetch_prs() in src/app.py for main board PR fetching
- [ ] T020 [US1] Update existing integration tests in tests/integration/ to verify date filtering behavior

**Checkpoint**: At this point, User Story 1 should be fully functional - main board shows only recent PRs

---

## Phase 4: User Story 2 - Discover Too Old PRs via Thread Message (Priority: P2)

**Goal**: Post thread reply listing team members with old PRs, including counts and GitHub search links

**Independent Test**: Configure 30-day threshold, create old PRs for specific team members, verify thread message contains correct links and counts for each team member

### Tests for User Story 2 (MANDATORY - TDD cycle) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T021 [P] [US2] Create tests/unit/test_url_builder.py with test for basic URL generation
- [ ] T022 [P] [US2] Add test for special character encoding in tests/unit/test_url_builder.py (e.g., user@org)
- [ ] T023 [P] [US2] Add test for empty username validation in tests/unit/test_url_builder.py
- [ ] T024 [P] [US2] Add test for invalid date type validation in tests/unit/test_url_builder.py
- [ ] T025 [P] [US2] Add test for URL length validation in tests/unit/test_url_builder.py (max 2000 chars)
- [ ] T026 [P] [US2] Add test for date format variations in tests/unit/test_url_builder.py
- [ ] T027 [P] [US2] Add test for URL decoding verification in tests/unit/test_url_builder.py
- [ ] T027a [P] [US2] Add test verifying state:open filter excludes closed PRs in tests/unit/test_url_builder.py
- [ ] T028 [P] [US2] Add test for OldPRReport model validation in tests/unit/test_models.py
- [ ] T029 [P] [US2] Add test for thread message formatting (English) in tests/unit/test_slack_client.py
- [ ] T030 [P] [US2] Add test for thread message formatting (Korean) in tests/unit/test_slack_client.py
- [ ] T031 [P] [US2] Add test for post_thread_reply() method in tests/unit/test_slack_client.py
- [ ] T032 [P] [US2] Add test for old PR search with inverted date filter in tests/unit/test_github_client.py
- [ ] T033 [P] [US2] Add test for PR grouping by team member in tests/unit/test_github_client.py

### Implementation for User Story 2

#### URL Builder Module

- [ ] T034 [P] [US2] Create src/url_builder.py with build_old_pr_search_url() function
- [ ] T035 [P] [US2] Implement query string construction in src/url_builder.py (is:pr state:open review-requested:USER updated:<DATE) - ensure state:open explicitly excludes closed/archived per FR-001a
- [ ] T036 [P] [US2] Implement URL encoding using urllib.parse.quote_plus() in src/url_builder.py
- [ ] T037 [P] [US2] Add input validation for username and cutoff_date in src/url_builder.py
- [ ] T038 [P] [US2] Add logging for generated URLs in src/url_builder.py
- [ ] T038a [P] [US2] Add URL length validation in src/url_builder.py (raise ValueError if generated URL exceeds 2000 chars - will be caught by T048a)

#### Data Model

- [ ] T039 [P] [US2] Add OldPRReport dataclass to src/models.py (github_username, pr_count, github_search_url)
- [ ] T040 [P] [US2] Add validation for OldPRReport fields in src/models.py (non-empty username, positive count, valid URL)

#### GitHub Client Updates

- [ ] T041 [US2] Add fetch_old_prs() method to src/github_client.py with updated:<date filter
- [ ] T042 [US2] Implement PR grouping by team member logic in src/github_client.py
- [ ] T043 [US2] Add helper to count PRs per team member in src/github_client.py

#### Slack Client Updates

- [ ] T044 [P] [US2] Add _build_thread_message() method to src/slack_client.py for formatting old PR report
- [ ] T045 [P] [US2] Add bilingual support for thread message text in src/slack_client.py (EN/KO)
- [ ] T046 [P] [US2] Implement user mention formatting in thread message in src/slack_client.py
- [ ] T047 [US2] Add post_thread_reply() method to src/slack_client.py using chat.postMessage with thread_ts
- [ ] T048 [US2] Add error handling for thread posting in src/slack_client.py
- [ ] T048a [P] [US2] Add URL length error handling in src/slack_client.py: catch ValueError from url_builder, in dry-run mode display error to console, in production mode skip team member with warning log (per spec.md edge case)

#### Main Application Logic

- [ ] T049 [US2] Add old PR fetching logic to src/app.py (call fetch_old_prs with cutoff date)
- [ ] T050 [US2] Implement OldPRReport generation in src/app.py (create reports only for members with count > 0)
- [ ] T051 [US2] Add URL generation for each team member in src/app.py using build_old_pr_search_url()
- [ ] T052 [US2] Add conditional thread posting in src/app.py (post only if old PRs exist)
- [ ] T053 [US2] Pass parent message timestamp to post_thread_reply() in src/app.py
- [ ] T054 [US2] Add logging for old PR detection and thread posting in src/app.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - main board shows recent PRs, thread shows old PRs

---

## Phase 5: User Story 3 - Configure Age Threshold (Priority: P3)

**Goal**: Administrators can configure age threshold via GH_SEARCH_WINDOW_SIZE environment variable

**Independent Test**: Set different threshold values (15, 30, 60 days), verify main board and thread messages reflect configured threshold

### Tests for User Story 3 (MANDATORY - TDD cycle) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T055 [P] [US3] Add test for GH_SEARCH_WINDOW_SIZE configuration validation in tests/unit/test_config.py
- [ ] T056 [P] [US3] Add test for default behavior when threshold not configured in tests/unit/test_config.py
- [ ] T057 [P] [US3] Add test for invalid threshold values in tests/unit/test_config.py (negative, zero, non-numeric)

### Implementation for User Story 3

- [ ] T058 [US3] Verify GH_SEARCH_WINDOW_SIZE is properly loaded in src/config.py (should already exist)
- [ ] T059 [US3] Add validation for GH_SEARCH_WINDOW_SIZE in src/config.py (must be positive integer)
- [ ] T060 [US3] Set default value for GH_SEARCH_WINDOW_SIZE in src/config.py (30 days) if not configured
- [ ] T061 [US3] Update configuration documentation comments in src/config.py to clarify usage for old PR filtering
- [ ] T062 [US3] Add backward compatibility check in src/app.py (skip old PR logic if threshold not configured)

**Checkpoint**: All user stories should now be independently functional with configurable threshold

---

## Phase 6: Integration & Polish

**Purpose**: End-to-end testing and cross-cutting improvements

### Integration Tests

- [ ] T063 [P] Create tests/integration/test_old_pr_workflow.py for end-to-end thread posting
- [ ] T064 [US2] Add integration test: fetch old PRs → generate URLs → post thread in tests/integration/test_old_pr_workflow.py
- [ ] T065 [US2] Add integration test: no old PRs → no thread posted in tests/integration/test_old_pr_workflow.py
- [ ] T066 [US2] Add integration test: verify thread appears under parent message in tests/integration/test_old_pr_workflow.py
- [ ] T066a [US2] Add performance test: verify thread posted within 5 seconds of main board message in tests/integration/test_old_pr_workflow.py

### Documentation (DEFERRED - Post-Implementation)

**Note**: These tasks are deferred to reduce critical path to 3-5 days per constitution. Complete after feature validation in production.

- [ ] T067 [P] [DEFERRED] Update README.md with Slack API migration instructions
- [ ] T068 [P] [DEFERRED] Create migration guide from webhooks to chat.postMessage in docs/ or README.md
- [ ] T069 [P] [DEFERRED] Update README.md with old PR reporting feature documentation
- [ ] T070 [P] [DEFERRED] Document required Slack permissions (chat:write) in README.md
- [ ] T071 [P] [DEFERRED] Add troubleshooting section for common Slack API errors in README.md

### Validation & Cleanup

- [ ] T072 Run all unit tests and verify 100% pass
- [ ] T073 Run all integration tests and verify 100% pass
- [ ] T074 Run linting (uvx ruff check .) and fix any issues
- [ ] T075 Run quickstart.md validation (manual test following guide)
- [ ] T076 Test dry-run mode with new functionality (uv run python src/app.py --dry-run)
- [ ] T077 Test production posting with real Slack workspace
- [ ] T078 [P] Code cleanup and refactoring if needed
- [ ] T079 [P] Performance check: verify completes within 60 seconds for 15 members/100 PRs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories (Slack API migration is breaking change)
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 (P1) can proceed first (MVP priority)
  - US2 (P2) can start after US1 or in parallel if staffed
  - US3 (P3) is mostly validation, can proceed independently
- **Integration & Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Logically builds on US1 but technically independent (tests old PR filtering separately)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Configuration is used by both US1 and US2, but validation can be tested independently

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services/utilities
- Utilities (url_builder) before main application logic
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**: All 3 tasks marked [P] can run in parallel

**Phase 2 (Foundational)**: Tasks within logical groups can run in parallel:
- T004, T005 (Config model updates)
- T008, T009 (SlackClient updates)
- T006, T007 (Config validation)
- T013 (Tests, independent)

**Phase 3 (US1)**:
- T014, T015 (Tests can run together)
- T016, T017 (GitHub client changes)
- T020 (Test updates, after implementation)

**Phase 4 (US2)**: Many parallel opportunities:
- T021-T033 (All tests can run in parallel)
- T034-T038 (URL builder module tasks)
- T039-T040 (Model updates)
- T044-T046 (Slack client formatting methods)

**Phase 6 (Integration & Polish)**:
- T063-T066 (Integration tests)
- T067-T071 (Documentation tasks)
- T078, T079 (Cleanup and performance)

---

## Parallel Example: User Story 2 Tests

```bash
# Launch all tests for User Story 2 together (13 tests):
Task T021: "test for basic URL generation"
Task T022: "test for special character encoding"
Task T023: "test for empty username validation"
Task T024: "test for invalid date type validation"
Task T025: "test for URL length validation"
Task T026: "test for date format variations"
Task T027: "test for URL decoding verification"
Task T028: "test for OldPRReport model validation"
Task T029: "test for thread message formatting (English)"
Task T030: "test for thread message formatting (Korean)"
Task T031: "test for post_thread_reply() method"
Task T032: "test for old PR search with inverted date filter"
Task T033: "test for PR grouping by team member"

# Launch all URL builder implementation together (5 tasks):
Task T034: "Create src/url_builder.py"
Task T035: "Implement query string construction"
Task T036: "Implement URL encoding"
Task T037: "Add input validation"
Task T038: "Add logging"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (install dependencies)
2. Complete Phase 2: Foundational (Slack API migration - CRITICAL)
3. Complete Phase 3: User Story 1 (main board filtering)
4. **STOP and VALIDATE**: Test that main board shows only recent PRs
5. Deploy/demo if ready (basic functionality working)

### Incremental Delivery

1. Complete Setup + Foundational → Slack API migrated, foundation ready
2. Add User Story 1 → Test independently → Deploy (MVP: main board filtering works!)
3. Add User Story 2 → Test independently → Deploy (Full feature: thread with old PR links!)
4. Add User Story 3 → Test independently → Deploy (Configuration validation complete)
5. Complete Integration & Polish → Full production ready
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. **Team completes Setup + Foundational together** (breaking changes require coordination)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (main board filtering)
   - **Developer B**: User Story 2 (thread posting with old PRs)
   - **Developer C**: User Story 3 (configuration validation) + start on Phase 6 documentation
3. Stories complete and integrate independently
4. Team reviews integration tests together

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **Breaking change alert**: Phase 2 includes Slack API migration (webhook → chat.postMessage)
- Existing users must update .env configuration (SLACK_WEBHOOK_URL → SLACK_BOT_TOKEN + SLACK_CHANNEL_ID)
- Verify tests fail before implementing (TDD cycle)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Total tasks: 79 (including tests, implementation, integration, documentation)
- Estimated time: 3-5 days (per plan.md post-design evaluation)
