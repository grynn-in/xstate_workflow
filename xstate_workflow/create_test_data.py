"""
Create test data for Purchase Invoice Variance Approval Workflow

This script creates:
1. Test Supplier
2. Test Items
3. Purchase Orders
4. Purchase Receipts
5. Purchase Invoices with variances (qty and price)

Run with: bench --site xs.local execute xstate_workflow.create_test_data.create_all
"""

import frappe
from frappe.utils import nowdate, add_days


def create_all():
    """Create all test data"""
    print("=" * 60)
    print("Creating Test Data for Purchase Invoice Variance Workflow")
    print("=" * 60)

    # Ensure we have required master data
    company = ensure_company()
    ensure_fiscal_year(company)
    allow_rate_variance()  # Allow price variance for testing
    warehouse = ensure_warehouse(company)
    supplier = create_supplier()
    items = create_items()
    cost_center = ensure_cost_center(company)
    expense_account = ensure_expense_account(company)

    # Create test scenarios
    print("\n[1/3] Creating Purchase Order...")
    po = create_purchase_order(supplier, items, company, warehouse)

    print("\n[2/3] Creating Purchase Receipt (partial qty)...")
    pr = create_purchase_receipt(po, company, warehouse)

    print("\n[3/3] Creating Purchase Invoices with variances...")
    pi_qty_variance = create_invoice_qty_variance(po, pr, company, cost_center, expense_account)
    pi_price_variance = create_invoice_price_variance(po, pr, company, cost_center, expense_account)
    pi_no_variance = create_invoice_no_variance(po, pr, company, cost_center, expense_account)

    frappe.db.commit()

    print("\n" + "=" * 60)
    print("Test Data Created Successfully!")
    print("=" * 60)
    print(f"\nPurchase Order: {po.name}")
    print(f"  - Item 1: {items[0].item_code} @ 100.00 x 10 qty")
    print(f"  - Item 2: {items[1].item_code} @ 200.00 x 5 qty")
    print(f"\nPurchase Receipt: {pr.name}")
    print(f"  - Item 1: received 8 qty (ordered 10)")
    print(f"  - Item 2: received 5 qty (ordered 5)")
    print(f"\nPurchase Invoices:")
    print(f"  1. {pi_qty_variance.name} - QTY VARIANCE (invoice qty 10 > receipt qty 8)")
    print(f"  2. {pi_price_variance.name} - PRICE VARIANCE (rate 110 > PO rate 100, +10%)")
    print(f"  3. {pi_no_variance.name} - NO VARIANCE (matches receipt qty and PO rate)")

    print("\n" + "-" * 60)
    print("To test the workflow, run:")
    print("-" * 60)
    print(f'''
# Test invoice with QTY variance (should trigger approval):
bench --site xs.local execute xstate_workflow.create_test_data.test_workflow --args "['{pi_qty_variance.name}']"

# Test invoice with PRICE variance (should trigger approval):
bench --site xs.local execute xstate_workflow.create_test_data.test_workflow --args "['{pi_price_variance.name}']"

# Test invoice with NO variance (should auto-approve):
bench --site xs.local execute xstate_workflow.create_test_data.test_workflow --args "['{pi_no_variance.name}']"
''')

    return {
        "po": po.name,
        "pr": pr.name,
        "pi_qty_variance": pi_qty_variance.name,
        "pi_price_variance": pi_price_variance.name,
        "pi_no_variance": pi_no_variance.name
    }


def ensure_fiscal_year(company):
    """Ensure a fiscal year exists for current date"""
    from frappe.utils import getdate

    current_date = getdate(nowdate())
    year = current_date.year
    fy_name = str(year)

    if frappe.db.exists("Fiscal Year", fy_name):
        print(f"  Fiscal year {fy_name} already exists")
    else:
        print(f"  Creating fiscal year: {fy_name}")
        fy = frappe.get_doc({
            "doctype": "Fiscal Year",
            "year": fy_name,
            "year_start_date": f"{year}-01-01",
            "year_end_date": f"{year}-12-31"
        })
        fy.insert(ignore_permissions=True)

    # Make sure it's linked to the company
    if not frappe.db.exists("Fiscal Year Company", {"parent": fy_name, "company": company}):
        fy = frappe.get_doc("Fiscal Year", fy_name)
        fy.append("companies", {"company": company})
        fy.save(ignore_permissions=True)
        print(f"  Linked fiscal year {fy_name} to company {company}")


