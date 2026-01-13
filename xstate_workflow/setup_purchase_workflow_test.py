"""
Setup script for Purchase Invoice Approval Workflow Testing

This script creates:
1. Test users with ERPNext purchasing/accounting roles
2. XSM Guards for quantity and price variance checks
3. State Machine workflow for Purchase Invoice approval

Run with: bench --site xs.local execute xstate_workflow.setup_purchase_workflow_test.setup_all
"""

import frappe
import json


def setup_all():
    """Main setup function - runs all setup steps"""
    frappe.flags.in_test = True

    print("=" * 60)
    print("Setting up Purchase Invoice Approval Workflow Test Environment")
    print("=" * 60)

    # Step 1: Create test users
    create_test_users()

    # Step 2: Create State Machine workflow (guards are embedded in the machine)
    create_workflow()

    frappe.db.commit()

    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("\nTest Users Created:")
    print("  - purchase.manager@example.com (Purchase Manager)")
    print("  - purchase.user@example.com (Purchase User)")
    print("  - accounts.manager@example.com (Accounts Manager)")
    print("  - accounts.user@example.com (Accounts User)")
    print("\nWorkflow: purchase_invoice_variance_approval")
    print("Attached to: Purchase Invoice")
    print("\nTrigger conditions:")
    print("  - Invoice qty > Receipt qty (any line)")
    print("  - Invoice rate > PO rate by > 5% (any line)")


def create_test_users():
    """Create test users with appropriate roles"""
    print("\n[1/3] Creating test users...")

    # Get default company for user permissions
    default_company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not default_company:
        default_company = frappe.db.get_value("Company", {}, "name")

    users_config = [
        {
            "email": "purchase.manager@example.com",
            "first_name": "Purchase",
            "last_name": "Manager",
            "roles": ["Purchase Manager", "Purchase User"]
        },
        {
            "email": "purchase.user@example.com",
            "first_name": "Purchase",
            "last_name": "User",
            "roles": ["Purchase User"]
        },
        {
            "email": "accounts.manager@example.com",
            "first_name": "Accounts",
            "last_name": "Manager",
            "roles": ["Accounts Manager", "Accounts User"]
        },
        {
            "email": "accounts.user@example.com",
            "first_name": "Accounts",
            "last_name": "User",
            "roles": ["Accounts User"]
        }
    ]

    for user_config in users_config:
        email = user_config["email"]

        if frappe.db.exists("User", email):
            print(f"  - User {email} already exists, updating roles...")
            user = frappe.get_doc("User", email)
        else:
            print(f"  - Creating user {email}...")
            user = frappe.new_doc("User")
            user.email = email
            user.first_name = user_config["first_name"]
            user.last_name = user_config["last_name"]
            user.send_welcome_email = 0
            user.new_password = "test1234"  # Simple password for testing

        # Clear existing roles and add new ones
        user.roles = []
        for role_name in user_config["roles"]:
            user.append("roles", {"role": role_name})

        user.save(ignore_permissions=True)
        print(f"    Roles: {', '.join(user_config['roles'])}")

        # Add company permission for the user
        if default_company:
            add_user_permission(email, default_company)

    print("  Test users created successfully!")


def add_user_permission(user, company):
    """Add User Permission for company access"""
    if not frappe.db.exists("User Permission", {"user": user, "allow": "Company", "for_value": company}):
        perm = frappe.get_doc({
            "doctype": "User Permission",
            "user": user,
            "allow": "Company",
            "for_value": company,
            "apply_to_all_doctypes": 1
        })
        perm.insert(ignore_permissions=True)
        print(f"    Added company permission for {company}")


