# Tasks: Enhanced Stale PR Board UI with Korean Language Support

**Input**: Design documents from `/specs/002-ui-enhance-on-stale-pr-board/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: MANDATORY per constitution (TDD cycle). Tests written BEFORE implementation for each user story.

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

**Status**: ✅ Project already initialized with Python 3.12, pytest, requests

- [x] T001 Project structure exists with src/ and tests/ directories
- [x] T002 Python 3.12 with pytest and requests dependencies installed

**Checkpoint**: Setup complete - proceeding to foundational phase

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Add LANGUAGE environment variable to src/config.py (values: 'en' or 'ko', default: 'en')
- [ ] T004 Add SUPPORTED_LANGUAGES constant and validation logic in src/config.py
- [ ] T005 [P] Write config validation test for valid language codes in tests/test_config.py
- [ ] T006 [P] Write config validation test for invalid language codes in tests/test_config.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Visual Enhancement with Block Kit (Priority: P1) 🎯 MVP

**Goal**: Transform plain text stale PR reports into visually engaging Slack messages using Block Kit components (header, section, divider, context blocks) with structured hierarchy and scannable layout.

**Independent Test**: Configure system to send Block Kit formatted messages and verify recipients see properly formatted sections, dividers, emphasis, and styling. Delivers immediate value through improved readability.

### Tests for User Story 1 (MANDATORY - TDD cycle) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

#### Unit Tests - SlackClient Constructor

- [ ] T007 [P] [US1] Write test for SlackClient initialization with language parameter in tests/unit/test_slack_client.py
- [ ] T008 [P] [US1] Write test for SlackClient default language ('en') in tests/unit/test_slack_client.py

#### Unit Tests - Helper Methods

- [ ] T009 [P] [US1] Write test for _escape_mrkdwn with special characters (&, <, >) in tests/unit/test_slack_client.py
- [ ] T010 [P] [US1] Write test for _escape_mrkdwn with Korean characters (UTF-8) in tests/unit/test_slack_client.py

#### Unit Tests - Block Builders (English)

- [ ] T011 [P] [US1] Write test for _build_header_block('rotten') in English in tests/unit/test_slack_client.py
- [ ] T012 [P] [US1] Write test for _build_header_block('aging') in English in tests/unit/test_slack_client.py
- [ ] T013 [P] [US1] Write test for _build_header_block('fresh') in English in tests/unit/test_slack_client.py

#### Unit Tests - Block Builders (Korean)

- [ ] T014 [P] [US1] Write test for _build_header_block('rotten') in Korean in tests/unit/test_slack_client.py
- [ ] T015 [P] [US1] Write test for _build_header_block('aging') in Korean in tests/unit/test_slack_client.py
- [ ] T016 [P] [US1] Write test for _build_header_block('fresh') in Korean in tests/unit/test_slack_client.py

#### Unit Tests - PR Section Builder

- [ ] T017 [P] [US1] Write test for _build_pr_section with English strings in tests/unit/test_slack_client.py
- [ ] T018 [P] [US1] Write test for _build_pr_section with Korean strings in tests/unit/test_slack_client.py
- [ ] T019 [P] [US1] Write test for _build_pr_section with special characters in PR title in tests/unit/test_slack_client.py
- [ ] T019a [P] [US1] Write test for _build_pr_section with Slack user ID mentions format (@U123ABC) from team_members.json in tests/unit/test_slack_client.py

#### Unit Tests - Truncation Warning

- [ ] T020 [P] [US1] Write test for _build_truncation_warning in English in tests/unit/test_slack_client.py
- [ ] T021 [P] [US1] Write test for _build_truncation_warning in Korean in tests/unit/test_slack_client.py

#### Unit Tests - Category Blocks

- [ ] T022 [P] [US1] Write test for _build_category_blocks with empty PR list in tests/unit/test_slack_client.py
- [ ] T023 [P] [US1] Write test for _build_category_blocks with <15 PRs (no truncation) in tests/unit/test_slack_client.py
- [ ] T024 [P] [US1] Write test for _build_category_blocks with >15 PRs (with truncation) in tests/unit/test_slack_client.py
- [ ] T025 [P] [US1] Write test for _build_category_blocks with exactly 15 PRs in tests/unit/test_slack_client.py

#### Unit Tests - Full Blocks Assembly

- [ ] T026 [P] [US1] Write test for _build_blocks with all three categories populated in tests/unit/test_slack_client.py
- [ ] T027 [P] [US1] Write test for _build_blocks with mixed empty and populated categories in tests/unit/test_slack_client.py
- [ ] T028 [P] [US1] Write test for _build_blocks verifying dividers only between categories in tests/unit/test_slack_client.py
- [ ] T029 [P] [US1] Write test for _build_blocks verifying block count stays under 50 in tests/unit/test_slack_client.py

#### Integration Tests

- [ ] T030 [P] [US1] Write integration test for post_stale_pr_summary with mocked webhook success in tests/integration/test_slack_integration.py
- [ ] T031 [P] [US1] Write integration test for post_stale_pr_summary with mocked webhook failure in tests/integration/test_slack_integration.py
- [x] T031a [P] [US1] Write integration test verifying webhook URL, request headers, and POST method remain unchanged from current implementation in tests/integration/test_slack_integration.py
- [ ] T032 [P] [US1] Write integration test for full message assembly validating Block Kit JSON structure in tests/integration/test_slack_integration.py

### Implementation for User Story 1

> **IMPORTANT: Run tests after each implementation step to verify TDD cycle**

#### Core Infrastructure

- [ ] T033 [US1] Update SlackClient.__init__ to accept language parameter (default='en') in src/slack_client.py
- [ ] T034 [US1] Add MAX_PRS_TOTAL constant (value: 45) to SlackClient class in src/slack_client.py

#### Helper Methods

- [ ] T035 [US1] Implement _escape_mrkdwn(text) method to escape &, <, > characters in src/slack_client.py

#### Block Builder Methods

- [ ] T036 [US1] Implement _build_header_block(category) with language-aware headers in src/slack_client.py
- [ ] T037 [US1] Implement _build_pr_section(pr) with language-aware age and review strings, maintaining existing @mention functionality for Slack user IDs in src/slack_client.py
- [ ] T038 [US1] Implement _build_truncation_warning(count) with language-aware warning message in src/slack_client.py

#### Category and Full Message Assembly

- [ ] T039 [US1] Implement _build_category_blocks(category, prs) respecting total PR limit across all categories in src/slack_client.py
- [ ] T040 [US1] Implement _build_blocks(categorized_prs) to assemble all category blocks with dividers in src/slack_client.py
- [x] T040a [US1] Implement empty state handling in _build_blocks() that returns engaging "all clear" Block Kit message (header + section with positive emoji) when all categories are empty in src/slack_client.py

#### Public API

- [ ] T041 [US1] Implement post_stale_pr_summary(categorized_prs) public method with webhook POST in src/slack_client.py
- [ ] T042 [US1] Add error handling and logging for webhook failures in post_stale_pr_summary in src/slack_client.py

#### Application Integration

- [ ] T043 [US1] Update app.py to import LANGUAGE from config
- [ ] T044 [US1] Update SlackClient initialization in app.py to pass language parameter
- [ ] T045 [US1] Replace plain text message posting with post_stale_pr_summary call in app.py

**Checkpoint**: User Story 1 complete - Block Kit messages should now be sent to Slack with visual formatting

---

## Phase 4: User Story 2 - Korean Language Support (Priority: P2)

**Goal**: Korean-speaking team members receive stale PR reports in Korean with witty, engaging expressions that make notifications more culturally relevant and attention-grabbing.

**Independent Test**: Configure language preference to Korean and verify all message text appears in Korean with appropriate witty expressions and tone. Delivers value through improved comprehension for Korean speakers.

**Note**: Primary implementation already completed in User Story 1 (inline conditionals in builder methods). This phase focuses on validation and verification.

### Tests for User Story 2 (MANDATORY - TDD cycle) ⚠️

- [ ] T046 [P] [US2] Write test verifying Korean category headers use correct expressions ("부패 중", "숙성 중", "갓 태어난") in tests/unit/test_slack_client.py
- [ ] T047 [P] [US2] Write test verifying Korean age format uses Arabic numerals with "일 묵음" in tests/unit/test_slack_client.py
- [ ] T048 [P] [US2] Write test verifying Korean review count format uses "리뷰 X개 대기중" in tests/unit/test_slack_client.py
- [ ] T049 [P] [US2] Write test verifying Korean truncation warning uses "개 더 있음" format in tests/unit/test_slack_client.py
- [x] T050 [P] [US2] Write test verifying UTF-8 encoding preserves Korean characters without corruption in tests/unit/test_slack_client.py
- [x] T051 [P] [US2] Write integration test for full Korean message with mixed Korean and English content in tests/integration/test_slack_integration.py

### Implementation for User Story 2

> **NOTE: Most implementation already in US1. These are verification tasks.**

- [ ] T052 [US2] Verify all 7 string pairs are correctly implemented with inline conditionals in src/slack_client.py
- [ ] T053 [US2] Run pytest suite to verify all Korean tests pass
- [ ] T054 [US2] Manual verification: Send test message to Slack in Korean (LANGUAGE=ko)
- [ ] T055 [US2] Manual verification: Check Korean text renders correctly on desktop Slack client
- [ ] T056 [US2] Manual verification: Check Korean text renders correctly on mobile Slack client

**Checkpoint**: User Story 2 complete - Korean messages should display with proper witty expressions and correct encoding

---

## Phase 5: User Story 3 - Language Configuration (Priority: P3)

**Goal**: Teams can configure their preferred language (English or Korean) for stale PR reports, with English remaining the default to maintain backward compatibility.

**Independent Test**: Set language configuration to different values and verify system sends reports in correct language. Delivers value through flexibility and user choice.

### Tests for User Story 3 (MANDATORY - TDD cycle) ⚠️

- [ ] T057 [P] [US3] Write test verifying LANGUAGE defaults to 'en' when not set in tests/test_config.py
- [ ] T058 [P] [US3] Write test verifying LANGUAGE=ko is accepted in tests/test_config.py
- [ ] T059 [P] [US3] Write test verifying LANGUAGE=en is accepted in tests/test_config.py
- [ ] T060 [P] [US3] Write test verifying invalid LANGUAGE raises ValueError in tests/test_config.py

### Implementation for User Story 3

- [x] T061 [US3] Add LANGUAGE configuration documentation to .env.example
- [x] T062 [US3] Document language configuration in README.md with examples
- [ ] T063 [US3] Test LANGUAGE environment variable switching between en and ko
- [ ] T064 [US3] Verify invalid language codes log warning and default to English

**Checkpoint**: User Story 3 complete - Language configuration should be fully documented and tested

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories, final validation, and documentation

- [ ] T065 [P] Run full pytest suite and verify 100% of tests pass
- [ ] T066 [P] Run ruff check to verify no linting errors in src/
- [ ] T067 [P] Verify test coverage meets requirements for all new methods in src/slack_client.py
- [ ] T068 Manual verification: Test with 0 PRs (empty state) to ensure graceful handling
- [ ] T069 Manual verification: Test with exactly 45 PRs total distributed across categories (edge case)
- [ ] T070 Manual verification: Test with >50 PRs total (truncation across all categories)
- [ ] T071 Manual verification: Test with PR titles containing special characters (&, <, >, *, _)
- [ ] T072 Manual verification: Verify clickable links work correctly in Slack
- [ ] T073 Manual verification: Verify emoji rendering (🤢, 🧀, ✨) on desktop and mobile
- [ ] T074 Review code for any unnecessary complexity or violations of "Simplicity First" principle
- [ ] T075 Final documentation pass: ensure CLAUDE.md is updated (via agent context script)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: ✅ Already complete
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories CAN proceed in parallel after Phase 2 (if staffed)
  - Or sequentially in priority order: P1 → P2 → P3
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Implementation already in US1 - just verification tasks - No blocking dependencies
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - No dependencies on other stories

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD cycle)
- Unit tests for builders before integration tests
- Builder helpers before builder methods
- Individual builders before category assembly
- Category assembly before full message assembly
- Implementation before manual verification

### Parallel Opportunities

**Phase 2 - Foundational**:
- T005 and T006 can run in parallel (different test cases)

**Phase 3 - User Story 1 Tests**:
- All unit tests (T007-T029) can run in parallel after test fixtures created
- All integration tests (T030-T032) can run in parallel

**Phase 3 - User Story 1 Implementation**:
- T036, T037, T038 can run in parallel (different builder methods)

**Phase 4 - User Story 2 Tests**:
- All tests (T046-T051) can run in parallel

**Phase 5 - User Story 3 Tests**:
- All tests (T057-T060) can run in parallel

**Phase 6 - Polish**:
- T065, T066, T067 can run in parallel (different validation tools)

---

## Parallel Example: User Story 1 - Block Builder Tests

```bash
# Launch all header block tests together:
Task: "Write test for _build_header_block('rotten') in English"
Task: "Write test for _build_header_block('aging') in English"
Task: "Write test for _build_header_block('fresh') in English"
Task: "Write test for _build_header_block('rotten') in Korean"
Task: "Write test for _build_header_block('aging') in Korean"
Task: "Write test for _build_header_block('fresh') in Korean"