def allow_rate_variance():
    """Temporarily allow rate variance in Buying Settings for testing"""
    # Disable maintain_same_rate entirely
    frappe.db.set_single_value("Buying Settings", "maintain_same_rate", 0)
    frappe.db.set_single_value("Buying Settings", "maintain_same_rate_action", "Warn")
    # Clear cache to ensure the new values are used
    frappe.clear_cache()
    print("  Buying Settings: Disabled rate matching validation")


def ensure_company():
    """Ensure a test company exists"""
    company_name = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company_name:
        # Get any existing company
        company_name = frappe.db.get_value("Company", {}, "name")

    if not company_name:
        print("  Creating test company...")
        company = frappe.get_doc({
            "doctype": "Company",
            "company_name": "Test Company",
            "abbr": "TC",
            "default_currency": "USD",
            "country": "United States"
        })
        company.insert(ignore_permissions=True)
        company_name = company.name

    print(f"  Using company: {company_name}")
    return company_name


def ensure_warehouse(company):
    """Ensure a warehouse exists"""
    warehouse = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")
    if not warehouse:
        warehouse = frappe.db.get_value("Warehouse", {"is_group": 0}, "name")

    if not warehouse:
        print("  Creating test warehouse...")
        wh = frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": "Stores",
            "company": company
        })
        wh.insert(ignore_permissions=True)
        warehouse = wh.name

    print(f"  Using warehouse: {warehouse}")
    return warehouse


def ensure_cost_center(company):
    """Ensure a cost center exists"""
    cost_center = frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name")
    if not cost_center:
        cost_center = frappe.db.get_value("Cost Center", {"is_group": 0}, "name")

    print(f"  Using cost center: {cost_center}")
    return cost_center


def ensure_expense_account(company):
    """Ensure an expense account exists"""
    expense_account = frappe.db.get_value(
        "Account",
        {"company": company, "account_type": "Expense Account", "is_group": 0},
        "name"
    )
    if not expense_account:
        expense_account = frappe.db.get_value(
            "Account",
            {"root_type": "Expense", "is_group": 0},
            "name"
        )

    print(f"  Using expense account: {expense_account}")
    return expense_account


def create_supplier():
    """Create a test supplier"""
    supplier_name = "Test Supplier - Workflow"

    if frappe.db.exists("Supplier", supplier_name):
        print(f"  Supplier '{supplier_name}' already exists")
        return frappe.get_doc("Supplier", supplier_name)

    print(f"  Creating supplier: {supplier_name}")
    supplier = frappe.get_doc({
        "doctype": "Supplier",
        "supplier_name": supplier_name,
        "supplier_group": frappe.db.get_value("Supplier Group", {}, "name") or "All Supplier Groups",
        "supplier_type": "Company"
    })
    supplier.insert(ignore_permissions=True)
    return supplier


def create_items():
    """Create test items"""
    items_config = [
        {"item_code": "TEST-ITEM-001", "item_name": "Test Item 001", "stock_uom": "Nos"},
        {"item_code": "TEST-ITEM-002", "item_name": "Test Item 002", "stock_uom": "Nos"}
    ]

    items = []
    for config in items_config:
        if frappe.db.exists("Item", config["item_code"]):
            print(f"  Item '{config['item_code']}' already exists")
            items.append(frappe.get_doc("Item", config["item_code"]))
        else:
            print(f"  Creating item: {config['item_code']}")
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": config["item_code"],
                "item_name": config["item_name"],
                "item_group": frappe.db.get_value("Item Group", {}, "name") or "All Item Groups",
                "stock_uom": config["stock_uom"],
                "is_stock_item": 1
            })
            item.insert(ignore_permissions=True)
            items.append(item)

    return items


