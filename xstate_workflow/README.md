# XState Workflow for Frappe

A powerful workflow engine powered by XState with a visual React Flow builder for Frappe/ERPNext.

## Features

- **Visual Workflow Builder**: Drag-and-drop React Flow editor at `/workflow-builder`
- **XState Backend**: Full XState state machine execution in Python
- **Any DocType Integration**: Attach workflows to any Frappe DocType
- **Guards & Actions**: Define Python conditions and actions
- **Hierarchical States**: Support for compound and parallel states
- **Real-time Updates**: Socket.io-based live state updates
- **Background Jobs**: Long-running actions via Frappe queue
- **Delayed Transitions**: Scheduled state changes
- **Audit Trail**: Complete transition history logging

## Installation

```bash
# Get the app
bench get-app xstate_workflow

# Install on your site
bench --site your-site.local install-app xstate_workflow

# Install Python dependency
pip install xstate-statemachine==0.4.2

# Build frontend (requires Node.js 18+)
cd apps/xstate_workflow/frontend
npm install
npm run build

# Clear cache and restart
bench --site your-site.local clear-cache
bench restart
```

## Quick Start

### 1. Create a Workflow

Navigate to `/workflow-builder` or go to **State Machine** list and click "New".

**Visual Editor:**
1. Add states by clicking "Add State"
2. Connect states by dragging from source handle to target
3. Click on states/transitions to edit properties
4. Set state types: initial (green), atomic (blue), final (red)
5. Add guards and actions to transitions
6. Click "Save" to persist

### 2. XState JSON Format

```json
{
  "id": "approval_workflow",
  "initial": "draft",
  "context": {
    "approver": null,
    "approved_at": null
  },
  "states": {
    "draft": {
      "on": {
        "SUBMIT": "pending_approval"
      }
    },
    "pending_approval": {
      "on": {
        "APPROVE": {
          "target": "approved",
          "guard": "hasApprovalPermission",
          "actions": ["recordApproval"]
        },
        "REJECT": {
          "target": "rejected",
          "actions": ["recordRejection"]
        }
      }
    },
    "approved": {
      "type": "final",
      "entry": ["notifyApproval"]
    },
    "rejected": {
      "on": {
        "RESUBMIT": "draft"
      }
    }
  }
}
```

### 3. Attach to DocType

Set **Attached DocType** in the State Machine form to link it to a Frappe DocType.

### 4. Trigger Events

**From Client Script:**
```javascript
frappe.xstate_workflow.trigger_event('Contact', 'CONT-001', 'SUBMIT')
  .then(result => {
    console.log('New state:', result.new_state);
  });
```

**From Python:**
```python
from xstate_workflow.workflow_engine import trigger_event_sync

result = trigger_event_sync('Contact', 'CONT-001', 'APPROVE', {'note': 'Looks good'})
print(result['new_state'])
```

## License

MIT License
