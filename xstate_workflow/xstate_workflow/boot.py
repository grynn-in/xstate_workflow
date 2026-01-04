# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Boot session additions for XState Workflow.
"""

import frappe


def boot_session(bootinfo):
    """
    Add workflow configuration to boot info.
    This makes workflow data available to client-side JavaScript.
    """
    if frappe.session.user == "Guest":
        return

    # Add list of DocTypes with active workflows
    attached_doctypes = frappe.get_all(
        "State Machine",
        filters={"is_active": 1},
        pluck="attached_doctype"
    )

    bootinfo.xstate_workflow = {
        "attached_doctypes": list(set(filter(None, attached_doctypes))),
        "is_workflow_manager": "Workflow Manager" in frappe.get_roles()
    }
