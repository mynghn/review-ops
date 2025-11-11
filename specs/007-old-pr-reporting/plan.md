# Implementation Plan: Too Old PRs Reporting

**Branch**: `007-old-pr-reporting` | **Date**: 2025-11-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-old-pr-reporting/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add "too old PR" reporting functionality to the Stale PR Board app. The main board will be restricted to PRs updated within the configured time window (GH_SEARCH_WINDOW_SIZE, e.g., 30 days). When team members have review-requested PRs older than this window, an in-thread Slack message will be posted containing a bulleted list of team members with counts and GitHub search links to view their old PRs. This keeps the main board focused on actionable PRs while still providing visibility into potentially abandoned PRs. Estimated implementation time: 3-5 days.

## Technical Context

**Language/Version**: Python 3.12 (existing)
**Primary Dependencies**: requests, PyGithub, gh CLI (existing), Slack Block Kit (JSON format)
**Storage**: N/A (stateless CLI application, in-memory processing only)
**Testing**: pytest (existing test infrastructure)
**Target Platform**: CLI application (Linux/macOS/Windows)
**Project Type**: Single project (CLI tool)
**Performance Goals**: Complete within 60 seconds for teams with 15 members and 100 PRs
**Constraints**:
- GitHub API rate limits (5000 requests/hour for authenticated requests)
- Slack Bot API (chat.postMessage) required for threading support - webhooks cannot support thread replies
- Thread message must be posted within 5 seconds of main board message
- No new environment variables (reuse existing GH_SEARCH_WINDOW_SIZE)
**Scale/Scope**:
- Support teams up to 15 members
- Handle up to 100 PRs per run
- Generate GitHub search URLs that don't exceed browser URL limits (~2000 chars)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity First ✅
**Status**: PASS

- **Justification**: Feature adds minimal complexity
  - GitHub search URL generation: Simple string formatting using existing patterns
  - Thread posting: Single new method in SlackClient using existing webhook infrastructure
  - Old PR search: Reuses existing dual search pattern with inverted date filter
  - No new abstractions, patterns, or architectural layers introduced

### II. Small Scope ✅
**Status**: PASS

- **Breakdown**:
  - P1: Main board restriction (independent, 1-2 days)
  - P2: Thread message with links (builds on P1, 1-2 days)
  - P3: Configuration (already satisfied, 0 days)
- **Total**: 2-4 days fits within single specify-plan-tasks-implement cycle
- **Independent testing**: Each story can be tested independently with clear acceptance scenarios

### III. Test-Driven Quality ✅
**Status**: PASS (with plan)

- **Unit tests planned**:
  - Old PR search with date filters (github_client)
  - GitHub URL generation and encoding (new utility function)
  - Thread message formatting with bilingual support (slack_client)
  - Thread timestamp return from main post (slack_client)
- **Integration tests planned**:
  - End-to-end thread posting workflow
  - Edge cases: no old PRs, all PRs old, URL length limits
- **Real components**: All tests use real date calculations, string formatting (no mocks needed)

### Conclusion
**GATE STATUS**: ✅ PASS - No constitution violations. Feature is simple, scoped appropriately, and testable.

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
├── app.py                      # Main entry point (MODIFY: add old PR logic)
├── config.py                   # Config loading (NO CHANGE: reuse existing GH_SEARCH_WINDOW_SIZE)
├── github_client.py            # GitHub API client (MODIFY: add old PR search)
├── slack_client.py             # Slack webhook client (MODIFY: add thread posting)
├── models.py                   # Data models (ADD: OldPRReport model)
├── staleness.py                # Staleness calculation (NO CHANGE)
└── url_builder.py              # NEW: GitHub search URL generation

tests/
├── unit/
│   ├── test_github_client.py   # MODIFY: add old PR search tests
│   ├── test_slack_client.py    # MODIFY: add thread posting tests
│   ├── test_url_builder.py     # NEW: URL generation tests
│   └── test_models.py          # MODIFY: add OldPRReport tests
└── integration/
    └── test_old_pr_workflow.py # NEW: end-to-end thread posting test

