# Tasks: Table View UI for Stale PR Board

**Input**: Design documents from `/specs/004-table-view-ui/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are MANDATORY per constitution (TDD cycle). Every user story has tests written BEFORE implementation following the TDD approach outlined in quickstart.md.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. User Stories 1 and 2 are implemented together in Phase 3 because bilingual support is naturally integrated into the table implementation from the start.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project structure:
- `src/` - Source code at repository root
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests

---

## Phase 1: Setup

**Purpose**: Environment setup and code review

- [X] T001 Create unit test file tests/unit/test_slack_table_view.py
- [X] T002 Review existing SlackClient implementation in src/slack_client.py:242-290 to understand current build_blocks() method

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Helper methods that support all user stories. These methods are language-aware from the start.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Implement _get_staleness_emoji() helper method in src/slack_client.py to map category names to Slack emoji names
- [X] T004 [P] Implement _build_rich_text_cell() helper method in src/slack_client.py to wrap elements in rich_text cell structure
- [X] T005 [P] Implement _build_reviewer_elements() helper method in src/slack_client.py to build reviewer mentions with newline separators

**Checkpoint**: Foundation ready - user story implementation can now begin ✓

---

## Phase 3: User Stories 1 & 2 - Unified Table View with Bilingual Support (Priority: P1, P2) 🎯 MVP

**Goal**: Deliver a working table view that displays all PRs in a single sorted table with 4 columns (staleness emoji, elapsed time, PR details, reviewers) supporting both English and Korean languages.

**Independent Test**:
- **US1**: Send a stale PR notification and verify all PRs appear in a single table sorted by age (oldest first), with correct emojis, elapsed time formatting, PR links, and reviewer mentions
- **US2**: Test with LANGUAGE=ko and LANGUAGE=en environment variables and verify table headers change accordingly

**Note**: User Stories 1 and 2 are implemented together because bilingual support is baked into every method from the start per the TDD approach in quickstart.md.

### Tests for Header Row (MANDATORY - TDD cycle) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [P] [US1][US2] Write test_table_header_row_english test in tests/unit/test_slack_table_view.py to verify English column labels
- [X] T007 [P] [US1][US2] Write test_table_header_row_korean test in tests/unit/test_slack_table_view.py to verify Korean column labels

### Implementation for Header Row

- [X] T008 [US1][US2] Implement _build_table_header_row() method in src/slack_client.py with bilingual support and verify tests pass

### Tests for Data Row (MANDATORY - TDD cycle) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T009 [P] [US1] Write test_table_data_row_structure test in tests/unit/test_slack_table_view.py to verify all 4 columns have correct cell structure
- [X] T010 [P] [US1] Write test_table_no_reviewers test in tests/unit/test_slack_table_view.py to verify dash display when PR has no reviewers

### Implementation for Data Row

- [X] T011 [US1] Implement _build_table_data_row() method in src/slack_client.py using helper methods and verify tests pass

### Tests for Main build_blocks() Method (MANDATORY - TDD cycle) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T012 [P] [US1][US2] Write test_build_blocks_table_format integration test in tests/unit/test_slack_table_view.py to verify table format and sorting (implemented via direct testing)
- [X] T013 [P] [US1][US2] Write test_empty_state_rendering test in tests/unit/test_slack_table_view.py to verify empty state message (implemented via direct testing)

### Implementation for Main build_blocks() Method

- [X] T014 [US1][US2] Replace build_blocks() method in src/slack_client.py with new table format implementation (flatten categories, sort by staleness descending, build table rows)
- [X] T015 [P] [US1][US2] Implement _build_board_header_block() method in src/slack_client.py for bilingual board title
- [X] T016 [P] [US1][US2] Implement _build_empty_state_blocks() method in src/slack_client.py for bilingual celebration message
- [X] T017 [US1][US2] Run all Phase 3 tests and verify they pass

**Checkpoint**: At this point, User Stories 1 and 2 should be fully functional and testable independently. The table view works with bilingual support. ✓

---

## Phase 4: User Story 3 - Maintain Truncation Behavior (Priority: P3)

**Goal**: Preserve existing truncation functionality to prevent overwhelming users with large tables. Display only the stalest N PRs (default 30, max 99) and show a warning message indicating how many PRs were hidden.

**Independent Test**: Configure max_prs_total to a low value (e.g., 5), run the application, and verify only the 5 stalest PRs appear in the table with a warning message below.

### Tests for Truncation (MANDATORY - TDD cycle) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T018 [P] [US3] Write test_table_truncation test in tests/unit/test_slack_table_view.py to verify only max_prs_total PRs are displayed
- [ ] T019 [P] [US3] Write test_truncation_warning_bilingual test in tests/unit/test_slack_table_view.py to verify warning appears in both languages

### Implementation for Truncation

- [ ] T020 [US3] Add truncation logic to build_blocks() method in src/slack_client.py (cap at min(max_prs_total, 99) and calculate truncated count)
- [ ] T021 [US3] Implement _build_truncation_warning() method in src/slack_client.py with bilingual warning messages
- [ ] T022 [US3] Run truncation tests and verify they pass

**Checkpoint**: All user stories should now be independently functional. The table view supports truncation with bilingual warnings.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Integration testing, manual validation, and documentation updates

- [ ] T023 Update existing tests in tests/ to expect table format instead of category-based section format
- [ ] T024 Run full test suite with pytest tests/ and ensure all tests pass with code coverage ≥73%
- [ ] T025 Perform manual testing with uv run python src/app.py --dry-run and verify output matches contract examples in specs/004-table-view-ui/contracts/
- [ ] T026 Test bilingual support by running with LANGUAGE=ko environment variable and verifying Korean headers and messages
- [ ] T027 Perform manual testing by sending to real Slack webhook and verifying rendering on desktop and mobile clients
- [ ] T028 Update CLAUDE.md with table format implementation details and remove category-based formatting references

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories 1 & 2 (Phase 3)**: Depends on Foundational phase completion - implements MVP
  - US1 and US2 are tightly coupled and implemented together
  - Bilingual support is integrated from the start, not added as a separate phase
- **User Story 3 (Phase 4)**: Depends on Phase 3 completion - adds truncation to existing table
- **Polish (Phase 5)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Implemented alongside US1 - Bilingual support is integrated into all helper methods from the start
- **User Story 3 (P3)**: Can start after Phase 3 - Adds truncation logic to existing build_blocks() method

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD cycle per quickstart.md)
- Helper methods before main methods
- Header row implementation before data row implementation
- Data row implementation before build_blocks() replacement
- Core implementation before edge case handling

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T003, T004, T005: All helper methods can be implemented in parallel (different independent methods in same file)

**Phase 3.1 (Header Row Tests)**:
- T006, T007: Both test functions can be written in parallel

**Phase 3.3 (Data Row Tests)**:
- T009, T010: Both test functions can be written in parallel

**Phase 3.5 (build_blocks Tests)**:
- T012, T013: Both integration tests can be written in parallel

**Phase 3.6 (build_blocks Implementation)**:
- T015, T016: Both helper methods can be implemented in parallel (after T014 is complete)

**Phase 4 (Truncation Tests)**:
- T018, T019: Both truncation tests can be written in parallel

---

## Parallel Example: User Story 1 & 2 (Phase 3)

```bash
# Launch header row tests together:
Task T006: "Write test_table_header_row_english test in tests/unit/test_slack_table_view.py"
Task T007: "Write test_table_header_row_korean test in tests/unit/test_slack_table_view.py"

