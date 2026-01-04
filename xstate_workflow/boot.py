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

    # Add active workflows info
    bootinfo.xstate_workflow = {
        "has_workflow_permission": has_workflow_permission(),
        "active_workflows": get_active_workflows()
    }


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
