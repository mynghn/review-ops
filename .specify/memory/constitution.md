<!--
SYNC IMPACT: v1.0.0 (Initial) | Ratified: 2025-10-30

Core Principles: 3 (Simplicity First, Small Scope, Test-Driven Quality)
- Merged "Prefer Real Components" into Principle III
- Merged "Incremental Delivery" into Principle II + Development Workflow

Templates Updated:
✅ tasks-template.md - Changed tests from OPTIONAL to MANDATORY (5 locations)
✅ spec-template.md - Already aligned with prioritized stories
✅ plan-template.md - Constitution check section present

Key Changes:
- TDD now mandatory with justified exception process
- Added scope breakdown guidance table in Principle II
- Simplified governance to essentials only
-->

# Review-Ops Constitution

## Core Principles

### I. Simplicity First (NON-NEGOTIABLE)

Start with the simplest solution. Add complexity only when justified with documented rationale.

**MUST NOT**:
- Add abstractions, patterns, or layers without demonstrable need
- Introduce architectural complexity speculatively

**Justify before adding**:
- Repository patterns (when direct access works)
- Multiple services (when one works)
- Frameworks (when simple code works)

### II. Small Scope (NON-NEGOTIABLE)

Every feature MUST fit within one specify-plan-tasks-implement cycle (3-5 days).

**Breaking down large requirements**:

| When you have | Break it into | Example |
|---------------|---------------|---------|
| Multiple user personas | One feature per persona | Admin UI → User UI → Guest UI |
| End-to-end workflow | One phase per feature | Data ingestion → Processing → Reporting |
| CRUD operations | One operation per iteration | Create → Read → Update → Delete |
| Multiple data entities | One entity per feature | Users → Posts → Comments |
| Complex UI screens | One screen/section per feature | Dashboard → Settings → Profile |

**Each iteration MUST**:
- Deliver independently testable value
- Have P1 story as viable MVP
- Complete in single cycle

**If scope still too large**: Further decompose P1 into sub-stories (P1a, P1b, etc.).

### III. Test-Driven Quality (NON-NEGOTIABLE)

TDD is mandatory: Write tests → Verify they fail → Implement → Tests pass.

**MUST**:
- Write automated tests for every user story
- Use real components over mocks (unless justified below)
- Define clear acceptance scenarios

**Mocks allowed only when**:
- Real component needs external services (APIs, paid services)
- Setup complexity exceeds value (multi-service orchestration)
- Test execution becomes impractical (>1s per test)

**Exception process**:
- Experimental/prototype work may defer tests
- MUST document why and plan to add tests before production
- Constitution check flags missing tests as violation

## Development Workflow

**Specify** → Define user scenarios, prioritize (P1 = MVP)
**Plan** → Constitution check, identify foundational vs story work
**Tasks** → Organize by user story, mark [P]arallel tasks
**Implement** → TDD cycle, validate each story independently

**Key checkpoints**:
- After foundational phase: Can user stories start?
- After each story: Does it work independently?
- After P1: Validate MVP before continuing to P2

## Governance

**Amendments**: Document rationale + impact analysis
**Versioning**: MAJOR.MINOR.PATCH (semantic versioning)
**Compliance**: Constitution check during planning phase

**Code reviews verify**:
- Scope fits single iteration
- Complexity is justified
- Tests validate real behavior
- Stories are independent

---

**Version**: 1.0.0 | **Ratified**: 2025-10-30 | **Last Amended**: 2025-10-30
