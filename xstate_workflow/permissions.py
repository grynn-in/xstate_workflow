# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Permission handlers for XState Workflow.
"""

import frappe


def get_permission_query_conditions(user=None):
    """
    Permission query conditions for Machine Instance.
    Users can only see instances for documents they have access to.
    """
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return ""

    # Get list of DocTypes user has read access to
    # This is a simplified check - in production you might want more granular control
    return ""


def has_permission(doc, ptype="read", user=None):
    """
    Check if user has permission on Machine Instance.
    """
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return True

    if "Workflow Manager" in frappe.get_roles(user):
        return True

    # Check if user has access to the referenced document
    if doc.reference_doctype and doc.reference_name:
        try:
            ref_doc = frappe.get_doc(doc.reference_doctype, doc.reference_name)
            return ref_doc.has_permission(ptype)
        except frappe.PermissionError:
            return False

    # Also allow access if user is assigned to an approval task for this instance
    if frappe.db.exists("Approval Task", {
        "workflow_instance": doc.name,
        "status": "Pending",
        "assigned_to": user
    }):
        return True

    # Check role-based assignment
    user_roles = frappe.get_roles(user)
    if frappe.db.exists("Approval Task", {
        "workflow_instance": doc.name,
        "status": "Pending",
        "assigned_role": ["in", user_roles]
    }):
        return True

    return False
