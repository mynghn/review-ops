# Implementation Plan: Enhanced Stale PR Board UI with Korean Language Support

**Branch**: `002-ui-enhance-on-stale-pr-board` | **Date**: 2025-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from [/specs/002-ui-enhance-on-stale-pr-board/spec.md](spec.md)

## Summary

Transform the plain text stale PR report into a visually engaging, attention-grabbing Slack message using **Block Kit components** (Header, Section, Divider, Context blocks). Add Korean language support with workplace-appropriate expressions matching the current tone. The design creates a "posting board" metaphor through structured visual hierarchy, emoji-based urgency indicators (keeping current 🤢/🧀/✨), and scannable layout.

**Key Decision**: Use traditional Block Kit components (NOT the new table block) for proven webhook compatibility, flexibility, and superior visual hierarchy. Use inline conditionals for Korean translations (no abstraction layer) following the "Simplicity First" principle.

---

## Technical Context

**Language/Version**: Python 3.12 (existing)
**Primary Dependencies**: requests (existing), Slack Block Kit (incoming webhook compatible - no new libraries)
**Storage**: N/A (stateless message generation from team_members.json + GitHub API)
**Testing**: pytest (existing), pytest-mock (existing)
**Target Platform**: Linux server (existing deployment environment)
**Project Type**: Single project (CLI/service)
**Performance Goals**: Message generation ≤ 200ms increase vs plain text (SC-004 from spec)
**Constraints**:
- Slack message size: 40,000 characters max
- Block Kit: 50 blocks per message max
- Incoming webhook limitations (no interactive components, no table block guaranteed)
**Scale/Scope**: Handle up to 45 PRs per report (total across all categories) with graceful truncation for larger sets

---

## Constitution Check ✅ PASS

### Principle I: Simplicity First
**Status**: ✅ COMPLIANT
- Using existing webhook integration (no OAuth, no Slack SDK)
- Block Kit is simple JSON structure (no new frameworks)
- Translation via inline conditionals (no i18n libraries, no translation dictionaries)
- No abstractions beyond necessary formatting functions
- Total of ~7 string pairs (too few to justify abstraction layer)

**Justification**: Inline conditionals chosen over translation dictionary because:
- Only 2 languages (en/ko)
- Only ~10 strings total
- No pluralization complexity in Korean
- Direct if/else is simpler than dict lookup for this scale

### Principle II: Small Scope
**Status**: ✅ COMPLIANT
- Fits within single cycle (estimated 3-5 hours implementation time)
- P1 (Block Kit enhancement) is independently testable MVP
- P2 (Korean translation) builds on P1 without coupling
- P3 (language config) is simple environment variable
- Each user story can be validated independently

**Breakdown**:
- P1: Block Kit formatting (headers, sections, dividers, context blocks)
- P2: Korean inline translations (7 string pairs)
- P3: LANGUAGE env var validation

### Principle III: Test-Driven Quality
**Status**: ✅ COMPLIANT
- Each user story has clear acceptance scenarios in spec
- Tests will use real Slack webhook structure validation (not mocks for Block Kit JSON)
- Mock only external HTTP calls (requests.post responses)
- TDD cycle: Write tests → Verify fail → Implement → Tests pass
- Real components: Block Kit JSON validation, UTF-8 encoding tests

**Test Strategy**:
- Unit tests: Block builders (header, section, context, divider), truncation logic, language lookup
- Integration tests: Full message assembly with mocked HTTP POST
- Manual verification: Visual check in Slack workspace (one-time QA)

**Gate Evaluation**: ✅ All gates passed - proceed to implementation

---

## Project Structure

### Documentation (this feature)

```text
specs/002-ui-enhance-on-stale-pr-board/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - Block Kit research, Korean UX patterns
├── data-model.md        # Phase 1 output - Enhanced SlackClient structure
├── quickstart.md        # Phase 1 output - Step-by-step implementation guide
├── contracts/           # Phase 1 output
│   ├── slack_block_kit_payload.json  # Example Block Kit JSON
│   ├── slack_client_interface.md     # Enhanced SlackClient API
│   └── translation_strings.md        # EN/KO string pairs
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created yet)
```

### Source Code (repository root)

```text
src/
├── app.py               # MODIFY: Pass language to SlackClient
├── config.py            # MODIFY: Add LANGUAGE env var validation
├── slack_client.py      # MODIFY: Add Block Kit formatting + language support
├── models.py            # NO CHANGE: PullRequest model used as-is
├── staleness.py         # NO CHANGE: PR categorization logic unchanged
└── github_client.py     # NO CHANGE: PR fetching unchanged

tests/
├── unit/
│   └── test_slack_client.py  # MODIFY: Add Block Kit tests, Korean tests
├── integration/
│   └── test_slack_integration.py  # MODIFY: Test full message assembly
└── test_config.py        # MODIFY: Add LANGUAGE validation tests

.env.example             # MODIFY: Document LANGUAGE variable
README.md                # MODIFY: Add language configuration docs (optional)
```