team_members.json               # Team config (NO CHANGE)
.env                            # Environment vars (NO CHANGE: reuse GH_SEARCH_WINDOW_SIZE)
```

**Structure Decision**: Single project structure maintained. All changes are additions or modifications to existing files, preserving the established flat module structure. New URL builder module added for GitHub search URL generation (separation of concerns).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

N/A - No constitution violations detected. All complexity is justified and minimal.

---

## Post-Design Constitution Re-evaluation

*Re-evaluated after Phase 1 design completion*

### I. Simplicity First ✅
**Status**: STILL PASS

**Design Review**:
- Research revealed Slack webhook limitation (can't return message timestamp)
- Design decision: Migrate to `chat.postMessage` API (simpler than workarounds)
- New module: `url_builder.py` (single function, 40 lines)
- New model: `OldPRReport` (3 fields, dataclass)
- Changes to existing modules: Minimal (add methods, not replace)

**Complexity Assessment**:
- **Added**: Slack SDK dependency (official library, well-maintained)
- **Added**: URL encoding logic (standard library only, no dependencies)
- **Added**: Thread posting logic (reuses existing Slack client pattern)
- **Removed**: Webhook complexity (simpler API with better error handling)

**Net Complexity**: Slightly increased, but justified by:
- More reliable threading (no race conditions)
- Better error messages (official SDK)
- Cleaner architecture (no webhook timestamp hacks)

### II. Small Scope ✅
**Status**: STILL PASS

**Design Validation**:
- P1: Main board restriction (1-2 days) - Reuses existing PR fetch, adds date filter
- P2: Thread posting (2-3 days) - New `post_thread_reply()` method, URL generation
- P3: Configuration (0 days) - Already satisfied by existing config

**Total Estimated**: 3-5 days (within constitutional single cycle limit)

**Implementation Breakdown** (3-5 days):
- Day 1: URL builder + tests (unit)
- Day 2: Slack migration (bot token setup, API switch)
- Day 3: Old PR search logic (github_client) + main board filtering
- Day 4: Thread posting (slack_client)
- Day 5 (optional): Integration tests + edge case handling

**Independent Testing**: All stories can still be tested independently:
- P1: Test main board shows only recent PRs
- P2: Test thread appears with correct links
- P3: Test configuration validation

### III. Test-Driven Quality ✅
**Status**: STILL PASS

**Test Coverage Plan**:

**Unit Tests** (14 tests planned):
- `test_url_builder.py` (7 tests):
  - Basic URL generation
  - Special character encoding
  - Empty username validation
  - Invalid date type validation
  - URL length validation
  - Date format variations
  - URL decoding verification

- `test_models.py` (2 tests):
  - OldPRReport validation
  - Config with bot token/channel ID

- `test_slack_client.py` (3 tests):
  - Thread message formatting
  - Timestamp return from main post
  - Thread posting with thread_ts

- `test_github_client.py` (2 tests):
  - Old PR search with inverted date filter
  - PR grouping by team member

**Integration Tests** (2 tests planned):
- `test_old_pr_workflow.py`:
  - End-to-end: fetch old PRs → generate URLs → post thread
  - Edge case: No old PRs (no thread posted)

**Real Components**: All tests use real date calculations, string formatting, URL parsing (no mocks needed except Slack API)

### Summary of Re-evaluation

**Constitution Compliance**: ✅ PASS (all three principles satisfied)

**Key Changes from Initial Check**:
1. **API Migration**: Webhook → chat.postMessage (reduces complexity)
2. **New Module**: url_builder.py (simple, single-purpose)
3. **Dependencies**: +1 (slack-sdk) -0 (net increase justified by reliability)

**Risk Assessment**:
- **Low Risk**: URL generation (standard library, well-tested)
- **Medium Risk**: Slack API migration (breaking change, needs user migration)
- **Mitigation**: Comprehensive quickstart guide for Slack Bot setup

**Final Verdict**: Feature design maintains simplicity, fits single iteration, and is fully testable. Ready for Phase 2 (task generation).
