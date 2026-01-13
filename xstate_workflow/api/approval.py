# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Approval Task API Endpoints.

Whitelisted methods for managing approval tasks from the frontend.
"""

import json
import frappe
from frappe import _


@frappe.whitelist()
def get_my_approval_tasks(
    status: str = "Pending",
    limit: int = 20,
    offset: int = 0,
    filters: str = None
) -> dict:
    """
    Get approval tasks for the current user.

    Args:
        status: Task status filter
        limit: Page size
        offset: Page offset
        filters: Additional JSON filters

    Returns:
        Dict with tasks and total count
    """
    from xstate_workflow.approval import get_my_approval_tasks as get_tasks

    additional_filters = json.loads(filters) if filters else None

    tasks = get_tasks(
        user=frappe.session.user,
        status=status,
        limit=int(limit),
        offset=int(offset),
        filters=additional_filters
    )

    # Get total count (including role-based tasks)
    user_roles = frappe.get_roles(frappe.session.user)
    base_count_filters = {"status": status}
    if additional_filters:
        base_count_filters.update(additional_filters)

    # Count tasks assigned directly to user
    direct_filters = {**base_count_filters, "assigned_to": frappe.session.user}
    direct_count = frappe.db.count("Approval Task", direct_filters)

    # Count tasks assigned to user's roles (excluding those already counted)
    role_count = 0
    if user_roles:
        role_filters = {
            **base_count_filters,
            "assigned_role": ["in", user_roles],
            "assigned_to": ["!=", frappe.session.user]
        }
        role_count = frappe.db.count("Approval Task", role_filters)

    total = direct_count + role_count

    return {
        "tasks": tasks,
        "total": total,
        "limit": int(limit),
        "offset": int(offset)
    }


@frappe.whitelist()
def complete_approval_task(
    task_name: str,
    action: str,
    comments: str = None
) -> dict:
    """
    Complete an approval task.

    Args:
        task_name: Approval Task name
        action: Action taken (must be in available_actions)
        comments: Optional comments

    Returns:
        Completion result
    """
    from xstate_workflow.approval import complete_approval_task as complete_task
    return complete_task(task_name, action, comments)


@frappe.whitelist()
def reassign_task(
    task_name: str,
    new_user: str,
    reason: str = None
) -> dict:
    """
    Reassign an approval task.

    Args:
        task_name: Approval Task name
        new_user: User to reassign to
        reason: Optional reason

    Returns:
        Reassignment result
    """
    from xstate_workflow.approval import reassign_task
    return reassign_task(task_name, new_user, reason)


@frappe.whitelist()
def escalate_task(
    task_name: str,
    escalate_to: str = None,
    reason: str = None
) -> dict:
    """
    Escalate an approval task.

    Args:
        task_name: Approval Task name
        escalate_to: Optional user to escalate to
        reason: Optional reason

    Returns:
        Dict with new task name
    """
    from xstate_workflow.approval import escalate_task
    new_task = escalate_task(task_name, escalate_to, reason)
    return {"new_task": new_task.name}


@frappe.whitelist()
def get_task_details(task_name: str) -> dict:
    """
    Get detailed information about an approval task.

    Args:
        task_name: Approval Task name

    Returns:
        Task details with reference document info
    """
    task = frappe.get_doc("Approval Task", task_name)

    # Get reference document details
    ref_doc = None
    if task.reference_doctype and task.reference_name:
        try:
            ref_doc = frappe.get_doc(task.reference_doctype, task.reference_name)
        except frappe.DoesNotExistError:
            pass

    # Parse available actions
    available_actions = task.get_available_actions_list()

    return {
        "name": task.name,
        "workflow_instance": task.workflow_instance,
        "node_id": task.node_id,
        "node_label": task.node_label,
        "reference_doctype": task.reference_doctype,
        "reference_name": task.reference_name,
        "assigned_to": task.assigned_to,
        "original_assignee": task.original_assignee,
        "status": task.status,
        "priority": task.priority,
        "available_actions": available_actions,
        "action_taken": task.action_taken,
        "comments": task.comments,
        "due_date": str(task.due_date) if task.due_date else None,
        "is_overdue": task.is_overdue(),
        "time_remaining_hours": task.get_time_remaining(),
        "completed_at": str(task.completed_at) if task.completed_at else None,
        "completed_by": task.completed_by,
        "escalation_level": task.escalation_level,
        "escalated_from": task.escalated_from,
        "created": str(task.creation),
        "reference_document": {
            "doctype": task.reference_doctype,
            "name": task.reference_name,
            "title": getattr(ref_doc, "title", None) or getattr(ref_doc, "name", None) if ref_doc else None,
            "owner": ref_doc.owner if ref_doc else None,
        } if ref_doc else None
    }


@frappe.whitelist()
def get_approval_counts() -> dict:
    """
    Get counts of approval tasks for the current user.

    Returns:
        Dict with task counts by status
    """
    user = frappe.session.user

    counts = {}
    for status in ["Pending", "In Progress", "Completed", "Cancelled", "Escalated"]:
        counts[status.lower().replace(" ", "_")] = frappe.db.count(
            "Approval Task",
            {"assigned_to": user, "status": status}
        )

    # Count overdue
    from frappe.utils import now_datetime
    counts["overdue"] = frappe.db.count(
        "Approval Task",
        {
            "assigned_to": user,
            "status": "Pending",
            "due_date": ["<", now_datetime()]
        }
    )

    return counts


@frappe.whitelist()
def claim_task(task_name: str) -> dict:
    """
    Claim a role-based task for the current user.

    Args:
        task_name: Approval Task name

    Returns:
        Dict with success status
    """
    task = frappe.get_doc("Approval Task", task_name)
    user = frappe.session.user

    # Verify user can claim (has the role or is System Manager)
    if task.assigned_role:
        user_roles = frappe.get_roles(user)
        if task.assigned_role not in user_roles and "System Manager" not in user_roles:
            frappe.throw(_("You don't have the required role to claim this task"))
    elif task.assigned_to and task.assigned_to != user:
        # Task is assigned to a specific user, not a role
        if "System Manager" not in frappe.get_roles(user):
            frappe.throw(_("This task is assigned to another user"))

    # Update assignment (use ignore_permissions since we've already verified authorization)
    old_assignee = task.assigned_to
    task.assigned_to = user
    task.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "old_assignee": old_assignee,
        "new_assignee": user
    }


@frappe.whitelist()
def get_role_assignees(task_name: str) -> list:
    """
    Get all users who can action a role-based task.

    Args:
        task_name: Approval Task name

    Returns:
        List of user details
    """
    task = frappe.get_doc("Approval Task", task_name)

    if not task.assigned_role:
        # Not role-based, return empty
        return []

    # Get users with the role
    users = frappe.get_all(
        "Has Role",
        filters={"role": task.assigned_role, "parenttype": "User"},
        pluck="parent"
    )

    # Filter enabled users only
    enabled_users = frappe.get_all(
        "User",
        filters={"name": ["in", users], "enabled": 1},
        fields=["name", "full_name", "user_image"]
    )

    return enabled_users


@frappe.whitelist()
def get_resolver_types() -> list:
    """
    Get available resolver types for UI configuration.

    Returns:
        List of resolver type definitions
    """
    from xstate_workflow.resolvers import list_resolver_types
    return list_resolver_types()


@frappe.whitelist()
def preview_resolver(
    doctype: str,
    docname: str,
    resolver_config: str
) -> dict:
    """
    Preview resolver results for a document.

    Args:
        doctype: Document type
        docname: Document name
        resolver_config: JSON resolver configuration

    Returns:
        Dict with resolved users
    """
    from xstate_workflow.resolvers import resolve_assignment

    doc = frappe.get_doc(doctype, docname)
    config = json.loads(resolver_config)

    try:
        users = resolve_assignment(doc, config, {}, apply_delegation=False)
        return {
            "success": True,
            "users": users,
            "user_details": [
                {
                    "user": u,
                    "full_name": frappe.db.get_value("User", u, "full_name"),
                    "enabled": frappe.db.get_value("User", u, "enabled")
                }
                for u in users
            ]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "users": []
        }
