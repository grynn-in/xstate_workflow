# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Sales Order Approval Workflow Logic

This module provides guards and actions for a Sales Order approval workflow.
Demo Users:
    - Brad Pitt (Sales User) - creates orders
    - Angelina Jolie (Sales Manager) - approves high-value orders (> 100,000)
    - Black Jack (Reviewer) - reviews low-value orders

Reference in State Machine as:
    logic_module = "xstate_workflow.logic.sales_order_approval"
"""

import frappe
from frappe import _


# ============================================================================
# CONSTANTS
# ============================================================================

HIGH_VALUE_THRESHOLD = 100000
SALES_MANAGER_EMAIL = "angelina.jolie@example.com"
REVIEWER_EMAIL = "black.jack@example.com"


# ============================================================================
# GUARDS
# ============================================================================

def is_high_value_order(context: dict, event: dict) -> bool:
    """
    Guard: Check if order value exceeds threshold (100,000).
    Returns True if grand_total > HIGH_VALUE_THRESHOLD.
    """
    grand_total = context.get("grand_total", 0)
    try:
        grand_total = float(grand_total)
    except (ValueError, TypeError):
        grand_total = 0

    return grand_total > HIGH_VALUE_THRESHOLD


def is_low_value_order(context: dict, event: dict) -> bool:
    """
    Guard: Check if order value is at or below threshold.
    Returns True if grand_total <= HIGH_VALUE_THRESHOLD.
    """
    return not is_high_value_order(context, event)


def is_sales_manager(context: dict, event: dict) -> bool:
    """
    Guard: Check if current user is a Sales Manager.
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    return "Sales Manager" in roles or "System Manager" in roles


def is_sales_user(context: dict, event: dict) -> bool:
    """
    Guard: Check if current user is a Sales User.
    """
    user = frappe.session.user
    roles = frappe.get_roles(user)
    return "Sales User" in roles


def is_reviewer(context: dict, event: dict) -> bool:
    """
    Guard: Check if current user is the assigned reviewer.
    """
    user = frappe.session.user
    assigned_reviewer = context.get("assigned_reviewer")

    # Check if user is the assigned reviewer
    if assigned_reviewer and user == assigned_reviewer:
        return True

    # Also allow System Manager
    return "System Manager" in frappe.get_roles(user)


def is_not_creator(context: dict, event: dict) -> bool:
    """
    Guard: Prevent self-approval - creator cannot approve their own order.
    """
    user = frappe.session.user
    owner = context.get("owner")
    return user != owner


def can_approve(context: dict, event: dict) -> bool:
    """
    Guard: Combined check - is Sales Manager AND is not the creator.
    """
    return is_sales_manager(context, event) and is_not_creator(context, event)


def can_review(context: dict, event: dict) -> bool:
    """
    Guard: Check if user can review (is assigned reviewer or System Manager).
    """
    return is_reviewer(context, event) and is_not_creator(context, event)


def has_valid_contact(context: dict, event: dict) -> bool:
    """
    Guard: Check if order has a valid contact attached.
    """
    contact = context.get("contact_person") or context.get("contact")
    if not contact:
        return False

    # Optionally verify contact exists
    if frappe.db.exists("Contact", contact):
        return True

    return bool(contact)


# ============================================================================
# ACTIONS
# ============================================================================