**Structure Decision**: Single project structure (Option 1) - this is a CLI/service application with no frontend. All code resides in `src/` with corresponding tests in `tests/`. No new modules or packages needed; enhancements are confined to existing `slack_client.py` and `config.py`.

---

## Phase 0: Research (COMPLETED)

All research questions resolved. See [research.md](research.md) for full details.

### Key Decisions Summary

| Area | Decision | Rationale |
|------|----------|-----------|
| **Slack Formatting** | Block Kit (sections, dividers, context) | Native UI, mobile-friendly, no deps, proven webhook support |
| **Translations** | Inline conditionals (if/else) | Simple, zero deps, only 7 string pairs (too few for abstraction) |
| **Truncation** | 45 PRs total (across all categories) | Stays under 50-block limit, flexible distribution |
| **Testing** | Pytest with mocked HTTP, real Block Kit JSON validation | Fast, existing infra, validates real structure |
| **Language Config** | LANGUAGE env var (en/ko) | Simple, validated at startup, default to 'en' |
| **Korean Expressions** | Keep current tone with direct translations | Matches existing English style, workplace-appropriate |

### Research Artifacts

- ✅ [research.md](research.md): Block Kit capabilities, Korean UX patterns, truncation strategy
- ✅ [data-model.md](data-model.md): Enhanced SlackClient class structure, Block Kit JSON format
- ✅ [quickstart.md](quickstart.md): Step-by-step implementation guide with code examples
- ✅ [contracts/](contracts/): Block Kit payload examples, translation strings, API interfaces

---

## Phase 1: Design Artifacts (COMPLETED)

### A. Data Model ([data-model.md](data-model.md))

**Enhanced SlackClient Class**:
- Add `language` attribute (`str`, values: 'en' or 'ko', default: 'en')
- Add `MAX_PRS_TOTAL` constant (45)
- Add Block Kit builder methods:
  - `_build_blocks(categorized_prs)` → list of all blocks
  - `_build_category_blocks(category, prs)` → blocks for one category
  - `_build_header_block(category)` → header block (language-aware)
  - `_build_pr_section(pr)` → section block for PR (language-aware)
  - `_build_truncation_warning(count)` → context block (language-aware)
  - `_escape_mrkdwn(text)` → escape special characters

**No New Models**: Existing `PullRequest`, `TeamMember` models used as-is.

### B. API Contract ([contracts/](contracts/))

**Slack Block Kit Message Structure**:
```json
{
  "blocks": [
    {"type": "header", "text": {"type": "plain_text", "text": "🤢 Rotten PRs"}},
    {"type": "section", "text": {"type": "mrkdwn", "text": "PR details..."}},
    {"type": "context", "elements": [{"type": "mrkdwn", "text": "metadata"}]},
    {"type": "divider"}
  ]
}
```

**Translation Strings (7 pairs)**:
1. Category headers: Rotten, Aging, Fresh (3 pairs)
2. Age format: "{days} days old" / "{days}일 묵음"
3. Review count: "{count} reviews pending" / "리뷰 {count}개 대기중"
4. Truncation: "+{count} more PRs" / "+{count}개 더 있음"

### C. Implementation Quickstart ([quickstart.md](quickstart.md))

**12-step implementation guide** with:
- Code examples for each method
- Test cases (unit + integration)
- Manual verification checklist
- Common pitfalls and solutions
- Estimated timeline: 3-5 hours

---

## Implementation Approach

### Phase P1: Block Kit Formatting (User Story 1)

**Tasks**:
1. Add `_escape_mrkdwn()` helper function
2. Implement `_build_header_block()` with language support
3. Implement `_build_pr_section()` with mrkdwn formatting
4. Implement `_build_truncation_warning()` with language support
5. Implement `_build_category_blocks()` with 15 PR limit
6. Implement `_build_blocks()` to assemble all categories
7. Add `post_stale_pr_summary()` public method
8. Write unit tests for all builders
9. Write integration test for full message assembly
10. Manual verification in Slack workspace

**Success Criteria**:
- ✅ SC-001: Category identification within 2 seconds (header blocks + dividers)
- ✅ SC-002: Renders correctly on desktop and mobile (Block Kit guarantees)
- ✅ SC-006: 100% information preservation (context blocks maintain metadata)
- ✅ SC-007: Immediate action identification (section + context structure)

### Phase P2: Korean Translation (User Story 2)

