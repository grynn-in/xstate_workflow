# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Web Page controller for Workflow Instance Viewer
"""

import frappe
from frappe import _


def get_context(context):
    """
    Context for workflow-viewer page.
    Displays the current runtime state of a document's workflow.
    """
    # Check if user is logged in
    if frappe.session.user == "Guest":
        frappe.throw(_("Please login to access the Workflow Viewer"), frappe.PermissionError)

    # Check permissions
    if not frappe.has_permission("Machine Instance", "read"):
        frappe.throw(_("You don't have permission to access Workflow Viewer"), frappe.PermissionError)

    # machine_id, doctype, docname are extracted from URL via JavaScript in the template
    context.title = _("Workflow Viewer")

    # Add CSRF token for API calls
    context.csrf_token = frappe.sessions.get_csrf_token()

    # Add meta tags
    context.no_cache = 1
    context.no_breadcrumbs = 1
    context.full_width = 1

    # Include React Flow bundle (same as builder for now)
    context.include_script = [
        "/assets/xstate_workflow/js/workflow_builder.bundle.js"
    ]

    return context
