"""
Test the Purchase Order Approval Workflow

This script creates test Purchase Orders and runs them through the workflow.

Usage:
    bench --site xs.local execute xstate_workflow.fixtures.test_po_workflow.run_tests
"""

import json
import frappe
from frappe.utils import nowdate, add_days


def get_or_create_test_supplier():
    """Get or create a test supplier."""
    supplier_name = "Test Supplier - Workflow"
    if not frappe.db.exists("Supplier", supplier_name):
        supplier = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": supplier_name,
            "supplier_group": frappe.db.get_single_value("Buying Settings", "supplier_group") or "All Supplier Groups",
            "supplier_type": "Company",
        })
        supplier.insert(ignore_permissions=True)
        print(f"Created supplier: {supplier_name}")
    return supplier_name


def get_or_create_test_item():
    """Get or create a test item."""
    item_code = "TEST-ITEM-WORKFLOW"
    if not frappe.db.exists("Item", item_code):
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": item_code,
            "item_name": "Test Item for Workflow",
            "item_group": "All Item Groups",
            "stock_uom": "Nos",
            "is_stock_item": 0,
            "is_purchase_item": 1,
        })
        item.insert(ignore_permissions=True)
        print(f"Created item: {item_code}")
    return item_code


def get_company():
    """Get the default company."""
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        company = frappe.db.get_value("Company", {}, "name")
    return company


def create_purchase_order(amount, suffix=""):
    """Create a test Purchase Order with specified amount."""
    supplier = get_or_create_test_supplier()
    item_code = get_or_create_test_item()
    company = get_company()

    # Calculate qty and rate to get desired amount
    rate = amount
    qty = 1

    po = frappe.get_doc({
        "doctype": "Purchase Order",
        "supplier": supplier,
        "company": company,
        "transaction_date": nowdate(),
        "schedule_date": add_days(nowdate(), 7),
        "items": [{
            "item_code": item_code,
            "qty": qty,
            "rate": rate,
            "schedule_date": add_days(nowdate(), 7),
        }],
    })
    po.insert(ignore_permissions=True)
    print(f"Created PO: {po.name} with amount: {po.grand_total}{suffix}")
    return po


def start_workflow(doctype, docname):
    """Start the workflow on a document."""
    from xstate_workflow.workflow_engine import get_or_create_instance, get_machine_state

    instance_name = get_or_create_instance(doctype, docname)
    state = get_machine_state(doctype, docname)

    print(f"  Workflow started - Instance: {instance_name}")
    print(f"  Current state: {state.get('current_state')}")
    return instance_name, state


def trigger_event(doctype, docname, event, data=None):
    """Trigger a workflow event."""
    from xstate_workflow.workflow_engine import trigger_event_sync

    result = trigger_event_sync(
        doctype=doctype,
        docname=docname,
        event=event,
        data=json.dumps(data or {})
    )

    if result.get("success"):
        print(f"  ✅ Event '{event}' → New state: {result.get('new_state')}")
    else:
        print(f"  ❌ Event '{event}' failed: {result.get('error')}")

    return result


def get_current_state(doctype, docname):
    """Get current workflow state."""
    from xstate_workflow.workflow_engine import get_machine_state
    return get_machine_state(doctype, docname)


def print_available_events(state):
    """Print available events for current state."""
    events = state.get("available_events", [])
    if events:
        enabled = [e["event"] for e in events if e.get("enabled")]
        disabled = [e["event"] for e in events if not e.get("enabled")]
        if enabled:
            print(f"  Available events: {', '.join(enabled)}")
        if disabled:
            print(f"  Disabled events: {', '.join(disabled)}")
    else:
        print("  No events available (final state)")


def test_auto_approval_path():
    """Test the auto-approval path for small orders (< 10K)."""
    print("\n" + "=" * 60)
    print("TEST 1: Auto-Approval Path (Amount < 10,000)")
    print("=" * 60)

    # Create PO with small amount
    po = create_purchase_order(5000, " (small order)")

    # Start workflow
    print("\n1. Starting workflow...")
    instance, state = start_workflow("Purchase Order", po.name)
    print_available_events(state)

    # Submit for review
    print("\n2. Submitting for review...")
    result = trigger_event("Purchase Order", po.name, "SUBMIT_FOR_REVIEW")

    # Check state after submission
    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")
    print_available_events(state)

    # Approve - should auto-route to auto_approved then to approved
    print("\n3. Approving (should auto-approve due to amount < 10K)...")
    result = trigger_event("Purchase Order", po.name, "APPROVE")

    # Check final state
    state = get_current_state("Purchase Order", po.name)
    print(f"  Final state: {state.get('current_state')}")

    # Check context
    context = state.get("context", {})
    if context.get("auto_approved"):
        print(f"  ✅ Auto-approved: Yes")
        print(f"  ✅ Reason: {context.get('auto_approved_reason', 'N/A')}")

    return po.name