**Tasks**:
1. Add `LANGUAGE` validation to `config.py`
2. Add `language` parameter to `SlackClient.__init__()`
3. Add inline conditionals for Korean strings in builder methods
4. Update app.py to pass language to SlackClient
5. Write tests for Korean text validation
6. Test UTF-8 encoding with mixed Korean/English
7. Manual verification of Korean messages in Slack

**Korean String Examples** (keeping current tone):
- "🤢 Rotten PRs" → "🤢 PR 부패 중..."
- "🧀 Aging PRs" → "🧀 PR 숙성 중..."
- "✨ Fresh PRs" → "✨ 갓 태어난 PR"
- "X days old" → "X일 경과" (X days passed)
- "X reviews pending" → "리뷰 X개 대기중" (X reviews waiting)

**Success Criteria**:
- ✅ SC-003: Korean speakers report improved comprehension (UAT)
- ✅ FR-016: Uses 요/습니다 formality level
- ✅ FR-018: Arabic numerals + Korean text ("8일", "5개")

### Phase P3: Configuration (User Story 3)

**Tasks**:
1. Document `LANGUAGE` variable in `.env.example`
2. Update README with language configuration (optional)
3. Test invalid language codes (should default to 'en')

**Success Criteria**:
- ✅ FR-010: Read from LANGUAGE env var
- ✅ FR-011: Default to 'en' if missing/invalid

---

## Complexity Tracking

> No violations - this section empty per constitution guidelines

**No complexity violations identified**. All design decisions align with "Simplicity First" principle:
- No unnecessary abstractions (inline conditionals over translation system)
- No new frameworks or libraries
- Enhances existing code only
- Stateless, no new storage requirements

---

## Post-Design Constitution Re-Check ✅ PASS

**After Phase 1 design, re-verified**:
- ✅ No new abstractions beyond formatting functions
- ✅ Scope remains within single iteration (3-5 hours estimated)
- ✅ All user stories testable with real Block Kit JSON validation
- ✅ Design maintains simplicity (JSON serialization, inline conditionals)
- ✅ No framework dependencies added
- ✅ TDD approach planned (tests alongside implementation)

**Constitution compliance maintained throughout planning**.

---

## Success Metrics

**Immediate Validation** (testable in development):
- ✅ SC-001: Category identification within 2 seconds → Header blocks + dividers achieve this
- ✅ SC-002: Renders correctly on desktop and mobile → Block Kit guarantees this
- ✅ SC-004: Generation time ≤ 200ms increase → Estimated 30-80ms, well under budget
- ✅ SC-006: 100% information preservation → Context blocks maintain all metadata
- ✅ SC-007: Immediate action identification → Section + Context blocks create scannability

**Post-Deployment Validation** (requires production usage):
- SC-003: Korean speakers report improved comprehension → User feedback required
- SC-005: Zero Slack API errors from Block Kit → Monitor error logs
- SC-008: 50+ PRs handled gracefully → Truncation testing required

---

## Risks & Mitigations

**HIGH - Webhook Block Kit compatibility**:
- **Risk**: Documentation doesn't guarantee all Block Kit features work with webhooks
- **Mitigation**: Test early with real webhook; use only proven components (header/section/divider/context)
- **Validation**: Send test message in first sprint, verify rendering

**MEDIUM - Message size limits**:
- **Risk**: Block Kit JSON more verbose than plain text; may hit 40k char limit sooner
- **Mitigation**: Implement truncation logic (45 PRs total across all categories); test with 50+ PRs
- **Validation**: Log message sizes in development, test truncation triggers

**MEDIUM - Korean character encoding**:
- **Risk**: Korean characters (Hangul) in JSON may cause encoding issues
- **Mitigation**: Ensure UTF-8 throughout; test with mixed Korean/English content
- **Validation**: Create test cases with Korean strings in all fields

**LOW - Emoji rendering**:
- **Risk**: Emoji may render differently across Slack clients
- **Mitigation**: Use standard emoji (🤢/🧀/✨); always pair with text (accessibility)
- **Validation**: Test on desktop and mobile Slack apps

---

## Next Steps

1. **Ready for implementation**: All planning artifacts complete
2. **Run `/speckit.tasks`**: Generate task list from this plan
3. **Implement using TDD**: Write tests → Verify fail → Implement → Pass
4. **Test with real Slack webhook**: Use test channel for verification
5. **Korean UAT**: Gather informal feedback from Korean team members
6. **Deploy**: No special deployment steps (environment variable only)

---

## References

- [Feature Specification](spec.md): User stories, requirements, success criteria
- [Research Findings](research.md): Block Kit investigation, Korean UX patterns
- [Data Model](data-model.md): Enhanced SlackClient structure
- [Implementation Guide](quickstart.md): Step-by-step with code examples
- [Contracts](contracts/): Block Kit payload examples, translation strings

**Planning phase complete. Ready to proceed to task generation (`/speckit.tasks`).**
