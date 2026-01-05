# Sales Order Approval Workflow Demo

This demo showcases a complete Sales Order approval workflow using XState Workflow.

## Scenario

A company requires approval workflows for Sales Orders:
- **Low-value orders** (≤ 100,000): Go to a Reviewer for assessment
- **High-value orders** (> 100,000): Go directly to Sales Manager for approval

## Demo Users

| User | Email | Role | Responsibility |
|------|-------|------|----------------|
| Brad Pitt | brad.pitt@example.com | Sales User | Creates Sales Orders |
| Angelina Jolie | angelina.jolie@example.com | Sales Manager | Approves high-value orders |
| Black Jack | black.jack@example.com | Reviewer | Reviews low-value orders |

**Default password for all demo users:** `demo1234`

## Workflow States

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
┌──────────┐   SUBMIT    ┌──────────────────┐   APPROVE  │  ┌──────────┐
│          │────────────▶│ pending_approval │───────────────▶│          │
│  draft   │  (> 100K)   │ (Sales Manager)  │             │  │ approved │
│          │             └────────┬─────────┘             │  │  (final) │
└──────────┘                      │                       │  └──────────┘
     │                            │ SEND_TO_REVIEW        │       ▲
     │ SUBMIT                     │                       │       │
     │ (≤ 100K)                   ▼                       │       │
     │               ┌─────────────────┐                  │       │
     │               │ pending_review  │   COMPLETE       │       │
     └──────────────▶│   (Reviewer)    │───────────▶ reviewed ───┘
                     └────────┬────────┘              (auto)
                              │
                              │ REJECT    ┌──────────┐
                              └──────────▶│ rejected │
                                          │  (final) │
                                          └────┬─────┘
                                               │
                                               │ RESUBMIT
                                               └──────────▶ draft
```

## Setup Instructions

### 1. Run the Demo Setup

```bash
# Complete setup (users, roles, state machine, sample orders)
bench --site your-site.local execute xstate_workflow.xstate_workflow.demo.setup_demo.setup_all
```

### 2. Access the Visual Builder

Open in browser:
```
http://your-site.local/workflow-builder?machine=sales_order_approval
```

### 3. View the State Machine

In Frappe Desk:
1. Go to **State Machine** list
2. Click on **sales_order_approval**
3. View the JSON configuration and guards/actions

## Testing the Workflow

### Manual Testing via Bench

```bash
# Run the automated test
bench --site your-site.local execute xstate_workflow.xstate_workflow.demo.setup_demo.test_workflow
```

### Testing via API

```python
import frappe
from xstate_workflow.workflow_engine import trigger_event, get_current_state

# Check state of a high-value order
instance_id = "sales_order_approval:SO-DEMO-001"
state = get_current_state(instance_id)
print(f"Current state: {state}")  # draft

# Login as Brad Pitt and submit
frappe.set_user("brad.pitt@example.com")
new_state = trigger_event(instance_id, "SUBMIT")
print(f"After SUBMIT: {new_state}")  # pending_approval (because > 100K)

# Login as Angelina Jolie and approve
frappe.set_user("angelina.jolie@example.com")
new_state = trigger_event(instance_id, "APPROVE")
print(f"After APPROVE: {new_state}")  # approved
```

### Testing via REST API

```bash
# Get workflow state
curl -X GET "http://your-site.local/api/method/xstate_workflow.api.workflow.get_workflow_state" \
  -H "Authorization: token api_key:api_secret" \
  -d "machine_id=sales_order_approval" \
  -d "document_name=SO-DEMO-001"

# Trigger transition
curl -X POST "http://your-site.local/api/method/xstate_workflow.api.workflow.trigger_workflow_event" \
  -H "Authorization: token api_key:api_secret" \
  -d "machine_id=sales_order_approval" \
  -d "document_name=SO-DEMO-001" \
  -d "event=SUBMIT"
