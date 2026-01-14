# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Web Page controller for Workflow Dashboard
"""

import frappe
from frappe import _


def get_context(context):
    """
    Context for workflow-dashboard page.
    """
    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.throw(_("Please login to access the Workflow Dashboard"), frappe.PermissionError)

    # Check permissions
    if not frappe.has_permission("State Machine", "read"):
        frappe.throw(_("You don't have permission to access Workflow Dashboard"), frappe.PermissionError)

    context.title = _("Workflow Dashboard")

    # Add meta tags
    context.no_cache = 1
    context.no_breadcrumbs = 1
    context.full_width = 1

    # Include React standalone bundle and CSS
    context.include_css = [
        "/assets/xstate_workflow/js/workflow_builder.css"
    ]
    context.include_script = [
        "/assets/xstate_workflow/js/workflow_builder.standalone.iife.js"
    ]

    return context
