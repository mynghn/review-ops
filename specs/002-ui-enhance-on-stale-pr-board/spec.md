# Feature Specification: Enhanced Stale PR Board UI with Korean Language Support

**Feature Branch**: `002-ui-enhance-on-stale-pr-board`
**Created**: 2025-10-31
**Status**: Draft
**Input**: User description: "[Feature name: ui-enhance-on-stale-pr-board] Let's enhance final report UI (slack message) of the stale PR board aesthetically interesting. Since my team use Korean as first language, we'll add Korean representation this time. I want witty expressions and bold and pop appearance so that it intrigues following actions of my teammates. Use Slack's block kit components fluently."

## Clarifications

### Session 2025-10-31

- Q: How should the new Block Kit formatting and Korean translation features be monitored or debugged in production? → A: No additional logging - rely on existing system logs only
- Q: What should happen if Block Kit messages exceed Slack's message size limits when many PRs exist? → A: Truncate with warning message - show first N PRs that fit, add "X more PRs not shown" notice
- Q: Where and how should the language configuration be stored and accessed? → A: Environment variable (e.g., LANGUAGE=ko) set before script execution
- Q: How should numbers and dates be formatted in Korean translations (e.g., "8 days old")? → A: Arabic numerals (1, 2, 3) with Korean text (e.g., "8일 전", "5개의 PR")
- Q: What should happen if the Slack webhook call fails (network error, invalid URL, service down)? → A: Log error and exit with failure status (non-zero exit code)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visual Enhancement with Block Kit (Priority: P1)

Team members receive stale PR reports in Slack that use rich visual formatting with Block Kit components, making the information easier to scan and more engaging than plain text messages.

**Why this priority**: This is the core value proposition - transforming the existing plain text report into a visually appealing, easy-to-read format. Block Kit provides structure, hierarchy, and visual polish that encourages action. Without this, the feature delivers no value.

**Independent Test**: Can be fully tested by configuring the system to send Block Kit formatted messages and verifying that recipients see properly formatted sections, dividers, emphasis, and styling. Delivers immediate value through improved readability and visual appeal.

**Acceptance Scenarios**:

1. **Given** the stale PR board system has PRs in all categories (Rotten, Aging, Fresh), **When** the report is generated and sent to Slack, **Then** the message uses Block Kit components including sections, dividers, and rich text formatting
2. **Given** a stale PR report is sent to Slack, **When** team members view the message, **Then** they see visually distinct categories with proper hierarchy, bold/prominent headings, and clear visual separation between sections
3. **Given** the report contains multiple PRs in each category, **When** rendered in Slack, **Then** each PR displays with structured formatting including clickable links, author/reviewer information laid out clearly, and visual status indicators
4. **Given** a PR has multiple reviewers and detailed status information, **When** displayed in the Block Kit message, **Then** the information is organized in a scannable format with proper use of context blocks, mrkdwn formatting, and visual grouping
5. **Given** the report is empty (no stale PRs), **When** sent to Slack, **Then** the Block Kit message displays a friendly, visually appealing "all clear" message

---

### User Story 2 - Korean Language Support (Priority: P2)

Korean-speaking team members receive stale PR reports in Korean with witty, engaging expressions that make the notifications more culturally relevant and attention-grabbing.

**Why this priority**: Provides significant value for Korean-speaking teams by making reports more accessible and engaging in their native language. Secondary to Block Kit enhancement because visual improvement benefits all users regardless of language.

**Independent Test**: Can be fully tested by configuring language preference to Korean and verifying that all message text appears in Korean with appropriate witty expressions and tone. Delivers value through improved comprehension and cultural relevance for Korean speakers.

**Acceptance Scenarios**:

