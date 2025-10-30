---
description: "Task list for Stale PR Board implementation"
---

# Tasks: Stale PR Board

**Input**: Design documents from `/specs/001-stale-pr-board/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are MANDATORY per constitution (TDD cycle). Every user story MUST have tests written BEFORE implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single project structure: `src/`, `tests/` at repository root
- Flat module structure (no packages) under src/

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project directory structure with src/, tests/unit/, tests/integration/, tests/fixtures/ directories
- [ ] T002 Create .python-version file pinning Python 3.12
- [ ] T003 Initialize Python project with uv and create pyproject.toml with project metadata
- [ ] T004 Add primary dependencies to pyproject.toml: PyGithub>=2.1, requests>=2.31, python-dotenv>=1.0
- [ ] T005 [P] Add testing dependencies to pyproject.toml: pytest>=7.4, pytest-cov, pytest-mock
- [ ] T006 [P] Configure ruff in pyproject.toml with ANN rules enabled for type hint enforcement
- [ ] T007 [P] Configure pytest in pyproject.toml with test paths and coverage settings
- [ ] T008 [P] Configure ty (type checker) in pyproject.toml
- [ ] T009 [P] Create .env.example with GITHUB_TOKEN, GITHUB_ORG, SLACK_WEBHOOK_URL, LOG_LEVEL, API_TIMEOUT
- [ ] T010 [P] Create team_members.json.example with sample team member structure (github_username, slack_user_id)
- [ ] T011 [P] Create .gitignore to exclude .env, team_members.json, __pycache__, .pytest_cache, uv.lock, venv/
- [ ] T012 Run uv sync to install all dependencies and generate uv.lock file

**Checkpoint**: Project structure is ready for implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T013 [P] Create TeamMember dataclass in src/models.py with github_username (str) and slack_user_id (str | None)
- [ ] T014 [P] Create PullRequest dataclass in src/models.py with all required fields (repo_name, number, title, author, reviewers, url, created_at, ready_at, current_approvals, required_approvals, base_branch)
- [ ] T015 [P] Add is_draft and has_sufficient_approval properties to PullRequest in src/models.py
- [ ] T016 [P] Create StalePR dataclass in src/models.py with pr (PullRequest), staleness_days (float)
- [ ] T017 [P] Add category and emoji properties to StalePR in src/models.py (fresh: 1-3 days ✨, aging: 4-7 days 🧀, rotten: 8+ days 🤢)
- [ ] T018 [P] Create Config dataclass in src/models.py with github_token, github_org, slack_webhook_url, log_level, api_timeout
- [ ] T019 Create src/config.py with load_config() function that loads from .env using python-dotenv and validates required fields
- [ ] T020 Add load_team_members() function to src/config.py that loads and validates team_members.json
- [ ] T021 [P] Create tests/fixtures/github_pr_response.json with sample PR API response (draft and non-draft examples)
- [ ] T022 [P] Create tests/fixtures/github_reviews_response.json with sample reviews (APPROVED, CHANGES_REQUESTED, COMMENTED states)
- [ ] T023 [P] Create tests/fixtures/team_members_valid.json with valid team member examples
- [ ] T024 [P] Create tests/fixtures/github_commits_response.json with sample commit timestamps
- [ ] T025 Create tests/conftest.py with shared pytest fixtures for mock config, mock team members, mock GitHub API responses

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Basic Stale PR Detection & Notification (Priority: P1) 🎯 MVP

**Goal**: A development team lead runs a command-line tool that identifies all open pull requests across their GitHub organization that involve team members and currently lack sufficient approval. The tool calculates staleness and sends a prioritized list to Slack.

**Independent Test**: Configure a team list, run the script against a GitHub organization with known PRs in various states, and verify the Slack message contains the correct PRs sorted by staleness with PRs that have sufficient approval excluded.

### Tests for User Story 1 (MANDATORY - TDD cycle) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T026 [P] [US1] Unit test in tests/unit/test_staleness.py: PR marked ready 5 days ago with no approvals should show 5 days staleness
- [ ] T027 [P] [US1] Unit test in tests/unit/test_staleness.py: PR with commit after approval should calculate staleness from commit time
- [ ] T028 [P] [US1] Unit test in tests/unit/test_staleness.py: PR with sufficient approvals should return None (not stale)
- [ ] T029 [P] [US1] Unit test in tests/unit/test_staleness.py: Draft PR should be excluded entirely (return None)
- [ ] T030 [P] [US1] Unit test in tests/unit/test_staleness.py: PR with approval but no commits after should not be stale
- [ ] T031 [P] [US1] Unit test in tests/unit/test_config.py: Valid .env file should load successfully with all required fields
- [ ] T032 [P] [US1] Unit test in tests/unit/test_config.py: Missing required environment variables should raise ValueError with clear message
- [ ] T033 [P] [US1] Unit test in tests/unit/test_config.py: Invalid webhook URL format should raise validation error
- [ ] T034 [P] [US1] Unit test in tests/unit/test_config.py: Valid team_members.json should load successfully
- [ ] T035 [P] [US1] Unit test in tests/unit/test_config.py: Invalid team_members.json (empty array) should raise validation error
- [ ] T036 [P] [US1] Unit test in tests/unit/test_models.py: StalePR.category returns "fresh" for 2 days, "aging" for 5 days, "rotten" for 10 days
- [ ] T037 [P] [US1] Unit test in tests/unit/test_models.py: StalePR.emoji returns ✨ for fresh, 🧀 for aging, 🤢 for rotten
- [ ] T038 [P] [US1] Unit test in tests/unit/test_models.py: PullRequest.is_draft returns True when ready_at is None
- [ ] T039 [P] [US1] Unit test in tests/unit/test_models.py: PullRequest.has_sufficient_approval compares current vs required correctly
- [ ] T040 [P] [US1] Integration test in tests/integration/test_github_client.py: Fetch PRs from organization with mocked API responses
- [ ] T041 [P] [US1] Integration test in tests/integration/test_github_client.py: Parse PR reviews and count approvals correctly (latest review per user wins)
- [ ] T042 [P] [US1] Integration test in tests/integration/test_github_client.py: Get branch protection or use default (1 approval) on 404
- [ ] T043 [P] [US1] Integration test in tests/integration/test_github_client.py: Skip repositories with 403/404 errors and log warning
- [ ] T044 [P] [US1] Integration test in tests/integration/test_github_client.py: Handle rate limit exceeded with proper error message
- [ ] T045 [P] [US1] Integration test in tests/integration/test_slack_client.py: Format basic stale PR message with correct structure
- [ ] T046 [P] [US1] Integration test in tests/integration/test_slack_client.py: Format celebratory message when no stale PRs found
- [ ] T047 [P] [US1] Integration test in tests/integration/test_slack_client.py: Handle webhook POST with success response (200)
- [ ] T048 [P] [US1] Integration test in tests/integration/test_slack_client.py: Handle webhook POST with error response and raise exception

### Implementation for User Story 1

- [ ] T049 [P] [US1] Implement calculate_staleness() function in src/staleness.py using commit-based detection algorithm
- [ ] T050 [P] [US1] Add helper function _get_last_approval_time() in src/staleness.py to find most recent approval timestamp
- [ ] T051 [P] [US1] Add helper function _get_last_commit_time() in src/staleness.py to get most recent commit timestamp
- [ ] T052 [US1] Implement GitHubClient class in src/github_client.py with __init__(token, org, timeout) constructor
- [ ] T053 [US1] Add fetch_team_prs() method to GitHubClient in src/github_client.py that gets all repos and filters PRs by team members
- [ ] T054 [US1] Add _get_required_approvals() method to GitHubClient in src/github_client.py that checks branch protection or defaults to 1
- [ ] T055 [US1] Add _count_current_approvals() method to GitHubClient in src/github_client.py that counts valid approvals (latest review per user)
- [ ] T056 [US1] Add error handling for rate limits and network errors to GitHubClient in src/github_client.py
- [ ] T057 [US1] Implement SlackClient class in src/slack_client.py with __init__(webhook_url, timeout) constructor
- [ ] T058 [US1] Add format_stale_prs_message() method to SlackClient in src/slack_client.py that creates basic text message sorted by staleness
- [ ] T059 [US1] Add format_celebration_message() method to SlackClient in src/slack_client.py for when no stale PRs found
- [ ] T059a [US1] Add _format_staleness() helper method to SlackClient in src/slack_client.py that formats staleness_days as "N hours" for values <1.0, "N days" for values ≥1.0 (implements FR-016)
- [ ] T060 [US1] Add send_message() method to SlackClient in src/slack_client.py that posts to webhook URL
- [ ] T060a [US1] Add network error handling to send_message() in src/slack_client.py for connection failures, timeouts, and invalid webhook responses (implements FR-035 for Slack)
- [ ] T061 [US1] Create main() function in src/app.py that orchestrates: load config → load team → fetch PRs → calculate staleness → send to Slack
- [ ] T061a [US1] Implement secondary sort in main() function in src/app.py to sort PRs with identical staleness by creation date (oldest first) per FR-018
- [ ] T062 [US1] Add CLI argument parsing to src/app.py for optional --dry-run flag that prints message without sending
- [ ] T063 [US1] Add logging configuration to src/app.py using stdlib logging with configurable level from .env
- [ ] T064 [US1] Add __main__ block to src/app.py to enable python -m src.app execution
- [ ] T065 [US1] Add error handling and user-friendly error messages to main() in src/app.py
- [ ] T066 [US1] Verify all functions have complete type annotations and run uvx ty src/ to validate

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Can run end-to-end with real GitHub org and Slack webhook.

---

## Phase 4: User Story 2 - Enhanced Slack UI with PR Context (Priority: P2)

**Goal**: A development team receives a rich, visually engaging Slack message with Block Kit formatting that provides key context for each PR including repository name, PR title, author, URL, approval progress, and visual indicators (emojis, color coding) for easy scanning.

**Independent Test**: Run the script with enhanced formatting enabled and verify the Slack message uses Block Kit blocks with properly formatted fields, color-coded emojis based on staleness severity, and clickable PR links.

### Tests for User Story 2 (MANDATORY - TDD cycle) ⚠️

- [ ] T067 [P] [US2] Integration test in tests/integration/test_slack_client.py: Format message with Block Kit header, sections, dividers, context blocks
- [ ] T068 [P] [US2] Integration test in tests/integration/test_slack_client.py: Group PRs by category (rotten, aging, fresh) with correct emoji headers
- [ ] T069 [P] [US2] Integration test in tests/integration/test_slack_client.py: Format PR rows with clickable URLs, author/reviewer mentions, staleness, approval progress
- [ ] T070 [P] [US2] Integration test in tests/integration/test_slack_client.py: Include repository name, PR number, and title in PR row
- [ ] T071 [P] [US2] Integration test in tests/integration/test_slack_client.py: Verify message stays within Slack size constraints (40,000 chars, 50 blocks)
- [ ] T072 [P] [US2] Integration test in tests/integration/test_slack_client.py: Format Slack user mentions as <@USER_ID> when slack_user_id available

### Implementation for User Story 2

- [ ] T073 [US2] Replace format_stale_prs_message() in src/slack_client.py with Block Kit implementation using header, section, divider blocks
- [ ] T074 [US2] Add _group_by_category() helper method to SlackClient in src/slack_client.py that groups StalePRs into rotten/aging/fresh lists
- [ ] T075 [US2] Add _format_category_section() method to SlackClient in src/slack_client.py that creates category header with emoji and count
- [ ] T076 [US2] Add _format_pr_row() method to SlackClient in src/slack_client.py with rich formatting: emoji, clickable link, title, author, reviewers, staleness, approval progress
- [ ] T076a [US2] Update _format_pr_row() in src/slack_client.py to use _format_staleness() helper for consistent hours/days display per FR-016
- [ ] T077 [US2] Add _format_user_mention() helper to SlackClient in src/slack_client.py that uses <@USER_ID> format when slack_user_id available, otherwise @username
- [ ] T078 [US2] Add _create_footer_context() method to SlackClient in src/slack_client.py with generation timestamp
- [ ] T079 [US2] Update format_celebration_message() in src/slack_client.py to use Block Kit with 🎉 emoji and engaging text
- [ ] T080 [US2] Add message size validation to SlackClient in src/slack_client.py to ensure under 40,000 chars and 50 blocks; implement truncation logic that removes PRs from the end of the list and adds footer "... and N more PRs" when limits approached (implements FR-027 overflow handling)

**Checkpoint**: Slack messages are now visually rich with Block Kit formatting, making it easy to scan and prioritize PRs

---

## Phase 5: User Story 3 - Configurable Staleness Scoring (Priority: P3)

**Goal**: A development team can customize how staleness is calculated by configuring weights or rules for different scenarios, such as giving higher priority to PRs from certain repositories or applying different thresholds for staleness categories.

**Independent Test**: Create a configuration with custom scoring rules (e.g., "PRs in 'critical-services' repo get 2x staleness weight"), run the script, and verify that PRs are sorted according to the adjusted scoring rather than pure time-based staleness.

### Tests for User Story 3 (MANDATORY - TDD cycle) ⚠️

- [ ] T081 [P] [US3] Unit test in tests/unit/test_staleness.py: Apply repository weight multiplier to staleness score
- [ ] T082 [P] [US3] Unit test in tests/unit/test_staleness.py: Apply label-based staleness bonus (e.g., "urgent" label adds days)
- [ ] T083 [P] [US3] Unit test in tests/unit/test_staleness.py: Sort PRs by adjusted staleness score instead of raw days
- [ ] T084 [P] [US3] Unit test in tests/unit/test_config.py: Load optional staleness_rules.json with repository weights and label bonuses
- [ ] T085 [P] [US3] Unit test in tests/unit/test_config.py: Handle missing staleness_rules.json gracefully (use defaults)
- [ ] T086 [P] [US3] Integration test in tests/integration/test_github_client.py: Fetch PR labels from GitHub API for scoring

### Implementation for User Story 3

- [ ] T087 [P] [US3] Create StalenessRules dataclass in src/models.py with repository_weights (dict), label_bonuses (dict), custom_thresholds (optional)
- [ ] T088 [US3] Add load_staleness_rules() function to src/config.py that loads optional staleness_rules.json
- [ ] T088a [US3] Create specs/001-stale-pr-board/contracts/staleness_rules.schema.json defining JSON schema for scoring rules configuration (implements FR-031 documentation requirement)
- [ ] T089 [US3] Create staleness_rules.json.example with sample configuration (repository weights, label bonuses)
- [ ] T090 [US3] Update .gitignore to exclude staleness_rules.json (optional user config)
- [ ] T091 [US3] Extend calculate_staleness() in src/staleness.py to accept optional StalenessRules parameter
- [ ] T092 [US3] Add _apply_repository_weight() helper to src/staleness.py that multiplies staleness by repository weight if configured
- [ ] T093 [US3] Add _apply_label_bonus() helper to src/staleness.py that adds days for matching PR labels
- [ ] T094 [US3] Add labels field to PullRequest dataclass in src/models.py (list[str])
- [ ] T095 [US3] Update GitHubClient.fetch_team_prs() in src/github_client.py to include PR labels in PullRequest objects
- [ ] T096 [US3] Update main() in src/app.py to load staleness rules and pass to calculate_staleness()
- [ ] T097 [US3] Update README.md with section documenting staleness scoring configuration options

**Checkpoint**: All user stories should now be independently functional with full customization support

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final documentation

- [ ] T098 [P] Create comprehensive README.md with overview, installation via uv, configuration setup, usage examples, troubleshooting
- [ ] T099 [P] Add GitHub token scope requirements (repo, read:org) and Slack webhook setup instructions to README.md
- [ ] T100 [P] Add examples section to README.md showing sample commands and expected Slack message output
- [ ] T101 Run uvx ty src/ to validate all type annotations are correct and complete
- [ ] T102 Run ruff check . to verify code style and fix any linting issues
- [ ] T103 Run pytest with coverage to ensure all tests pass and coverage meets target (>80%)
- [ ] T104 [P] Test with real GitHub organization and Slack webhook to verify end-to-end functionality
- [ ] T105 [P] Validate all scenarios from specs/001-stale-pr-board/quickstart.md work as expected
- [ ] T106 [P] Add example use case to README.md: scheduling script with cron for daily notifications
- [ ] T107 Review all error messages for clarity and user-friendliness
- [ ] T108 Final code review: check for unused imports, commented code, TODOs, security issues

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Extends US1 components but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Extends US1 components but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Data models before business logic
- Business logic (staleness, clients) before main orchestration
- Main app orchestration last
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T003-T011)
- All Foundational model tasks marked [P] can run in parallel (T013-T018, T021-T024)
- All tests for a user story marked [P] can run in parallel
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all unit tests for User Story 1 together:
Task: "Unit test in tests/unit/test_staleness.py: PR marked ready 5 days ago..."
Task: "Unit test in tests/unit/test_staleness.py: PR with commit after approval..."
Task: "Unit test in tests/unit/test_staleness.py: PR with sufficient approvals..."
Task: "Unit test in tests/unit/test_staleness.py: Draft PR should be excluded..."
Task: "Unit test in tests/unit/test_staleness.py: PR with approval but no commits..."

# Launch all config unit tests in parallel:
Task: "Unit test in tests/unit/test_config.py: Valid .env file should load..."
Task: "Unit test in tests/unit/test_config.py: Missing required variables..."
Task: "Unit test in tests/unit/test_config.py: Invalid webhook URL..."

# Launch all integration tests in parallel:
Task: "Integration test in tests/integration/test_github_client.py: Fetch PRs..."
Task: "Integration test in tests/integration/test_github_client.py: Parse PR reviews..."
Task: "Integration test in tests/integration/test_slack_client.py: Format basic message..."
```