```

## Sample Orders

| Order ID | Grand Total | Expected Route |
|----------|-------------|----------------|
| SO-DEMO-001 | 150,000 | draft → pending_approval → approved |
| SO-DEMO-002 | 50,000 | draft → pending_review → reviewed → approved |
| SO-DEMO-003 | 100,000 | draft → pending_review (edge case, ≤ threshold) |
| SO-DEMO-004 | 250,000 | draft → pending_approval → approved |

## Guards Explained

| Guard | Description |
|-------|-------------|
| `isHighValueOrder` | Returns `true` if `grand_total > 100,000` |
| `isLowValueOrder` | Returns `true` if `grand_total <= 100,000` |
| `canApprove` | User is Sales Manager AND not the order creator |
| `canReview` | User is assigned reviewer AND not the order creator |
| `isSalesManager` | User has Sales Manager role |
| `isReviewer` | User is the assigned reviewer (Black Jack) |

## Actions Explained

| Action | Description |
|--------|-------------|
| `recordSubmission` | Records submitter and timestamp |
| `assignToSalesManager` | Creates ToDo for Angelina Jolie |
| `assignToReviewer` | Creates ToDo for Black Jack |
| `recordApproval` | Records approver and timestamp |
| `recordRejection` | Records rejector, reason, and timestamp |
| `notifyCreatorApproved` | Sends email to order creator |
| `notifyCreatorRejected` | Sends email with rejection reason |
| `notifySalesManager` | Sends email to Sales Manager |
| `notifyReviewer` | Sends email to Reviewer |
| `logWorkflowEvent` | Creates audit log entry |

## Trigger Configuration

Each transition can have button triggers configured:

```json
{
  "trigger": {
    "button": {
      "enabled": true,
      "label": "Submit for Approval",
      "style": "primary",
      "allowedRoles": ["Sales User"]
    }
  }
}
```

Button styles: `primary`, `secondary`, `success`, `danger`, `warning`

## Cleanup

To remove all demo data:

```bash
bench --site your-site.local execute xstate_workflow.xstate_workflow.demo.setup_demo.cleanup_demo
```

## Customization

### Modify the Value Threshold

Edit `xstate_workflow/xstate_workflow/logic/sales_order_approval.py`:

```python
HIGH_VALUE_THRESHOLD = 100000  # Change this value
```

### Add New Guards

1. Add the Python function in `sales_order_approval.py`
2. Register it in the `guards` dict
3. Reference it in the State Machine JSON config

### Add New Actions

1. Add the Python function in `sales_order_approval.py`
2. Register it in the `actions` dict
3. Add to transitions in the State Machine JSON config

## Integration with Real Sales Orders

To use this workflow with actual Frappe Sales Orders:

1. Create a Machine Instance when a Sales Order is created
2. Pass the Sales Order fields as context
3. Trigger events based on form actions

Example hook in `hooks.py`:

```python
doc_events = {
    "Sales Order": {
        "after_insert": "xstate_workflow.integrations.sales_order.on_create",
        "on_update": "xstate_workflow.integrations.sales_order.on_update",
    }
}
```

```python
# integrations/sales_order.py
def on_create(doc, method):
    from xstate_workflow.workflow_engine import create_machine_instance

    create_machine_instance(
        machine_id="sales_order_approval",
        document_type="Sales Order",
        document_name=doc.name,
        initial_context={
            "name": doc.name,
            "grand_total": doc.grand_total,
            "owner": doc.owner,
            "customer": doc.customer,
        }
    )
```

## Troubleshooting

### "Guard function not found"

Ensure the logic module is correctly specified in State Machine:
```
logic_module = "xstate_workflow.logic.sales_order_approval"
```

### "Permission denied"

Check that the user has the required role for the transition.

### Emails not sending

Configure email settings in Frappe:
- Setup → Email Domain
- Setup → Email Account

For development, check Error Log for email errors.