def get_guards_config():
    """Return guard configurations to be embedded in State Machine"""
    # Note: Multi-line guards must set 'result' variable instead of using 'return'
    # Available vars: context, event, doc, frappe
    return [
        {
            "guard_name": "check_qty_variance",
            "description": "Check if any invoice line qty exceeds receipt qty",
            "python_code": '''# Check for quantity variance: Invoice qty > Receipt qty
# Set result=True if variance exists (workflow should trigger)
result = False
for item in doc.items:
    if not item.pr_detail or not item.purchase_receipt:
        continue
    receipt_qty = frappe.db.get_value("Purchase Receipt Item", item.pr_detail, "qty")
    if receipt_qty is not None and item.qty > receipt_qty:
        result = True
        break'''
        },
        {
            "guard_name": "check_price_variance",
            "description": "Check if any invoice line rate exceeds PO rate by more than 5%",
            "python_code": '''# Check for price variance: Invoice rate > PO rate by > 5%
# Set result=True if variance exists
result = False
threshold_pct = 5.0
for item in doc.items:
    if not item.po_detail or not item.purchase_order:
        continue
    po_rate = frappe.db.get_value("Purchase Order Item", item.po_detail, "rate")
    if po_rate and po_rate > 0:
        variance_pct = ((item.rate - po_rate) / po_rate) * 100
        if variance_pct > threshold_pct:
            result = True
            break'''
        },
        {
            "guard_name": "check_any_variance",
            "description": "Check if any variance (qty or price) exists",
            "python_code": '''# Combined check for any variance (qty or price)
# Set result=True if any variance exists
result = False
threshold_pct = 5.0
for item in doc.items:
    # Check quantity variance against receipt
    if item.pr_detail and item.purchase_receipt:
        receipt_qty = frappe.db.get_value("Purchase Receipt Item", item.pr_detail, "qty")
        if receipt_qty is not None and item.qty > receipt_qty:
            result = True
            break
    # Check price variance against PO
    if item.po_detail and item.purchase_order:
        po_rate = frappe.db.get_value("Purchase Order Item", item.po_detail, "rate")
        if po_rate and po_rate > 0:
            variance_pct = ((item.rate - po_rate) / po_rate) * 100
            if variance_pct > threshold_pct:
                result = True
                break'''
        },
        {
            "guard_name": "no_variance",
            "description": "Check if NO variance exists (inverse of check_any_variance)",
            "python_code": '''# Set result=True if NO variance exists (auto-approve path)
result = True
threshold_pct = 5.0
for item in doc.items:
    # Check quantity variance against receipt
    if item.pr_detail and item.purchase_receipt:
        receipt_qty = frappe.db.get_value("Purchase Receipt Item", item.pr_detail, "qty")
        if receipt_qty is not None and item.qty > receipt_qty:
            result = False
            break
    # Check price variance against PO
    if item.po_detail and item.purchase_order:
        po_rate = frappe.db.get_value("Purchase Order Item", item.po_detail, "rate")
        if po_rate and po_rate > 0:
            variance_pct = ((item.rate - po_rate) / po_rate) * 100
            if variance_pct > threshold_pct:
                result = False
                break'''
        }
    ]