# Launch all builder method implementations together:
Task: "Implement _build_header_block(category)"
Task: "Implement _build_pr_section(pr)"
Task: "Implement _build_truncation_warning(count)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup ✅
2. Complete Phase 2: Foundational (T003-T006)
3. Complete Phase 3: User Story 1 (T007-T045)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

**MVP Delivers**: Block Kit formatted messages in English with visual hierarchy

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → **Deploy/Demo (MVP!)**
3. Add User Story 2 → Test independently → **Deploy/Demo (adds Korean support)**
4. Add User Story 3 → Test independently → **Deploy/Demo (adds config flexibility)**
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T003-T006)
2. Once Foundational is done:
   - Developer A: User Story 1 (T007-T045) - This is the main work
   - Developer B: User Story 3 (T057-T064) - Can work in parallel on config docs
3. User Story 2 (T046-T056) completes after US1 (verification only)

---

## Notes

- [P] tasks = different files/tests, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing (TDD cycle)
- Commit after each logical group of tasks
- Stop at any checkpoint to validate story independently
- Total string pairs: 7 (category headers: 3, age: 1, review count: 1, truncation: 1, empty state: 1)
- Block Kit components: header (category titles), section (PR details), context (truncation warning), divider (visual separation)
- Truncation limit: 45 PRs total across all categories (not per-category limit)
- Target message generation time: ≤200ms increase over plain text

