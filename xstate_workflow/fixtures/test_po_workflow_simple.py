"""
Simple test for Purchase Order Approval Workflow (no email)

This test creates a minimal workflow without email notifications to test core functionality.

Usage:
    bench --site xs.local execute xstate_workflow.fixtures.test_po_workflow_simple.run_tests
"""

import json
import frappe
from frappe.utils import nowdate, add_days


def get_simple_workflow_config():
    """Build a simple workflow config without notifications."""
    return {
        "id": "po_approval_simple",
        "initial": "draft",
        "context": {
            "escalation_count": 0,
            "approval_history": [],
        },
        "states": {
            "draft": {
                "on": {
                    "SUBMIT_FOR_REVIEW": {
                        "target": "review",
                    },
                },
            },
            "review": {
                "on": {
                    "APPROVE": [
                        {
                            "target": "auto_approved",
                            "guard": "amount_under_10k",
                        },
                        {
                            "target": "manager_approval",
                            "guard": "amount_10k_to_100k",
                        },
                        {
                            "target": "director_approval",
                            "guard": "amount_over_100k",
                        },
                    ],
                    "REJECT": "rejected",
                    "PAUSE": "paused",
                },
            },
            "paused": {
                "on": {
                    "RESUME": "review",
                    "CANCEL": "cancelled",
                },
            },
            "auto_approved": {
                "entry": ["set_auto_approved"],
                "always": [{"target": "approved"}],
            },
            "manager_approval": {
                "on": {
                    "APPROVE": {
                        "target": "approved",
                        "actions": ["record_approval"],
                    },
                    "REJECT": "rejected",
                },
            },
            "director_approval": {
                "on": {
                    "APPROVE": {
                        "target": "approved",
                        "actions": ["record_approval"],
                    },
                    "REJECT": "rejected",
                },
            },
            "approved": {
                "meta": {
                    "domain_node": {
                        "type": "end",
                        "final_status": "Approved",
                    },
                },
                "on": {
                    "SEND_TO_SUPPLIER": "sent_to_supplier",
                },
            },
            "sent_to_supplier": {
                "on": {
                    "CONFIRM_RECEIPT": "order_confirmed",
                },
            },
            "order_confirmed": {
                "type": "final",
                "meta": {
                    "domain_node": {
                        "type": "end",
                        "final_status": "Completed",
                    },
                },
            },
            "rejected": {
                "type": "final",
                "meta": {
                    "domain_node": {
                        "type": "end",
                        "final_status": "Rejected",
                    },
                },
            },
            "cancelled": {
                "type": "final",
                "meta": {
                    "domain_node": {
                        "type": "end",
                        "final_status": "Cancelled",
                    },
                },
            },
        },
    }


def get_simple_guards():
    """Simple guards for amount-based routing."""
    return [
        {
            "guard_name": "amount_under_10k",
            "description": "Amount under 10,000",
            "python_code": "doc.grand_total < 10000",
        },
        {
            "guard_name": "amount_10k_to_100k",
            "description": "Amount between 10K and 100K",
            "python_code": "doc.grand_total >= 10000 and doc.grand_total <= 100000",
        },
        {
            "guard_name": "amount_over_100k",
            "description": "Amount over 100,000",
            "python_code": "doc.grand_total > 100000",
        },
    ]


def get_simple_actions():
    """Simple actions without email."""
    return [
        {
            "action_name": "set_auto_approved",
            "action_type": "entry",
            "description": "Set auto-approved flag",
            "python_code": """
context['auto_approved'] = True
context['auto_approved_at'] = str(frappe.utils.now_datetime())
context['approval_type'] = 'Auto'
frappe.logger().info(f"PO {doc.name} auto-approved (amount: {doc.grand_total})")
""",
        },
        {
            "action_name": "record_approval",
            "action_type": "transition",
            "description": "Record approval in context",
            "python_code": """
if 'approval_history' not in context:
    context['approval_history'] = []

context['approval_history'].append({
    'action': 'APPROVE',
    'user': frappe.session.user,
    'timestamp': str(frappe.utils.now_datetime())
})
context['last_approved_by'] = frappe.session.user
context['last_approved_at'] = str(frappe.utils.now_datetime())
frappe.logger().info(f"PO {doc.name} approved by {frappe.session.user}")
""",
        },
    ]


