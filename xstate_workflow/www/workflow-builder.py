# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Web Page controller for Workflow Builder
"""

import frappe
from frappe import _


def get_context(context):
    """
    Context for workflow-builder page.
    """
    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.throw(_("Please login to access the Workflow Builder"), frappe.PermissionError)

    # Check permissions
    if not frappe.has_permission("State Machine", "read"):
        frappe.throw(_("You don't have permission to access Workflow Builder"), frappe.PermissionError)

    # Get machine_id from URL if provided
    machine_id = frappe.form_dict.get("machine_id") or frappe.form_dict.get("name")

    context.machine_id = machine_id
    context.title = _("Workflow Builder")

    # Add meta tags
    context.no_cache = 1
    context.no_breadcrumbs = 1
    context.full_width = 1

    # Include React Flow bundle
    context.include_script = [
        "/assets/xstate_workflow/js/workflow_builder.bundle.js"
    ]

    return context