---

## Parallel Example: User Story 1 Implementation

```bash
# After tests are written and failing, launch foundational implementations in parallel:
Task: "Implement calculate_staleness() function in src/staleness.py..."
Task: "Add helper function _get_last_approval_time() in src/staleness.py..."
Task: "Add helper function _get_last_commit_time() in src/staleness.py..."

# Then launch client implementations in parallel:
Task: "Implement GitHubClient class in src/github_client.py..."
Task: "Implement SlackClient class in src/slack_client.py..."
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (~12 tasks)
2. Complete Phase 2: Foundational (~13 tasks) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (~41 tasks including tests)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready - full value delivered!

**MVP delivers**: Complete stale PR detection and basic Slack notification

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (~25 tasks)
2. Add User Story 1 → Test independently → Deploy/Demo (MVP! ~41 tasks)
3. Add User Story 2 → Test independently → Deploy/Demo (Enhanced UI! ~14 tasks)
4. Add User Story 3 → Test independently → Deploy/Demo (Full customization! ~17 tasks)
5. Add Polish → Final production ready (~11 tasks)

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Tests → Implementation)
   - Developer B: User Story 2 (Tests → Implementation)
   - Developer C: User Story 3 (Tests → Implementation)
3. Stories complete and integrate independently
4. Team converges on Polish phase

---

## Notes

- **Total tasks**: 113 tasks
- **Task breakdown by phase**:
  - Phase 1 (Setup): 12 tasks
  - Phase 2 (Foundational): 13 tasks
  - Phase 3 (US1 - MVP): 44 tasks (23 tests + 21 implementation)
  - Phase 4 (US2): 15 tasks (6 tests + 9 implementation)
  - Phase 5 (US3): 18 tasks (6 tests + 12 implementation)
  - Phase 6 (Polish): 11 tasks
- **Parallel opportunities**: ~45 tasks marked [P] can run in parallel within their phase
- **MVP scope**: Phases 1-3 = 69 tasks (61% of total) delivers full core value
- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