---

## Success Criteria Mapping

- **SC-001** (Category identification <2 seconds): Achieved via header blocks + dividers (Phase 3)
- **SC-002** (Renders on desktop/mobile): Guaranteed by Block Kit (Phase 3)
- **SC-003** (Korean comprehension): Validated via Korean strings + UAT (Phase 4)
- **SC-004** (Generation time ≤200ms): Monitored during testing (Phase 6)
- **SC-005** (Zero Slack API errors): Verified via error handling tests (Phase 3)
- **SC-006** (100% information preservation): Validated via context blocks (Phase 3)
- **SC-007** (Immediate action identification): Achieved via section + context structure (Phase 3)
- **SC-008** (50+ PRs handled gracefully): Tested via truncation logic (Phase 3 & 6)

---

## Estimated Timeline

| Phase | Task Range | Estimated Time | Cumulative |
|-------|------------|----------------|------------|
| Setup (Phase 1) | T001-T002 | ✅ Complete | 0:00 |
| Foundational (Phase 2) | T003-T006 | 20 min | 0:20 |
| User Story 1 Tests (Phase 3) | T007-T032 | 60 min | 1:20 |
| User Story 1 Implementation (Phase 3) | T033-T045 | 90 min | 2:50 |
| User Story 2 (Phase 4) | T046-T056 | 30 min | 3:20 |
| User Story 3 (Phase 5) | T057-T064 | 20 min | 3:40 |
| Polish (Phase 6) | T065-T075 | 30 min | 4:10 |
| **Total** | **T001-T075** | **~4 hours** | |

**Note**: Quickstart.md estimates 3-5 hours. This task breakdown aligns with that estimate.