# Then implement header row sequentially:
Task T008: "Implement _build_table_header_row() method in src/slack_client.py"

# Launch data row tests together:
Task T009: "Write test_table_data_row_structure test in tests/unit/test_slack_table_view.py"
Task T010: "Write test_table_no_reviewers test in tests/unit/test_slack_table_view.py"

# Then implement data row sequentially:
Task T011: "Implement _build_table_data_row() method in src/slack_client.py"

# Launch integration tests together:
Task T012: "Write test_build_blocks_table_format integration test"
Task T013: "Write test_empty_state_rendering test"

# Implement build_blocks sequentially, then parallel helper methods:
Task T014: "Replace build_blocks() method"
Task T015: "Implement _build_board_header_block() method" (parallel with T016)
Task T016: "Implement _build_empty_state_blocks() method" (parallel with T015)
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T005) - CRITICAL, blocks all stories
3. Complete Phase 3: User Stories 1 & 2 (T006-T017)
4. **STOP and VALIDATE**: Test User Stories 1 & 2 independently using acceptance scenarios from spec.md
5. Deploy/demo MVP - working table view with bilingual support

**MVP Scope**: Phases 1-3 (Tasks T001-T017)
- Delivers: Working table view with all 4 columns, bilingual support (EN/KO), sorted by staleness descending, empty state handling
- Excludes: Truncation behavior (Phase 4), final polish (Phase 5)
- Can be tested independently per US1 and US2 acceptance criteria

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Stories 1 & 2 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 3 → Test independently → Deploy/Demo (Full feature)
4. Complete Polish phase → Final validation and documentation
5. Each phase adds value without breaking previous functionality

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T005)
2. Once Foundational is done:
   - Developer A: Header row (T006-T008)
   - Developer B: Data row (T009-T011) - can start in parallel with Developer A
   - Both converge on: build_blocks() implementation (T012-T017)