def test_manager_approval_path():
    """Test the manager approval path for mid-range orders (10K - 100K)."""
    print("\n" + "=" * 60)
    print("TEST 2: Manager Approval Path (10,000 <= Amount <= 100,000)")
    print("=" * 60)

    # Create PO with mid-range amount
    po = create_purchase_order(50000, " (mid-range order)")

    # Start workflow
    print("\n1. Starting workflow...")
    instance, state = start_workflow("Purchase Order", po.name)

    # Submit for review
    print("\n2. Submitting for review...")
    trigger_event("Purchase Order", po.name, "SUBMIT_FOR_REVIEW")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")
    print_available_events(state)

    # Approve - should go to manager_approval
    print("\n3. Approving (should route to manager_approval)...")
    result = trigger_event("Purchase Order", po.name, "APPROVE")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")
    print_available_events(state)

    # Manager approves
    print("\n4. Manager approving...")
    result = trigger_event("Purchase Order", po.name, "APPROVE", {
        "comments": "Approved by manager - looks good"
    })

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")

    # Check approval history in context
    context = state.get("context", {})
    approval_history = context.get("approval_history", [])
    if approval_history:
        print(f"  Approval history: {len(approval_history)} entries")
        for entry in approval_history:
            print(f"    - {entry.get('action')} by {entry.get('user')} at {entry.get('timestamp')}")

    return po.name


def test_parallel_approval_path():
    """Test the parallel approval path for high-value orders (> 100K)."""
    print("\n" + "=" * 60)
    print("TEST 3: Parallel Approval Path (Amount > 100,000)")
    print("=" * 60)

    # Create PO with high amount
    po = create_purchase_order(150000, " (high-value order)")

    # Start workflow
    print("\n1. Starting workflow...")
    instance, state = start_workflow("Purchase Order", po.name)

    # Submit for review
    print("\n2. Submitting for review...")
    trigger_event("Purchase Order", po.name, "SUBMIT_FOR_REVIEW")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")

    # Approve - should go to parallel_approval
    print("\n3. Approving (should route to parallel_approval)...")
    result = trigger_event("Purchase Order", po.name, "APPROVE")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")
    print_available_events(state)

    # Finance approves
    print("\n4. Finance approving...")
    result = trigger_event("Purchase Order", po.name, "APPROVE_FINANCE")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")
    context = state.get("context", {})
    print(f"  Finance approved: {context.get('finance_approved')}")
    print(f"  Legal approved: {context.get('legal_approved')}")
    print_available_events(state)

    # Legal approves
    print("\n5. Legal approving...")
    result = trigger_event("Purchase Order", po.name, "APPROVE_LEGAL")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")
    context = state.get("context", {})
    print(f"  Finance approved: {context.get('finance_approved')}")
    print(f"  Legal approved: {context.get('legal_approved')}")

    return po.name


def test_pause_resume():
    """Test the pause and resume (history state) functionality."""
    print("\n" + "=" * 60)
    print("TEST 4: Pause and Resume (History State)")
    print("=" * 60)

    # Create PO
    po = create_purchase_order(8000, " (for pause/resume test)")

    # Start workflow
    print("\n1. Starting workflow...")
    start_workflow("Purchase Order", po.name)

    # Submit for review
    print("\n2. Submitting for review...")
    trigger_event("Purchase Order", po.name, "SUBMIT_FOR_REVIEW")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")

    # Pause
    print("\n3. Pausing workflow...")
    trigger_event("Purchase Order", po.name, "PAUSE")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")
    context = state.get("context", {})
    print(f"  Paused from: {context.get('paused_from_state')}")

    # Resume
    print("\n4. Resuming workflow...")
    trigger_event("Purchase Order", po.name, "RESUME")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")
    print(f"  ✅ Resumed to previous state!")

    return po.name


