"""Test workflow blocking of document submission"""
import frappe


def setup_and_test():
    """Create a test invoice, reject it, and verify submit is blocked"""

    print("=" * 60)
    print("Testing Workflow Blocking of Document Submission")
    print("=" * 60)

    # First, find an invoice we can test with
    # Use one that doesn't have overbilling issues

    # Get the existing PO and PR
    po_name = frappe.db.get_value("Purchase Order", {"supplier": "Test Supplier - Workflow"}, "name")
    pr_name = frappe.db.get_value("Purchase Receipt", {"supplier": "Test Supplier - Workflow"}, "name")

    if not po_name or not pr_name:
        print("No test data found. Run create_test_data.create_all first.")
        return

    po = frappe.get_doc("Purchase Order", po_name)
    pr = frappe.get_doc("Purchase Receipt", pr_name)

    print(f"Using PO: {po_name}, PR: {pr_name}")

    # Create a new invoice with price variance but matching qty
    # This should trigger workflow but not ERPNext overbilling
    company = frappe.db.get_value("Company", {}, "name")
    cost_center = frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name")
    expense_account = frappe.db.get_value("Account", {"company": company, "account_type": "Stock"}, "name")

    # Use item 2 which has full receipt (5 out of 5)
    pi = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": po.supplier,
        "company": company,
        "items": [{
            "item_code": po.items[1].item_code,
            "qty": 5,  # Matches receipt qty - no overbilling
            "rate": 250.00,  # 25% above PO rate of 200 - price variance!
            "purchase_order": po.name,
            "po_detail": po.items[1].name,
            "purchase_receipt": pr.name,
            "pr_detail": pr.items[1].name,
            "cost_center": cost_center,
            "expense_account": expense_account
        }]
    })
    pi.insert(ignore_permissions=True)
    print(f"\n1. Created test invoice: {pi.name} (25% price variance, no qty variance)")

    # Trigger workflow - should go to pending_purchase_approval
    from xstate_workflow.workflow_engine import trigger_event_sync

    result = trigger_event_sync("Purchase Invoice", pi.name, "SUBMIT", {})
    print(f"2. Triggered workflow: {result.get('new_state')}")

    # Check state
    state = frappe.db.get_value(
        "Machine Instance",
        {"reference_doctype": "Purchase Invoice", "reference_name": pi.name},
        ["current_state", "status"],
        as_dict=True
    )
    print(f"   Current state: {state}")

    # Try to submit while pending - should be blocked
    print(f"\n3. Attempting to submit while PENDING...")
    try:
        pi.reload()
        pi.submit()
        print("   FAIL: Submit succeeded - should have been blocked!")
    except frappe.ValidationError as e:
        if "pending" in str(e).lower() or "workflow" in str(e).lower():
            print(f"   SUCCESS: Blocked by workflow: {e}")
        else:
            print(f"   Blocked by other validation: {e}")

    # Now reject the invoice
    result = trigger_event_sync("Purchase Invoice", pi.name, "REJECT", {})
    print(f"\n4. Rejected invoice: {result.get('new_state')}")

    # Try to submit rejected invoice - should be blocked
    print(f"\n5. Attempting to submit REJECTED invoice...")
    try:
        pi.reload()
        pi.submit()
        print("   FAIL: Submit succeeded - should have been blocked!")
    except frappe.ValidationError as e:
        if "rejected" in str(e).lower() or "workflow" in str(e).lower():
            print(f"   SUCCESS: Blocked by workflow: {e}")
        else:
            print(f"   Blocked by other validation: {e}")

    # Cleanup - delete the test invoice
    frappe.delete_doc("Purchase Invoice", pi.name, force=True)
    # Also delete the machine instance
    mi_name = frappe.db.get_value("Machine Instance",
        {"reference_doctype": "Purchase Invoice", "reference_name": pi.name}, "name")
    if mi_name:
        frappe.delete_doc("Machine Instance", mi_name, force=True)

    print(f"\n6. Cleaned up test invoice")
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
