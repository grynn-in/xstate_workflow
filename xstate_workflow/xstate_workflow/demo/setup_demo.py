# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Demo Setup Script for Sales Order Approval Workflow

This script sets up the demo environment with:
- Demo users: Brad Pitt (Sales User), Angelina Jolie (Sales Manager), Black Jack (Reviewer)
- Demo roles if not exist
- Sample Sales Orders for testing
- State Machine configuration for Sales Order approval

Usage:
    bench execute xstate_workflow.xstate_workflow.demo.setup_demo.setup_all
    bench execute xstate_workflow.xstate_workflow.demo.setup_demo.create_demo_users
    bench execute xstate_workflow.xstate_workflow.demo.setup_demo.create_state_machine
    bench execute xstate_workflow.xstate_workflow.demo.setup_demo.create_sample_orders
    bench execute xstate_workflow.xstate_workflow.demo.setup_demo.cleanup_demo
"""

import frappe
from frappe import _
import json


# ============================================================================
# DEMO CONFIGURATION
# ============================================================================

DEMO_USERS = [
    {
        "email": "brad.pitt@example.com",
        "first_name": "Brad",
        "last_name": "Pitt",
        "roles": ["Sales User"],
        "description": "Creates Sales Orders",
    },
    {
        "email": "angelina.jolie@example.com",
        "first_name": "Angelina",
        "last_name": "Jolie",
        "roles": ["Sales Manager"],
        "description": "Approves high-value orders (> 100,000)",
    },
    {
        "email": "black.jack@example.com",
        "first_name": "Black",
        "last_name": "Jack",
        "roles": ["Sales User"],  # Reviewer doesn't need special role
        "description": "Reviews low-value orders",
    },
]

SAMPLE_ORDERS = [
    {
        "name": "SO-DEMO-001",
        "grand_total": 150000,
        "customer": "Demo Customer High",
        "description": "High-value order - goes to Sales Manager for approval",
    },
    {
        "name": "SO-DEMO-002",
        "grand_total": 50000,
        "customer": "Demo Customer Low",
        "description": "Low-value order - goes to Reviewer",
    },
    {
        "name": "SO-DEMO-003",
        "grand_total": 100000,
        "customer": "Demo Customer Edge",
        "description": "Edge case (exactly 100,000) - goes to Reviewer",
    },
    {
        "name": "SO-DEMO-004",
        "grand_total": 250000,
        "customer": "Demo Customer VIP",
        "description": "VIP high-value order",
    },
]


# ============================================================================
# STATE MACHINE CONFIGURATION
# ============================================================================

SALES_ORDER_MACHINE_CONFIG = {
    "id": "salesOrderApproval",
    "version": "1.0.0",
    "initial": "draft",
    "context": {
        "grand_total": 0,
        "owner": "",
        "assigned_to": "",
        "workflow_status": "Draft"
    },
    "states": {
        "draft": {
            "meta": {
                "label": "Draft",
                "description": "Order is being created"
            },
            "on": {
                "SUBMIT": [
                    {
                        "target": "pending_approval",
                        "guard": "isHighValueOrder",
                        "actions": ["recordSubmission", "assignToSalesManager", "notifySalesManager", "logWorkflowEvent"]
                    },
                    {
                        "target": "pending_review",
                        "guard": "isLowValueOrder",
                        "actions": ["recordSubmission", "assignToReviewer", "notifyReviewer", "logWorkflowEvent"]
                    }
                ]
            }
        },
        "pending_approval": {
            "meta": {
                "label": "Pending Approval",
                "description": "High-value order awaiting Sales Manager approval"
            },
            "on": {
                "APPROVE": {
                    "target": "approved",
                    "guard": "canApprove",
                    "actions": ["recordApproval", "notifyCreatorApproved", "logWorkflowEvent"]
                },
                "REJECT": {
                    "target": "rejected",
                    "guard": "canApprove",
                    "actions": ["recordRejection", "notifyCreatorRejected", "logWorkflowEvent"]
                },
                "SEND_TO_REVIEW": {
                    "target": "pending_review",
                    "guard": "isSalesManager",
                    "actions": ["assignToReviewer", "notifyReviewer", "logWorkflowEvent"]
                }
            }
        },
        "pending_review": {
            "meta": {
                "label": "Pending Review",
                "description": "Order awaiting reviewer assessment"
            },
            "on": {
                "COMPLETE_REVIEW": {
                    "target": "reviewed",
                    "guard": "canReview",
                    "actions": ["recordReviewComplete", "logWorkflowEvent"]
                },
                "ESCALATE": {
                    "target": "pending_approval",
                    "guard": "isReviewer",
                    "actions": ["assignToSalesManager", "notifySalesManager", "logWorkflowEvent"]
                },
                "REJECT": {
                    "target": "rejected",
                    "guard": "canReview",
                    "actions": ["recordRejection", "notifyCreatorRejected", "logWorkflowEvent"]
                }
            }
        },
        "reviewed": {
            "meta": {
                "label": "Reviewed",
                "description": "Review completed, auto-transitions to approved"
            },
            "always": {
                "target": "approved",
                "actions": ["logWorkflowEvent"]
            }
        },
        "approved": {
            "type": "final",
            "meta": {
                "label": "Approved",
                "description": "Order has been approved"
            },
            "entry": ["notifyCreatorApproved"]
        },
        "rejected": {
            "type": "final",
            "meta": {
                "label": "Rejected",
                "description": "Order has been rejected"
            },
            "on": {
                "RESUBMIT": {
                    "target": "draft",
                    "actions": ["logWorkflowEvent"]
                }
            }
        }
    }
}

# Visual builder config with node positions
WORKFLOW_BUILDER_CONFIG = {
    "nodes": [
        {
            "id": "draft",
            "type": "atomic",
            "position": {"x": 100, "y": 200},
            "data": {
                "label": "Draft",
                "xstateType": "atomic",
                "isInitial": True,
                "description": "Order is being created"
            }
        },
        {
            "id": "pending_approval",
            "type": "atomic",
            "position": {"x": 400, "y": 100},
            "data": {
                "label": "Pending Approval",
                "xstateType": "atomic",
                "description": "High-value order awaiting Sales Manager approval"
            }
        },
        {
            "id": "pending_review",
            "type": "atomic",
            "position": {"x": 400, "y": 300},
            "data": {
                "label": "Pending Review",
                "xstateType": "atomic",
                "description": "Order awaiting reviewer assessment"
            }
        },
        {
            "id": "reviewed",
            "type": "atomic",
            "position": {"x": 650, "y": 300},
            "data": {
                "label": "Reviewed",
                "xstateType": "atomic",
                "description": "Review completed"
            }
        },
        {
            "id": "approved",
            "type": "final",
            "position": {"x": 850, "y": 200},
            "data": {
                "label": "Approved",
                "xstateType": "final",
                "description": "Order has been approved"
            }
        },
        {
            "id": "rejected",
            "type": "final",
            "position": {"x": 400, "y": 450},
            "data": {
                "label": "Rejected",
                "xstateType": "final",
                "description": "Order has been rejected"
            }
        }
    ],
    "edges": [
        {
            "id": "draft-to-approval",
            "source": "draft",
            "target": "pending_approval",
            "data": {
                "event": "SUBMIT",
                "transitionType": "event",
                "guard": {
                    # NO CODE REQUIRED! Visual guard using simple field comparison
                    "type": "simple",
                    "name": "isHighValueOrder",
                    "field": "grand_total",
                    "operator": ">",
                    "value": 100000
                },
                "actions": ["recordSubmission", "assignToSalesManager"],
                "trigger": {
                    "button": {
                        "enabled": True,
                        "label": "Submit for Approval",
                        "style": "primary",
                        "allowedRoles": ["Sales User"]
                    }
                }
            }
        },
        {
            "id": "draft-to-review",
            "source": "draft",
            "target": "pending_review",
            "data": {
                "event": "SUBMIT",
                "transitionType": "event",
                "guard": {
                    # NO CODE REQUIRED! Visual guard - opposite of high value
                    "type": "simple",
                    "name": "isLowValueOrder",
                    "field": "grand_total",
                    "operator": "<=",
                    "value": 100000
                },
                "actions": ["recordSubmission", "assignToReviewer"],
                "trigger": {
                    "button": {
                        "enabled": True,
                        "label": "Submit for Review",
                        "style": "primary",
                        "allowedRoles": ["Sales User"]
                    }
                }
            }
        },
        {
            "id": "approval-approve",
            "source": "pending_approval",
            "target": "approved",
            "data": {
                "event": "APPROVE",
                "transitionType": "event",
                "guard": {
                    # NO CODE REQUIRED! Role-based guard
                    "type": "role",
                    "name": "canApprove",
                    "roles": ["Sales Manager", "System Manager"],
                    "require_all": False
                },
                "actions": ["recordApproval", "notifyCreatorApproved"],
                "trigger": {
                    "button": {
                        "enabled": True,
                        "label": "Approve",
                        "style": "success",
                        "allowedRoles": ["Sales Manager"]
                    }
                }
            }
        },
        {
            "id": "approval-reject",
            "source": "pending_approval",
            "target": "rejected",
            "data": {
                "event": "REJECT",
                "transitionType": "event",
                "guard": {
                    # NO CODE REQUIRED! Role-based guard
                    "type": "role",
                    "name": "canReject",
                    "roles": ["Sales Manager", "System Manager"],
                    "require_all": False
                },
                "actions": ["recordRejection", "notifyCreatorRejected"],
                "trigger": {
                    "button": {
                        "enabled": True,
                        "label": "Reject",
                        "style": "danger",
                        "allowedRoles": ["Sales Manager"]
                    }
                }
            }
        },
        {
            "id": "approval-to-review",
            "source": "pending_approval",
            "target": "pending_review",
            "data": {
                "event": "SEND_TO_REVIEW",
                "transitionType": "event",
                "guard": {
                    # NO CODE REQUIRED! Role-based guard
                    "type": "role",
                    "name": "isSalesManager",
                    "roles": ["Sales Manager"],
                    "require_all": False
                },
                "actions": ["assignToReviewer"],
                "trigger": {
                    "button": {
                        "enabled": True,
                        "label": "Send to Review",
                        "style": "secondary",
                        "allowedRoles": ["Sales Manager"]
                    }
                }
            }
        },
        {
            "id": "review-complete",
            "source": "pending_review",
            "target": "reviewed",
            "data": {
                "event": "COMPLETE_REVIEW",
                "transitionType": "event",
                "guard": {
                    # NO CODE REQUIRED! Role-based guard - any logged in user can complete
                    "type": "role",
                    "name": "canReview",
                    "roles": ["Sales User", "Sales Manager", "System Manager"],
                    "require_all": False
                },
                "actions": ["recordReviewComplete"],
                "trigger": {
                    "button": {
                        "enabled": True,
                        "label": "Complete Review",
                        "style": "success",
                        "allowedRoles": ["Sales User"]
                    }
                }
            }
        },
        {
            "id": "review-escalate",
            "source": "pending_review",
            "target": "pending_approval",
            "data": {
                "event": "ESCALATE",
                "transitionType": "event",
                "guard": {
                    # NO CODE REQUIRED! Role-based guard
                    "type": "role",
                    "name": "isReviewer",
                    "roles": ["Sales User", "System Manager"],
                    "require_all": False
                },
                "actions": ["assignToSalesManager"],
                "trigger": {
                    "button": {
                        "enabled": True,
                        "label": "Escalate to Manager",
                        "style": "warning",
                        "allowedRoles": ["Sales User"]
                    }
                }
            }
        },
        {
            "id": "review-reject",
            "source": "pending_review",
            "target": "rejected",
            "data": {
                "event": "REJECT",
                "transitionType": "event",
                "guard": {
                    # NO CODE REQUIRED! Role-based guard
                    "type": "role",
                    "name": "reviewerCanReject",
                    "roles": ["Sales User", "Sales Manager", "System Manager"],
                    "require_all": False
                },
                "actions": ["recordRejection", "notifyCreatorRejected"],
                "trigger": {
                    "button": {
                        "enabled": True,
                        "label": "Reject",
                        "style": "danger",
                        "allowedRoles": ["Sales User"]
                    }
                }
            }
        },
        {
            "id": "reviewed-to-approved",
            "source": "reviewed",
            "target": "approved",
            "data": {
                "transitionType": "always",
                "actions": []
            }
        },
        {
            "id": "rejected-resubmit",
            "source": "rejected",
            "target": "draft",
            "data": {
                "event": "RESUBMIT",
                "transitionType": "event",
                "trigger": {
                    "button": {
                        "enabled": True,
                        "label": "Resubmit",
                        "style": "secondary",
                        "allowedRoles": ["Sales User"]
                    }
                }
            }
        }
    ],
    "viewport": {"x": 0, "y": 0, "zoom": 1}
}


# ============================================================================
# SETUP FUNCTIONS
# ============================================================================

def setup_all():
    """
    Complete demo setup: users, roles, state machine, sample orders.
    """
    frappe.flags.in_demo_setup = True

    print("Setting up XState Workflow Demo...")
    print("-" * 50)

    create_demo_roles()
    create_demo_users()
    create_demo_contact()
    create_state_machine()
    create_sample_orders()

    frappe.db.commit()

    print("-" * 50)
    print("Demo setup complete!")
    print("\nDemo Users:")
    for user in DEMO_USERS:
        print(f"  - {user['first_name']} {user['last_name']} ({user['email']})")
        print(f"    Roles: {', '.join(user['roles'])}")
        print(f"    {user['description']}")
    print("\nState Machine: sales_order_approval")
    print("Attached to: Sales Order")
    print("\nVisual Builder: /workflow-builder?machine=sales_order_approval")
    print("\nSample Orders created for testing.")


def create_demo_roles():
    """
    Ensure required roles exist.
    """
    roles_to_create = ["Sales User", "Sales Manager"]

    for role_name in roles_to_create:
        if not frappe.db.exists("Role", role_name):
            print(f"Creating role: {role_name}")
            role = frappe.get_doc({
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": 1,
            })
            role.insert(ignore_permissions=True)
        else:
            print(f"Role exists: {role_name}")


def create_demo_users():
    """
    Create demo users with appropriate roles.
    """
    for user_data in DEMO_USERS:
        email = user_data["email"]

        if frappe.db.exists("User", email):
            print(f"User exists: {email}")
            # Update roles
            user = frappe.get_doc("User", email)
            existing_roles = [r.role for r in user.roles]
            for role in user_data["roles"]:
                if role not in existing_roles:
                    user.append("roles", {"role": role})
            user.save(ignore_permissions=True)
        else:
            print(f"Creating user: {email}")
            user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "enabled": 1,
                "send_welcome_email": 0,
                "new_password": "XstateDemo$2024!",  # Password for demo
            })

            for role in user_data["roles"]:
                user.append("roles", {"role": role})

            user.insert(ignore_permissions=True)


def create_demo_contact():
    """
    Create a demo contact for Sales Orders.
    """
    contact_email = "demo.contact@example.com"

    if not frappe.db.exists("Contact", {"email_id": contact_email}):
        print(f"Creating demo contact: {contact_email}")
        contact = frappe.get_doc({
            "doctype": "Contact",
            "first_name": "Demo",
            "last_name": "Contact",
        })
        contact.append("email_ids", {
            "email_id": contact_email,
            "is_primary": 1
        })
        contact.insert(ignore_permissions=True)
    else:
        print(f"Contact exists: {contact_email}")


def create_state_machine():
    """
    Create the Sales Order approval State Machine.
    """
    machine_id = "sales_order_approval"

    if frappe.db.exists("State Machine", machine_id):
        print(f"State Machine exists: {machine_id}")
        # Update it
        machine = frappe.get_doc("State Machine", machine_id)
        machine.json_config = json.dumps(SALES_ORDER_MACHINE_CONFIG, indent=2)
        machine.workflow_builder_config = json.dumps(WORKFLOW_BUILDER_CONFIG, indent=2)
        machine.save(ignore_permissions=True)
        print(f"Updated State Machine: {machine_id}")
    else:
        print(f"Creating State Machine: {machine_id}")
        machine = frappe.get_doc({
            "doctype": "State Machine",
            "machine_id": machine_id,
            "title": "Sales Order Approval Workflow",
            "description": "Demo workflow for Sales Order approval with value-based routing. NO CODE REQUIRED - uses visual guards!",
            "attached_doctype": "ToDo",  # Using ToDo for demo (Sales Order requires ERPNext)
            "is_active": 1,
            "version": 1,
            # NO logic_module needed! Guards are defined visually in workflow_builder_config
            "json_config": json.dumps(SALES_ORDER_MACHINE_CONFIG, indent=2),
            "workflow_builder_config": json.dumps(WORKFLOW_BUILDER_CONFIG, indent=2),
        })

        # NO guards_table entries needed! Guards are defined visually in workflow_builder_config
        # The visual guard builder supports:
        # - Simple guards: field comparisons (grand_total > 100000)
        # - Role guards: check user roles (Sales Manager, System Manager)
        # - Compound guards: AND/OR of multiple conditions

        # Actions still need Python code (for now - could add visual actions later)
        # For this no-code demo, we'll skip actions too - the workflow works without them
        # In production, you'd either:
        # 1. Add a logic_module with action functions
        # 2. Add inline Python in actions_table
        # 3. Use future visual action builder

        # For minimal demo, just show workflow transitions work without any Python
        print("  Note: This demo uses NO Python code for guards!")
        print("  Guards are defined visually in workflow_builder_config")
        print("  Actions are disabled for this pure no-code demo")

        # Optionally add action stubs (no Python code, just documentation)
        action_stubs = [
            ("recordSubmission", "transition", "Would record submission details"),
            ("assignToSalesManager", "transition", "Would create assignment"),
            ("assignToReviewer", "transition", "Would create assignment"),
            ("recordApproval", "transition", "Would record approval"),
            ("recordRejection", "transition", "Would record rejection"),
        ]

        for action_name, action_type, description in action_stubs:
            machine.append("actions_table", {
                "action_name": action_name,
                "action_type": action_type,
                "description": description + " (stub - no code)",
            })

        machine.insert(ignore_permissions=True)
        print(f"Created State Machine: {machine_id}")


def create_sample_orders():
    """
    Create sample order contexts for testing (stored as Machine Instances).
    """
    machine_id = "sales_order_approval"

    print("Creating sample order instances...")

    for order in SAMPLE_ORDERS:
        instance_id = f"{machine_id}:{order['name']}"

        # First, create a ToDo to use as a reference document
        todo_name = f"DEMO-{order['name']}"
        if not frappe.db.exists("ToDo", {"description": todo_name}):
            todo = frappe.get_doc({
                "doctype": "ToDo",
                "description": todo_name,
                "owner": "brad.pitt@example.com",
                "status": "Open",
            })
            todo.insert(ignore_permissions=True)
            reference_name = todo.name
        else:
            reference_name = frappe.db.get_value("ToDo", {"description": todo_name}, "name")

        context = {
            "name": order["name"],
            "grand_total": order["grand_total"],
            "customer": order["customer"],
            "owner": "brad.pitt@example.com",  # Brad creates all orders
            "doctype": "ToDo",
            "docname": reference_name,
            "workflow_status": "Draft",
        }

        # Check if instance exists by querying (name is auto-generated)
        existing = frappe.db.get_value(
            "Machine Instance",
            {"machine": machine_id, "reference_name": reference_name},
            "name"
        )

        if existing:
            print(f"  Instance exists: {existing}")
            instance = frappe.get_doc("Machine Instance", existing)
            instance.context = json.dumps(context, indent=2)
            instance.save(ignore_permissions=True)
        else:
            print(f"  Creating instance for {order['name']} (grand_total: {order['grand_total']})")
            instance = frappe.get_doc({
                "doctype": "Machine Instance",
                "machine": machine_id,
                "reference_doctype": "ToDo",
                "reference_name": reference_name,
                "current_state": "draft",
                "status": "active",
                "context": json.dumps(context, indent=2),
            })
            instance.insert(ignore_permissions=True)


def cleanup_demo():
    """
    Remove all demo data.
    """
    print("Cleaning up demo data...")

    # Remove machine instances
    instances = frappe.get_all(
        "Machine Instance",
        filters={"machine": "sales_order_approval"},
        pluck="name"
    )
    for instance in instances:
        frappe.delete_doc("Machine Instance", instance, ignore_permissions=True)
        print(f"  Deleted instance: {instance}")

    # Remove demo ToDos
    for order in SAMPLE_ORDERS:
        todo_name = f"DEMO-{order['name']}"
        todos = frappe.get_all("ToDo", filters={"description": todo_name}, pluck="name")
        for todo in todos:
            frappe.delete_doc("ToDo", todo, ignore_permissions=True)
            print(f"  Deleted ToDo: {todo}")

    # Remove state machine
    if frappe.db.exists("State Machine", "sales_order_approval"):
        frappe.delete_doc("State Machine", "sales_order_approval", ignore_permissions=True)
        print("  Deleted State Machine: sales_order_approval")

    # Remove users
    for user_data in DEMO_USERS:
        if frappe.db.exists("User", user_data["email"]):
            frappe.delete_doc("User", user_data["email"], ignore_permissions=True)
            print(f"  Deleted user: {user_data['email']}")

    frappe.db.commit()
    print("Cleanup complete!")


# ============================================================================
# TESTING HELPERS
# ============================================================================

def test_workflow():
    """
    Test the workflow transitions.
    """
    from xstate_workflow.workflow_engine import trigger_event, get_current_state

    print("\nTesting Sales Order Approval Workflow")
    print("=" * 50)

    instance_id = "sales_order_approval:SO-DEMO-001"  # High value order

    # Check initial state
    state = get_current_state(instance_id)
    print(f"\n1. Initial state: {state}")

    # Login as Brad Pitt and submit
    frappe.set_user("brad.pitt@example.com")
    print(f"\n2. User: Brad Pitt submitting high-value order...")

    try:
        new_state = trigger_event(instance_id, "SUBMIT")
        print(f"   New state: {new_state}")  # Should be pending_approval
    except Exception as e:
        print(f"   Error: {e}")

    # Login as Angelina Jolie and approve
    frappe.set_user("angelina.jolie@example.com")
    print(f"\n3. User: Angelina Jolie approving...")

    try:
        new_state = trigger_event(instance_id, "APPROVE")
        print(f"   New state: {new_state}")  # Should be approved
    except Exception as e:
        print(f"   Error: {e}")

    frappe.set_user("Administrator")
    print("\nTest complete!")