1. **Given** the system is configured for Korean language, **When** a stale PR report is generated, **Then** all text content appears in Korean including category headers, status labels, and explanatory text
2. **Given** a Korean language report is sent, **When** team members read it, **Then** the expressions are witty and engaging (not literal translations), using workplace-appropriate humor and culturally familiar phrases
3. **Given** the report contains PR information in Korean, **When** displayed, **Then** technical terms (PR, GitHub, repository names, usernames) remain in English while surrounding text is Korean
4. **Given** status messages for different staleness levels, **When** rendered in Korean, **Then** each level uses distinct, memorable expressions that convey urgency appropriately (e.g., Rotten = more urgent/witty, Fresh = encouraging/positive)
5. **Given** an error occurs or the report is empty, **When** displayed in Korean, **Then** the message uses friendly, culturally appropriate phrasing

---

### User Story 3 - Language Configuration (Priority: P3)

Teams can configure their preferred language (English or Korean) for stale PR reports, with English remaining the default to maintain backward compatibility.

**Why this priority**: Enables the Korean language feature to be optional and maintains existing English functionality. Lower priority because it's a simple configuration change with clear implementation path.

**Independent Test**: Can be fully tested by setting language configuration to different values and verifying the system sends reports in the correct language. Delivers value through flexibility and user choice.

**Acceptance Scenarios**:

1. **Given** no LANGUAGE environment variable is set, **When** a report is generated, **Then** the system defaults to English language output
2. **Given** LANGUAGE=ko environment variable is set, **When** a report is generated, **Then** all message content appears in Korean
3. **Given** LANGUAGE=en environment variable is set, **When** a report is generated, **Then** all message content appears in English
4. **Given** an invalid language code is set in LANGUAGE environment variable, **When** the system starts, **Then** it logs a warning and defaults to English
5. **Given** the LANGUAGE environment variable is changed between executions, **When** the next report is generated, **Then** it uses the new language setting

---

### Edge Cases

- What happens when a PR title or description contains characters that need escaping in Block Kit mrkdwn format (asterisks, underscores, tildes)?
- How does the system handle extremely long PR titles that might break Block Kit layout or exceed text limits?
- What happens when there are zero PRs in one or more categories (e.g., no Rotten PRs but several Fresh ones)?
- **Korean number/date formatting**: Numbers and dates in Korean messages use Arabic numerals with Korean text (e.g., "8일 전" for "8 days ago", "5개의 PR" for "5 PRs")
- **Message size limit exceeded**: If the Block Kit message exceeds Slack's size limits, the system truncates the PR list to fit within limits and appends a warning notice (e.g., "5 more PRs not shown due to message size limits")
- **Slack webhook failure**: If the webhook call fails (network error, invalid URL, Slack service unavailable), the system logs the error and exits with non-zero status code
- How does the system handle emoji rendering in both English and Korean contexts?
- What happens when GitHub usernames contain special characters or Korean characters?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate Slack messages using Block Kit format instead of plain text
- **FR-002**: Messages MUST include proper visual hierarchy with distinct sections, visual separators, prominent headings, and supporting context
- **FR-003**: System MUST use rich text formatting (bold, italic, inline code, clickable links) to emphasize important information (PR age, review count, status indicators) and maintain readability with clickable PR titles
- **FR-004**: System MUST display PR categories (Rotten, Aging, Fresh) as visually distinct sections with clear headings
- **FR-005**: System MUST render PR links as clickable elements within the message structure
- **FR-006**: System MUST maintain existing functionality for user mentions (Slack user IDs when available, otherwise usernames)
- **FR-007**: System MUST support Korean language as a complete translation layer separate from English implementation
- **FR-008**: Korean translations MUST use witty, engaging expressions that are culturally appropriate for workplace communication
- **FR-009**: System MUST preserve technical terms (GitHub, repository names, usernames, PR numbers) in English even in Korean messages
- **FR-010**: System MUST read language preference from LANGUAGE environment variable (values: "en" or "ko")
- **FR-011**: System MUST default to English when LANGUAGE environment variable is not set or contains invalid value
- **FR-012**: System MUST properly escape or handle special characters in PR titles and descriptions that could interfere with message formatting
- **FR-013**: System MUST handle empty categories gracefully (e.g., show "No rotten PRs" or equivalent)
- **FR-014**: System MUST maintain backward compatibility with existing webhook-based Slack integration
- **FR-015**: System MUST format "all clear" messages (no stale PRs) in an engaging, visually appealing way
- **FR-016**: Korean messages MUST use appropriate formality level (professional but friendly, using 요/습니다 form)
- **FR-017**: System MUST truncate PR list and append a warning notice (e.g., "X more PRs not shown") if the Block Kit message exceeds Slack's message size limits
- **FR-018**: Korean translations MUST format numbers and dates using Arabic numerals combined with Korean text (e.g., "8일 전" not "팔 일 전")
- **FR-019**: System MUST log webhook errors and exit with non-zero status code if Slack webhook delivery fails