def create_purchase_order(supplier, items, company, warehouse):
    """Create a Purchase Order"""
    # Check if we already have a test PO from this supplier
    existing_po = frappe.db.get_value(
        "Purchase Order",
        {"supplier": supplier.name, "docstatus": 1},
        "name"
    )
    if existing_po:
        print(f"  Using existing PO: {existing_po}")
        return frappe.get_doc("Purchase Order", existing_po)

    po = frappe.get_doc({
        "doctype": "Purchase Order",
        "supplier": supplier.name,
        "company": company,
        "schedule_date": add_days(nowdate(), 7),
        "items": [
            {
                "item_code": items[0].item_code,
                "qty": 10,
                "rate": 100.00,
                "warehouse": warehouse,
                "schedule_date": add_days(nowdate(), 7)
            },
            {
                "item_code": items[1].item_code,
                "qty": 5,
                "rate": 200.00,
                "warehouse": warehouse,
                "schedule_date": add_days(nowdate(), 7)
            }
        ]
    })
    po.insert(ignore_permissions=True)
    po.submit()
    print(f"  Created and submitted PO: {po.name}")
    return po


def create_purchase_receipt(po, company, warehouse):
    """Create a Purchase Receipt with partial qty for first item"""
    # Check if we already have a test PR
    existing_pr = frappe.db.get_value(
        "Purchase Receipt",
        {"supplier": po.supplier, "docstatus": 1},
        "name"
    )
    if existing_pr:
        print(f"  Using existing PR: {existing_pr}")
        return frappe.get_doc("Purchase Receipt", existing_pr)

    pr = frappe.get_doc({
        "doctype": "Purchase Receipt",
        "supplier": po.supplier,
        "company": company,
        "items": [
            {
                "item_code": po.items[0].item_code,
                "qty": 8,  # Partial receipt - only 8 out of 10
                "rate": po.items[0].rate,
                "warehouse": warehouse,
                "purchase_order": po.name,
                "purchase_order_item": po.items[0].name
            },
            {
                "item_code": po.items[1].item_code,
                "qty": 5,  # Full receipt
                "rate": po.items[1].rate,
                "warehouse": warehouse,
                "purchase_order": po.name,
                "purchase_order_item": po.items[1].name
            }
        ]
    })
    pr.insert(ignore_permissions=True)
    pr.submit()
    print(f"  Created and submitted PR: {pr.name}")
    print(f"    - Item 1: received 8 qty (PO had 10)")
    print(f"    - Item 2: received 5 qty (PO had 5)")
    return pr


def create_invoice_qty_variance(po, pr, company, cost_center, expense_account):
    """Create a Purchase Invoice with QTY variance (invoice qty > receipt qty)"""
    pi = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": po.supplier,
        "company": company,
        "items": [
            {
                "item_code": po.items[0].item_code,
                "qty": 10,  # Invoice for 10, but only received 8 - QTY VARIANCE!
                "rate": po.items[0].rate,  # Same rate as PO
                "purchase_order": po.name,
                "po_detail": po.items[0].name,
                "purchase_receipt": pr.name,
                "pr_detail": pr.items[0].name,
                "cost_center": cost_center,
                "expense_account": expense_account
            }
        ]
    })
    pi.insert(ignore_permissions=True)
    print(f"  Created PI with QTY variance: {pi.name}")
    print(f"    - Invoice qty: 10, Receipt qty: 8 (VARIANCE!)")
    return pi


def create_invoice_price_variance(po, pr, company, cost_center, expense_account):
    """Create a Purchase Invoice with PRICE variance (rate > PO rate by >5%)"""
    pi = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": po.supplier,
        "company": company,
        "items": [
            {
                "item_code": po.items[1].item_code,
                "qty": 5,  # Same qty as receipt
                "rate": 220.00,  # PO rate was 200, this is +10% - PRICE VARIANCE!
                "purchase_order": po.name,
                "po_detail": po.items[1].name,
                "purchase_receipt": pr.name,
                "pr_detail": pr.items[1].name,
                "cost_center": cost_center,
                "expense_account": expense_account
            }
        ]
    })
    pi.insert(ignore_permissions=True)
    print(f"  Created PI with PRICE variance: {pi.name}")
    print(f"    - Invoice rate: 220, PO rate: 200 (+10% VARIANCE!)")
    return pi


