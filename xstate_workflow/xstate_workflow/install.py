# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Installation hooks for XState Workflow app.
"""

import frappe
from frappe import _


def before_install():
    """Pre-installation checks."""
    pass


def after_install():
    """Post-installation setup."""
    create_workflow_manager_role()
    create_sample_workflow()


def create_workflow_manager_role():
    """Create Workflow Manager role if not exists."""
    if not frappe.db.exists("Role", "Workflow Manager"):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": "Workflow Manager",
            "desk_access": 1,
            "is_custom": 1
        }).insert(ignore_permissions=True)
        frappe.db.commit()


def create_sample_workflow():
    """Create a sample approval workflow for demonstration."""
    if frappe.db.exists("State Machine", "contact_approval"):
        return

    sample_config = {
        "id": "contact_approval",
        "initial": "draft",
        "context": {
            "approver": None,
            "approved_at": None,
            "rejection_reason": None
        },
        "states": {
            "draft": {
                "on": {
                    "SUBMIT": "pending_approval"
                },
                "entry": ["notifySubmission"]
            },
            "pending_approval": {
                "on": {
                    "APPROVE": {
                        "target": "approved",
                        "guard": "hasApprovalPermission",
                        "actions": ["recordApproval"]
                    },
                    "REJECT": {
                        "target": "rejected",
                        "actions": ["recordRejection"]
                    },
                    "REQUEST_CHANGES": "draft"
                }
            },
            "approved": {
                "type": "final",
                "entry": ["notifyApproval"]
            },
            "rejected": {
                "on": {
                    "RESUBMIT": "draft"
                },
                "entry": ["notifyRejection"]
            }
        },
        "meta": {
            "auto_triggers": {
                "status": {
                    "Submitted": "SUBMIT"
                }
            },
            "notifications": {
                "approved": [{
                    "type": "email",
                    "recipients": ["owner"],
                    "subject": "Contact Approved",
                    "message": "Your contact has been approved."
                }]
            }
        }
    }

    import json

    frappe.get_doc({
        "doctype": "State Machine",
        "machine_id": "contact_approval",
        "title": "Contact Approval Workflow",
        "description": "Sample approval workflow for Contact DocType",
        "attached_doctype": "Contact",
        "json_config": json.dumps(sample_config, indent=2),
        "is_active": 0,  # Disabled by default
        "logic_module": "xstate_workflow.logic.approval_workflow"
    }).insert(ignore_permissions=True)

    frappe.db.commit()
