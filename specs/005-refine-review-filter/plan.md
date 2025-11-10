# Implementation Plan: Refine Review-Needed PR Criteria

**Branch**: `005-refine-review-filter` | **Date**: 2025-11-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-refine-review-filter/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Expand PR search criteria to include both `review:none` and `review:required` PRs, with proper deduplication and team member filtering. For `review:required` PRs, filter to only include those where at least one team member is in the current `reviewRequests` field. Display only reviewers from `reviewRequests` (which GitHub automatically manages to reflect pending reviewers). This ensures team members see PRs that need their attention regardless of whether partial reviews have been submitted.

## Technical Context

**Language/Version**: Python 3.12 (existing)
**Primary Dependencies**: requests, PyGithub, gh CLI (existing), Slack Block Kit (JSON format)
**Storage**: N/A (stateless CLI application, in-memory PR deduplication only)
**Testing**: pytest (existing)
**Target Platform**: Cross-platform CLI (macOS/Linux/Windows with gh CLI installed)
**Project Type**: Single project (CLI tool)
**Performance Goals**: Complete dual search + deduplication + filtering within 30 seconds for teams with up to 15 members and 100 PRs per search query
**Constraints**:

- GitHub API rate limits (5000 requests/hour for authenticated users)
- Existing retry and backoff logic must handle dual searches
- Maximum team size: 100 members per GitHub team (fail-safe if exceeded)
- Search results must be deduplicated before detail fetching to avoid redundant API calls

**Scale/Scope**:

- Teams with up to 15 members (validated in config)
- Up to 100 PRs per search query (configurable via GH_SEARCH_LIMIT)
- Support for multiple GitHub teams as reviewers (already exists)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Simplicity First ✅

**Status**: PASS

- No new abstractions or design patterns introduced
- Modifies existing `GitHubClient.fetch_team_prs()` to execute dual searches
- Uses existing retry/backoff logic for additional search query
- Adds filtering logic using existing data structures (`reviewRequests` field)
- No repository patterns, service layers, or frameworks added

### Principle II: Small Scope ✅

**Status**: PASS

- Feature fits within single specify-plan-tasks-implement cycle (3-5 days)
- Focused on enhancing PR search criteria only
- P1 story (dual search with deduplication) is independently testable
- P2 story (display current reviewers) leverages GitHub's existing `reviewRequests` behavior
- P3 stories (filtering) build incrementally on P1/P2

**Scope breakdown**:

- Foundational: Dual search + deduplication (1 day)
- P1: Include review:required PRs (1 day)
- P2: Display current requested reviewers (0.5 day, uses existing field)
- P3: Filter by team member presence (1 day)
- P3: Handle GitHub team expansion (0.5 day, already exists)

Total: ~4 days (within 3-5 day target)

### Principle III: Test-Driven Quality ✅

**Status**: PASS

- TDD approach planned for all user stories
- Tests will use real GitHub CLI calls where possible
- Mock GitHub API responses only for edge cases (rate limits, failures)
- Clear acceptance scenarios defined in spec for each story
- Existing test infrastructure (pytest) supports TDD workflow

**Test strategy**:

1. Unit tests for dual search deduplication logic
2. Unit tests for team member filtering logic
3. Integration tests with mock `gh` CLI responses
4. Edge case tests for rate limits, empty results, team expansion failures

---

### Post-Design Re-Evaluation ✅

**Date**: 2025-11-10
**Status**: All principles still satisfied after Phase 1 design

**Principle I: Simplicity First** - PASS

- No new abstractions introduced during design
- Internal `pr_search_metadata` dictionary is simplest solution for tracking search origins
- Reuses existing `_retry_with_backoff()` and `_execute_gh_command()` methods
- No repository patterns, service layers, or architectural changes

**Principle II: Small Scope** - PASS

- Design fits within original 4-day estimate
- Phase breakdown remains valid:
  - Foundational: Helper method for single search query (0.5 day)
  - P1: Dual search + deduplication (1 day)
  - P2: Display reviewers from reviewRequests (0 days, already works)
  - P3: Team member filtering (1 day)
  - P3: Team size limit check (0.5 day)
  - Testing: (1 day)
- Total: 4 days (within 3-5 day target)

**Principle III: Test-Driven Quality** - PASS

- TDD approach confirmed in quickstart.md
- Test fixtures defined in data-model.md
- Clear test scenarios for each implementation step
- Tests use real components (gh CLI) with mocked responses for edge cases
- No mocks for production code paths (only for API responses)

## Project Structure

### Documentation (this feature)

```text
specs/005-refine-review-filter/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── app.py               # Main entry point (existing)
├── config.py            # Configuration loading (existing)
├── models.py            # Data models (existing)
├── github_client.py     # GitHub API client (MODIFIED - dual search + filtering)
├── slack_client.py      # Slack webhook client (existing)
└── staleness.py         # Staleness calculation (existing)

tests/
├── unit/
│   ├── test_github_client.py          # NEW - dual search tests
│   ├── test_github_client_filtering.py # NEW - team member filtering tests
│   └── [existing test files]
└── integration/
    └── [existing test files]
```

**Structure Decision**: Single project (CLI tool). This feature modifies only `src/github_client.py` to add dual search capability and filtering logic. The existing `fetch_team_prs()` method will be enhanced to:

1. Execute two separate search queries (`review:none` and `review:required`)
2. Deduplicate PR keys before detail fetching
3. Filter `review:required` PRs by team member presence in `reviewRequests`
4. Maintain existing retry/backoff and GraphQL batching optimizations

No new files or architectural changes required - focused enhancement to existing search logic.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations - all constitution principles satisfied. This feature adds minimal complexity by enhancing existing search logic without introducing new abstractions.
