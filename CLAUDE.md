# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

XState Workflow is a state machine-based workflow engine for Frappe Framework. It provides:
- Visual React Flow-based workflow builder
- XState-compatible state machine execution
- Approval task system with assignment, escalation, and delegation
- Integration with any Frappe DocType

## Commands

### Backend Development

```bash
# Site name: xs.local (accessible at http://xs.local:8001)

# Run all Python tests
bench --site xs.local run-tests --app xstate_workflow

# Run specific test file
bench --site xs.local run-tests --app xstate_workflow --module xstate_workflow.tests.test_workflow_engine

# Run specific test class
bench --site xs.local run-tests --app xstate_workflow --module xstate_workflow.tests.test_workflow_engine --test TestWorkflowEngine

# Python linting
ruff check xstate_workflow/
ruff format xstate_workflow/

# Pre-commit (runs ruff, eslint, prettier)
pre-commit run --all-files
```

### Worker Configuration

XState Workflow uses dedicated queues for background job isolation:

- **`workflow`** queue: State transitions, service invocations, async actions
- **`long`** queue: Agentic node execution (LLM-based, longer timeouts)
- **`default`** queue: Everything else (Frappe standard)

The `workflow` queue is auto-registered in `site_config.json` on install and migrate.
To register manually (e.g., for common_site_config):

```bash
bench set-config -g -p workers '{"workflow": {"timeout": 300}}'
```

```bash
# Production: run dedicated workers per queue
bench worker --queue workflow
bench worker --queue long
bench worker --queue default

# Development: a single `bench worker` (no --queue) processes all queues
bench worker
```

### Frontend Development

```bash
cd frontend

# Install dependencies
pnpm install

# Development server (all packages in parallel)
pnpm dev

# Build all packages
pnpm build

# Build specific apps
pnpm build:standalone   # /xstate-builder page
pnpm build:desk         # Form widget

# Testing
pnpm test              # Run once
pnpm test:watch        # Watch mode
pnpm test:coverage     # With coverage

# Linting and type checking
pnpm lint
pnpm typecheck
```

## Architecture

### Backend Structure

```
xstate_workflow/
├── workflow_engine.py          # Core engine: event triggering, state transitions, guards/actions
├── hooks.py                    # Frappe integration: doc events, boot data, permissions
├── mermaid_generator.py        # State diagram generation
├── xstate_workflow/
│   ├── doctype/
│   │   ├── state_machine/      # Workflow definition (json_config, attached_doctype)
│   │   ├── machine_instance/   # Runtime state per document
│   │   ├── approval_task/      # Task assignment and completion
│   │   ├── xsm_guard/          # Inline Python guard conditions
│   │   └── xsm_action/         # Inline Python actions
│   ├── resolvers/              # Assignment resolvers (user, role, hierarchy, delegation)
│   ├── domain_nodes/           # Approval/auto-action node handlers
│   └── approval/               # Task manager (task_manager.py)
```

### Frontend Structure (pnpm monorepo)

```
frontend/
├── packages/
│   ├── core/                   # Shared components and converters
│   │   ├── components/         # React Flow nodes, edges, panels
│   │   ├── converters/         # XState <-> workflow format conversion
│   │   └── types/              # TypeScript definitions
│   └── frappe-adapter/         # Frappe API client
└── apps/
    ├── standalone/             # /xstate-builder full workflow editor
    └── desk-widget/            # Form-embedded workflow widget
```

### Key APIs

**Python:**
```python
from xstate_workflow.workflow_engine import (
    trigger_event_sync,    # Immediate state transition
    trigger_event,         # Background job transition
    get_machine_state,     # Current state + available events
)
```

**JavaScript:**
```javascript
frappe.xstate_workflow.trigger_event(doctype, docname, event)
frappe.xstate_workflow.get_state(doctype, docname)
```

### State Machine Flow

1. Event triggered (API or document event hook)
2. Permission check
3. Get/create Machine Instance for document
4. Load XState config from State Machine
5. Evaluate guards (inline Python or logic_module)
6. Execute actions
7. Persist new state to Machine Instance
8. Emit socket events for real-time UI updates

## Development Approach

**Always follow Test-Driven Development (TDD):**
1. Write failing tests first that describe the expected behavior
2. Implement the minimum code to make tests pass
3. Refactor while keeping tests green

For backend changes, write Python tests in `xstate_workflow/tests/`. For frontend changes, write tests alongside components using Vitest.

## Code Style

- **Python**: Ruff formatting with tabs (indent-style = "tab"), line-length 110
- **Frontend**: ESLint + Prettier, TypeScript strict mode
- **Guards/Actions**: Inline Python code stored in child tables, evaluated via `exec()`

## Key Patterns

### Adding Guards and Actions

Guards are defined in the State Machine's Guards child table with `name` and `code` fields. The code runs with `context`, `doc`, and `frappe` available:

```python
# Guard example - must return boolean
context['user_level'] > 5 and doc.status == 'Active'
```

Actions are similar but perform side effects:

```python
# Action example
context['approved_at'] = frappe.utils.now()
frappe.sendmail(recipients=[doc.owner], subject='Approved')
```

### Resolvers

Assignment resolvers determine who gets approval tasks. Built-in resolvers:
- `user_resolver`: Static user assignment
- `role_resolver`: Role-based assignment
- `linked_doc_resolver`: Field-based resolution
- `hierarchy_resolver`: Organizational hierarchy walk
- `delegation_resolver`: Delegation chain resolution

### Document Event Integration

Workflows auto-trigger on document events via hooks.py:
- `after_insert`: Initializes workflow instance
- `on_update`: Triggers configured events
- `before_submit`/`before_save`: Validates workflow state allows operation

### Agentic Node Configuration

Agentic (AI agent) nodes require LLM API keys to be configured in **XState Workflow Settings**:

1. Go to `/app/xstate-workflow-settings`
2. Set the **Anthropic API Key** (for Claude models) and/or **OpenAI API Key** (for GPT models)
3. Optionally set the **Default LLM Model**

Supported model aliases:
- `claude-sonnet` → Claude 3.5 Sonnet
- `claude-haiku` → Claude 3.5 Haiku
- `claude-opus` → Claude 3 Opus
- `gpt-4`, `gpt-4o`, `gpt-3.5-turbo` → OpenAI models
