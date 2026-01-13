"""Simple test of workflow submit hook"""
import frappe


def test():
    """Create a new invoice, reject it, and try to submit"""
    from xstate_workflow.workflow_engine import trigger_event_sync

    # Get test data
    po = frappe.get_doc("Purchase Order", {"supplier": "Test Supplier - Workflow"})
    pr = frappe.get_doc("Purchase Receipt", {"supplier": "Test Supplier - Workflow"})
    company = frappe.db.get_value("Company", {}, "name")
    cost_center = frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name")
    expense_account = frappe.db.get_value("Account", {"company": company, "account_type": "Stock"}, "name")

    # Create invoice WITH PO/PR links to trigger variance detection
    print("1. Creating new invoice with PO/PR links (price variance)...")
    pi = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": po.supplier,
        "company": company,
        "items": [{
            "item_code": po.items[1].item_code,
            "qty": 1,  # Small qty
            "rate": 250.00,  # Price variance (PO rate is 200)
            "purchase_order": po.name,
            "po_detail": po.items[1].name,
            "purchase_receipt": pr.name,
            "pr_detail": pr.items[1].name,
            "cost_center": cost_center,
            "expense_account": expense_account
        }]
    })
    pi.insert(ignore_permissions=True)
    print(f"   Created: {pi.name} (linked to PO {po.name})")

    # Trigger workflow
    print("\n2. Triggering workflow SUBMIT...")
    result = trigger_event_sync("Purchase Invoice", pi.name, "SUBMIT", {})
    print(f"   State: {result.get('new_state')}")

    # Reject
    print("\n3. Rejecting...")
    result = trigger_event_sync("Purchase Invoice", pi.name, "REJECT", {})
    print(f"   State: {result.get('new_state')}")

    # Check workflow state
    state = frappe.db.get_value(
        "Machine Instance",
        {"reference_doctype": "Purchase Invoice", "reference_name": pi.name},
        ["current_state", "status"],
        as_dict=True
    )
    print(f"   Workflow: {state}")

    # Try to submit
    print("\n4. Attempting to submit rejected invoice...")
    try:
        pi.reload()
        pi.submit()
        print("   FAILED: Invoice was submitted (should have been blocked)!")
    except frappe.ValidationError as e:
        error_msg = str(e)
        if "workflow" in error_msg.lower() or "rejected" in error_msg.lower():
            print(f"   SUCCESS: Blocked by workflow validation!")
            print(f"   Message: {error_msg[:200]}")
        else:
            print(f"   Blocked by other validation: {error_msg[:200]}")
    except Exception as e:
        print(f"   Error: {type(e).__name__}: {e}")

    # Cleanup
    print("\n5. Cleaning up...")
    frappe.db.rollback()
    print("   Done!")
