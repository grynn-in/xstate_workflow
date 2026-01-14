# Code Review Prompt for XState Workflow

Use this prompt when requesting a code review from an AI assistant or providing context to human reviewers.

---

## Prompt

```
You are reviewing a Frappe Framework application called "xstate_workflow" - an XState-based workflow engine with visual builder and approval system.

## Project Overview

This is a workflow/state machine engine that:
1. Allows users to define workflows using XState JSON configuration
2. Provides a visual React-based workflow builder
3. Attaches workflows to Frappe DocTypes
4. Manages workflow instances (runtime state) for documents
5. Includes a full approval task system with assignment, escalation, and delegation

## Tech Stack

- **Backend**: Python 3.10+, Frappe Framework
- **Frontend**: React 18, TypeScript, ReactFlow, Vite
- **State Machine**: XState v5 concepts (not direct dependency)
- **Database**: MariaDB (via Frappe ORM)

## Key Files to Review

### Backend (Python)

1. **`xstate_workflow/workflow_engine.py`** - Core workflow engine
   - State machine execution logic
   - Event triggering (sync/async)
   - Guard and action evaluation
   - Instance management
   - API endpoints

2. **`xstate_workflow/xstate_workflow/doctype/state_machine/state_machine.py`** - State Machine DocType
   - Workflow definition model
   - Validation logic

3. **`xstate_workflow/xstate_workflow/doctype/machine_instance/machine_instance.py`** - Machine Instance DocType
   - Runtime state persistence
   - Permission queries

4. **`xstate_workflow/xstate_workflow/doctype/approval_task/approval_task.py`** - Approval Task DocType
   - Task assignment logic
   - Claiming, completion, escalation
   - Permission handling

5. **`xstate_workflow/resolvers.py`** - Assignment resolvers
   - Pluggable resolver system
   - Built-in resolvers (static_user, document_field, hierarchy_walk, etc.)

6. **`xstate_workflow/hooks.py`** - Frappe hooks
   - Document event handlers
   - Boot session data

### Frontend (TypeScript/React)

1. **`frontend/packages/core/src/`** - Core builder components
   - `components/` - React components (nodes, edges, panels)
   - `converters/` - XState ↔ Workflow conversion
   - `store/` - State management

2. **`frontend/packages/frappe-adapter/src/`** - Frappe API integration
   - API client
   - Type definitions

3. **`frontend/packages/desk-widget/src/`** - Desk form integration

### Tests

- `xstate_workflow/tests/test_workflow_engine.py`
- `xstate_workflow/tests/test_approval_system.py`
- `xstate_workflow/tests/test_guards_actions.py`

## Review Focus Areas

Please review the following aspects:

### 1. Security
- [ ] SQL injection vulnerabilities (especially in dynamic queries)
- [ ] Permission bypass possibilities
- [ ] XSS in frontend components
- [ ] Unsafe eval/exec usage in Python guards/actions
- [ ] CSRF protection on API endpoints
- [ ] Input validation and sanitization

### 2. Code Quality
- [ ] Code organization and separation of concerns
- [ ] Error handling and edge cases
- [ ] Logging and debugging support
- [ ] Code duplication
- [ ] Naming conventions and readability
- [ ] Type safety (Python type hints, TypeScript types)

### 3. Performance
- [ ] Database query efficiency (N+1 queries, missing indexes)
- [ ] Caching strategy
- [ ] Memory usage in long-running operations
- [ ] Frontend bundle size and lazy loading
- [ ] Async operation handling

### 4. Frappe Best Practices
- [ ] Proper use of Frappe ORM
- [ ] DocType design and field types
- [ ] Permission system integration
- [ ] Hook implementation patterns
- [ ] Whitelisted method security

### 5. State Machine Logic
- [ ] Correct XState semantics implementation
- [ ] Parallel state handling
- [ ] History state restoration
- [ ] Guard evaluation order
- [ ] Action execution timing
- [ ] Delayed transition scheduling

### 6. Approval System
- [ ] Task assignment logic correctness
- [ ] Role-based claiming race conditions
- [ ] Escalation chain handling
- [ ] Delegation rule application
- [ ] SLA and overdue detection

### 7. Frontend Architecture
- [ ] Component composition and reusability
- [ ] State management patterns
- [ ] API error handling
- [ ] Accessibility (a11y)
- [ ] Responsive design

### 8. Testing
- [ ] Test coverage adequacy
- [ ] Edge case testing
- [ ] Integration test completeness
- [ ] Mock usage appropriateness

## Specific Questions

1. Are there any security vulnerabilities in the Python guard/action execution?
2. Is the permission model robust enough for enterprise use?
3. Are there race conditions in the approval task claiming mechanism?
4. Is the XState-to-workflow conversion bidirectional and lossless?
5. Are database transactions handled correctly for state transitions?
6. Is the delayed transition cron job reliable and idempotent?

## Output Format

Please provide:
1. **Critical Issues** - Security vulnerabilities, data loss risks
2. **Major Issues** - Bugs, logic errors, performance problems
3. **Minor Issues** - Code style, best practices, minor improvements
4. **Suggestions** - Architecture improvements, feature ideas
5. **Questions** - Clarifications needed about design decisions

For each issue, include:
- File path and line number (if applicable)
- Description of the issue
- Suggested fix or approach
- Severity rating (Critical/Major/Minor)
```

---

## Quick Review Checklist

For faster reviews, use this checklist:

### Security Checklist
- [ ] No raw SQL queries with user input
- [ ] All API endpoints check permissions
- [ ] Guard/action code is sandboxed appropriately
- [ ] No sensitive data in client-side code
- [ ] CSRF tokens on state-changing operations

### Frappe Checklist
- [ ] DocTypes have proper permissions configured
- [ ] Whitelisted methods validate input
- [ ] Hooks don't cause infinite loops
- [ ] Database operations use Frappe ORM
- [ ] Cache invalidation is correct

### Frontend Checklist
- [ ] No hardcoded credentials or URLs
- [ ] Error boundaries in place
- [ ] Loading states handled
- [ ] API errors shown to users
- [ ] No console.log in production code

### Testing Checklist
- [ ] Happy path tests exist
- [ ] Error cases are tested
- [ ] Permission tests exist
- [ ] Concurrent operation tests exist

---

## Repository Structure Reference

```
xstate_workflow/
├── xstate_workflow/
│   ├── doctype/
│   │   ├── state_machine/
│   │   ├── machine_instance/
│   │   ├── approval_task/
│   │   └── user_delegation/
│   ├── tests/
│   └── public/
├── workflow_engine.py
├── resolvers.py
├── hooks.py
└── frontend/
    ├── packages/
    │   ├── core/
    │   ├── frappe-adapter/
    │   └── desk-widget/
    └── apps/
        └── standalone/
```