def assign_to_sales_manager(context: dict, event: dict) -> dict:
    """
    Action: Assign order to Sales Manager (Angelina Jolie) for approval.
    """
    context = context.copy()
    context["assigned_to"] = SALES_MANAGER_EMAIL
    context["assignment_type"] = "approval"
    context["assigned_at"] = str(frappe.utils.now())

    # Create ToDo assignment if document reference exists
    doctype = context.get("doctype")
    docname = context.get("docname") or context.get("name")

    if doctype and docname:
        try:
            frappe.get_doc({
                "doctype": "ToDo",
                "owner": SALES_MANAGER_EMAIL,
                "allocated_to": SALES_MANAGER_EMAIL,
                "reference_type": doctype,
                "reference_name": docname,
                "description": f"Please approve this {doctype}: {docname} (Value: {context.get('grand_total', 0)})",
                "priority": "High",
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Failed to create ToDo: {e}", "Workflow Assignment")

    return context


def assign_to_reviewer(context: dict, event: dict) -> dict:
    """
    Action: Assign order to Reviewer (Black Jack) for review.
    """
    context = context.copy()
    context["assigned_to"] = REVIEWER_EMAIL
    context["assigned_reviewer"] = REVIEWER_EMAIL
    context["assignment_type"] = "review"
    context["assigned_at"] = str(frappe.utils.now())

    # Create ToDo assignment if document reference exists
    doctype = context.get("doctype")
    docname = context.get("docname") or context.get("name")

    if doctype and docname:
        try:
            frappe.get_doc({
                "doctype": "ToDo",
                "owner": REVIEWER_EMAIL,
                "allocated_to": REVIEWER_EMAIL,
                "reference_type": doctype,
                "reference_name": docname,
                "description": f"Please review this {doctype}: {docname} (Value: {context.get('grand_total', 0)})",
                "priority": "Medium",
            }).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Failed to create ToDo: {e}", "Workflow Assignment")

    return context


def record_submission(context: dict, event: dict) -> dict:
    """
    Action: Record submission details.
    """
    context = context.copy()
    context["submitted_by"] = frappe.session.user
    context["submitted_at"] = str(frappe.utils.now())
    context["workflow_status"] = "Submitted"
    return context


def record_approval(context: dict, event: dict) -> dict:
    """
    Action: Record approval details.
    """
    context = context.copy()
    context["approved_by"] = frappe.session.user
    context["approved_at"] = str(frappe.utils.now())
    context["approval_note"] = event.get("note", "")
    context["workflow_status"] = "Approved"

    # Close any pending ToDos
    _close_pending_todos(context)

    return context


def record_rejection(context: dict, event: dict) -> dict:
    """
    Action: Record rejection details.
    """
    context = context.copy()
    context["rejected_by"] = frappe.session.user
    context["rejected_at"] = str(frappe.utils.now())
    context["rejection_reason"] = event.get("reason", "No reason provided")
    context["workflow_status"] = "Rejected"

    # Close any pending ToDos
    _close_pending_todos(context)

    return context


def record_review_complete(context: dict, event: dict) -> dict:
    """
    Action: Record review completion.
    """
    context = context.copy()
    context["reviewed_by"] = frappe.session.user
    context["reviewed_at"] = str(frappe.utils.now())
    context["review_notes"] = event.get("notes", "")
    context["workflow_status"] = "Reviewed"

    # Close any pending ToDos
    _close_pending_todos(context)

    return context


def notify_creator_approved(context: dict, event: dict) -> dict:
    """
    Action: Notify the creator that their order was approved.
    """
    owner = context.get("owner")
    if owner:
        try:
            frappe.sendmail(
                recipients=[owner],
                subject=_("Sales Order Approved"),
                message=_("""
                    <p>Good news! Your Sales Order has been approved.</p>
                    <p><b>Order:</b> {name}</p>
                    <p><b>Value:</b> {grand_total}</p>
                    <p><b>Approved by:</b> {approved_by}</p>
                """).format(**context)
            )
        except Exception as e:
            frappe.log_error(f"Failed to send approval notification: {e}", "Workflow Notification")

    return context


def notify_creator_rejected(context: dict, event: dict) -> dict:
    """
    Action: Notify the creator that their order was rejected.
    """
    owner = context.get("owner")
    if owner:
        try:
            frappe.sendmail(
                recipients=[owner],
                subject=_("Sales Order Rejected"),
                message=_("""
                    <p>Your Sales Order has been rejected.</p>
                    <p><b>Order:</b> {name}</p>
                    <p><b>Value:</b> {grand_total}</p>
                    <p><b>Rejected by:</b> {rejected_by}</p>
                    <p><b>Reason:</b> {rejection_reason}</p>
                    <p>Please make necessary corrections and resubmit.</p>
                """).format(**context)
            )
        except Exception as e:
            frappe.log_error(f"Failed to send rejection notification: {e}", "Workflow Notification")

    return context


def notify_sales_manager(context: dict, event: dict) -> dict:
    """
    Action: Notify Sales Manager of pending approval.
    """
    try:
        frappe.sendmail(
            recipients=[SALES_MANAGER_EMAIL],
            subject=_("Sales Order Pending Approval"),
            message=_("""
                <p>A new high-value Sales Order requires your approval.</p>
                <p><b>Order:</b> {name}</p>
                <p><b>Value:</b> {grand_total}</p>
                <p><b>Created by:</b> {owner}</p>
                <p>Please review and approve/reject this order.</p>
            """).format(**context)
        )
    except Exception as e:
        frappe.log_error(f"Failed to send manager notification: {e}", "Workflow Notification")

    return context


def notify_reviewer(context: dict, event: dict) -> dict:
    """
    Action: Notify Reviewer of pending review.
    """
    try:
        frappe.sendmail(
            recipients=[REVIEWER_EMAIL],
            subject=_("Sales Order Pending Review"),
            message=_("""
                <p>A Sales Order requires your review.</p>
                <p><b>Order:</b> {name}</p>
                <p><b>Value:</b> {grand_total}</p>
                <p><b>Created by:</b> {owner}</p>
                <p>Please review this order.</p>
            """).format(**context)
        )
    except Exception as e:
        frappe.log_error(f"Failed to send reviewer notification: {e}", "Workflow Notification")

    return context


def log_workflow_event(context: dict, event: dict) -> dict:
    """
    Action: Log workflow transition for audit trail.
    """
    frappe.log_error(
        title="Sales Order Workflow Event",
        message=f"""
        Event: {event.get('type')}
        Document: {context.get('doctype')}/{context.get('name')}
        User: {frappe.session.user}
        Timestamp: {frappe.utils.now()}
        Grand Total: {context.get('grand_total', 0)}
        """
    )
    return context


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _close_pending_todos(context: dict):
    """Helper: Close any pending ToDos for this document."""
    doctype = context.get("doctype")
    docname = context.get("docname") or context.get("name")

    if doctype and docname:
        try:
            todos = frappe.get_all(
                "ToDo",
                filters={
                    "reference_type": doctype,
                    "reference_name": docname,
                    "status": "Open"
                },
                pluck="name"
            )
            for todo in todos:
                frappe.db.set_value("ToDo", todo, "status", "Closed")
        except Exception as e:
            frappe.log_error(f"Failed to close ToDos: {e}", "Workflow Cleanup")


# ============================================================================
# EXPORT GUARDS AND ACTIONS
# ============================================================================

# These dicts are loaded by the workflow engine when logic_module is specified
guards = {
    "isHighValueOrder": is_high_value_order,
    "isLowValueOrder": is_low_value_order,
    "isSalesManager": is_sales_manager,
    "isSalesUser": is_sales_user,
    "isReviewer": is_reviewer,
    "isNotCreator": is_not_creator,
    "canApprove": can_approve,
    "canReview": can_review,
    "hasValidContact": has_valid_contact,
}

actions = {
    "assignToSalesManager": assign_to_sales_manager,
    "assignToReviewer": assign_to_reviewer,
    "recordSubmission": record_submission,
    "recordApproval": record_approval,
    "recordRejection": record_rejection,
    "recordReviewComplete": record_review_complete,
    "notifyCreatorApproved": notify_creator_approved,
    "notifyCreatorRejected": notify_creator_rejected,
    "notifySalesManager": notify_sales_manager,
    "notifyReviewer": notify_reviewer,
    "logWorkflowEvent": log_workflow_event,
}
