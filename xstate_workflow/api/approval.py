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
    status: str = "pending_with_me",
    limit: int = 20,
    offset: int = 0,
    filters: str = None
) -> dict:
    """
    Get approval tasks for the current user.

    Args:
        status: User-centric status filter. Options:
            - "pending_with_me": Tasks assigned to user (direct or role) that are pending
            - "overdue_with_me": Pending tasks past due date
            - "completed_by_me": Tasks completed by this user
            - "escalated": Escalated tasks assigned to user
            - "in_progress_others": Workflows user participated in, currently with someone else
        limit: Page size
        offset: Page offset
        filters: Additional JSON filters

    Returns:
        Dict with tasks and total count
    """
    from xstate_workflow.approval import get_my_approval_tasks as get_tasks
    from frappe.utils import now_datetime

    additional_filters = json.loads(filters) if filters else None

    tasks = get_tasks(
        user=frappe.session.user,
        status=status,
        limit=int(limit),
        offset=int(offset),
        filters=additional_filters
    )

    # Get total count based on user-centric status
    total = _get_status_count(frappe.session.user, status, additional_filters)

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
    # Use ignore_permissions since user is assigned to this approval task
    ref_doc = None
    if task.reference_doctype and task.reference_name:
        try:
            ref_doc = frappe.get_doc(task.reference_doctype, task.reference_name)
        except (frappe.DoesNotExistError, frappe.PermissionError):
            # Fall back to db.get_value for basic info if user lacks permission
            try:
                doc_info = frappe.db.get_value(
                    task.reference_doctype,
                    task.reference_name,
                    ["name", "owner"],
                    as_dict=True
                )
                if doc_info:
                    # Create a minimal dict to provide basic info
                    ref_doc = frappe._dict({
                        "name": doc_info.name,
                        "owner": doc_info.owner,
                        "title": doc_info.name
                    })
            except Exception:
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
def get_current_user_info() -> dict:
    """
    Get current user info including workflow-relevant roles.

    Returns:
        Dict with user info and roles used in workflows
    """
    user = frappe.session.user
    user_doc = frappe.get_doc("User", user)

    # Get all user roles
    user_roles = frappe.get_roles(user)

    # Get roles that are used in approval tasks
    workflow_roles = []
    try:
        # Get roles used in active approval tasks
        used_roles = frappe.db.sql("""
            SELECT DISTINCT assigned_role
            FROM `tabApproval Task`
            WHERE assigned_role IS NOT NULL
            AND assigned_role != ''
        """, as_list=True)
        used_roles = [r[0] for r in used_roles]

        # Filter to only roles the user has
        workflow_roles = [r for r in user_roles if r in used_roles]

        # Also add common approval roles if user has them
        common_approval_roles = ["Sales User", "Sales Manager", "Accounts User", "Accounts Manager",
                                  "Purchase User", "Purchase Manager", "HR User", "HR Manager",
                                  "System Manager", "Workflow Manager"]
        for role in common_approval_roles:
            if role in user_roles and role not in workflow_roles:
                workflow_roles.append(role)
    except Exception:
        workflow_roles = []

    return {
        "user": user,
        "full_name": user_doc.full_name,
        "email": user_doc.email,
        "user_roles": user_roles,
        "workflow_roles": workflow_roles
    }


@frappe.whitelist()
def get_approval_counts() -> dict:
    """
    Get counts of approval tasks for the current user using user-centric statuses.

    Returns:
        Dict with task counts by user-centric status:
        - pending_with_me: Tasks assigned to user (direct or role) that are pending
        - overdue_with_me: Pending tasks past due date
        - completed_by_me: Tasks completed by this user
        - escalated: Escalated tasks assigned to user
        - in_progress_others: Workflows user participated in, currently with someone else
    """
    user = frappe.session.user

    return {
        "pending_with_me": _get_status_count(user, "pending_with_me"),
        "overdue_with_me": _get_status_count(user, "overdue_with_me"),
        "completed_by_me": _get_status_count(user, "completed_by_me"),
        "escalated": _get_status_count(user, "escalated"),
        "in_progress_others": _get_status_count(user, "in_progress_others")
    }


