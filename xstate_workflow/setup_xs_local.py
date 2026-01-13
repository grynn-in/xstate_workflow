"""
Set up xs.local with required ERPNext master data for testing
"""
import frappe


def setup():
    """Set up xs.local with required master data"""
    print("Setting up xs.local with ERPNext master data...")

    company = frappe.db.get_value("Company", {}, "name")
    if not company:
        print("No company found!")
        return

    print(f"Company: {company}")

    # Create all required accounts
    create_stock_accounts(company)

    # Set default accounts on company
    set_company_defaults(company)

    # Set account on warehouses
    set_warehouse_accounts(company)

    frappe.db.commit()
    print("Setup complete!")


def create_stock_accounts(company):
    """Create all required stock-related accounts"""
    abbr = company[:1]

    # Find parent accounts
    asset_parent = frappe.db.get_value("Account", {"company": company, "root_type": "Asset", "is_group": 1}, "name")
    liability_parent = frappe.db.get_value("Account", {"company": company, "root_type": "Liability", "is_group": 1}, "name")
    expense_parent = frappe.db.get_value("Account", {"company": company, "root_type": "Expense", "is_group": 1}, "name")

    accounts_to_create = [
        {"name": f"1200 - Inventory - {abbr}", "parent": asset_parent, "type": "Stock", "root": "Asset"},
        {"name": f"2000 - Creditors - {abbr}", "parent": liability_parent, "type": "Payable", "root": "Liability"},
        {"name": f"2100 - Stock Received But Not Billed - {abbr}", "parent": liability_parent, "type": "Stock Received But Not Billed", "root": "Liability"},
        {"name": f"5100 - Cost of Goods Sold - {abbr}", "parent": expense_parent, "type": "Cost of Goods Sold", "root": "Expense"},
        {"name": f"5200 - Stock Adjustment - {abbr}", "parent": expense_parent, "type": "Stock Adjustment", "root": "Expense"},
        {"name": f"5300 - Expenses Included In Valuation - {abbr}", "parent": expense_parent, "type": "Expenses Included In Valuation", "root": "Expense"},
    ]

    for acc in accounts_to_create:
        if frappe.db.exists("Account", acc["name"]):
            print(f"  Account {acc['name']} already exists")
            continue

        print(f"  Creating account: {acc['name']}")
        account = frappe.get_doc({
            "doctype": "Account",
            "account_name": acc["name"].split(" - ")[0] + " - " + acc["name"].split(" - ")[1],
            "parent_account": acc["parent"],
            "company": company,
            "account_type": acc["type"],
            "root_type": acc["root"]
        })
        account.insert(ignore_permissions=True)


def set_company_defaults(company):
    """Set all required default accounts on company"""
    abbr = company[:1]

    defaults = {
        "default_inventory_account": f"1200 - Inventory - {abbr}",
        "default_payable_account": f"2000 - Creditors - {abbr}",
        "stock_received_but_not_billed": f"2100 - Stock Received But Not Billed - {abbr}",
        "default_expense_account": f"5100 - Cost of Goods Sold - {abbr}",
        "stock_adjustment_account": f"5200 - Stock Adjustment - {abbr}",
        "expenses_included_in_valuation": f"5300 - Expenses Included In Valuation - {abbr}",
    }

    for field, account in defaults.items():
        if frappe.db.exists("Account", account):
            frappe.db.set_value("Company", company, field, account)
            print(f"  Set {field}: {account}")


def set_warehouse_accounts(company):
    """Set account on all warehouses"""
    account = frappe.db.get_value("Account", {"company": company, "account_type": "Stock"}, "name")
    if not account:
        return

    warehouses = frappe.get_all("Warehouse", filters={"company": company, "is_group": 0}, pluck="name")
    for wh in warehouses:
        frappe.db.set_value("Warehouse", wh, "account", account)
        print(f"  Set account on warehouse: {wh}")
