# XState Workflow Testing Guide

This guide walks through testing the XState Workflow app with a Contact approval workflow.

## Prerequisites

1. Install the app:
```bash
bench --site your-site.local install-app xstate_workflow
pip install xstate-statemachine==0.4.2
```

2. Build the frontend:
```bash
cd apps/xstate_workflow/frontend
npm install
npm run build
```

3. Migrate and restart:
```bash
bench --site your-site.local migrate
bench restart
```

## Test 1: Create Workflow in Visual Builder

1. Navigate to `/workflow-builder`
2. You should see a canvas with one "draft" state
3. Add states:
   - Click "Add State" to add "pending_approval"
   - Click "Add State" to add "approved"
   - Click "Add State" to add "rejected"

4. Set state types:
   - Click "draft" → Set type to "Initial"
   - Click "approved" → Set type to "Final"
   - Click "rejected" → Leave as "Atomic"

5. Create transitions:
   - Drag from "draft" to "pending_approval"
   - Click the edge, set event name to "SUBMIT"
   - Drag from "pending_approval" to "approved"
   - Set event to "APPROVE", add guard "hasApprovalPermission"
   - Drag from "pending_approval" to "rejected"
   - Set event to "REJECT"
   - Drag from "rejected" to "draft"
   - Set event to "RESUBMIT"

6. Configure:
   - Set Machine ID to "contact_approval"
   - Click "Auto Layout" to organize

7. Save:
   - Click "Save"
   - Should see success message

## Test 2: Verify Backend Storage

1. Go to `/app/state-machine/contact_approval`
2. Verify:
   - JSON Config contains XState configuration
   - React Flow Config contains nodes/edges
   - Version is 1

## Test 3: Attach to Contact DocType

1. Edit State Machine "contact_approval"
2. Set "Attached DocType" to "Contact"
3. Enable "Is Active"
4. Save

## Test 4: Trigger Workflow from Console

Open browser console on any Frappe page:

```javascript
// Create a test contact first if needed
frappe.xcall('frappe.client.insert', {
  doc: {
    doctype: 'Contact',
    first_name: 'Test',
    last_name: 'Workflow'
  }
}).then(doc => {
  console.log('Created:', doc.name);
  window.testContact = doc.name;
});

// Check initial state (should be "draft")
frappe.xstate_workflow.get_state('Contact', testContact).then(console.log);

// Submit for approval
frappe.xstate_workflow.trigger_event('Contact', testContact, 'SUBMIT').then(console.log);

// Check state (should be "pending_approval")
frappe.xstate_workflow.get_state('Contact', testContact).then(console.log);

// Approve (if you have permission)
frappe.xstate_workflow.trigger_event('Contact', testContact, 'APPROVE').then(console.log);

// Check final state (should be "approved")
frappe.xstate_workflow.get_state('Contact', testContact).then(console.log);
```

## Test 5: Form Integration

1. Open any Contact document
2. You should see a "Workflow State" section
3. Current state badge should be visible
4. Available action buttons should appear

## Test 6: Python API

In Frappe console (`bench console`):

```python
from xstate_workflow.workflow_engine import (
    trigger_event_sync,
    get_machine_state,
    reset_instance
)

# Get current state
state = get_machine_state('Contact', 'CONT-00001')
print(state)

# Trigger event
result = trigger_event_sync('Contact', 'CONT-00001', 'SUBMIT')
print(result)

# Reset workflow
reset_instance('Contact', 'CONT-00001')
```

## Test 7: Guard Validation

1. Create a guard that always returns False:
   - Edit State Machine
   - Add to Guards table: name="alwaysFail", code="False"
   - Update JSON config to use this guard on APPROVE

2. Try to approve:
```javascript
frappe.xstate_workflow.trigger_event('Contact', testContact, 'APPROVE')
  .then(r => console.log('Should fail:', r));
```

3. Result should show "Transition blocked by guard"

## Test 8: Actions Execution

1. Add an action that updates context:
   - Add to Actions table: name="logApproval", code:
   ```python
   context['log'] = f"Approved by {frappe.session.user}"
   ```

2. Trigger transition with action
3. Check Machine Instance context field for logged data

## Test 9: Export/Import

1. In workflow builder, click "Export"
2. JSON file downloads with full configuration
3. Create new workflow, click "Import"
4. Select exported file
5. Verify nodes/edges are restored

## Test 10: Background Jobs

1. Use async trigger:
```python
from xstate_workflow.workflow_engine import trigger_event

job = trigger_event('Contact', 'CONT-00001', 'SUBMIT')
print(job)  # Contains job_id
```

2. Check job queue: `bench show-queue`
3. Verify transition completed in Machine Instance

## Common Issues

### "No active State Machine attached"
- Ensure Is Active is checked on State Machine
- Ensure Attached DocType matches exactly

### Guards not being called
- Check logic_module path is correct
- Verify guard name matches exactly (case-sensitive)
- Check Error Log for import errors

### React Flow not loading
- Rebuild frontend: `cd frontend && npm run build`
- Clear browser cache
- Check browser console for errors

### Transitions not persisting
- Check Redis is running
- Verify database connection
- Look at Error Log for exceptions

## Performance Testing

For large workflows (50+ states):

1. Test auto-layout performance
2. Monitor save/load times
3. Check browser memory usage
4. Consider pagination for instance list

## Cleanup

Remove test data:
```python
import frappe

# Delete test instances
frappe.db.delete('Machine Instance', {'reference_doctype': 'Contact'})

# Optionally delete test machine
frappe.delete_doc('State Machine', 'contact_approval')

frappe.db.commit()
```
