# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

import frappe


def get_context(context):
    """Get context for My Approvals page."""
    context.no_cache = 1

    # Ensure user is logged in
    if frappe.session.user == "Guest":
        frappe.throw("Please login to view your approvals", frappe.PermissionError)

    context.title = "My Approvals"
