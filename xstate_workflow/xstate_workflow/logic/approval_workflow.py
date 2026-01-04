# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Logic module for approval workflows.

This module provides guards and actions for typical approval workflows.
It can be referenced in State Machine as:
    logic_module = "xstate_workflow.logic.approval_workflow"
"""

import frappe
from frappe import _


# ============================================================================
# GUARDS
# ============================================================================

def has_approval_permission(context: dict, event: dict) -> bool:
    """
    Check if current user has permission to approve.
    Can be customized based on context.approver or role-based checks.
    """
    user = frappe.session.user

    # System Manager can always approve
    if "System Manager" in frappe.get_roles(user):
        return True

    # Check if user is the designated approver
    if context.get("approver") and context["approver"] == user:
        return True

    # Check for Workflow Manager role
    if "Workflow Manager" in frappe.get_roles(user):
        return True

    return False


def is_not_owner(context: dict, event: dict) -> bool:
    """
    Guard: Prevent self-approval.
    """
    user = frappe.session.user
    owner = context.get("owner") or context.get("created_by")
    return user != owner


def has_required_fields(context: dict, event: dict) -> bool:
    """
    Guard: Check that required fields are filled.
    """
    required = context.get("required_fields", [])
    for field in required:
        if not context.get(field):
            return False
    return True


def is_within_amount_limit(context: dict, event: dict) -> bool:
    """
    Guard: Check if amount is within user's approval limit.
    """
    amount = context.get("amount", 0)
    user = frappe.session.user

    # Get user's approval limit (could be from User Settings or custom DocType)
    user_limit = frappe.db.get_value("User", user, "approval_limit") or 10000

    return amount <= user_limit


# ============================================================================
# ACTIONS
# ============================================================================

def record_approval(context: dict, event: dict) -> dict:
    """
    Action: Record who approved and when.
    """
    context = context.copy()
    context["approver"] = frappe.session.user
    context["approved_at"] = str(frappe.utils.now())
    context["approval_note"] = event.get("note", "")
    return context


def record_rejection(context: dict, event: dict) -> dict:
    """
    Action: Record rejection details.
    """
    context = context.copy()
    context["rejected_by"] = frappe.session.user
    context["rejected_at"] = str(frappe.utils.now())
    context["rejection_reason"] = event.get("reason", "No reason provided")
    return context


def notify_submission(context: dict, event: dict) -> dict:
    """
    Action: Send notification on submission.
    """
    # Get approvers
    approvers = frappe.get_all(
        "Has Role",
        filters={"role": "Workflow Manager", "parenttype": "User"},
        pluck="parent"
    )

    if approvers:
        frappe.sendmail(
            recipients=approvers[:5],  # Limit to 5
            subject=_("New Approval Request"),
            message=_("A new document is pending your approval.")
        )

    return context


def notify_approval(context: dict, event: dict) -> dict:
    """
    Action: Notify owner of approval.
    """
    owner = context.get("owner")
    if owner:
        frappe.sendmail(
            recipients=[owner],
            subject=_("Your Request Has Been Approved"),
            message=_("Your document has been approved by {0}").format(context.get("approver"))
        )

    return context


def notify_rejection(context: dict, event: dict) -> dict:
    """
    Action: Notify owner of rejection.
    """
    owner = context.get("owner")
    if owner:
        reason = context.get("rejection_reason", "No reason provided")
        frappe.sendmail(
            recipients=[owner],
            subject=_("Your Request Has Been Rejected"),
            message=_("Your document has been rejected. Reason: {0}").format(reason)
        )

    return context


def update_document_status(context: dict, event: dict) -> dict:
    """
    Action: Update the referenced document's status field.
    """
    # This would be called with access to the actual document
    # In real implementation, the action function receives more context
    return context


def log_transition(context: dict, event: dict) -> dict:
    """
    Action: Log the transition for audit.
    """
    frappe.log_error(
        title="Workflow Transition",
        message=f"Event: {event.get('type')}, User: {frappe.session.user}"
    )
    return context


# ============================================================================
# EXPORT GUARDS AND ACTIONS
# ============================================================================

# These dicts are loaded by the workflow engine when logic_module is specified
guards = {
    "hasApprovalPermission": has_approval_permission,
    "isNotOwner": is_not_owner,
    "hasRequiredFields": has_required_fields,
    "isWithinAmountLimit": is_within_amount_limit,
}

actions = {
    "recordApproval": record_approval,
    "recordRejection": record_rejection,
    "notifySubmission": notify_submission,
    "notifyApproval": notify_approval,
    "notifyRejection": notify_rejection,
    "updateDocumentStatus": update_document_status,
    "logTransition": log_transition,
}
