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

    # Include CSS with cache-busting version
    # NOTE: JS is loaded directly in HTML template for better cache control
    import time
    cache_bust = int(time.time())

    context.include_css = [
        f"/assets/xstate_workflow/js/workflow_builder.css?v={cache_bust}"
    ]
    # Script is loaded directly in HTML template with cache-busting
    context.include_script = []

    return context
