# XState Workflow - Feature Documentation

A comprehensive XState-based workflow engine for Frappe Framework with visual builder, approval system, and advanced state machine capabilities.

---

## Table of Contents

1. [Core State Machine Engine](#1-core-state-machine-engine)
2. [API Endpoints](#2-api-endpoints)
3. [Frontend Workflow Builder](#3-frontend-workflow-builder)
4. [Frappe Integration](#4-frappe-integration)
5. [Permission & Authorization](#5-permission--authorization)
6. [Guards, Actions & Triggers](#6-guards-actions--triggers)
7. [Assignment Resolvers](#7-assignment-resolvers)
8. [Advanced State Machine Features](#8-advanced-state-machine-features)
9. [Approval System](#9-approval-system)
10. [Testing Infrastructure](#10-testing-infrastructure)
11. [Utilities & Extras](#11-utilities--extras)

---

## 1. Core State Machine Engine

### State Machine Definition (DocType: `State Machine`)

The core workflow definition stored as a Frappe DocType.

| Field | Type | Description |
|-------|------|-------------|
| `machine_id` | Data | Unique identifier for the workflow |
| `title` | Data | Human-readable name |
| `description` | Text | Workflow description |
| `version` | Int | Version number for tracking changes |
| `attached_to` | Link | DocType this workflow applies to |
| `is_active` | Check | Enable/disable the workflow |
| `auto_start_on_create` | Check | Auto-start when document is created |
| `edit_restriction_mode` | Select | Edit blocking mode during workflow |
| `json_config` | JSON | XState machine configuration |
| `workflow_builder_config` | JSON | Visual builder layout data |
| `logic_module` | Data | Optional Python module for custom logic |

**Edit Restriction Modes:**
- `None` - No restrictions
- `Assigned Only` - Only assigned user can edit
- `Role Only` - Only users with assigned role can edit
- `Assigned or Role` - Either assigned user or role members can edit

**Child Tables:**
- `guards` - Inline Python guard conditions
- `actions` - Inline Python actions

### Machine Instance (DocType: `Machine Instance`)

Runtime state for each document-workflow pair.

| Field | Type | Description |
|-------|------|-------------|
| `machine` | Link | Reference to State Machine |
| `reference_doctype` | Link | Document type being tracked |
| `reference_name` | Dynamic Link | Specific document name |
| `current_state` | Data | Current state in the workflow |
| `status` | Select | `idle`, `running`, `paused`, `completed` |
| `context` | JSON | Arbitrary state data |
| `transition_log` | JSON | Last 100 transitions with timestamps |
| `parallel_states` | JSON | State tracking for parallel regions |
| `history_states` | JSON | Stored history state values |
| `active_services` | JSON | Currently running services |
| `delayed_transitions` | JSON | Queued delayed transitions |
| `transition_count` | Int | Total transitions executed |
| `error_count` | Int | Total errors encountered |
| `is_auto_submitted` | Check | Whether doc was auto-submitted |

---

## 2. API Endpoints

All endpoints are whitelisted Frappe methods in `xstate_workflow.workflow_engine`.

### State Query APIs

```python
# Get current workflow state and available events
get_workflow_state(doctype: str, docname: str) -> dict

# Get state with full transition history
get_machine_state_with_history(doctype: str, docname: str) -> dict

# Batch query for multiple documents
bulk_get_workflow_states(doc_refs: list[dict]) -> list[dict]

# Get transition history
get_workflow_history(doctype: str, docname: str, limit: int = 50) -> list
get_transition_history(doctype: str, docname: str, limit: int = 50) -> list
```

### Workflow Management APIs

```python
# List workflows for a DocType
list_workflows(attached_to: str = None) -> list[dict]

# Get workflow configuration
get_workflow_definition(machine_id: str) -> dict

# Save/update workflow definition
save_workflow_definition(
    machine_id: str,
    title: str,
    json_config: dict,
    workflow_builder_config: dict = None,
    attached_to: str = None,
    is_active: bool = True,
    auto_start_on_create: bool = True,
    edit_restriction_mode: str = "None"
) -> dict
```

### Event & Transition APIs

```python
# Trigger event asynchronously (via job queue)
trigger_event(doctype: str, docname: str, event: str, data: dict = None) -> dict

# Trigger event synchronously (immediate execution)
trigger_event_sync(doctype: str, docname: str, event: str, data: dict = None) -> dict

# Start workflow manually (when auto_start disabled)
start_workflow(doctype: str, docname: str) -> dict

# Reset workflow to initial state
reset_workflow(doctype: str, docname: str) -> dict
```

### Configuration APIs

```python
# Get DocType fields for guard builder
get_doctype_fields(doctype: str) -> list[dict]

# Get available roles
get_roles() -> list[str]
```

### Internal APIs (Non-Whitelisted)

These functions are used internally by hooks and system operations. They skip permission checks because the calling code has already validated permissions.

```python
# Internal async event trigger - used by hooks
# Does NOT perform permission check
_trigger_event_internal(doctype: str, docname: str, event: str, data: str = None) -> dict

# Internal sync event trigger - used by hooks
# Does NOT perform permission check
_trigger_event_sync_internal(doctype: str, docname: str, event: str, data: str = None) -> dict
```

**Why Internal Functions Exist**: When `check_and_trigger()` is called from a document hook (e.g., `on_update`), the regular `trigger_event_sync()` would fail with a permission error because the document save transaction is still in progress. The internal versions bypass this check since the hook execution context already implies the user has permission to modify the document.

---

## 3. Frontend Workflow Builder

### Architecture

```
frontend/
├── packages/
│   ├── core/           # React Flow visual builder
│   ├── frappe-adapter/ # Frappe API bindings
│   ├── desk-widget/    # Desk form integration
│   └── standalone/     # Standalone builder app
├── apps/
│   └── standalone/     # Standalone entry point
```

**Tech Stack:**
- React 18 + TypeScript
- Vite build system
- ReactFlow for visual editing
- Vitest for testing

### Node Types

| Node Type | Description |
|-----------|-------------|
| `atomic` | Simple leaf state |
| `compound` | Contains child states |
| `parallel` | Concurrent state regions |
| `history` | Shallow/deep history state |
| `final` | Terminal state |

**Domain-Specific Nodes:**

| Node Type | Description |
|-----------|-------------|
| `start` | Workflow entry point |
| `end` | Workflow exit point |
| `approval` | Creates approval task, waits for decision |
| `auto_action` | Auto-executes actions (submit, update, etc.) |
| `threshold_gate` | Conditional branch based on value |
| `classification_branch` | Route based on field value |

### Visual Guard Builder

**Simple Guard Structure:**
```json
{
  "type": "simple",
  "field": "status",
  "operator": "eq",
  "value": "Pending"
}
```

**Supported Operators:**
| Operator | Description |
|----------|-------------|
| `eq` | Equals |
| `ne` | Not equals |
| `gt` | Greater than |
| `lt` | Less than |
| `gte` | Greater than or equal |
| `lte` | Less than or equal |
| `in` | Value in list |
| `contains` | String contains |
| `is_set` | Field has value |
| `is_not_set` | Field is empty |

**Compound Guard Structure:**
```json
{
  "type": "compound",
  "operator": "and",
  "conditions": [
    { "type": "simple", "field": "amount", "operator": "gt", "value": 1000 },
    { "type": "simple", "field": "status", "operator": "eq", "value": "Draft" }
  ]
}
```

### Converters

```typescript
// Convert visual workflow to XState JSON
workflowToXState(workflowConfig: WorkflowConfig): XStateConfig

// Convert XState JSON to visual workflow
// Optional existingLayout parameter preserves node positions
xstateToWorkflow(
  xstateConfig: XStateConfig,
  existingLayout?: WorkflowBuilderConfig
): WorkflowConfig
```

**Position Matching**: When loading saved workflows, positions are matched by:
1. `node.id` (state name) - primary match
2. `node.data.label` - backwards compatibility fallback

This ensures node positions are preserved when re-opening saved workflows, even if the visual config was saved with different node ID formats.

---

## 4. Frappe Integration

### Document Hooks

```python
# xstate_workflow/hooks.py
doc_events = {
    "*": {
        "before_save": "xstate_workflow.workflow_engine.validate_workflow_state_for_save",
        "on_update": "xstate_workflow.workflow_engine.check_and_trigger",
        "after_insert": "xstate_workflow.workflow_engine.check_and_trigger",
        "before_submit": "xstate_workflow.workflow_engine.validate_workflow_state_for_submit"
    }
}
```

| Hook | Function | Description |
|------|----------|-------------|
| `before_save` | `validate_workflow_state_for_save` | Enforces edit restrictions based on task assignment |
| `on_update` | `check_and_trigger` | Auto-triggers workflow events on document changes |
| `after_insert` | `check_and_trigger` | Auto-starts workflow on document creation |
| `before_submit` | `validate_workflow_state_for_submit` | Validates workflow allows submission |

### Boot Session Data

Added to `frappe.boot` on login:
- `active_workflows` - List of active workflow definitions
- `pending_approvals_count` - User's pending approval tasks
- `workflow_permissions` - User's workflow permissions
- `workflow_attached_doctypes` - DocTypes with workflows

### Jinja Template Helpers

```python
# Available in Jinja templates
get_workflow_state(doctype, docname)      # Current state info
get_workflow_buttons(doctype, docname)    # Render action buttons
get_workflow_history(doctype, docname, limit=10)  # Transition history
has_workflow(doctype)                     # Check if workflow exists
```

### Website Routes

| Route | Description |
|-------|-------------|
| `/xstate-builder` | Create new workflow |
| `/xstate-builder/<machine_id>` | Edit existing workflow |
| `/xstate-viewer` | View workflow list |
| `/xstate-viewer/<machine_id>` | View specific workflow |
| `/my-approvals` | User approval dashboard |

---

## 5. Permission & Authorization

### Role-Based Access Control

**Roles:**
- `System Manager` - Full access to all workflows and instances
- `Workflow Manager` - Manage workflow definitions and instances
- Standard roles - Access based on assignment

**Permission Query:**
```python
def get_permission_query_conditions(user):
    # Filters Machine Instances to only those user can access
    # Based on direct assignment or role membership
```

### Edit Restrictions

When a document is in an active workflow, edits can be restricted based on task assignment. This feature prevents unauthorized modifications during approval processes.

#### Configuration

Set `edit_restriction_mode` on the State Machine DocType:

| Mode | Behavior |
|------|----------|
| `None` | No restrictions (default) |
| `Assigned Only` | Only the directly assigned user can edit |
| `Role Only` | Only users with the assigned role can edit |
| `Assigned or Role` | Either assigned user or role members can edit |

#### How It Works

1. **Before Save Hook**: `validate_workflow_state_for_save()` checks permissions
2. **API Response**: `get_machine_state()` returns `can_user_edit` and `current_task` info
3. **Frontend**: Form is disabled for unauthorized users with informative message

#### Permission Check Logic

```python
# Restrictions apply when ALL conditions are met:
# 1. edit_restriction_mode is NOT "None"
# 2. Workflow instance exists for the document
# 3. Workflow status is NOT "idle" or "final"
# 4. A pending Approval Task exists

# User is allowed to edit if:
# - Mode is "Assigned Only" and user == task.assigned_to
# - Mode is "Role Only" and task.assigned_role in user's roles
# - Mode is "Assigned or Role" and either condition above is true
# - User has "System Manager" role (always allowed)
```

#### API Response Fields

`get_machine_state()` now returns additional fields:

```python
{
    # ... existing fields ...
    "edit_restriction_mode": "Assigned Only",  # Current restriction mode
    "can_user_edit": True,                      # Whether current user can edit
    "current_task": {                           # Current pending task info
        "name": "TASK-00001",
        "assigned_to": "user@example.com",
        "assigned_role": "Accounts Manager"
    }
}
```

#### Frontend Behavior

When `can_user_edit` is `False`:
- Form fields are disabled via `frm.disable_form()`
- Info message displayed: "This document is in workflow approval. Only the assigned approver can edit."
- Assignee info shown if available

#### Bypassing Restrictions

For system operations, set the flag before save:
```python
doc.flags.ignore_workflow_edit_check = True
doc.save()
```

#### Edge Cases

| Scenario | Behavior |
|----------|----------|
| New document (`__islocal`) | No restrictions |
| No workflow instance | No restrictions |
| Workflow status = `idle` | No restrictions |
| Workflow status = `final` | No restrictions |
| No pending Approval Task | No restrictions |
| System Manager user | Always allowed |

### Delegation System

**User Delegation DocType:**

| Field | Description |
|-------|-------------|
| `delegator` | User delegating tasks |
| `delegate` | User receiving delegation |
| `from_date` | Delegation start date |
| `to_date` | Delegation end date |
| `doctype` | Specific DocType (optional) |
| `workflow` | Specific workflow (optional) |

**Features:**
- Date-based delegation ranges
- Circular delegation prevention
- Specific DocType/workflow scoping

---

## 6. Guards, Actions & Triggers

### Guard Types

#### Simple Guards
```python
{
    "type": "simple",
    "field": "grand_total",
    "operator": "gt",
    "value": 10000
}
```

#### Compound Guards
```python
{
    "type": "compound",
    "operator": "and",  # or "or"
    "conditions": [...]
}
```

#### Python Guards
```python
# Stored in State Machine guards table
# Available variables: context, event, doc, frappe
def guard(context, event, doc, frappe):
    return doc.grand_total > 10000 and doc.owner != frappe.session.user
```

#### Role Guards
```python
{
    "type": "role",
    "roles": ["Purchase Manager", "Finance Manager"]
}
```

### Action Types

| Type | When Executed |
|------|---------------|
| `entry` | On entering a state |
| `exit` | On leaving a state |
| `transition` | During a transition |

#### Python Actions
```python
# Stored in State Machine actions table
# Available variables: context, event, doc, frappe, instance
def action(context, event, doc, frappe, instance):
    doc.status = "In Progress"
    doc.save()
```

**Action Configuration:**
- `is_async` - Run asynchronously
- `timeout` - Execution timeout (default 300s)
- `run_in_background` - Execute as background job

### Built-in Domain Actions

| Action | Description |
|--------|-------------|
| `create_approval_task` | Create approval task at approval node |
| `cancel_approval_tasks` | Cancel pending approval tasks |
| `submit_document` | Submit the document |
| `cancel_document` | Cancel the document |
| `update_field` | Update a document field |
| `update_status` | Update status field |
| `send_notification` | Send email notification |
| `call_api` | Call external HTTP API |
| `run_method` | Run a Frappe method |
| `resolve_assignment` | Resolve task assignee |

### Transition Types

#### Event Transitions
```json
{
  "on": {
    "APPROVE": { "target": "approved" },
    "REJECT": { "target": "rejected" }
  }
}
```

#### Delayed Transitions
```json
{
  "after": {
    "delay": "24h",
    "target": "escalated"
  }
}
```

**Delay Formats:**
- `500ms` - Milliseconds
- `30s` - Seconds
- `5m` - Minutes
- `2h` - Hours
- `1d` - Days

Delayed transitions are processed by cron job (`* * * * *`).

#### Always Transitions
```json
{
  "always": {
    "target": "next_state",
    "cond": "someGuard"
  }
}
```

---

## 7. Assignment Resolvers

Pluggable system for determining task assignees.

### Built-in Resolvers

#### Static User Resolver (`static_user`)
```json
{
  "type": "static_user",
  "user": "admin@example.com"
}
```

#### Document Field Resolver (`document_field`)
```json
{
  "type": "document_field",
  "field": "custom_approver",
  "fallback_field": "owner",
  "fallback_user": "admin@example.com"
}
```
Supports dot notation: `customer.account_manager`

#### Owner Resolver (`owner`)
```json
{
  "type": "owner",
  "fallback_user": "admin@example.com"
}
```

#### Linked Document Resolver (`linked_doc`)
```json
{
  "type": "linked_doc",
  "link_field": "customer",
  "target_field": "account_manager"
}
```

#### Role Resolver (`role`)
```json
{
  "type": "role",
  "role": "Purchase Manager"
}
```

#### Hierarchy Walk Resolver (`hierarchy_walk`)
```json
{
  "type": "hierarchy_walk",
  "doctype": "Employee",
  "start_field": "employee",
  "parent_field": "reports_to",
  "user_field": "user_id",
  "levels": 2,
  "stop_condition": {
    "type": "role",
    "role": "Department Head"
  }
}
```

#### Delegation Resolver (`delegation`)
```json
{
  "type": "delegation",
  "base_resolver": {
    "type": "document_field",
    "field": "approver"
  }
}
```

### Custom Resolvers

```python
# Register custom resolver
from xstate_workflow.resolvers import register_resolver

@register_resolver("custom_resolver")
def resolve_custom(doc, config, context):
    # Custom logic
    return "user@example.com"
```

---

## 8. Advanced State Machine Features

### Parallel States

Execute multiple state regions concurrently.

```json
{
  "type": "parallel",
  "states": {
    "payment": {
      "initial": "pending",
      "states": {
        "pending": {},
        "received": { "type": "final" }
      }
    },
    "shipping": {
      "initial": "pending",
      "states": {
        "pending": {},
        "shipped": { "type": "final" }
      }
    }
  },
  "onDone": "completed"
}
```

### History States

Remember and restore previous state.

```json
{
  "states": {
    "editing": {
      "initial": "draft",
      "states": {
        "draft": {},
        "review": {},
        "hist": { "type": "history", "history": "deep" }
      }
    },
    "paused": {
      "on": {
        "RESUME": { "target": "editing.hist" }
      }
    }
  }
}
```

- `shallow` - Remember direct child state
- `deep` - Remember deepest nested state

### Services & Invoked Actors

```json
{
  "invoke": {
    "src": "fetchData",
    "onDone": { "target": "success" },
    "onError": { "target": "failure" }
  }
}
```

**Service Types:**
- HTTP service invocation
- Python callable invocation
- Background execution support

### Submission Control

**Block Submission:**
```python
# In before_submit hook
def validate_submit_allowed(doc, method):
    # Checks if workflow allows submission
    # Raises if document cannot be submitted yet
```

**Auto-Submit:**
Configure final states to auto-submit the document:
```json
{
  "approved": {
    "type": "final",
    "meta": {
      "autoSubmit": true
    }
  }
}
```

### Document Auto-Triggering

Workflows can auto-start based on document events:

```python
# Configuration in State Machine
{
  "auto_start_on_create": True,
  "triggers": [
    {
      "event": "on_update",
      "workflow_event": "UPDATE",
      "guard": {
        "type": "simple",
        "field": "status",
        "operator": "eq",
        "value": "Submitted"
      }
    }
  ]
}
```

---

## 9. Approval System

### Approval Task (DocType)

| Field | Type | Description |
|-------|------|-------------|
| `workflow_instance` | Link | Parent Machine Instance |
| `reference_doctype` | Link | Document type |
| `reference_name` | Dynamic Link | Document name |
| `assigned_to` | Link (User) | Direct assignee |
| `assigned_role` | Link (Role) | Role-based assignment |
| `original_assignee` | Link (User) | Original assignee before reassignment |
| `status` | Select | `Pending`, `In Progress`, `Completed`, `Escalated` |
| `priority` | Select | `Low`, `Medium`, `High`, `Urgent` |
| `available_actions` | Data | Comma-separated actions (e.g., "Approve,Reject") |
| `action_taken` | Data | Action that was taken |
| `comments` | Text | Completion comments |
| `due_date` | Datetime | Task due date |
| `sla_hours` | Float | SLA in hours |
| `completed_at` | Datetime | Completion timestamp |
| `completed_by` | Link (User) | Who completed the task |
| `escalation_level` | Int | Current escalation level |
| `escalated_from` | Link | Previous task if escalated |

### Task Assignment

**Direct Assignment:**
Task assigned to specific user.

**Role-Based Assignment:**
Task assigned to a role; any user with that role can claim it.

```python
# Claim a role-based task
claim_approval_task(task_name: str) -> dict
```

### Task Actions

```python
# Complete an approval task
complete_approval_task(
    task_name: str,
    action: str,           # "Approve", "Reject", etc.
    comments: str = None
) -> dict

# Reassign a task
reassign_approval_task(
    task_name: str,
    new_assignee: str,
    reason: str = None
) -> dict

# Escalate a task
escalate_approval_task(
    task_name: str,
    escalate_to: str = None,  # User or role
    reason: str = None
) -> dict
```

### Task Queries

```python
# Get tasks for current user
get_my_approval_tasks(
    status: str = "pending_with_me",
    doctype: str = None,
    limit: int = 20
) -> list[dict]
```

**Status Filters:**
| Status | Description |
|--------|-------------|
| `pending_with_me` | Direct + role assignments pending |
| `overdue_with_me` | Past due pending tasks |
| `completed_by_me` | Tasks completed by user |
| `escalated` | Escalated tasks |
| `in_progress_others` | Workflows user participated in, with others |

### Approval Dashboard

Route: `/my-approvals`

Features:
- List of pending approval tasks
- Filter by DocType, priority, status
- Task details modal
- Quick action buttons
- Real-time updates via WebSocket

---

## 10. Testing Infrastructure

### Test Files

| File | Coverage |
|------|----------|
| `test_workflow_engine.py` | Core engine, state management, transitions, guards, events |
| `test_approval_system.py` | Task creation, assignment, claiming, reassignment, escalation |
| `test_guards_actions.py` | Guard evaluation (simple, compound, Python), action execution |
| `test_workflow_auto_submit.py` | Auto-submission at final states |
| `test_workflow_edit_permissions.py` | Edit restriction modes |
| `test_mermaid_diagram.py` | Mermaid diagram export |

### Running Tests

```bash
# Run all workflow tests
bench --site [site] run-tests --app xstate_workflow

# Run specific test file
bench --site [site] run-tests --app xstate_workflow --module xstate_workflow.tests.test_workflow_engine

# Run frontend tests
cd frontend && npm test
```

---

## 11. Utilities & Extras

### Mermaid Diagram Generation

```python
from xstate_workflow.utils import generate_mermaid_diagram

diagram = generate_mermaid_diagram(machine_id)
# Returns Mermaid stateDiagram-v2 syntax
```

### Cache Management

Workflow states are cached for performance:
```python
# Cache key format
f"workflow_state:{doctype}:{docname}"

# Clear cache on transition
frappe.cache().delete_key(cache_key)
```

### Multi-Tenant Support

Approval tasks include `tenant` field for multi-tenant deployments.

### Bulk Operations

```python
# Get states for multiple documents
bulk_get_workflow_states([
    {"doctype": "Sales Order", "name": "SO-001"},
    {"doctype": "Sales Order", "name": "SO-002"}
])
```

### Error Handling

- Comprehensive error logging to Frappe error log
- Failed transitions recorded in `transition_log`
- `error_count` incremented on failures
- User-friendly validation messages

### Installation

```bash
# Install app
bench get-app https://github.com/[repo]/xstate_workflow
bench --site [site] install-app xstate_workflow

# Run migrations
bench --site [site] migrate
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  Workflow   │  │    Desk     │  │      Standalone         │ │
│  │   Builder   │  │   Widget    │  │        Builder          │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                      │               │
│         └────────────────┼──────────────────────┘               │
│                          │                                      │
│                    ┌─────┴─────┐                                │
│                    │  Frappe   │                                │
│                    │  Adapter  │                                │
│                    └─────┬─────┘                                │
└──────────────────────────┼──────────────────────────────────────┘
                           │ API Calls
┌──────────────────────────┼──────────────────────────────────────┐
│                     Backend                                      │
│                          │                                      │
│  ┌───────────────────────┴───────────────────────────────────┐ │
│  │                  Workflow Engine                           │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │ │
│  │  │   Guards    │  │   Actions   │  │    Resolvers    │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                          │                                      │
│  ┌───────────────────────┴───────────────────────────────────┐ │
│  │                    DocTypes                                │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │ │
│  │  │   State     │  │   Machine   │  │    Approval     │   │ │
│  │  │   Machine   │  │   Instance  │  │      Task       │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                          │                                      │
│  ┌───────────────────────┴───────────────────────────────────┐ │
│  │              Frappe Framework Integration                  │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │ │
│  │  │    Hooks    │  │   Jinja     │  │   Permissions   │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## License

MIT License - See LICENSE file for details.