3. Single developer: User Story 3 (T018-T022)
4. Team: Polish phase together (T023-T028)

---

## Notes

- [P] tasks = different files OR independent methods/functions with no dependencies
- [Story] label maps task to specific user story for traceability
- User Stories 1 and 2 are implemented together because bilingual support is naturally integrated
- Tests follow TDD cycle: write test, see it fail, implement, see it pass
- Each checkpoint allows validation of story independence
- Verify tests fail before implementing (per quickstart.md TDD approach)
- Commit after each task or logical group
- Empty state and truncation are edge cases handled within core implementation
- All translation strings support both EN and KO from the start
- Table format uses Slack Block Kit rich_text cells (not mrkdwn)
- Maximum table size: 99 data rows + 1 header row (Slack limit: 100 rows total)

---

## Test Coverage Requirements

Per constitution Principle III and existing baseline:

- Code coverage: ≥73% (existing baseline, maintain or improve)
- All user story acceptance scenarios must have corresponding tests
- TDD cycle mandatory: tests before implementation
- Test categories:
  - Unit tests: Helper methods, cell construction, row generation
  - Integration tests: Full build_blocks() output, sorting, truncation
  - Manual tests: Slack rendering (desktop + mobile), bilingual display
  - Edge cases: Empty state, no reviewers, missing Slack IDs, long titles, 100+ PRs

---

## Risk Mitigation

**Low Risk Areas** (per research.md):
- Slack Block Kit table format is well-documented and stable
- No external dependencies beyond existing `requests` library
- Change is isolated to `SlackClient.build_blocks()` method and helpers

**Mitigation Strategies**:
- Comprehensive unit tests validate table structure before Slack integration
- Dry-run mode allows testing without sending to Slack
- Contract examples in specs/004-table-view-ui/contracts/ serve as validation fixtures
- Bilingual tests ensure translation correctness for both EN and KO
- Manual testing phase (T025-T027) catches rendering issues early

---

## Success Criteria (from spec.md)

Upon completion of all phases, verify:

- **SC-001**: Users can view all PRs in a single unified table without navigating between category sections
- **SC-002**: PRs are visually ordered by urgency (stalest first), allowing users to identify critical reviews in under 3 seconds
- **SC-003**: Table layout displays consistently across Slack desktop and mobile clients with proper column alignment
- **SC-004**: Message rendering time remains under 1 second for up to 30 PRs (no performance degradation from format change)
- **SC-005**: Existing bilingual support (EN/KO) works correctly with table headers matching configured language

All acceptance scenarios from spec.md should pass for User Stories 1, 2, and 3.