def create_workflow():
    """Create the State Machine workflow for Purchase Invoice"""
    print("\n[2/3] Creating State Machine workflow with embedded guards...")

    machine_id = "purchase_invoice_variance_approval"

    # XState JSON configuration for the workflow
    workflow_config = {
        "id": machine_id,
        "initial": "draft",
        "context": {
            "variance_type": None,
            "variance_details": []
        },
        "states": {
            "draft": {
                "meta": {
                    "domain_node": {
                        "type": "auto-action",
                        "label": "Draft",
                        "description": "Invoice in draft state"
                    }
                },
                "on": {
                    "SUBMIT": [
                        {
                            "target": "pending_purchase_approval",
                            "guard": "check_any_variance"
                        },
                        {
                            "target": "approved",
                            "guard": "no_variance"
                        }
                    ]
                }
            },
            "pending_purchase_approval": {
                "meta": {
                    "domain_node": {
                        "type": "approval",
                        "label": "Purchase Manager Approval",
                        "description": "Variance detected - requires Purchase Manager approval",
                        "resolver": {
                            "type": "role",
                            "role": "Purchase Manager",
                            "strategy": "all"
                        },
                        "available_actions": ["Approve", "Reject", "Escalate"],
                        "priority": "High",
                        "sla_hours": 24
                    }
                },
                "on": {
                    "APPROVE": "pending_accounts_approval",
                    "REJECT": "rejected",
                    "ESCALATE": "pending_accounts_approval"
                }
            },
            "pending_accounts_approval": {
                "meta": {
                    "domain_node": {
                        "type": "approval",
                        "label": "Accounts Manager Approval",
                        "description": "Final approval by Accounts Manager",
                        "resolver": {
                            "type": "role",
                            "role": "Accounts Manager",
                            "strategy": "all"
                        },
                        "available_actions": ["Approve", "Reject", "Return"],
                        "priority": "High",
                        "sla_hours": 48
                    }
                },
                "on": {
                    "APPROVE": "approved",
                    "REJECT": "rejected",
                    "RETURN": "pending_purchase_approval"
                }
            },
            "approved": {
                "type": "final",
                "meta": {
                    "domain_node": {
                        "type": "end",
                        "label": "Approved",
                        "description": "Invoice approved for processing",
                        "final_status": "Approved"
                    }
                }
            },
            "rejected": {
                "type": "final",
                "meta": {
                    "domain_node": {
                        "type": "end",
                        "label": "Rejected",
                        "description": "Invoice rejected due to variance issues",
                        "final_status": "Rejected"
                    }
                }
            }
        }
    }

    # Visual builder configuration (positions for the workflow builder UI)
    builder_config = {
        "nodes": [
            {"id": "draft", "position": {"x": 100, "y": 200}, "type": "auto-action"},
            {"id": "pending_purchase_approval", "position": {"x": 350, "y": 100}, "type": "approval"},
            {"id": "pending_accounts_approval", "position": {"x": 600, "y": 100}, "type": "approval"},
            {"id": "approved", "position": {"x": 850, "y": 100}, "type": "end"},
            {"id": "rejected", "position": {"x": 600, "y": 300}, "type": "end"}
        ],
        "edges": [
            {"source": "draft", "target": "pending_purchase_approval", "label": "SUBMIT (variance)"},
            {"source": "draft", "target": "approved", "label": "SUBMIT (no variance)"},
            {"source": "pending_purchase_approval", "target": "pending_accounts_approval", "label": "APPROVE"},
            {"source": "pending_purchase_approval", "target": "rejected", "label": "REJECT"},
            {"source": "pending_accounts_approval", "target": "approved", "label": "APPROVE"},
            {"source": "pending_accounts_approval", "target": "rejected", "label": "REJECT"},
            {"source": "pending_accounts_approval", "target": "pending_purchase_approval", "label": "RETURN"}
        ]
    }

    if frappe.db.exists("State Machine", machine_id):
        print(f"  - State Machine '{machine_id}' already exists, updating...")
        machine = frappe.get_doc("State Machine", machine_id)
        machine.json_config = json.dumps(workflow_config, indent=2)
        machine.workflow_builder_config = json.dumps(builder_config, indent=2)
    else:
        print(f"  - Creating State Machine '{machine_id}'...")
        machine = frappe.new_doc("State Machine")
        machine.machine_id = machine_id
        machine.title = "Purchase Invoice Variance Approval"
        machine.description = """Approval workflow for Purchase Invoices with variances.

Triggers approval when:
- Invoice quantity > Receipt quantity (any line item)
- Invoice rate > PO rate by more than 5% (any line item)

Approval Flow:
1. Purchase Manager reviews variance
2. Accounts Manager gives final approval"""
        machine.attached_doctype = "Purchase Invoice"
        machine.json_config = json.dumps(workflow_config, indent=2)
        machine.workflow_builder_config = json.dumps(builder_config, indent=2)

    # Add guards as child rows in the guards_table
    machine.guards_table = []
    for guard_config in get_guards_config():
        machine.append("guards_table", {
            "guard_name": guard_config["guard_name"],
            "description": guard_config.get("description", ""),
            "python_code": guard_config["python_code"]
        })

    machine.save(ignore_permissions=True)

    print(f"  State Machine '{machine_id}' created successfully!")
    print(f"  - Attached to: Purchase Invoice")
    print(f"  - Guards added: {len(machine.guards_table)}")


def cleanup():
    """Remove all test data created by this script"""
    print("Cleaning up test data...")

    # Delete test users
    test_emails = [
        "purchase.manager@example.com",
        "purchase.user@example.com",
        "accounts.manager@example.com",
        "accounts.user@example.com"
    ]

    for email in test_emails:
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True)
            print(f"  Deleted user: {email}")

    # Delete state machine (guards are embedded and deleted with it)
    machine_id = "purchase_invoice_variance_approval"
    if frappe.db.exists("State Machine", machine_id):
        frappe.delete_doc("State Machine", machine_id, force=True)
        print(f"  Deleted state machine: {machine_id}")

    frappe.db.commit()
    print("Cleanup complete!")


if __name__ == "__main__":
    setup_all()
