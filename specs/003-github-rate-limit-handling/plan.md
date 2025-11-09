# Implementation Plan: GitHub API Rate Limit Handling

**Branch**: `003-github-rate-limit-handling` | **Date**: 2025-10-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-github-rate-limit-handling/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement robust GitHub API rate limit handling to prevent the application from getting stuck during runs. The feature includes three priorities: (P1) Rate limit detection and graceful degradation with auto-wait or fail-fast behavior, (P2) Smart retry with exponential backoff for HTTP 429 errors, and (P3) API call optimization through in-memory PR deduplication and query limit optimization based on Slack display constraints (configurable total PR limit: `MAX_PRS_TOTAL` env var / `max_prs_total` config field, default 30). Technical approach uses gh CLI subprocess calls with retry wrappers, GraphQL batch fetching for PR details (65% API savings), and priority-based PR display allocation (rotten → aging → fresh)

## Technical Context

**Language/Version**: Python 3.12 (existing)
**Primary Dependencies**:
- `requests` (existing) - for Slack webhook HTTP calls
- `subprocess` (stdlib) - for gh CLI integration
- `dataclasses` (stdlib) - for new models (RateLimitStatus, APICallMetrics)
- `time` (stdlib) - for retry backoff sleep
**Storage**: N/A (stateless CLI application, in-memory PR deduplication only)
**Testing**: pytest (existing), unittest.mock for subprocess mocking
**Target Platform**: macOS/Linux (requires gh CLI installation)
**Project Type**: Single CLI application
**Performance Goals**:
- Complete PR fetching for 5-member team within 2 minutes (normal case)
- Auto-wait and resume within 7 minutes total when rate limit reset < 5 min
- Fail fast within 5 seconds when rate limit reset > 5 min
**Constraints**:
- GitHub API rate limit: 5000 points/hour for authenticated users
- Team size: Max 15 members (recommended limit per FR-017)
- API call reduction: Min 30% savings via deduplication and query optimization (SC-007)
- Must work with existing gh CLI subprocess pattern (no REST SDK migration)
**Scale/Scope**:
- 5-15 team members typical use case
- 20-50 PRs per run typical (configurable via MAX_PRS_TOTAL, default 30)
- ~10-15 API calls for search phase, ~2-4 GraphQL calls for details phase (optimized)
- Single Python module modifications (github_client.py, config.py, models.py, slack_client.py)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Simplicity First ✓

**Status**: PASS (with justified complexity)

**Simple approaches used**:
- No new external libraries (uses stdlib: subprocess, time, dataclasses)
- Simple retry logic (~30 lines) instead of retry library (tenacity, backoff)
- In-memory dict for deduplication instead of caching framework

**Justified complexity**:
- GraphQL batch fetching adds complexity BUT justified by 65% API call reduction
- Complexity needed to meet SC-007 (30%+ API reduction) and prevent rate limit exhaustion
- Feature flag `use_graphql_batch` allows fallback to simpler REST approach
- **Rationale**: Rate limit is blocking issue for 5-member teams; optimization prevents problem

### Principle II: Small Scope ✓

**Status**: PASS

**Scope breakdown**:
- P1 (Rate limit detection): 1-2 days - Viable MVP, prevents app from getting stuck
- P2 (Smart retry): 1-2 days - Incremental improvement, independent from P1
- P3 (API optimization): 1 day - Further optimization, independent from P1/P2
- **Total**: 3-5 days fits single cycle

**Independent delivery**:
- P1 alone solves the blocking "app gets stuck" problem (SC-001, SC-002)
- P2 can be added independently (doesn't break P1)
- P3 can be added independently (doesn't break P1/P2)

**Decomposition**:
| Have | Break into | This feature |
|------|------------|--------------|
| Rate limit handling + optimization | P1: Detection, P2: Retry, P3: Optimization | ✓ Already decomposed |

### Principle III: Test-Driven Quality ✓

**Status**: PASS

**Test strategy**:
- Unit tests for rate limit detection logic (mocked gh CLI responses)
- Integration tests for retry scenarios (simulated HTTP 429)
- Integration tests for GraphQL batch fetching (mocked gh api graphql)
- Use real subprocess mocking pattern (existing in tests/integration/test_github_client.py)

**Real components**:
- Real subprocess calls (mocked at boundary)
- Real retry logic (no mocks, actual time.sleep with short intervals)
- Real deduplication tracking (in-memory dict, no mocks)

**Mocks justified**:
- Mock gh CLI subprocess (external service, rate limit protection)
- Mock time.sleep in tests (execution speed, tests complete in <1s)

**No exceptions needed**: TDD mandatory for all user stories

### Gates Summary

| Gate | Status | Justification |
|------|--------|---------------|
| Simplicity First | ✓ PASS | GraphQL complexity justified by 65% savings, feature flag for fallback |
| Small Scope | ✓ PASS | 3-5 days, P1 is viable MVP, incremental P2/P3 |
| Test-Driven | ✓ PASS | Pytest with mocked subprocess, real logic testing |

**Overall**: ✅ PASS - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/003-github-rate-limit-handling/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command) - N/A for this feature
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── models.py            # MODIFY: Add RateLimitStatus, APICallMetrics dataclasses
├── config.py            # MODIFY: Add rate limit config fields + validation
├── github_client.py     # MODIFY: Add retry, rate limit detection, GraphQL batch
├── slack_client.py      # MODIFY: Change from per-category to total PR limit
├── app.py               # MODIFY: Add rate limit check, metrics logging
└── staleness.py         # NO CHANGE

tests/
├── integration/
│   ├── test_github_client.py      # MODIFY: Add rate limit scenarios
│   ├── test_retry_logic.py        # NEW: Retry and backoff testing
│   └── test_graphql_batch.py      # NEW: GraphQL batch fetching
└── unit/
    ├── test_config.py              # MODIFY: Add config validation tests
    ├── test_slack_client.py        # MODIFY: Update truncation tests for total limit
    └── test_rate_limit.py          # NEW: Rate limit status logic

.env.example             # MODIFY: Add new config options
CLAUDE.md                # AUTO-UPDATE: Via update-agent-context.sh script
```

**Structure Decision**: Single CLI application (Option 1). All modifications are in existing Python modules, no new top-level directories needed. New test files added to appropriate test subdirectories (unit vs integration based on subprocess mocking need).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**Status**: No violations requiring justification table

All complexity has been approved in Constitution Check with documented rationale (GraphQL batching justified by 65% API savings and rate limit prevention).
