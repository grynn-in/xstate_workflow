# Planned Fixes

This document tracks planned fixes and improvements to be reviewed in future implementations.

---

## Critical Bugs

### 5. ~~Domain Nodes Missing `isInitial` Flag~~ (FIXED)

**Status:** ✅ Fixed
**Component:** `frontend/packages/core/src/converters/xstateToWorkflow.ts`

**Issue:**
When loading an existing workflow, domain nodes (like `start`, `approval`, `end`) never received the `isInitial: true` flag, causing "Failed to save: No initial state found in workflow" error.

**Fix Applied:**
Added `isInitial` check after `buildDomainNode()` returns in `processStates()`:
```typescript
if (stateName === initialState && !parentId) {
  domainNode.data.isInitial = true;
}
```

---

## UI/UX Fixes

### 1. ~~Hide Trigger Options for "Always" Transitions~~ (FIXED)

**Status:** ✅ Fixed
**Component:** `frontend/packages/core/src/components/panels/PropertiesPanel.tsx`

**Issue:**
The Trigger configuration section was shown for all transition types, including "always" transitions where it doesn't apply.

**Fix Applied:**
Wrapped the Trigger section in a conditional:
```tsx
{selectedEdge.data.transitionType !== 'always' && (
  <div className="xsw-panel-section">...</div>
)}
```

---

### 2. ~~Guard Builder "Select Field" Dropdown is Empty~~ (FIXED)

**Status:** ✅ Fixed
**Component:** `frontend/packages/frappe-adapter/src/api.ts`

**Issue:**
In the Guard Builder panel, the "Select field" dropdown showed no options even when a DocType was attached.

**Fix Applied:**
- Removed `.docs[0]` accessor from the response handling
- Updated TypeScript type annotation to match actual response structure

---

### 4. ~~Improve Compound Guard Condition Remove Button Styling~~ (FIXED)

**Status:** ✅ Fixed
**Component:** `frontend/packages/core/src/components/panels/GuardBuilderPanel.tsx`

**Issue:**
The X button for removing conditions was poorly placed with absolute positioning, no hover state, and small hit target.

**Fix Applied:**
- Replaced absolute positioning with flexbox layout
- Added condition header with label ("Condition 1", "Condition 2", etc.)
- Styled button with proper size (24x24), border, and hover effects
- Added `aria-label` for accessibility
- Button turns red on hover for clear delete affordance

---

## Performance Improvements

### 3. ~~Replace Polling with Event-Driven Form Detection~~ (FIXED)

**Status:** ✅ Fixed
**Component:** `xstate_workflow/public/js/workflow_client.js`

**Issue:**
The workflow client used `setInterval` polling every 500ms to detect when to add the workflow section to forms, running indefinitely and creating console noise.

**Fix Applied:**
Replaced polling with Frappe's event-driven form hooks:
- Registered `frappe.ui.form.on(doctype, { refresh: ... })` for each attached doctype
- Removed `setInterval` and debug logging
- Kept `page-change` event listener as fallback for edge cases

---

### 6. ~~"Always" Transitions Not Firing on Initial State~~ (FIXED)

**Status:** ✅ Fixed
**Component:** `xstate_workflow/workflow_engine.py`
**Lines:** 1197-1206

**Issue:**
When a workflow instance is first created, the initial state's "always" transitions were not being executed. This caused workflows with a "Start" node (using always transition) to get stuck.

**Root Cause:**
The initialization code executed entry actions for the initial state but did NOT check for "always" transitions. Normal transitions did check for "always" (line 1562-1566), but initialization didn't.

**Fix Applied:**
Added "always" transition check after initial state entry:
```python
# Check for "always" transitions on initial state (auto-transition)
if state_config.get("always"):
    try:
        execute_transition(instance.name, "xstate.always", {})
    except Exception as e:
        frappe.log_error(f"Failed to execute always transition from initial state: {e}")
```

---

## Summary

All planned fixes have been implemented:

| # | Issue | Status |
|---|-------|--------|
| 5 | Domain Nodes Missing `isInitial` Flag | ✅ Fixed |
| 1 | Hide Trigger Options for "Always" Transitions | ✅ Fixed |
| 2 | Guard Builder "Select Field" Dropdown Empty | ✅ Fixed |
| 3 | Replace Polling with Event-Driven Form Detection | ✅ Fixed |
| 4 | Improve Compound Guard Remove Button Styling | ✅ Fixed |
| 6 | "Always" Transitions Not Firing on Initial State | ✅ Fixed |