def create_simple_workflow(force=False):
    """Create the simple test workflow."""
    machine_id = "po_approval_simple"

    if frappe.db.exists("State Machine", {"machine_id": machine_id}):
        if force:
            frappe.delete_doc("State Machine", machine_id, force=True)
            frappe.db.commit()
        else:
            return frappe.get_doc("State Machine", machine_id)

    machine = frappe.get_doc({
        "doctype": "State Machine",
        "machine_id": machine_id,
        "title": "Simple PO Approval (Test)",
        "description": "Simplified workflow for testing",
        "json_config": json.dumps(get_simple_workflow_config(), indent=2),
        "attached_doctype": "Purchase Order",
        "is_active": 1,
        "auto_start_on_create": 0,
        "xstate_version": "v5",
        "guards_table": get_simple_guards(),
        "actions_table": get_simple_actions(),
    })
    machine.insert(ignore_permissions=True)
    frappe.db.commit()

    print(f"✅ Created simple workflow: {machine.title}")
    return machine


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
    return item_code


def get_company():
    """Get the default company."""
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        company = frappe.db.get_value("Company", {}, "name")
    return company


def create_purchase_order(amount, suffix=""):
    """Create a test Purchase Order."""
    supplier = get_or_create_test_supplier()
    item_code = get_or_create_test_item()
    company = get_company()

    po = frappe.get_doc({
        "doctype": "Purchase Order",
        "supplier": supplier,
        "company": company,
        "transaction_date": nowdate(),
        "schedule_date": add_days(nowdate(), 7),
        "items": [{
            "item_code": item_code,
            "qty": 1,
            "rate": amount,
            "schedule_date": add_days(nowdate(), 7),
        }],
    })
    po.insert(ignore_permissions=True)
    print(f"Created PO: {po.name} with amount: {po.grand_total}{suffix}")
    return po


def start_workflow(doctype, docname, machine_id="po_approval_simple"):
    """Start the workflow on a document."""
    from xstate_workflow.workflow_engine import get_or_create_instance, get_machine_state

    # Get or create instance using the simple workflow
    instance = frappe.db.get_value(
        "Machine Instance",
        {"reference_doctype": doctype, "reference_name": docname},
        "name"
    )

    if not instance:
        machine = frappe.get_doc("State Machine", machine_id)
        config = json.loads(machine.json_config)

        instance_doc = frappe.get_doc({
            "doctype": "Machine Instance",
            "machine": machine_id,
            "reference_doctype": doctype,
            "reference_name": docname,
            "current_state": config.get("initial", "draft"),
            "status": "active",
            "context": json.dumps(config.get("context", {})),
        })
        instance_doc.insert(ignore_permissions=True)
        instance = instance_doc.name

    state = get_machine_state(doctype, docname)
    print(f"  Workflow started - Instance: {instance}")
    print(f"  Current state: {state.get('current_state')}")
    return instance, state


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
    """Print available events."""
    events = state.get("available_events", [])
    if events:
        enabled = [e["event"] for e in events if e.get("enabled")]
        if enabled:
            print(f"  Available events: {', '.join(enabled)}")
    else:
        print("  No events available (final state)")


def test_auto_approval_path():
    """Test auto-approval for small orders."""
    print("\n" + "=" * 60)
    print("TEST 1: Auto-Approval Path (Amount < 10,000)")
    print("=" * 60)

    po = create_purchase_order(5000, " (small order)")

    print("\n1. Starting workflow...")
    instance, state = start_workflow("Purchase Order", po.name)
    print_available_events(state)

    print("\n2. Submitting for review...")
    trigger_event("Purchase Order", po.name, "SUBMIT_FOR_REVIEW")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")
    print_available_events(state)

    print("\n3. Approving (should auto-approve)...")
    trigger_event("Purchase Order", po.name, "APPROVE")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Final state: {state.get('current_state')}")

    context = state.get("context", {})
    if context.get("auto_approved"):
        print(f"  ✅ Auto-approved: Yes")

    return po.name


def test_manager_approval_path():
    """Test manager approval for mid-range orders."""
    print("\n" + "=" * 60)
    print("TEST 2: Manager Approval Path (10K - 100K)")
    print("=" * 60)

    po = create_purchase_order(50000, " (mid-range order)")

    print("\n1. Starting workflow...")
    instance, state = start_workflow("Purchase Order", po.name)

    print("\n2. Submitting for review...")
    trigger_event("Purchase Order", po.name, "SUBMIT_FOR_REVIEW")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")
    print_available_events(state)

    print("\n3. Approving (should go to manager_approval)...")
    trigger_event("Purchase Order", po.name, "APPROVE")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")
    print_available_events(state)

    print("\n4. Manager approving...")
    trigger_event("Purchase Order", po.name, "APPROVE")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")

    context = state.get("context", {})
    if context.get("approval_history"):
        print(f"  Approval history: {len(context['approval_history'])} entries")

    return po.name


