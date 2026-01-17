# XState Workflow Manual

A comprehensive guide to using XState Workflow for Frappe Framework.

---

## Table of Contents

- [Part 1: Getting Started](#part-1-getting-started)
  - [1.1 What is XState Workflow?](#11-what-is-xstate-workflow)
  - [1.2 Key Features](#12-key-features)
  - [1.3 Quick Start](#13-quick-start)
- [Part 2: Workflow Builder Guide](#part-2-workflow-builder-guide)
  - [2.1 Accessing the Builder](#21-accessing-the-builder)
  - [2.2 Node Types](#22-node-types)
  - [2.3 Transitions & Edges](#23-transitions--edges)
  - [2.4 Properties Panel](#24-properties-panel)
  - [2.5 Saving & Loading Workflows](#25-saving--loading-workflows)
- [Part 3: Core Concepts](#part-3-core-concepts)
  - [3.1 State Machine Fundamentals](#31-state-machine-fundamentals)
  - [3.2 Guards (Conditions)](#32-guards-conditions)
  - [3.3 Actions](#33-actions)
  - [3.4 Assignment Resolvers](#34-assignment-resolvers)
- [Part 4: Approval System](#part-4-approval-system)
  - [4.1 Approval Tasks](#41-approval-tasks)
  - [4.2 User Actions](#42-user-actions)
  - [4.3 My Approvals Dashboard](#43-my-approvals-dashboard)
  - [4.4 Delegation](#44-delegation)
- [Part 5: Integration Guide](#part-5-integration-guide)
  - [5.1 Attaching Workflows to DocTypes](#51-attaching-workflows-to-doctypes)
  - [5.2 Document Event Hooks](#52-document-event-hooks)
  - [5.3 JavaScript API](#53-javascript-api)
  - [5.4 Python API](#54-python-api)
  - [5.5 Form Widget](#55-form-widget)
- [Part 6: Advanced Features](#part-6-advanced-features)
  - [6.1 Parallel States](#61-parallel-states)
  - [6.2 History States](#62-history-states)
  - [6.3 Delayed Transitions](#63-delayed-transitions)
  - [6.4 Auto-Submission](#64-auto-submission)
  - [6.5 Multi-Tenant Support](#65-multi-tenant-support)
  - [6.6 Agentic Nodes (AI Agents)](#66-agentic-nodes-ai-agents)
- [Part 7: Administration](#part-7-administration)
  - [7.1 Permissions & Roles](#71-permissions--roles)
  - [7.2 Monitoring & Debugging](#72-monitoring--debugging)
  - [7.3 Scheduled Jobs](#73-scheduled-jobs)
- [Part 8: Examples & Recipes](#part-8-examples--recipes)
  - [8.1 Simple Approval Workflow](#81-simple-approval-workflow)
  - [8.2 Multi-Level Approval](#82-multi-level-approval)
  - [8.3 Parallel Review Process](#83-parallel-review-process)
  - [8.4 Conditional Routing](#84-conditional-routing)
  - [8.5 AI-Powered Invoice Matching](#85-ai-powered-invoice-matching-agentic-node)
- [Part 9: End User Quick Reference](#part-9-end-user-quick-reference)
  - [9.1 Receiving Approval Tasks](#91-receiving-approval-tasks)
  - [9.2 Processing Tasks](#92-processing-tasks)
  - [9.3 Task Status Guide](#93-task-status-guide)
  - [9.4 Common Actions](#94-common-actions)
  - [9.5 Keyboard Navigation](#95-keyboard-navigation)
  - [9.6 Delegation](#96-delegation-out-of-office)
- [Appendix](#appendix)
  - [A. Troubleshooting](#a-troubleshooting)
  - [B. API Reference](#b-api-reference)
  - [C. Configuration Reference](#c-configuration-reference)

---

# Part 1: Getting Started

## 1.1 What is XState Workflow?

XState Workflow is a state machine-based workflow engine for Frappe Framework that enables you to design, build, and execute complex business workflows. It combines an intuitive visual builder with the power of XState-compatible state machine execution.

```
                    XState Workflow Architecture
+------------------------------------------------------------------+
|                                                                  |
|  +----------------+    +----------------+    +------------------+|
|  |   Workflow     |    |   Machine      |    |    Approval      ||
|  |   Builder      |--->|   Instance     |--->|     Tasks        ||
|  |   (React)      |    |   (State)      |    |   (Actions)      ||
|  +----------------+    +----------------+    +------------------+|
|         |                   |                     |              |
|         v                   v                     v              |
|  +----------------------------------------------------------+   |
|  |                  Frappe Framework                         |   |
|  |    DocTypes  |  Permissions  |  Events  |  Scheduler      |   |
|  +----------------------------------------------------------+   |
|                                                                  |
+------------------------------------------------------------------+
```

### Use Cases

XState Workflow excels at handling complex business processes where documents need to flow through multiple stages with approvals, conditions, and automated actions.

#### Document Approvals with Multi-Level Hierarchies

Many organizations require different approval levels based on document value, type, or urgency. For example, a purchase order workflow might need:

- **Under $1,000**: Auto-approve
- **$1,000 - $10,000**: Manager approval
- **$10,000 - $50,000**: Director approval
- **Over $50,000**: CFO and CEO approval

XState Workflow handles this by evaluating guard conditions on transitions. When an approver clicks "Approve," the system checks the amount and routes to the appropriate next step. This eliminates manual routing decisions and ensures compliance with approval policies.

#### Employee Onboarding Processes

New employee onboarding involves multiple departments working in sequence and parallel:

1. HR creates employee record
2. IT provisions accounts AND Facilities assigns workspace (parallel)
3. Manager assigns mentor
4. Training department schedules orientation
5. Payroll sets up compensation

The workflow tracks which steps are complete, automatically notifies the next department when prerequisites are met, and provides visibility into where each new hire is in the process.

#### Expense Claim Processing

Expense claims require validation, approval, and integration with accounting:

1. Employee submits claim with receipts
2. System validates against policy limits
3. Manager approves (or requests changes)
4. Finance verifies receipts and coding
5. Payment processing triggered

The workflow can automatically reject claims that exceed policy limits, route high-value claims to additional approvers, and trigger payment processing when all approvals are complete.

#### Contract Review and Approval

Legal documents often require review from multiple stakeholders:

1. Sales creates contract from template
2. Legal reviews terms
3. Finance reviews payment terms
4. Compliance checks regulatory requirements
5. Executive signs off

Parallel approval nodes allow Legal, Finance, and Compliance to review simultaneously, reducing total cycle time. The workflow tracks who has approved and who is still pending.

#### Support Ticket Escalation

Customer support often needs automated escalation:

1. Ticket created, assigned to support agent
2. If not resolved within 4 hours, escalate to senior agent
3. If not resolved within 24 hours, escalate to team lead
4. Notify customer at each escalation

Delayed transitions automatically escalate tickets based on time elapsed, ensuring SLAs are met without manual monitoring.

#### Leave Request Management

Leave requests need manager approval and policy validation:

1. Employee submits leave request
2. System checks leave balance
3. Manager receives notification
4. Approval/rejection flows back to employee
5. Leave balance updated on approval

The workflow integrates with leave balance tracking, automatically validates requests against available balance, and updates records when approved.

---

## 1.2 Key Features

XState Workflow provides four core capabilities that work together to handle complex business processes.

### 1. Visual Workflow Builder + Code When Needed

The workflow builder provides a drag-and-drop canvas for designing workflows visually. You can create most workflows entirely through the UI, but when you need custom logic, you have full access to Python code.

```
+------------------------------------------------------------------+
|  XState Workflow Builder                                   [Save] |
+---------+------------------------------------------+-------------+
|         |                                          |             |
|  NODES  |         CANVAS AREA                      | PROPERTIES  |
|         |                                          |   PANEL     |
|  ------  |    +-------+                            |  ---------- |
|  o Start |    | Start |                            |             |
|          |    +---+---+                            |  Node: draft|
|  [] State|        |                                |             |
|          |        v                                |  Label:     |
|  <> Aprv |    +-------+      +-------+             |  [Draft   ] |
|          |    | Draft |----->|Pending|             |             |
|  * Auto  |    +-------+      +-------+             |  Entry:     |
|          |                       |                 |  [None   v] |
|  = Parll |                       v                 |             |
|          |                   +-------+             |  Transitions|
|  @ End   |                   |Approve|             |  +--------+ |
|          |                   +-------+             |  |+ Add   | |
|          |                                         |  +--------+ |
+---------+------------------------------------------+-------------+
```

**UI-based workflow design:**
- Drag nodes from the palette to create states
- Connect nodes to define transitions
- Configure properties in the side panel
- Preview workflow execution with the built-in simulator

**Code when you need it:**
- Write Python guards for complex conditions
- Create custom actions that update fields, call APIs, or send notifications
- Define custom resolvers for assignment logic
- Extend the engine with custom node handlers

### 2. Real-Time Workflow State Visibility

Every document with an attached workflow displays its current state and available actions directly in the form. Users always know where a document is in its lifecycle.

```
+------------------------------------------------------------------+
|  PURCHASE ORDER: PO-00123                                        |
+------------------------------------------------------------------+
|                                                                  |
|  +--------------------------------------------------------------+|
|  |  WORKFLOW STATUS                                             ||
|  |  ----------------                                            ||
|  |                                                              ||
|  |  Current State: * Pending Manager Approval                   ||
|  |                                                              ||
|  |  Assigned to: Sales Manager                                  ||
|  |                                                              ||
|  |  +----------+  +----------+  +----------------+              ||
|  |  | Approve  |  |  Reject  |  | Request Info   |              ||
|  |  +----------+  +----------+  +----------------+              ||
|  |                                                              ||
|  +--------------------------------------------------------------+|
|                                                                  |
|  --- Document Fields ---                                         |
|                                                                  |
|  Supplier:    [ABC Corp                              ]           |
|  Amount:      [15,000.00                             ]           |
|  ...                                                             |
|                                                                  |
+------------------------------------------------------------------+
```

**Real-time updates include:**
- Current state displayed prominently
- Available action buttons based on current state
- Assignment information (who needs to act)
- Transition history (expandable)
- WebSocket-based updates when state changes

### 3. Multiple Assignment Strategies

Different business scenarios require different ways to determine who handles an approval. XState Workflow provides multiple resolver types to match your organizational structure.

```
+------------------------------------------------------------------+
|                    RESOLVER SYSTEM                                |
+------------------------------------------------------------------+
|                                                                  |
|  When task needs assignment:                                     |
|                                                                  |
|    Approval Node Config                                          |
|           |                                                      |
|           v                                                      |
|    +-----------------------------------------------------+       |
|    |                  RESOLVER TYPE                       |       |
|    +-----------------------------------------------------+       |
|    |                                                      |       |
|    |  static_user ----> "john@example.com"               |       |
|    |                                                      |       |
|    |  role -----------> "Purchase Manager"               |       |
|    |                    (any member can claim)           |       |
|    |                                                      |       |
|    |  document_field -> doc.custom_approver              |       |
|    |                                                      |       |
|    |  owner ----------> doc.owner                        |       |
|    |                                                      |       |
|    |  linked_doc -----> doc.customer -> account_manager  |       |
|    |                                                      |       |
|    |  hierarchy_walk:                                    |       |
|    |    Employee -> reports_to -> reports_to -> ...      |       |
|    |    (walks up org chart until condition met)         |       |
|    |                                                      |       |
|    |  delegation -----> Checks User Delegation records   |       |
|    |                    (wraps another resolver)         |       |
|    |                                                      |       |
|    +-----------------------------------------------------+       |
|                         |                                        |
|                         v                                        |
|                  Assigned User(s)                                |
|                                                                  |
+------------------------------------------------------------------+
```

**Static User**: Assign to a specific user - good for single-person roles like "CFO approval"

**Role-Based**: Assign to anyone with a role - any team member can claim and complete the task

**Document Field**: Read the approver from a field on the document - allows document creators to specify who should approve

**Linked Document**: Look up the approver from a related record - e.g., assign to the customer's account manager

**Hierarchy Walk**: Walk up the org chart to find the appropriate approver - e.g., find the employee's manager, or manager's manager if above a threshold

**Delegation**: Wrapper that checks for active delegations - if the resolved user is out of office, route to their delegate

### 4. Approval System for Complex Requirements

The approval system handles sophisticated scenarios that go beyond simple approve/reject flows.

#### Parallel Approval (Committee Decisions)

When multiple approvers need to sign off, the Parallel Approval node manages the coordination:

```
+------------------------------------------------------------------+
|                 PARALLEL APPROVAL NODE                            |
+------------------------------------------------------------------+
|                                                                  |
|  Scenario: Budget changes need approval from multiple            |
|  department heads                                                |
|                                                                  |
|                    +-------------------+                         |
|                    | Budget Change     |                         |
|                    | Submitted         |                         |
|                    +---------+---------+                         |
|                              |                                   |
|                              v                                   |
|   +------------------------------------------------------+       |
|   |  PARALLEL APPROVAL: Committee Review                 |       |
|   |                                                      |       |
|   |  Approval Threshold: 2 of 3                          |       |
|   |                                                      |       |
|   |  +------------+  +------------+  +------------+      |       |
|   |  | Finance    |  | Operations |  | Sales      |      |       |
|   |  | Director   |  | Director   |  | Director   |      |       |
|   |  | [Required] |  | [Required] |  | [Optional] |      |       |
|   |  +------+-----+  +------+-----+  +------+-----+      |       |
|   |         |               |               |            |       |
|   |   Approved        Pending         Pending            |       |
|   |                                                      |       |
|   |  Status: 1 of 2 required approvals received          |       |
|   +------------------------------------------------------+       |
|                              |                                   |
|          +-------------------+-------------------+               |
|          |                                       |               |
|     [Threshold Met]                        [Any Reject]          |
|          |                                       |               |
|          v                                       v               |
|   +-------------+                         +-------------+        |
|   |  Approved   |                         |  Rejected   |        |
|   +-------------+                         +-------------+        |
|                                                                  |
+------------------------------------------------------------------+
```

**Configuration options:**
- Set how many approvals are required (e.g., "2 of 3")
- Mark approvers as required or optional
- Define what happens if any approver rejects
- Track individual approval status

#### Escalation Chains

When approvals are overdue, automatic escalation ensures timely processing:

```
+------------------------------------------------------------------+
|                    ESCALATION WORKFLOW                            |
+------------------------------------------------------------------+
|                                                                  |
|  Initial Assignment: Support Agent                               |
|                                                                  |
|    t=0h        t=4h         t=24h        t=48h                   |
|     |           |            |            |                      |
|     v           v            v            v                      |
|  +-------+   +-------+   +--------+   +-------+                  |
|  | Agent |-->| Senior|-->|  Team  |-->|Manager|                  |
|  |       |   | Agent |   |  Lead  |   |       |                  |
|  +-------+   +-------+   +--------+   +-------+                  |
|                                                                  |
|  Delayed transitions automatically escalate if not completed:    |
|                                                                  |
|    "after": {                                                    |
|      "4h": { "target": "senior_review" },                        |
|      "24h": { "target": "lead_review" },                         |
|      "48h": { "target": "manager_review" }                       |
|    }                                                             |
|                                                                  |
+------------------------------------------------------------------+
```

#### Conditional Routing

Route documents to different approvers based on document attributes:

```
+------------------------------------------------------------------+
|                 CONDITIONAL ROUTING                               |
+------------------------------------------------------------------+
|                                                                  |
|  Purchase Request submitted...                                   |
|                                                                  |
|                    +------------------+                          |
|                    | Check Category & |                          |
|                    | Amount           |                          |
|                    +--------+---------+                          |
|                             |                                    |
|     +-------------------+---+---+-------------------+            |
|     |                   |       |                   |            |
|  [IT Equipment]    [Services]  [Capital]       [Other]          |
|  [Any amount]     [> $5000]   [Any]          [< $1000]          |
|     |                   |       |                   |            |
|     v                   v       v                   v            |
|  +------+          +------+ +------+          +--------+         |
|  |  IT  |          |Procur| |  CFO |          |  Auto  |         |
|  |Manager          |ement | |      |          | Approve|         |
|  +------+          +------+ +------+          +--------+         |
|                                                                  |
|  Guards evaluated in order - first match wins:                   |
|                                                                  |
|  1. category == "IT Equipment" -> IT Manager                     |
|  2. category == "Services" AND amount > 5000 -> Procurement      |
|  3. is_capital_expenditure == true -> CFO                        |
|  4. amount < 1000 -> Auto-approve (no guard = default)           |
|                                                                  |
+------------------------------------------------------------------+
```

#### Dual Signature Requirements

Some documents require specific combinations of approvers:

```
Example: Contracts over $100,000 require BOTH Legal AND Finance

+------------------+
|  Contract Draft  |
+--------+---------+
         |
         v
+------------------+
| Parallel State:  |
| Dual Signature   |
+------------------+
| +----+ +-------+ |
| |Legal| |Finance ||
| +--+--+ +---+---+ |
|    |        |     |
+----+--------+-----+
     |
     | (both complete)
     v
+------------------+
|    Executed      |
+------------------+
```

---

## 1.3 Quick Start

Let's create a simple approval workflow for a Leave Application DocType.

### Step 1: Open the Workflow Builder

Navigate to `/xstate-builder` in your browser.

### Step 2: Create the Workflow Structure

```
                    QUICK START: Leave Approval Workflow
+------------------------------------------------------------------+
|                                                                  |
|                         o Start                                  |
|                            |                                     |
|                            v                                     |
|                     +-----------+                                |
|                     |   Draft   |                                |
|                     +-----+-----+                                |
|                           | SUBMIT                               |
|                           v                                      |
|                  +-----------------+                             |
|                  | <> Pending      |                             |
|                  |    Approval     |                             |
|                  +--------+--------+                             |
|                     +-----+-----+                                |
|                     |           |                                |
|              APPROVE|           |REJECT                          |
|                     v           v                                |
|              +----------+ +----------+                           |
|              | Approved | | Rejected |                           |
|              |    @     | |    @     |                           |
|              +----------+ +----------+                           |
|                                                                  |
+------------------------------------------------------------------+
```

### Step 3: Add Nodes

1. The canvas starts with a **Start** node
2. Drag an **Atomic State** node onto the canvas, label it "Draft"
3. Drag an **Approval** node, label it "Pending Approval"
4. Drag two **End** nodes: "Approved" and "Rejected"

### Step 4: Connect with Transitions

1. Connect Start -> Draft (this is typically automatic)
2. Connect Draft -> Pending Approval, set event name: `SUBMIT`
3. Connect Pending Approval -> Approved, set event name: `APPROVE`
4. Connect Pending Approval -> Rejected, set event name: `REJECT`

### Step 5: Configure the Approval Node

1. Select the "Pending Approval" node
2. In the Properties Panel, configure:
   - **Assignment Type**: Hierarchy Walk
   - **Start From**: Owner (the person who created the document)
   - **Levels Up**: 1 (direct manager)
   - **Available Actions**: Approve, Reject

### Step 6: Save the Workflow

1. Click the **Save** button in the toolbar
2. Fill in the save dialog:
   - **Machine ID**: `leave_approval`
   - **Title**: Leave Approval Workflow
   - **Attached DocType**: Leave Application
   - **Auto-start on Create**: Yes (check this)

### Step 7: Test the Workflow

1. Create a new Leave Application document
2. The workflow starts automatically in "Draft" state
3. Click the "Submit" action button
4. The workflow moves to "Pending Approval"
5. Log in as the employee's manager
6. Open the Leave Application - you'll see "Approve" and "Reject" buttons
7. Click "Approve" to complete the workflow

---

# Part 2: Workflow Builder Guide

## 2.1 Accessing the Builder

### URL Routes

| URL | Purpose |
|-----|---------|
| `/xstate-builder` | Create new workflow |
| `/xstate-builder/<machine_id>` | Edit existing workflow |

### Builder Interface Overview

```
+------------------------------------------------------------------+
|  XState Workflow Builder                              [Save] [v]  |
+---------+------------------------------------------+-------------+
|         |                                          |             |
|  NODES  |         CANVAS AREA                      | PROPERTIES  |
|  PANEL  |                                          |   PANEL     |
|  ------  |    +-------+                            |  ---------- |
|         |    | Start |                             |             |
| o Start |    +---+---+                             | Node: draft |
|         |        |                                 |             |
| [] State|        v                                 | Label:      |
|         |    +-------+      +-------+              | [Draft    ] |
| <> Aprv |    | Draft |----->|Pending|              |             |
|         |    +-------+      +-------+              | On Entry:   |
| * Auto  |                       |                  | [None     v]|
|         |                       v                  |             |
| = Parll |                   +-------+              | Transitions:|
|         |                   |Approve|              | +----------+|
| @ End   |                   +-------+              | |+ Add     ||
|         |                                          | +----------+|
| H Hist  |                                          |             |
|         |                                          |             |
+---------+------------------------------------------+-------------+
     |                    |                              |
     |                    |                              |
     v                    v                              v
  Drag nodes         Design your              Configure selected
  to canvas          workflow here            node/edge properties
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Z` | Undo last action |
| `Ctrl+Shift+Z` | Redo last undone action |
| `Ctrl+C` | Copy selected nodes/edges |
| `Ctrl+V` | Paste copied nodes/edges |
| `Delete` / `Backspace` | Delete selected elements |
| `Ctrl+A` | Select all nodes |
| `Escape` | Deselect all |

### Resizable Panels

Both the Node Palette (left) and Properties Panel (right) are resizable:

- **Drag** the panel edge to resize
- **Double-click** the edge to collapse/expand
- **Minimum/Maximum widths**:
  - Node Palette: 150px - 350px
  - Properties Panel: 280px - 500px

---

## 2.2 Node Types

The workflow builder provides several node types for different purposes.

```
+------------------------------------------------------------------+
|                         NODE TYPES                                |
+------------------------------------------------------------------+
|                                                                  |
|  o START NODE              Entry point of workflow               |
|  ------------                                                    |
|      o-->                  Every workflow needs exactly one      |
|                                                                  |
|  [] ATOMIC STATE           Simple state with no children         |
|  --------------                                                  |
|    +---------+             Basic workflow step                   |
|    |  State  |             Can have entry/exit actions           |
|    +---------+                                                   |
|                                                                  |
|  [+] COMPOUND STATE        State containing nested states        |
|  ----------------                                                |
|    +-----------------+     Groups related states together        |
|    | Parent          |     Has its own initial state             |
|    |  +-----++-----+ |                                           |
|    |  | A   || B   | |                                           |
|    |  +-----++-----+ |                                           |
|    +-----------------+                                           |
|                                                                  |
|  = PARALLEL STATE          Concurrent execution regions          |
|  ---------------                                                 |
|    +=================+     Multiple states active at once        |
|    | Region1| Region2|     All regions must complete             |
|    | +---+  | +---+  |                                           |
|    | | A |  | | X |  |                                           |
|    | +---+  | +---+  |                                           |
|    +=================+                                           |
|                                                                  |
|  <> APPROVAL NODE          Creates approval task                 |
|  --------------                                                  |
|    +-------------+         Assigns to user or role               |
|    | <> Approval |         Waits for human action                |
|    |   [Actions] |         Configurable action buttons           |
|    +-------------+                                               |
|                                                                  |
|  <><> PARALLEL APPROVAL    Multi-approver workflow               |
|  ------------------                                              |
|    +-------------+         Multiple concurrent approvers         |
|    |<><> Parallel|         Configurable approval threshold       |
|    |   [2 of 3]  |         Required vs optional approvers        |
|    +-------------+                                               |
|                                                                  |
|  * AUTO ACTION NODE        Automatic execution                   |
|  ------------------                                              |
|    +-------------+         Runs actions automatically            |
|    | * Auto      |         No human interaction needed           |
|    +-------------+         Good for API calls, updates           |
|                                                                  |
|  /\ THRESHOLD GATE         Conditional branching by value        |
|  ---------------                                                 |
|    +-------------+         Routes based on numeric thresholds    |
|    | /\ Threshold|         E.g., amount > 10000 -> Director      |
|    +-------------+         Multiple conditions evaluated in order|
|                                                                  |
|  <=> CLASSIFICATION        Multi-way conditional branch          |
|  --------------------                                            |
|    +-------------+         Routes based on field values          |
|    |<=> Category |         E.g., category == "IT" -> IT Manager  |
|    +-------------+         Supports multiple output paths        |
|                                                                  |
|  [AI] AGENTIC NODE         AI-powered decision making            |
|  --------------                                                  |
|    +-------------+         Spawns AI agent for analysis          |
|    |[AI] Agent   |         Can read documents, call tools        |
|    +-------------+         Makes routing decisions               |
|                                                                  |
|  {->} REST FETCH NODE      External API integration              |
|  -----------------                                               |
|    +-------------+         Calls external HTTP APIs              |
|    |{->} API Call|         Supports GET, POST, etc.              |
|    +-------------+         Maps response to workflow context     |
|                                                                  |
|  H HISTORY STATE           Remembers previous state              |
|  --------------                                                  |
|    +-------------+         Shallow: direct child only            |
|    | H History   |         Deep: deepest nested state            |
|    +-------------+                                               |
|                                                                  |
|  @ END NODE                Terminal state                        |
|  ---------                                                       |
|      -->@                  Marks workflow completion             |
|                            Can trigger auto-submit               |
|                                                                  |
+------------------------------------------------------------------+
```

### Node Type Details

#### Start Node
- Every workflow must have exactly one Start node
- Automatically connects to the initial state
- Cannot have incoming transitions

#### Atomic State Node
- Basic building block for workflows
- Can have entry actions (run when entering)
- Can have exit actions (run when leaving)
- Transitions defined for outgoing events

#### Compound State Node
- Contains child states
- Must specify an initial child state
- Useful for grouping related states
- Parent can have transitions that apply to all children

#### Parallel State Node
- Contains multiple regions that execute simultaneously
- All regions must reach final states to complete
- Useful for parallel reviews or concurrent processes

#### Approval Node
- Special node that creates an Approval Task
- Configurable assignment (user, role, resolver)
- Defines available actions (Approve, Reject, etc.)
- Workflow waits until task is completed

#### Parallel Approval Node
- Creates multiple approval tasks simultaneously
- Configure multiple approvers (each with their own resolver)
- Set approval threshold (e.g., "2 of 3 must approve")
- Mark approvers as required or optional
- Ideal for: dual-signature requirements, committee decisions, multi-department sign-offs

**Example Use Cases:**
- Finance AND Manager must both approve purchases over $10,000
- Any 2 of 3 department heads must approve budget changes
- Legal review required, but marketing review is optional

#### Auto Action Node
- Executes actions automatically on entry
- Immediately transitions to next state
- Good for: API calls, field updates, notifications

#### Threshold Gate Node
- Routes documents based on numeric thresholds
- Evaluates conditions in order, first match wins
- Perfect for amount-based approval routing
- Configure multiple threshold levels with different targets

#### Classification Branch Node
- Routes documents based on categorical values
- Supports multiple output paths
- Good for: department routing, type-based workflows
- Each path can have its own condition

#### Agentic Node
- Spawns an AI agent to analyze the document
- Agent can use tools (Frappe read, search, calculator)
- Makes routing decisions based on analysis
- Useful for: document classification, fraud detection, complex validation

#### REST Fetch Node
- Calls external HTTP APIs
- Supports all HTTP methods (GET, POST, PUT, DELETE)
- Maps response data to workflow context
- Can trigger different transitions based on response

#### History State Node
- Remembers which state was active when exiting parent
- **Shallow**: Remembers direct child state
- **Deep**: Remembers deepest nested state

#### End Node
- Marks workflow completion
- Optional auto-submit for documents
- No outgoing transitions allowed

---

## 2.3 Transitions & Edges

### Creating Transitions

1. Hover over source node to see connection handles
2. Drag from handle to target node
3. Release to create transition
4. Click transition to configure

```
+------------------------------------------------------------------+
|                    TRANSITION ANATOMY                             |
+------------------------------------------------------------------+
|                                                                  |
|    +---------+                      +---------+                  |
|    |  Draft  |------ SUBMIT ------->| Review  |                  |
|    +---------+        |             +---------+                  |
|                       |                                          |
|                       +-- Event name (trigger)                   |
|                       +-- Guard (optional condition)             |
|                       +-- Actions (optional side effects)        |
|                                                                  |
|    Example with guard:                                           |
|                                                                  |
|    +---------+   APPROVE              +---------+                |
|    | Review  |---[amount>10000]------>| Director|                |
|    +---------+                        +---------+                |
|                                                                  |
|    Example with action:                                          |
|                                                                  |
|    +---------+   COMPLETE             +---------+                |
|    | Process |---/sendEmail---------->|  Done   |                |
|    +---------+                        +---------+                |
|                                                                  |
+------------------------------------------------------------------+
```

### Event Naming Conventions

| Convention | Example | Usage |
|------------|---------|-------|
| UPPER_CASE | `SUBMIT`, `APPROVE` | User-triggered actions |
| snake_case | `auto_transition` | System-triggered events |
| dot.notation | `approval.complete` | Namespaced events |

### Transition Types

| Type | Description | Example |
|------|-------------|---------|
| **Event** | Triggered by named event | `on: { SUBMIT: 'review' }` |
| **Always** | Automatic with optional guard | `always: { target: 'next' }` |
| **Delayed** | After time period | `after: { 24h: 'escalated' }` |

---

## 2.4 Properties Panel

The Properties Panel appears on the right side when you select a node or edge.

### Node Properties

```
+-----------------------------------------+
|  NODE PROPERTIES                        |
+-----------------------------------------+
|                                         |
|  ID:     [pending_approval          ]   |
|  Label:  [Pending Approval          ]   |
|                                         |
|  --- Entry Actions ---                  |
|  +-------------------------------+      |
|  | create_approval_task          |      |
|  | [+ Add Action]                |      |
|  +-------------------------------+      |
|                                         |
|  --- Exit Actions ---                   |
|  +-------------------------------+      |
|  | [+ Add Action]                |      |
|  +-------------------------------+      |
|                                         |
|  --- Approval Settings ---              |
|  (for Approval nodes only)              |
|                                         |
|  Assignment Type: [Role           v]    |
|  Role:           [Sales Manager   v]    |
|                                         |
|  Available Actions:                     |
|  [x] Approve                            |
|  [x] Reject                             |
|  [ ] Request Info                       |
|  [+ Custom Action]                      |
|                                         |
+-----------------------------------------+
```

### Edge (Transition) Properties

```
+-----------------------------------------+
|  TRANSITION PROPERTIES                  |
+-----------------------------------------+
|                                         |
|  Event:  [APPROVE                   ]   |
|                                         |
|  --- Guard Condition ---                |
|                                         |
|  Type: [Simple               v]         |
|                                         |
|  Field:    [grand_total         ]       |
|  Operator: [greater than      v]        |
|  Value:    [10000               ]       |
|                                         |
|  --- Transition Actions ---             |
|  +-------------------------------+      |
|  | log_approval                  |      |
|  | [+ Add Action]                |      |
|  +-------------------------------+      |
|                                         |
+-----------------------------------------+
```

---

## 2.5 Saving & Loading Workflows

### Saving a Workflow

1. Click the **Save** button in the toolbar
2. Fill in the save dialog:

```
+-----------------------------------------+
|  SAVE WORKFLOW                          |
+-----------------------------------------+
|                                         |
|  Machine ID:    [purchase_approval  ]   |
|  (unique identifier, no spaces)         |
|                                         |
|  Title:         [Purchase Approval  ]   |
|  (human-readable name)                  |
|                                         |
|  Description:                           |
|  [Multi-level approval for purchases]   |
|                                         |
|  Attached DocType: [Purchase Order v]   |
|                                         |
|  [x] Active                             |
|  [x] Auto-start on Create               |
|                                         |
|  Edit Restriction:                      |
|  [Assigned Only                    v]   |
|                                         |
|        [Cancel]  [Save]                 |
|                                         |
+-----------------------------------------+
```

### Loading an Existing Workflow

**Method 1: Direct URL**
```
/xstate-builder/purchase_approval
```

**Method 2: Workflow Selector**
1. Open `/xstate-builder`
2. Use the dropdown in the toolbar to select an existing workflow
3. The workflow loads in the canvas

### Export/Import

**Export:**
1. Open workflow in builder
2. Click menu -> Export
3. JSON file downloads

**Import:**
1. Click menu -> Import
2. Select JSON file
3. Workflow loads in builder

---

# Part 3: Core Concepts

## 3.1 State Machine Fundamentals

### States and Transitions

A state machine consists of:
- **States**: The possible conditions of your workflow
- **Transitions**: Rules for moving between states
- **Events**: Triggers that cause transitions
- **Context**: Data that persists across states

```
+------------------------------------------------------------------+
|                    STATE MACHINE FLOW                             |
+------------------------------------------------------------------+
|                                                                  |
|   Document Created                                               |
|         |                                                        |
|         v                                                        |
|   +-----------+                                                  |
|   |  Check    |--No--> Normal Frappe flow                        |
|   | Workflow? |                                                  |
|   +-----+-----+                                                  |
|         | Yes                                                    |
|         v                                                        |
|   +---------------+                                              |
|   |    Create     |                                              |
|   |   Instance    |                                              |
|   +-------+-------+                                              |
|           |                                                      |
|           v                                                      |
|   +---------------+     +--------------+                         |
|   | Initial State |---->| Event Occurs |<-----------+            |
|   +---------------+     +------+-------+            |            |
|                                |                    |            |
|                                v                    |            |
|                        +---------------+            |            |
|                        | Check Guards  |            |            |
|                        +-------+-------+            |            |
|                                |                    |            |
|                    +-----------+-----------+        |            |
|                    v                       v        |            |
|              +----------+           +----------+    |            |
|              |  Guard   |           |  Guard   |    |            |
|              |  Passes  |           |  Fails   |    |            |
|              +----+-----+           +----------+    |            |
|                   |                                 |            |
|                   v                                 |            |
|           +---------------+                         |            |
|           |Execute Actions|                         |            |
|           +-------+-------+                         |            |
|                   |                                 |            |
|                   v                                 |            |
|           +---------------+                         |            |
|           |  Transition   |-------------------------+            |
|           |  to New State |                                      |
|           +-------+-------+                                      |
|                   |                                              |
|                   v                                              |
|           +---------------+                                      |
|           |  Final State? |--Yes--> Workflow Complete            |
|           +---------------+                                      |
|                                                                  |
+------------------------------------------------------------------+
```

### Initial and Final States

**Initial State:**
- First state entered when workflow starts
- Defined on compound/parallel states
- Start node connects to initial state

**Final State:**
- Marks completion of workflow or compound state
- Can trigger auto-submit for documents
- No outgoing transitions allowed

### Context (Workflow Variables)

Context stores data that persists across states:

```python
# Initial context defined in workflow
{
  "context": {
    "approval_count": 0,
    "approvers": [],
    "last_action": null
  }
}
```

Update context in actions:
```python
# In an action
context['approval_count'] += 1
context['approvers'].append(frappe.session.user)
```

---

## 3.2 Guards (Conditions)

Guards are conditions that must be true for a transition to occur.

### Simple Guards

Field-based comparisons:

```json
{
  "type": "simple",
  "field": "grand_total",
  "operator": "gt",
  "value": 10000
}
```

**Available Operators:**

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equals | `status eq "Draft"` |
| `ne` | Not equals | `priority ne "Low"` |
| `gt` | Greater than | `amount gt 1000` |
| `lt` | Less than | `quantity lt 5` |
| `gte` | Greater or equal | `score gte 80` |
| `lte` | Less or equal | `age lte 65` |
| `in` | In list | `type in ["A","B"]` |
| `contains` | String contains | `name contains "Test"` |
| `is_set` | Field has value | `approver is_set` |
| `is_not_set` | Field is empty | `rejection_reason is_not_set` |

### Compound Guards

Combine multiple conditions:

```json
{
  "type": "compound",
  "operator": "and",
  "conditions": [
    {
      "type": "simple",
      "field": "amount",
      "operator": "gt",
      "value": 10000
    },
    {
      "type": "simple",
      "field": "category",
      "operator": "eq",
      "value": "Equipment"
    }
  ]
}
```

**Compound Operators:**
- `and` - All conditions must be true
- `or` - At least one condition must be true

### Role Guards

Check if user has a specific role:

```json
{
  "type": "role",
  "roles": ["Purchase Manager", "Director"]
}
```

### Python Guards

Custom Python code for complex conditions:

```python
# Defined in Guards child table of State Machine
# Guard name: high_value_purchase

# Available variables: context, event, doc, frappe
doc.grand_total > 10000 and doc.category == "Equipment"
```

Use in workflow:
```json
{
  "on": {
    "APPROVE": {
      "target": "director_approval",
      "cond": "high_value_purchase"
    }
  }
}
```

---

## 3.3 Actions

Actions are side effects executed during state transitions.

### Action Types

| Type | When Executed | Use Case |
|------|---------------|----------|
| **Entry** | When entering state | Create tasks, send notifications |
| **Exit** | When leaving state | Cleanup, logging |
| **Transition** | During transition | Update fields, call APIs |

### Built-in Actions

| Action | Description |
|--------|-------------|
| `create_approval_task` | Creates approval task for current node |
| `cancel_approval_tasks` | Cancels pending tasks for document |
| `submit_document` | Submits the Frappe document |
| `cancel_document` | Cancels the Frappe document |
| `update_field` | Updates a document field |
| `update_status` | Updates status field |
| `send_notification` | Sends email notification |
| `call_api` | Calls external HTTP API |
| `run_method` | Runs a Frappe whitelisted method |

### Python Actions

Custom Python code:

```python
# Defined in Actions child table of State Machine
# Action name: notify_approval

# Available variables: context, event, doc, frappe, instance

# Update context
context['approved_at'] = frappe.utils.now()
context['approved_by'] = frappe.session.user

# Update document
doc.approval_status = "Approved"
doc.save()

# Send email
frappe.sendmail(
    recipients=[doc.owner],
    subject=f"{doc.doctype} {doc.name} Approved",
    message=f"Your {doc.doctype} has been approved."
)
```

---

## 3.4 Assignment Resolvers

Resolvers determine who gets assigned to approval tasks.

### Static User

Assign to a specific user:

```json
{
  "type": "static_user",
  "user": "manager@example.com"
}
```

### Role-Based

Assign to anyone with a role:

```json
{
  "type": "role",
  "role": "Purchase Manager"
}
```

Task appears for all role members; any can claim it.

### Document Field

Read assignee from document field:

```json
{
  "type": "document_field",
  "field": "custom_approver",
  "fallback_field": "owner",
  "fallback_user": "admin@example.com"
}
```

Supports dot notation for linked fields:
```json
{
  "type": "document_field",
  "field": "customer.account_manager"
}
```

### Owner

Assign to document creator:

```json
{
  "type": "owner",
  "fallback_user": "admin@example.com"
}
```

### Linked Document

Get user from linked document:

```json
{
  "type": "linked_doc",
  "link_field": "customer",
  "target_field": "account_manager"
}
```

### Hierarchy Walk

Walk up organizational hierarchy to find approvers. Perfect for manager chains.

**Configuration Options:**

| Field | Description |
|-------|-------------|
| `hierarchy_doctype` | DocType with hierarchy (e.g., Employee) |
| `parent_field` | Self-referential link (e.g., `reports_to`) |
| `user_field` | Link to User (e.g., `user_id`) |
| `start_from` | Where to start: `owner`, `document_field`, `linked_doc` |
| `level_mode` | How to walk: `fixed`, `until_condition`, `all_up_to` |
| `levels_up` | Number of levels for `fixed` mode |
| `stop_condition` | Field to check for `until_condition` mode |

**Example - Direct Manager Approval:**
```json
{
  "type": "hierarchy_walk",
  "hierarchy_doctype": "Employee",
  "parent_field": "reports_to",
  "user_field": "user_id",
  "start_from": "owner",
  "level_mode": "fixed",
  "levels_up": 1
}
```

### Delegation Wrapper

Apply delegation rules to another resolver:

```json
{
  "type": "delegation",
  "base_resolver": {
    "type": "document_field",
    "field": "approver"
  }
}
```

---

# Part 4: Approval System

## 4.1 Approval Tasks

### How Tasks Are Created

1. Workflow enters an Approval node
2. Entry action `create_approval_task` executes
3. Resolver determines assignee
4. Approval Task document created

```
+------------------------------------------------------------------+
|                   APPROVAL TASK LIFECYCLE                         |
+------------------------------------------------------------------+
|                                                                  |
|                    +-------------+                               |
|                    |   Created   |                               |
|                    |  (Pending)  |                               |
|                    +------+------+                               |
|                           |                                      |
|           +---------------+---------------+                      |
|           v               v               v                      |
|    +------------+  +------------+  +------------+                |
|    |  Claimed   |  | Reassigned |  | Escalated  |                |
|    |(In Progress)|  | (Pending)  |  | (Pending)  |                |
|    +-----+------+  +------------+  +------------+                |
|          |                                                       |
|          v                                                       |
|    +----------------------------------+                          |
|    |         Action Taken             |                          |
|    |  +--------+ +--------+ +------+  |                          |
|    |  |Approve | | Reject | | etc. |  |                          |
|    |  +--------+ +--------+ +------+  |                          |
|    +--------------------+-------------+                          |
|                         |                                        |
|                         v                                        |
|                  +------------+                                  |
|                  | Completed  |                                  |
|                  +------------+                                  |
|                                                                  |
+------------------------------------------------------------------+
```

### Task Statuses

| Status | Description |
|--------|-------------|
| **Pending** | Waiting for action |
| **In Progress** | Claimed by user |
| **Completed** | Action taken |
| **Cancelled** | Task cancelled (workflow moved on) |
| **Escalated** | Escalated to another user |
| **Reassigned** | Reassigned to different user |

---

## 4.2 User Actions

### Claiming Tasks

For role-based assignments, users must claim tasks:

```
+-----------------------------------------+
|  APPROVAL TASK: APT-2024-00042          |
+-----------------------------------------+
|                                         |
|  Document: Purchase Order PO-00123      |
|  Requested by: Jane Smith               |
|  Amount: $15,000                        |
|                                         |
|  Assigned to: Purchase Manager (Role)   |
|                                         |
|  Status: Pending                        |
|                                         |
|  +-------------------------------+      |
|  |         [Claim Task]          |      |
|  +-------------------------------+      |
|                                         |
+-----------------------------------------+
```

After claiming, action buttons appear:

```
+-----------------------------------------+
|  APPROVAL TASK: APT-2024-00042          |
+-----------------------------------------+
|                                         |
|  Assigned to: You (John Doe)            |
|  Status: In Progress                    |
|                                         |
|  Comments:                              |
|  [                                  ]   |
|                                         |
|  +----------+  +----------+             |
|  | Approve  |  |  Reject  |             |
|  +----------+  +----------+             |
|                                         |
+-----------------------------------------+
```

---

## 4.3 My Approvals Dashboard

Access at `/my-approvals` or via the Desk.

```
+------------------------------------------------------------------+
|  MY APPROVALS                                          [Refresh]  |
+------------------------------------------------------------------+
|                                                                  |
|  Filter: [Pending v]  DocType: [All v]  Search: [          ]     |
|                                                                  |
+------------------------------------------------------------------+
|  | Task ID      | Document          | State     | Due    | Pri | |
|  +--------------+-------------------+-----------+--------+-----+ |
|  | APT-00042    | PO-00123          | Pending   | Today  | *   | |
|  | APT-00041    | Leave-00089       | Pending   | 2 days | o   | |
|  | APT-00039    | Expense-00456     | Progress  | 5 days | .   | |
|  +--------------+-------------------+-----------+--------+-----+ |
|                                                                  |
|  Priority: * High  o Medium  . Low                               |
|                                                                  |
|  Showing 3 of 3 tasks                      [Previous] [Next]     |
|                                                                  |
+------------------------------------------------------------------+
```

---

## 4.4 Delegation

### Setting Up Delegations

Create a User Delegation record:

```
+-----------------------------------------+
|  USER DELEGATION                        |
+-----------------------------------------+
|                                         |
|  Delegator: [john@example.com      v]   |
|  Delegate:  [backup@example.com    v]   |
|                                         |
|  From Date: [2024-01-15]                |
|  To Date:   [2024-01-22]                |
|                                         |
|  [x] Is Active                          |
|                                         |
|  Reason:                                |
|  [Annual leave - out of office     ]    |
|                                         |
|  Scope: [All                       v]   |
|                                         |
|        [Cancel]  [Save]                 |
|                                         |
+-----------------------------------------+
```

### Scope Options

| Scope | Description |
|-------|-------------|
| **All** | Delegate all approval tasks |
| **Specific DocTypes** | Only selected DocTypes |
| **Specific Workflows** | Only selected workflows |

---

# Part 5: Integration Guide

## 5.1 Attaching Workflows to DocTypes

### Configuration Options

| Field | Description |
|-------|-------------|
| **Attached DocType** | The DocType this workflow applies to |
| **Auto-start on Create** | Automatically start workflow when document created |
| **Edit Restriction Mode** | Control who can edit document during workflow |

### Edit Restriction Modes

| Mode | Who Can Edit |
|------|--------------|
| **None** | Anyone with document permission |
| **Assigned Only** | Only the currently assigned user |
| **Role Only** | Only users with the assigned role |
| **Assigned or Role** | Assigned user OR role members |

### DocTypes to Avoid

**Do not attach workflows to internal system DocTypes.** These are auto-created by Frappe/ERPNext during other document operations and will cause submission failures:

| DocType | Why to Avoid |
|---------|--------------|
| **GL Entry** | Auto-created when submitting invoices, journals, etc. |
| **Stock Ledger Entry** | Auto-created during stock transactions |
| **Payment Ledger Entry** | Auto-created during payment processing |
| **Repost Item Valuation** | System document for stock reposting |
| **Communication** | Auto-created for emails, comments |
| **Version** | Auto-created for document versioning |
| **Activity Log** | System logging document |

If you accidentally attach a workflow to these DocTypes, you'll see errors like:
> "Cannot submit GL Entry: Workflow approval required"

**Fix:** Go to State Machine list, find workflows attached to internal DocTypes, and either delete them or set `Is Active = No`.

---

## 5.2 Document Event Hooks

### Automatic Event Triggers

Configure workflows to trigger on document events:

```python
# In State Machine json_config
{
  "triggers": [
    {
      "event": "on_update",          # Frappe hook
      "workflow_event": "UPDATE",     # Workflow event to trigger
      "guard": {                      # Optional condition
        "type": "simple",
        "field": "status",
        "operator": "eq",
        "value": "Submitted"
      }
    }
  ]
}
```

### Available Document Events

| Frappe Event | When Triggered |
|--------------|----------------|
| `after_insert` | After document created |
| `on_update` | After document saved |
| `before_submit` | Before document submitted |
| `on_submit` | After document submitted |
| `before_cancel` | Before document cancelled |
| `on_cancel` | After document cancelled |

---

## 5.3 JavaScript API

### Trigger Events

```javascript
// Trigger a workflow event
frappe.call({
    method: "xstate_workflow.api.workflow.trigger_event",
    args: {
        doctype: "Purchase Order",
        docname: "PO-00123",
        event: "APPROVE",
        data: {
            comments: "Approved for processing"
        }
    },
    callback: function(r) {
        if (r.message.success) {
            console.log("New state:", r.message.state);
        }
    }
});
```

### Get Current State

```javascript
// Get workflow state for a document
frappe.call({
    method: "xstate_workflow.api.workflow.get_machine_state",
    args: {
        doctype: "Purchase Order",
        docname: "PO-00123"
    },
    callback: function(r) {
        console.log("Current state:", r.message.current_state);
        console.log("Available events:", r.message.available_events);
    }
});
```

### Using the Global Helper

```javascript
// Available after boot
frappe.xstate_workflow.trigger_event("Purchase Order", "PO-00123", "SUBMIT")
    .then(result => {
        frappe.show_alert("Workflow transitioned to: " + result.state);
    });

frappe.xstate_workflow.get_state("Purchase Order", "PO-00123")
    .then(state => {
        console.log(state);
    });
```

---

## 5.4 Python API

### Core Functions

```python
from xstate_workflow.workflow_engine import (
    trigger_event_sync,
    trigger_event,
    get_machine_state,
    get_machine_state_with_history,
    start_workflow,
    reset_workflow
)

# Get current state
state = get_machine_state("Purchase Order", "PO-00123")
print(state["current_state"])       # "pending_approval"
print(state["available_events"])    # ["APPROVE", "REJECT"]

# Trigger event (synchronous)
result = trigger_event_sync(
    doctype="Purchase Order",
    docname="PO-00123",
    event="APPROVE",
    data={"comments": "Looks good"}
)

# Trigger event (background job)
trigger_event(
    doctype="Purchase Order",
    docname="PO-00123",
    event="PROCESS"
)

# Start workflow manually
start_workflow("Purchase Order", "PO-00123")

# Reset workflow to initial state
reset_workflow("Purchase Order", "PO-00123")
```

### Approval Task API

```python
from xstate_workflow.api.approval import (
    get_my_approval_tasks,
    complete_approval_task,
    claim_approval_task,
    reassign_approval_task,
    escalate_approval_task
)

# Get pending tasks
tasks = get_my_approval_tasks(
    status="pending_with_me",
    limit=20
)

# Complete a task
complete_approval_task(
    task_name="APT-2024-00042",
    action="Approve",
    comments="Approved"
)

# Claim a task
claim_approval_task("APT-2024-00042")

# Reassign
reassign_approval_task(
    task_name="APT-2024-00042",
    new_assignee="other@example.com",
    reason="Delegating"
)

# Escalate
escalate_approval_task(
    task_name="APT-2024-00042",
    escalate_to="manager@example.com"
)
```

---

## 5.5 Form Widget

The workflow widget automatically appears on forms for DocTypes with attached workflows.

```
+------------------------------------------------------------------+
|  PURCHASE ORDER: PO-00123                                        |
+------------------------------------------------------------------+
|                                                                  |
|  +--------------------------------------------------------------+|
|  |  WORKFLOW STATUS                                             ||
|  |  ----------------                                            ||
|  |                                                              ||
|  |  Current State: * Pending Manager Approval                   ||
|  |                                                              ||
|  |  Assigned to: Sales Manager                                  ||
|  |                                                              ||
|  |  +----------+  +----------+  +----------------+              ||
|  |  | Approve  |  |  Reject  |  | Request Info   |              ||
|  |  +----------+  +----------+  +----------------+              ||
|  |                                                              ||
|  +--------------------------------------------------------------+|
|                                                                  |
|  --- Document Fields ---                                         |
|                                                                  |
|  Supplier:    [ABC Corp                              ]           |
|  Amount:      [15,000.00                             ]           |
|  ...                                                             |
|                                                                  |
+------------------------------------------------------------------+
```

---

# Part 6: Advanced Features

## 6.1 Parallel States

Execute multiple state regions simultaneously.

```
+------------------------------------------------------------------+
|                    PARALLEL STATE EXAMPLE                         |
+------------------------------------------------------------------+
|                                                                  |
|                         o Start                                  |
|                            |                                     |
|                            v                                     |
|  +===========================================================+   |
|  ||                   Processing (Parallel)                  ||   |
|  |+===========================+=============================+|   |
|  ||      Finance Review       |      Legal Review           ||   |
|  ||  ---------------------    |  ---------------------      ||   |
|  ||                           |                             ||   |
|  ||  +---------+              |  +---------+                ||   |
|  ||  |Reviewing|              |  |Reviewing|                ||   |
|  ||  +----+----+              |  +----+----+                ||   |
|  ||       |                   |       |                     ||   |
|  ||       v                   |       v                     ||   |
|  ||  +---------+              |  +---------+                ||   |
|  ||  |Approved |@             |  |Approved |@               ||   |
|  ||  +---------+              |  +---------+                ||   |
|  ||                           |                             ||   |
|  |+===========================+=============================+|   |
|  +===========================================================+   |
|                            |                                     |
|                            | (both complete)                     |
|                            v                                     |
|                     +-----------+                                |
|                     | Completed |@                               |
|                     +-----------+                                |
|                                                                  |
+------------------------------------------------------------------+
```

---

## 6.2 History States

Remember and restore previous states.

### History Types

| Type | Behavior |
|------|----------|
| **Shallow** | Remembers direct child state only |
| **Deep** | Remembers deepest nested state |

---

## 6.3 Delayed Transitions

Automatic transitions after a time period.

```
+------------------------------------------------------------------+
|                 DELAYED TRANSITION EXAMPLE                        |
+------------------------------------------------------------------+
|                                                                  |
|                    +-------------+                               |
|                    |   Pending   |                               |
|                    |   Approval  |                               |
|                    +------+------+                               |
|                           |                                      |
|             +-------------+-------------+                        |
|             |             |             |                        |
|      APPROVE|      REJECT |      after  |                        |
|             |             |       24h   |                        |
|             v             v             v                        |
|       +----------+  +----------+  +----------+                   |
|       | Approved |  | Rejected |  |Escalated |                   |
|       +----------+  +----------+  +----------+                   |
|                                                                  |
|   If no action within 24 hours, auto-escalate                    |
|                                                                  |
+------------------------------------------------------------------+
```

### Delay Formats

| Format | Example | Duration |
|--------|---------|----------|
| Milliseconds | `500ms` | 0.5 seconds |
| Seconds | `30s` | 30 seconds |
| Minutes | `5m` | 5 minutes |
| Hours | `2h` | 2 hours |
| Days | `1d` | 24 hours |

---

## 6.4 Auto-Submission

Automatically submit documents when reaching final states.

### Configuration

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

---

## 6.5 Multi-Tenant Support

Isolate workflows by company/tenant.

Set the `tenant` field on:
- State Machine
- Machine Instance
- Approval Task

---

## 6.6 Agentic Nodes (AI Agents)

Agentic nodes enable AI-powered decision making within workflows.

### Prerequisites

Install required Python packages:

```bash
pip install langgraph langchain-core langchain-openai langchain-anthropic
```

Configure API keys in **XState Workflow Settings**:
- OpenAI API Key (for GPT models)
- Anthropic API Key (for Claude models)

### Agent Types

| Type | Description | Use Case |
|------|-------------|----------|
| **ReAct** | Reasoning + Acting agent | General-purpose decision making |
| **Tool Executor** | Direct tool execution | Simple tool-based workflows |
| **Plan & Execute** | Multi-step planning | Complex multi-step processes |

### Available Tools

| Tool | Access Level | Description |
|------|--------------|-------------|
| `frappe_read` | read_only, full_crud | Read Frappe documents |
| `frappe_write` | full_crud | Create/update documents |
| `frappe_search` | read_only, full_crud | Search across DocTypes |
| `frappe_method` | any | Call whitelisted methods |
| `web_search` | any | Search the web |
| `calculator` | any | Evaluate math expressions |
| `code_executor` | any | Execute sandboxed Python |

---

# Part 7: Administration

## 7.1 Permissions & Roles

### Built-in Roles

| Role | Capabilities |
|------|-------------|
| **System Manager** | Full access to all workflow features |
| **Workflow Manager** | Create/edit workflow definitions |

### Permission Matrix

| DocType | System Manager | Workflow Manager | Other Users |
|---------|----------------|------------------|-------------|
| State Machine | Full | Read/Write/Create | None |
| Machine Instance | Full | Read | Filtered* |
| Approval Task | Full | Read | Filtered* |

*Filtered by assignment or role membership

---

## 7.2 Monitoring & Debugging

### Transition Logs

Each Machine Instance maintains a transition log:

```python
instance = frappe.get_doc("Machine Instance", instance_name)
for entry in instance.transition_log:
    print(f"{entry['timestamp']}: {entry['from_state']} -> {entry['to_state']}")
    print(f"  Event: {entry['event']}")
    print(f"  User: {entry['user']}")
```

### Mermaid Diagrams

Generate visual diagrams:

```python
from xstate_workflow.mermaid_generator import generate_mermaid_diagram

diagram = generate_mermaid_diagram(
    config=workflow_config,
    current_state="pending_approval",
    transition_log=instance.transition_log
)
print(diagram)
```

---

## 7.3 Scheduled Jobs

### Automatic Jobs

| Schedule | Job | Purpose |
|----------|-----|---------|
| Every minute | `process_delayed_transitions` | Execute scheduled transitions |
| Every 15 min | `check_overdue_tasks` | Flag overdue approval tasks |
| Daily | `cleanup_old_snapshots` | Archive old workflow instances |

---

# Part 8: Examples & Recipes

## 8.1 Simple Approval Workflow

A basic single-level approval for any document.

```json
{
  "id": "simple_approval",
  "initial": "draft",
  "states": {
    "draft": {
      "on": {
        "SUBMIT": "pending_approval"
      }
    },
    "pending_approval": {
      "entry": ["create_approval_task"],
      "meta": {
        "nodeType": "approval",
        "assignment": {
          "type": "role",
          "role": "Manager"
        },
        "availableActions": ["Approve", "Reject"]
      },
      "on": {
        "APPROVE": "approved",
        "REJECT": "rejected"
      }
    },
    "approved": {
      "type": "final",
      "meta": { "autoSubmit": true }
    },
    "rejected": {
      "type": "final"
    }
  }
}
```

---

## 8.2 Multi-Level Approval

Approval based on amount thresholds.

```json
{
  "id": "multi_level_approval",
  "initial": "draft",
  "states": {
    "draft": {
      "on": { "SUBMIT": "manager_approval" }
    },
    "manager_approval": {
      "entry": ["create_approval_task"],
      "meta": {
        "nodeType": "approval",
        "assignment": { "type": "role", "role": "Manager" },
        "availableActions": ["Approve", "Reject"]
      },
      "on": {
        "APPROVE": [
          {
            "target": "director_approval",
            "cond": {
              "type": "simple",
              "field": "grand_total",
              "operator": "gt",
              "value": 10000
            }
          },
          { "target": "approved" }
        ],
        "REJECT": "rejected"
      }
    },
    "director_approval": {
      "entry": ["create_approval_task"],
      "meta": {
        "nodeType": "approval",
        "assignment": { "type": "role", "role": "Director" },
        "availableActions": ["Approve", "Reject"]
      },
      "on": {
        "APPROVE": "approved",
        "REJECT": "rejected"
      }
    },
    "approved": { "type": "final" },
    "rejected": { "type": "final" }
  }
}
```

---

## 8.3 Parallel Review Process

Multiple reviewers working simultaneously.

```json
{
  "id": "parallel_review",
  "initial": "draft",
  "states": {
    "draft": {
      "on": { "SUBMIT": "review" }
    },
    "review": {
      "type": "parallel",
      "states": {
        "technical": {
          "initial": "pending",
          "states": {
            "pending": {
              "entry": ["create_tech_review_task"],
              "on": { "TECH_APPROVE": "approved" }
            },
            "approved": { "type": "final" }
          }
        },
        "business": {
          "initial": "pending",
          "states": {
            "pending": {
              "entry": ["create_business_review_task"],
              "on": { "BIZ_APPROVE": "approved" }
            },
            "approved": { "type": "final" }
          }
        }
      },
      "onDone": "approved"
    },
    "approved": { "type": "final" }
  }
}
```

---

## 8.4 Conditional Routing

Route based on document category.

```json
{
  "id": "conditional_routing",
  "initial": "draft",
  "states": {
    "draft": {
      "on": { "SUBMIT": "routing" }
    },
    "routing": {
      "always": [
        {
          "target": "it_approval",
          "cond": {
            "type": "simple",
            "field": "category",
            "operator": "eq",
            "value": "Equipment"
          }
        },
        {
          "target": "ops_approval",
          "cond": {
            "type": "simple",
            "field": "category",
            "operator": "eq",
            "value": "Services"
          }
        },
        { "target": "general_approval" }
      ]
    },
    "it_approval": {
      "entry": ["create_approval_task"],
      "meta": {
        "assignment": { "type": "role", "role": "IT Manager" }
      },
      "on": { "APPROVE": "approved", "REJECT": "rejected" }
    },
    "ops_approval": {
      "entry": ["create_approval_task"],
      "meta": {
        "assignment": { "type": "role", "role": "Operations Manager" }
      },
      "on": { "APPROVE": "approved", "REJECT": "rejected" }
    },
    "general_approval": {
      "entry": ["create_approval_task"],
      "meta": {
        "assignment": { "type": "role", "role": "General Manager" }
      },
      "on": { "APPROVE": "approved", "REJECT": "rejected" }
    },
    "approved": { "type": "final" },
    "rejected": { "type": "final" }
  }
}
```

---

## 8.5 AI-Powered Invoice Matching (Agentic Node)

Automated 2-way and 3-way matching for Purchase Invoices using an AI agent.

```json
{
  "id": "purchase_invoice_matching",
  "initial": "draft",
  "states": {
    "draft": {
      "on": {
        "SUBMIT_FOR_MATCHING": "ai_matching"
      }
    },
    "ai_matching": {
      "on": {
        "DECISION_MATCHED": "approved",
        "DECISION_PARTIAL": "partial_approval",
        "DECISION_MISMATCH": "manual_review",
        "AGENT_FAILURE": "manual_review"
      },
      "meta": {
        "domain_node": {
          "type": "agentic",
          "label": "AI Invoice Matcher",
          "agentType": "react",
          "model": "gpt-4",
          "enabledTools": [
            { "name": "frappe_read", "enabled": true },
            { "name": "frappe_search", "enabled": true },
            { "name": "calculator", "enabled": true }
          ],
          "frappeAccess": "read_only",
          "transitionMode": "decision",
          "decisionRoutes": [
            { "condition": "matched" },
            { "condition": "partial" },
            { "condition": "mismatch" }
          ]
        }
      }
    },
    "partial_approval": {
      "on": {
        "RECEIPT_CONFIRMED": "approved",
        "REJECT": "rejected"
      },
      "meta": {
        "domain_node": {
          "type": "approval",
          "label": "Confirm Goods Receipt",
          "resolver": { "type": "role", "role": "Stock Manager" }
        }
      }
    },
    "manual_review": {
      "on": {
        "APPROVE": "approved",
        "REJECT": "rejected"
      },
      "meta": {
        "domain_node": {
          "type": "approval",
          "label": "Manual Review Required",
          "resolver": { "type": "role", "role": "Accounts Payable Manager" }
        }
      }
    },
    "approved": { "type": "final" },
    "rejected": { "type": "final" }
  }
}
```

---

# Part 9: End User Quick Reference

This section is for users who receive and process approval tasks.

## 9.1 Receiving Approval Tasks

When a document requires your approval:
1. Receive an email notification (if configured)
2. See the task in your **My Approvals** dashboard (`/my-approvals`)
3. See a notification in Frappe/ERPNext

## 9.2 Processing Tasks

1. **Review the document** - Click the document link to open it
2. **Add comments** (optional) - Notes explaining your decision
3. **Take action** - Click Approve, Reject, or other available action

## 9.3 Task Status Guide

| Status | Meaning |
|--------|---------|
| **Pending** | Awaiting your action |
| **In Progress** | You've claimed but not completed |
| **Completed** | Action taken, workflow moved on |
| **Escalated** | Task escalated to someone else |

## 9.4 Common Actions

| Action | When to Use |
|--------|-------------|
| **Claim** | Take ownership of a role-based task |
| **Approve** | Document meets requirements |
| **Reject** | Document doesn't meet requirements |
| **Request Changes** | Send back for modifications |
| **Reassign** | Pass to another person |
| **Escalate** | Pass to higher authority |

## 9.5 Keyboard Navigation

| Key | Action |
|-----|--------|
| `Enter` | Open selected task |
| `Up/Down` | Navigate task list |
| `R` | Refresh task list |

## 9.6 Delegation (Out of Office)

If you'll be unavailable:
1. Go to **User Delegation** in Desk
2. Create a new delegation record
3. Set your delegate and date range
4. Tasks will be routed to your delegate

---

# Appendix

## A. Troubleshooting

### Common Issues

#### Workflow Not Starting

**Symptoms:** Document created but no workflow instance.

**Solutions:**
1. Check `auto_start_on_create` is enabled
2. Verify workflow is active
3. Check `attached_doctype` matches document type

```python
# Debug: Check for workflow
from xstate_workflow.workflow_engine import get_machine_state
state = get_machine_state("DocType", "DocName")
print(state)  # Should show current state
```

#### Transitions Not Working

**Symptoms:** Event triggered but state doesn't change.

**Solutions:**
1. Check guard conditions
2. Verify event name matches exactly
3. Check user permissions

```python
# Debug: Check available events
state = get_machine_state("DocType", "DocName")
print(state['available_events'])
```

#### Approval Tasks Not Created

**Symptoms:** Workflow enters approval state but no task appears.

**Solutions:**
1. Ensure `create_approval_task` action is in entry actions
2. Check resolver configuration
3. Verify assignment target exists

#### Invalid Workflow Configuration - Submittable DocType Error

**Error Message:**
```
Invalid Workflow Configuration
Workflow for submittable doctype must have a final state that allows submission
```

**Solution:** For submittable DocTypes (Purchase Invoice, Sales Order, etc.), add `"autoSubmit": true` to your approved/completed final state:

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

---

## B. API Reference

### Workflow Engine

| Function | Description |
|----------|-------------|
| `trigger_event_sync(doctype, docname, event, data)` | Trigger event synchronously |
| `trigger_event(doctype, docname, event, data)` | Trigger event in background |
| `get_machine_state(doctype, docname)` | Get current workflow state |
| `start_workflow(doctype, docname)` | Start workflow for document |
| `reset_workflow(doctype, docname)` | Reset to initial state |

### Approval API

| Function | Description |
|----------|-------------|
| `get_my_approval_tasks(status, limit)` | Get pending tasks |
| `complete_approval_task(task_name, action, comments)` | Complete a task |
| `claim_approval_task(task_name)` | Claim a role-based task |
| `reassign_approval_task(task_name, new_assignee, reason)` | Reassign task |
| `escalate_approval_task(task_name, escalate_to)` | Escalate task |

---

## C. Configuration Reference

### State Machine Fields

| Field | Type | Description |
|-------|------|-------------|
| `machine_id` | Data | Unique identifier |
| `title` | Data | Human-readable name |
| `attached_doctype` | Link | DocType this applies to |
| `json_config` | JSON | XState configuration |
| `is_active` | Check | Enable/disable workflow |
| `auto_start_on_create` | Check | Auto-start on document create |
| `edit_restriction_mode` | Select | Control document editing |

### Approval Task Fields

| Field | Type | Description |
|-------|------|-------------|
| `reference_doctype` | Link | Source document type |
| `reference_name` | Data | Source document name |
| `state_name` | Data | Workflow state that created task |
| `assigned_to` | Link | Assigned user |
| `assigned_role` | Link | Assigned role |
| `status` | Select | Task status |
| `action_taken` | Data | Action that completed task |
| `comments` | Text | User comments |