### Key Entities

- **Enhanced Message Structure**: Represents the formatted Slack message with visual hierarchy, including header, content sections, visual separators, and contextual information displayed with appropriate emphasis

- **Translation Strings**: Collection of localizable text content organized by context (category headers, status labels, time expressions, witty phrases) with separate English and Korean versions; Korean translations use Arabic numerals for numbers and dates

- **Language Configuration**: LANGUAGE environment variable (values: "en" or "ko") that determines which language translation set to use when generating messages, with English as default

- **Formatted PR Display**: Structured representation of PR information for visual presentation, including formatted links, styled text for status, and organized metadata layout

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Team members can identify stale PR category (Rotten/Aging/Fresh) within 2 seconds of viewing the message (measured through visual hierarchy and distinct section headers)

- **SC-002**: The Block Kit formatted message displays correctly in Slack desktop and mobile clients without rendering errors or layout breaks

- **SC-003**: Korean-speaking team members report improved comprehension and engagement compared to English messages (measured through informal feedback or response rates)

- **SC-004**: Message generation time increases by no more than 200ms compared to plain text format (measured through execution time logging)

- **SC-005**: Zero Slack API errors related to Block Kit formatting issues occur during normal operation (measured through error logs and Slack webhook responses)

- **SC-006**: 100% of existing PR report information (PR links, authors, reviewers, status, age) is preserved and displayed in the new Block Kit format

- **SC-007**: Team members can identify PRs requiring their action within 3 seconds through visual emphasis (bold status indicators, emoji) and clear structure (dedicated context blocks per PR showing author/reviewer info)

- **SC-008**: Messages containing up to 45 stale PRs total (across all categories) render successfully; if size limits are exceeded, truncation occurs gracefully with clear warning notice to users

## Assumptions

- Slack workspace supports Block Kit (available in all modern Slack workspaces, minimum API version requirements are met)
- Current webhook integration remains the delivery mechanism (no migration to Slack app with OAuth required)
- Korean language support targets a single dialect (Standard Korean/Seoul dialect) rather than regional variations
- Team members using Korean language are familiar with common GitHub terminology in English (PR, merge, review, etc.)
- Existing Slack user ID mapping in team_members.json configuration remains valid for @mentions
- Visual "bold and pop appearance" refers to prominent use of formatting, emojis, and visual hierarchy, not custom colors or themes (which are limited in Block Kit)
- Witty expressions in Korean avoid slang or informal language inappropriate for professional workplace communication
- The system continues to run on-demand or on schedule, sending one message per execution (no message threading or updates)
- Plain text fallback for Slack clients that cannot render Block Kit is handled automatically by Slack (not system responsibility)
- Observability for Block Kit formatting and Korean translation relies on existing system logs without additional feature-specific logging infrastructure

## Dependencies

- Existing Slack webhook integration must remain functional
- Slack workspace must support Block Kit formatting for incoming messages
- System environment must support Unicode and Korean character encoding
- System execution environment must support reading environment variables (LANGUAGE)
- Existing PR and team member data must provide all necessary information for enhanced message rendering
- Team member configuration must maintain accurate Slack user ID mappings for mentions