def create_invoice_no_variance(po, pr, company, cost_center, expense_account):
    """Create a Purchase Invoice with NO variance"""
    pi = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": po.supplier,
        "company": company,
        "items": [
            {
                "item_code": po.items[1].item_code,
                "qty": 5,  # Same qty as receipt
                "rate": 200.00,  # Same rate as PO - NO VARIANCE
                "purchase_order": po.name,
                "po_detail": po.items[1].name,
                "purchase_receipt": pr.name,
                "pr_detail": pr.items[1].name,
                "cost_center": cost_center,
                "expense_account": expense_account
            }
        ]
    })
    pi.insert(ignore_permissions=True)
    print(f"  Created PI with NO variance: {pi.name}")
    print(f"    - Invoice qty: 5, Receipt qty: 5 (OK)")
    print(f"    - Invoice rate: 200, PO rate: 200 (OK)")
    return pi


def test_workflow(invoice_name):
    """Test the workflow by triggering SUBMIT event"""
    from xstate_workflow.workflow_engine import trigger_event_sync

    print(f"\n{'=' * 60}")
    print(f"Testing Workflow for: {invoice_name}")
    print("=" * 60)

    # Get the invoice
    pi = frappe.get_doc("Purchase Invoice", invoice_name)
    print(f"\nInvoice Details:")
    for item in pi.items:
        print(f"  - {item.item_code}: qty={item.qty}, rate={item.rate}")
        if item.pr_detail:
            receipt_qty = frappe.db.get_value("Purchase Receipt Item", item.pr_detail, "qty")
            print(f"    Receipt qty: {receipt_qty}")
        if item.po_detail:
            po_rate = frappe.db.get_value("Purchase Order Item", item.po_detail, "rate")
            print(f"    PO rate: {po_rate}")

    # Trigger the workflow
    print(f"\nTriggering SUBMIT event...")
    result = trigger_event_sync("Purchase Invoice", invoice_name, "SUBMIT", {})

    print(f"\nWorkflow Result:")
    print(f"  - Success: {result.get('success')}")
    print(f"  - Current State: {result.get('state')}")
    print(f"  - Message: {result.get('message', 'N/A')}")

    # Check if approval tasks were created
    tasks = frappe.get_all(
        "Approval Task",
        filters={"reference_doctype": "Purchase Invoice", "reference_name": invoice_name},
        fields=["name", "node_label", "status", "assigned_role"]
    )
    if tasks:
        print(f"\nApproval Tasks Created:")
        for task in tasks:
            print(f"  - {task.name}: {task.node_label} ({task.status}) - Role: {task.assigned_role}")
    else:
        print(f"\nNo approval tasks created (invoice may have auto-approved)")

    return result


def cleanup():
    """Remove all test data"""
    print("Cleaning up test data...")

    # Delete Purchase Invoices
    for pi in frappe.get_all("Purchase Invoice", filters={"supplier": "Test Supplier - Workflow"}):
        frappe.delete_doc("Purchase Invoice", pi.name, force=True)
        print(f"  Deleted PI: {pi.name}")

    # Delete Purchase Receipts
    for pr in frappe.get_all("Purchase Receipt", filters={"supplier": "Test Supplier - Workflow"}):
        frappe.delete_doc("Purchase Receipt", pr.name, force=True)
        print(f"  Deleted PR: {pr.name}")

    # Delete Purchase Orders
    for po in frappe.get_all("Purchase Order", filters={"supplier": "Test Supplier - Workflow"}):
        frappe.delete_doc("Purchase Order", po.name, force=True)
        print(f"  Deleted PO: {po.name}")

    # Delete Machine Instances for Purchase Invoice
    for mi in frappe.get_all("Machine Instance", filters={"reference_doctype": "Purchase Invoice"}):
        frappe.delete_doc("Machine Instance", mi.name, force=True)
        print(f"  Deleted Machine Instance: {mi.name}")

    # Delete Approval Tasks for Purchase Invoice
    for task in frappe.get_all("Approval Task", filters={"reference_doctype": "Purchase Invoice"}):
        frappe.delete_doc("Approval Task", task.name, force=True)
        print(f"  Deleted Approval Task: {task.name}")

    frappe.db.commit()
    print("Cleanup complete!")


if __name__ == "__main__":
    create_all()
