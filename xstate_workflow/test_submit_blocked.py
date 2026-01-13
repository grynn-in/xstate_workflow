"""Test that rejected invoice cannot be submitted"""
import frappe

def test_submit_rejected():
    """Try to submit a rejected invoice - should fail"""
    invoice_name = "ACC-PINV-2026-00002"

    print(f"Attempting to submit rejected invoice: {invoice_name}")

    # Check current state
    state = frappe.db.get_value(
        "Machine Instance",
        {"reference_doctype": "Purchase Invoice", "reference_name": invoice_name},
        ["current_state", "status"],
        as_dict=True
    )
    print(f"Current workflow state: {state}")

    # Try to submit
    try:
        doc = frappe.get_doc("Purchase Invoice", invoice_name)
        doc.submit()
        print("ERROR: Submit succeeded - this should have been blocked!")
    except frappe.ValidationError as e:
        print(f"SUCCESS: Submit blocked with message: {e}")
    except Exception as e:
        print(f"OTHER ERROR: {type(e).__name__}: {e}")


def test_submit_pending():
    """Try to submit a pending invoice - should fail"""
    invoice_name = "ACC-PINV-2026-00001"

    print(f"\nAttempting to submit pending invoice: {invoice_name}")

    # Check current state
    state = frappe.db.get_value(
        "Machine Instance",
        {"reference_doctype": "Purchase Invoice", "reference_name": invoice_name},
        ["current_state", "status"],
        as_dict=True
    )
    print(f"Current workflow state: {state}")

    # Try to submit
    try:
        doc = frappe.get_doc("Purchase Invoice", invoice_name)
        doc.submit()
        print("ERROR: Submit succeeded - this should have been blocked!")
    except frappe.ValidationError as e:
        print(f"SUCCESS: Submit blocked with message: {e}")
    except Exception as e:
        print(f"OTHER ERROR: {type(e).__name__}: {e}")


def test_submit_approved():
    """Try to submit an approved invoice - should succeed"""
    invoice_name = "ACC-PINV-2026-00003"

    print(f"\nAttempting to submit approved invoice: {invoice_name}")

    # Check current state
    state = frappe.db.get_value(
        "Machine Instance",
        {"reference_doctype": "Purchase Invoice", "reference_name": invoice_name},
        ["current_state", "status"],
        as_dict=True
    )
    print(f"Current workflow state: {state}")

    # Check docstatus
    docstatus = frappe.db.get_value("Purchase Invoice", invoice_name, "docstatus")
    if docstatus == 1:
        print("Invoice already submitted")
        return

    # Try to submit
    try:
        doc = frappe.get_doc("Purchase Invoice", invoice_name)
        doc.submit()
        print("SUCCESS: Approved invoice submitted successfully!")
    except frappe.ValidationError as e:
        print(f"ERROR: Submit blocked: {e}")
    except Exception as e:
        print(f"OTHER ERROR: {type(e).__name__}: {e}")


def run_all_tests():
    test_submit_rejected()
    test_submit_pending()
    test_submit_approved()