def _get_status_count(user: str, status: str, additional_filters: dict = None) -> int:
    """
    Get count for a specific user-centric status.

    Args:
        user: User ID
        status: User-centric status
        additional_filters: Optional additional filters

    Returns:
        Count of matching tasks
    """
    from frappe.utils import now_datetime

    user_roles = frappe.get_roles(user)

    if status == "pending_with_me":
        # Tasks assigned to user (direct or role) that are pending
        base_filters = {"status": "Pending"}
        if additional_filters:
            base_filters.update(additional_filters)

        # Count direct assignments
        direct_count = frappe.db.count("Approval Task", {
            **base_filters,
            "assigned_to": user
        })

        # Count role-based assignments (where no one has claimed it yet)
        role_count = 0
        if user_roles:
            role_count = frappe.db.count("Approval Task", {
                **base_filters,
                "assigned_role": ["in", user_roles],
                "assigned_to": ["is", "not set"]
            })
            # Also count role-based where assigned_to is empty string
            role_count += frappe.db.count("Approval Task", {
                **base_filters,
                "assigned_role": ["in", user_roles],
                "assigned_to": ""
            })

        return direct_count + role_count

    elif status == "overdue_with_me":
        # Pending tasks that are past due date
        base_filters = {
            "status": "Pending",
            "due_date": ["<", now_datetime()]
        }
        if additional_filters:
            base_filters.update(additional_filters)

        direct_count = frappe.db.count("Approval Task", {
            **base_filters,
            "assigned_to": user
        })

        role_count = 0
        if user_roles:
            role_count = frappe.db.count("Approval Task", {
                **base_filters,
                "assigned_role": ["in", user_roles],
                "assigned_to": ["is", "not set"]
            })
            role_count += frappe.db.count("Approval Task", {
                **base_filters,
                "assigned_role": ["in", user_roles],
                "assigned_to": ""
            })

        return direct_count + role_count

    elif status == "completed_by_me":
        # Tasks completed by this user (regardless of original assignee)
        base_filters = {"completed_by": user, "status": "Completed"}
        if additional_filters:
            base_filters.update(additional_filters)
        return frappe.db.count("Approval Task", base_filters)

    elif status == "escalated":
        # Escalated tasks assigned to user
        base_filters = {"status": "Escalated"}
        if additional_filters:
            base_filters.update(additional_filters)

        direct_count = frappe.db.count("Approval Task", {
            **base_filters,
            "assigned_to": user
        })

        role_count = 0
        if user_roles:
            role_count = frappe.db.count("Approval Task", {
                **base_filters,
                "assigned_role": ["in", user_roles],
                "assigned_to": ["is", "not set"]
            })
            role_count += frappe.db.count("Approval Task", {
                **base_filters,
                "assigned_role": ["in", user_roles],
                "assigned_to": ""
            })

        return direct_count + role_count

    elif status == "in_progress_others":
        # Workflows user participated in, currently with someone else
        return _count_in_progress_others(user, user_roles)

    else:
        # Legacy: direct status count
        return frappe.db.count("Approval Task", {
            "assigned_to": user,
            "status": status
        })


def _count_in_progress_others(user: str, user_roles: list) -> int:
    """
    Count tasks in workflows user participated in, currently with someone else.
    """
    # Get workflow instances user participated in
    participated = frappe.db.sql("""
        SELECT DISTINCT workflow_instance
        FROM `tabApproval Task`
        WHERE (assigned_to = %s OR completed_by = %s)
        AND workflow_instance IS NOT NULL
    """, (user, user), as_list=True)

    if not participated:
        return 0

    workflow_ids = [w[0] for w in participated]

    # Get all active tasks in those workflows
    all_tasks = frappe.get_all(
        "Approval Task",
        filters={
            "workflow_instance": ["in", workflow_ids],
            "status": ["in", ["Pending", "In Progress", "Escalated"]]
        },
        fields=["name", "assigned_to", "assigned_role"]
    )

    # Count tasks NOT assigned to current user
    count = 0
    for task in all_tasks:
        is_assigned_to_user = False

        if task.assigned_to == user:
            is_assigned_to_user = True
        elif task.assigned_role and task.assigned_role in user_roles:
            is_assigned_to_user = True

        if not is_assigned_to_user:
            count += 1

    return count


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
def submit_document(task_name: str) -> dict:
    """
    Submit the document associated with an approval task.

    Args:
        task_name: Approval Task name

    Returns:
        Dict with success status and docstatus
    """
    task = frappe.get_doc("Approval Task", task_name)

    # Verify user can complete this task
    user = frappe.session.user
    user_roles = frappe.get_roles(user)
    can_action = False

    if task.assigned_to == user:
        can_action = True
    elif task.assigned_role and task.assigned_role in user_roles:
        can_action = True
    elif "System Manager" in user_roles:
        can_action = True

    if not can_action:
        frappe.throw(_("You are not authorized to submit this document"))

    # Get reference document - use ignore_permissions since we've verified user can action the task
    try:
        ref_doc = frappe.get_doc(task.reference_doctype, task.reference_name)
    except frappe.PermissionError:
        # User can action this approval task but doesn't have direct doc permission
        # Allow access since they're an authorized approver
        ref_doc = frappe.get_doc(task.reference_doctype, task.reference_name, ignore_permissions=True)

    # Check if submittable
    if not ref_doc.meta.is_submittable:
        frappe.throw(_("This document type is not submittable"))

    # Check if already submitted
    if ref_doc.docstatus == 1:
        frappe.throw(_("Document is already submitted"))

    # Submit document - use ignore_permissions since user is authorized via approval task
    ref_doc.flags.ignore_permissions = True
    ref_doc.submit()

    return {"success": True, "docstatus": ref_doc.docstatus}


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
def get_document_approval_tasks(doctype: str, docname: str) -> list:
    """
    Get approval tasks for a specific document.

    Args:
        doctype: Document type
        docname: Document name

    Returns:
        List of approval tasks for this document
    """
    user = frappe.session.user
    user_roles = frappe.get_roles(user)

    # Get all tasks for this document
    tasks = frappe.get_all(
        "Approval Task",
        filters={
            "reference_doctype": doctype,
            "reference_name": docname
        },
        fields=[
            "name", "node_id", "node_label", "status",
            "assigned_to", "assigned_role", "priority",
            "available_actions", "action_taken", "due_date"
        ],
        order_by="creation desc"
    )

    # Add can_action flag to each task
    for task in tasks:
        can_action = False
        if task.status == "Pending":
            # Check if user can action this task
            if task.assigned_to == user:
                can_action = True
            elif task.assigned_role and task.assigned_role in user_roles:
                can_action = True
            elif "System Manager" in user_roles:
                can_action = True

        task["can_action"] = can_action

        # Parse available actions
        if task.available_actions:
            try:
                task["available_actions"] = json.loads(task.available_actions)
            except json.JSONDecodeError:
                task["available_actions"] = ["Approve", "Reject"]
        else:
            task["available_actions"] = ["Approve", "Reject"]

    return tasks


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
