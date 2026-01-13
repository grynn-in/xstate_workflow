# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Boot session data for XState Workflow.
Adds workflow-related info to the session boot.
"""

import frappe


def boot_session(bootinfo):
    """
    Add workflow info to boot session.
    Called on every page load via boot_session hook.
    """
    if frappe.session.user == "Guest":
        return

    active_workflows = get_active_workflows()

    # Add active workflows info
    bootinfo.xstate_workflow = {
        "has_workflow_permission": has_workflow_permission(),
        "is_workflow_manager": has_workflow_permission(),
        "active_workflows": active_workflows,
        "attached_doctypes": [w.get("attached_doctype") for w in active_workflows if w.get("attached_doctype")],
        "pending_approvals_count": get_pending_approvals_count()
    }


def get_pending_approvals_count():
    """Get count of pending approvals for current user."""
    try:
        if not frappe.db.table_exists("Approval Task"):
            return 0

        user = frappe.session.user
        user_roles = frappe.get_roles(user)

        # Count direct assignments
        direct_count = frappe.db.count(
            "Approval Task",
            {"assigned_to": user, "status": "Pending"}
        )

        # Count role-based assignments
        role_count = 0
        if user_roles:
            role_count = frappe.db.count(
                "Approval Task",
                {
                    "assigned_role": ["in", user_roles],
                    "status": "Pending",
                    "assigned_to": ["is", "not set"]
                }
            )

        return direct_count + role_count
    except Exception:
        return 0


def has_workflow_permission():
    """Check if current user can manage workflows."""
    return (
        frappe.session.user == "Administrator" or
        "System Manager" in frappe.get_roles() or
        "Workflow Manager" in frappe.get_roles()
    )


def get_active_workflows():
    """Get list of active workflow configurations."""
    try:
        if not frappe.db.table_exists("State Machine"):
            return []

        workflows = frappe.get_all(
            "State Machine",
            filters={"is_active": 1},
            fields=["name", "attached_doctype"],
            limit=100
        )
        return workflows
    except Exception:
        return []