def test_rejection_path():
    """Test the rejection path."""
    print("\n" + "=" * 60)
    print("TEST 5: Rejection Path")
    print("=" * 60)

    # Create PO
    po = create_purchase_order(25000, " (for rejection test)")

    # Start workflow
    print("\n1. Starting workflow...")
    start_workflow("Purchase Order", po.name)

    # Submit for review
    print("\n2. Submitting for review...")
    trigger_event("Purchase Order", po.name, "SUBMIT_FOR_REVIEW")

    # Reject at review stage
    print("\n3. Rejecting at review stage...")
    trigger_event("Purchase Order", po.name, "REJECT", {
        "rejection_reason": "Budget not approved for this quarter"
    })

    state = get_current_state("Purchase Order", po.name)
    print(f"  Final state: {state.get('current_state')}")
    print(f"  Is final: {state.get('is_final')}")

    context = state.get("context", {})
    print(f"  Rejection reason: {context.get('rejection_reason')}")

    return po.name


def test_supplier_flow():
    """Test the supplier communication flow."""
    print("\n" + "=" * 60)
    print("TEST 6: Supplier Communication Flow")
    print("=" * 60)

    # Create and approve a PO
    po = create_purchase_order(5000, " (for supplier flow test)")

    # Quick path to approved state
    print("\n1. Quick approval path...")
    start_workflow("Purchase Order", po.name)
    trigger_event("Purchase Order", po.name, "SUBMIT_FOR_REVIEW")
    trigger_event("Purchase Order", po.name, "APPROVE")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")
    print_available_events(state)

    # Send to supplier
    print("\n2. Sending to supplier...")
    trigger_event("Purchase Order", po.name, "SEND_TO_SUPPLIER")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")
    context = state.get("context", {})
    print(f"  Sent at: {context.get('sent_to_supplier_at')}")
    print_available_events(state)

    # Supplier confirms
    print("\n3. Supplier confirming receipt...")
    trigger_event("Purchase Order", po.name, "CONFIRM_RECEIPT", {
        "confirmation_reference": "SUP-CONF-12345"
    })

    state = get_current_state("Purchase Order", po.name)
    print(f"  Final state: {state.get('current_state')}")
    print(f"  Is final: {state.get('is_final')}")
    context = state.get("context", {})
    print(f"  Confirmation ref: {context.get('supplier_confirmation_ref')}")
    print(f"  Total workflow hours: {context.get('total_workflow_hours')}")

    return po.name


def cleanup_test_data(po_names):
    """Clean up test Purchase Orders and their workflow instances."""
    print("\n" + "=" * 60)
    print("CLEANUP")
    print("=" * 60)

    for po_name in po_names:
        # Delete workflow instance
        instances = frappe.get_all(
            "Machine Instance",
            filters={
                "reference_doctype": "Purchase Order",
                "reference_name": po_name
            },
            pluck="name"
        )
        for instance in instances:
            frappe.delete_doc("Machine Instance", instance, force=True)

        # Delete PO
        if frappe.db.exists("Purchase Order", po_name):
            frappe.delete_doc("Purchase Order", po_name, force=True)

        print(f"  Deleted: {po_name}")

    frappe.db.commit()
    print("  ✅ Cleanup complete")


def run_tests(cleanup=False):
    """Run all workflow tests."""
    print("\n" + "=" * 60)
    print("PURCHASE ORDER WORKFLOW TESTS")
    print("=" * 60)

    po_names = []

    try:
        # Test 1: Auto-approval path
        po_names.append(test_auto_approval_path())
        frappe.db.commit()

        # Test 2: Manager approval path
        po_names.append(test_manager_approval_path())
        frappe.db.commit()

        # Test 3: Parallel approval path
        po_names.append(test_parallel_approval_path())
        frappe.db.commit()

        # Test 4: Pause and resume
        po_names.append(test_pause_resume())
        frappe.db.commit()

        # Test 5: Rejection
        po_names.append(test_rejection_path())
        frappe.db.commit()

        # Test 6: Supplier flow
        po_names.append(test_supplier_flow())
        frappe.db.commit()

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)
        print(f"\nCreated {len(po_names)} test Purchase Orders:")
        for name in po_names:
            print(f"  - {name}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        frappe.db.rollback()

    finally:
        if cleanup:
            cleanup_test_data(po_names)

    return po_names


if __name__ == "__main__":
    run_tests()
