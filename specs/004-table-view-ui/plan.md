# Implementation Plan: Table View UI for Stale PR Board

**Branch**: `004-table-view-ui` | **Date**: 2025-11-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-table-view-ui/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Replace the current category-based Slack Block Kit format (separate headers and sections for rotten/aging/fresh) with a unified table view that displays all PRs sorted by staleness in descending order. The table will use Slack Block Kit's `table` block type with 4 columns (staleness emoji, elapsed time, PR details, reviewers) and maintain existing bilingual support (EN/KO).

## Technical Context

**Language/Version**: Python 3.12 (existing)
**Primary Dependencies**: requests (existing), Slack Block Kit API (JSON format - no new libraries)
**Storage**: N/A (stateless CLI application, in-memory processing only)
**Testing**: pytest (existing) with unit tests for Block Kit table generation
**Target Platform**: Linux/macOS server (CLI application)
**Project Type**: single (CLI application)
**Performance Goals**: Message generation <1 second for up to 30 PRs (per spec SC-004)
**Constraints**: Slack Block Kit table format (rich_text cells, max 20 columns, max 100 rows including header), bilingual support (EN/KO), truncation at max_prs_total (default 30, hard cap at 99 to respect Slack's 100-row limit including header)
**Scale/Scope**: Up to 30 PRs displayed by default (configurable via max_prs_total, capped at 99 rows), single table view with 4 columns (staleness emoji, elapsed time, PR details, reviewers)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Simplicity First ✅ PASS

**No new abstractions**: The feature only modifies the `SlackClient.build_blocks()` method to generate table blocks instead of section blocks. No new classes, patterns, or architectural layers are introduced.

**Justified complexity**: None added. The table format is a direct replacement of the existing category-based format, using the same data models (StalePR, PullRequest, TeamMember) and processing logic (sorting, truncation, bilingual support).

### Principle II: Small Scope ✅ PASS

**Single iteration scope**: This feature replaces one UI component (Slack message format) and fits comfortably within a 3-5 day cycle:

- Day 1: Research Slack table block structure, design data model
- Day 2: Implement table generation logic with bilingual support
- Day 3: Write tests (unit tests for table blocks)
- Day 4-5: Testing, refinement, and documentation

**Independently testable value**: The P1 story (Unified Table View) delivers the core MVP - users get a sortable table view. P2 (Bilingual Headers) and P3 (Truncation) build incrementally on the same foundation.

**No further decomposition needed**: Each user story is independently testable and can be implemented in sequence.

### Principle III: Test-Driven Quality ✅ PASS

**TDD approach**:

1. Write tests for table block generation (header row, PR rows, empty state)
2. Verify tests fail
3. Implement table generation logic
4. Tests pass

**Real components over mocks**: All tests will use real `SlackClient` and data models. No external services are involved (Slack webhook calls can be mocked in integration tests only).

**Acceptance scenarios**: All 3 user stories have clear acceptance scenarios defined in spec.md that map directly to test cases.

### Gate Evaluation: ✅ ALL GATES PASS

No violations. Feature adheres to all constitutional principles. Proceeding to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── app.py               # Main entry point
├── config.py            # Configuration loading
├── slack_client.py      # Slack webhook client (MODIFIED: table generation)
├── github_client.py     # GitHub PR fetching
├── models.py            # Data models (StalePR, PullRequest, TeamMember)
└── staleness.py         # Staleness calculation

tests/
├── unit/                # Unit tests (NEW: table block tests)
└── integration/         # Integration tests
```

**Structure Decision**: Single project structure (CLI application). The primary change is in [src/slack_client.py](../../src/slack_client.py) which will be modified to generate Slack Block Kit table blocks instead of category-based section blocks. New unit tests will be added to [tests/unit/](../../tests/unit/) to verify table generation logic.

## Complexity Tracking

N/A - No constitutional violations. All gates pass.

---

## Phase Completion Summary

### Phase 0: Research ✅ COMPLETE

**Artifacts Generated**:
- [research.md](./research.md) - 10 research topics resolved

**Key Findings**:
1. Slack Block Kit table format structure (table block, rows, rich_text cells)
2. Column alignment strategy (center for emoji/age, left for PR/reviewers)
3. Bilingual implementation approach (7 translation string pairs)
4. PR details format (two-line: repo#number + title)
5. Reviewer display format (vertical newline-separated list)
6. Sorting strategy (descending by staleness_days)
7. Truncation handling (max 99 data rows due to Slack 100-row limit)
8. Empty state handling (skip table, show celebration message)

### Phase 1: Design & Contracts ✅ COMPLETE

**Artifacts Generated**:
- [data-model.md](./data-model.md) - Data structures and entity relationships
- [contracts/README.md](./contracts/README.md) - Contract specification
- [contracts/table-block-example-ko.json](./contracts/table-block-example-ko.json) - Korean example
- [contracts/table-block-example-en.json](./contracts/table-block-example-en.json) - English example
- [contracts/empty-state-example.json](./contracts/empty-state-example.json) - Empty state examples
- [quickstart.md](./quickstart.md) - Implementation guide with TDD roadmap
- CLAUDE.md updated - Agent context refreshed

**Design Decisions**:
1. **No new Python models**: Reuse existing `StalePR`, `PullRequest`, `TeamMember`
2. **Table structure**: 4 columns, header row + data rows, column-specific alignment
3. **Translation model**: Dictionary-based with language key switching
4. **Cell construction**: Reusable `_build_rich_text_cell()` helper method
5. **Reviewer handling**: User mentions with fallback to `@username` when Slack ID missing

### Constitution Re-Check (Post-Design) ✅ ALL GATES PASS

**Principle I: Simplicity First** - ✅ PASS

No additional complexity introduced during design. All new methods are simple helper functions for cell/row construction. No abstractions, patterns, or layers added.

**Design adheres to**:
- Single responsibility per method (`_build_table_header_row`, `_build_table_data_row`, `_build_rich_text_cell`)
- Direct data transformation (StalePR → table row)
- No unnecessary indirection

**Principle II: Small Scope** - ✅ PASS

Design confirms feature fits within single iteration:
- **Phase 0 (Research)**: Completed
- **Phase 1 (Design)**: Completed
- **Phase 2 (Tasks)**: Next step - `speckit.tasks` command
- **Phase 3 (Implementation)**: TDD cycle as outlined in quickstart.md

Estimated total: 3-4 days (within 3-5 day target)

**Principle III: Test-Driven Quality** - ✅ PASS

Quickstart.md provides detailed TDD roadmap:
1. Write header row tests → Implement → Verify
2. Write data row tests → Implement → Verify
3. Write integration tests → Replace `build_blocks()` → Verify
4. Update existing tests → Manual testing

**Real components**: All tests use real `SlackClient`, `StalePR`, `PullRequest`, `TeamMember`. No mocks needed (stateless processing, no external services).

---

## Implementation Readiness

✅ **All design artifacts complete**
✅ **Constitution requirements met**
✅ **Contract examples validated**
✅ **TDD approach documented**

**Ready for Phase 2**: Task breakdown (`/speckit.tasks` command)

---

## Notes

- Maximum table size: 99 data rows + 1 header row (Slack limit: 100 rows total)
- Truncation occurs after sorting (preserves stalest-first order)
- Empty state skips table entirely (uses header + section block)
- Bilingual support maintained throughout (EN/KO)
- No breaking changes to existing data models or configuration