def test_director_approval_path():
    """Test director approval for high-value orders."""
    print("\n" + "=" * 60)
    print("TEST 3: Director Approval Path (> 100K)")
    print("=" * 60)

    po = create_purchase_order(150000, " (high-value order)")

    print("\n1. Starting workflow...")
    instance, state = start_workflow("Purchase Order", po.name)

    print("\n2. Submitting for review...")
    trigger_event("Purchase Order", po.name, "SUBMIT_FOR_REVIEW")

    print("\n3. Approving (should go to director_approval)...")
    trigger_event("Purchase Order", po.name, "APPROVE")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")

    print("\n4. Director approving...")
    trigger_event("Purchase Order", po.name, "APPROVE")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")

    return po.name


def test_full_flow():
    """Test the full flow from draft to order confirmed."""
    print("\n" + "=" * 60)
    print("TEST 4: Full Flow (Draft → Order Confirmed)")
    print("=" * 60)

    po = create_purchase_order(5000, " (full flow test)")

    print("\n1. Starting workflow...")
    start_workflow("Purchase Order", po.name)

    print("\n2. Submit → Review → Approve → Approved...")
    trigger_event("Purchase Order", po.name, "SUBMIT_FOR_REVIEW")
    trigger_event("Purchase Order", po.name, "APPROVE")

    print("\n3. Send to supplier...")
    trigger_event("Purchase Order", po.name, "SEND_TO_SUPPLIER")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")

    print("\n4. Confirm receipt...")
    trigger_event("Purchase Order", po.name, "CONFIRM_RECEIPT")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Final state: {state.get('current_state')}")
    print(f"  Is final: {state.get('is_final')}")

    return po.name


def test_rejection():
    """Test rejection path."""
    print("\n" + "=" * 60)
    print("TEST 5: Rejection Path")
    print("=" * 60)

    po = create_purchase_order(25000, " (for rejection)")

    print("\n1. Starting and submitting...")
    start_workflow("Purchase Order", po.name)
    trigger_event("Purchase Order", po.name, "SUBMIT_FOR_REVIEW")

    print("\n2. Rejecting...")
    trigger_event("Purchase Order", po.name, "REJECT")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Final state: {state.get('current_state')}")
    print(f"  Is final: {state.get('is_final')}")

    return po.name


def test_pause_resume():
    """Test pause and resume."""
    print("\n" + "=" * 60)
    print("TEST 6: Pause and Resume")
    print("=" * 60)

    po = create_purchase_order(8000, " (pause/resume test)")

    print("\n1. Starting and submitting...")
    start_workflow("Purchase Order", po.name)
    trigger_event("Purchase Order", po.name, "SUBMIT_FOR_REVIEW")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")

    print("\n2. Pausing...")
    trigger_event("Purchase Order", po.name, "PAUSE")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")

    print("\n3. Resuming...")
    trigger_event("Purchase Order", po.name, "RESUME")

    state = get_current_state("Purchase Order", po.name)
    print(f"  Current state: {state.get('current_state')}")

    return po.name


def cleanup_test_data(po_names):
    """Clean up test data."""
    print("\n" + "=" * 60)
    print("CLEANUP")
    print("=" * 60)

    for po_name in po_names:
        instances = frappe.get_all(
            "Machine Instance",
            filters={"reference_doctype": "Purchase Order", "reference_name": po_name},
            pluck="name"
        )
        for instance in instances:
            frappe.delete_doc("Machine Instance", instance, force=True)

        if frappe.db.exists("Purchase Order", po_name):
            frappe.delete_doc("Purchase Order", po_name, force=True)

        print(f"  Deleted: {po_name}")

    frappe.db.commit()


def run_tests(cleanup=False):
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SIMPLE PURCHASE ORDER WORKFLOW TESTS")
    print("=" * 60)

    # First, create the simple workflow
    create_simple_workflow(force=True)

    po_names = []

    try:
        po_names.append(test_auto_approval_path())
        frappe.db.commit()

        po_names.append(test_manager_approval_path())
        frappe.db.commit()

        po_names.append(test_director_approval_path())
        frappe.db.commit()

        po_names.append(test_full_flow())
        frappe.db.commit()

        po_names.append(test_rejection())
        frappe.db.commit()

        po_names.append(test_pause_resume())
        frappe.db.commit()

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)

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
