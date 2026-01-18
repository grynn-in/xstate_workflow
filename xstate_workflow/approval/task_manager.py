# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Approval Task Manager.

Central module for creating, managing, and completing approval tasks
within the XState workflow system.
"""

import json
from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.utils import now_datetime, add_to_date

if TYPE_CHECKING:
    from frappe.model.document import Document


class ApprovalTaskManager:
    """
    Manager class for approval task operations.

    Provides a unified interface for creating and managing approval tasks
    that integrates with the workflow engine and resolver system.
    """

    def __init__(self, workflow_instance: str = None):
        """
        Initialize manager for a specific workflow instance.

        Args:
            workflow_instance: Optional workflow instance name
        """
        self.workflow_instance = workflow_instance
        self._instance_doc = None

    @property
    def instance_doc(self):
        """Get the workflow instance document."""
        if not self._instance_doc and self.workflow_instance:
            self._instance_doc = frappe.get_doc("Machine Instance", self.workflow_instance)
        return self._instance_doc

    def create_task(
        self,
        node_id: str,
        node_label: str,
        assignees: list[str],
        available_actions: list[str] = None,
        sla_hours: float = None,
        priority: str = "Medium",
        tenant: str = None,
        assigned_role: str = None
    ) -> "Document":
        """
        Create an approval task for a workflow node.

        Args:
            node_id: The state/node ID in the workflow
            node_label: Human-readable label for the node
            assignees: List of user IDs who can complete the task
            available_actions: List of action names (default: ["Approve", "Reject"])
            sla_hours: Optional SLA in hours
            priority: Task priority (Low, Medium, High, Urgent)
            tenant: Optional tenant/company
            assigned_role: Optional role name for role-based assignments

        Returns:
            Created Approval Task document
        """
        if not self.instance_doc:
            frappe.throw(_("Workflow instance not set"))

        if not assignees:
            frappe.throw(_("At least one assignee is required"))

        # Get reference from workflow instance
        reference_doctype = self.instance_doc.reference_doctype
        reference_name = self.instance_doc.reference_name

        # Default actions
        if not available_actions:
            available_actions = ["Approve", "Reject"]

        # Determine tenant
        if not tenant:
            tenant = self._get_tenant()

        # For role-based assignments, don't set a specific assignee initially
        # Any user with the role can claim and action the task
        # For user-based assignments, set the specific user
        if assigned_role:
            primary_assignee = None  # Role-based: anyone with role can claim
        else:
            primary_assignee = assignees[0] if assignees else None

        task = frappe.get_doc({
            "doctype": "Approval Task",
            "workflow_instance": self.workflow_instance,
            "node_id": node_id,
            "node_label": node_label,
            "reference_doctype": reference_doctype,
            "reference_name": reference_name,
            "assigned_to": primary_assignee,
            "assigned_role": assigned_role,
            "original_assignee": primary_assignee,
            "status": "Pending",
            "priority": priority,
            "available_actions": json.dumps(available_actions),
            "sla_hours": sla_hours,
            "tenant": tenant
        })

        task.insert(ignore_permissions=True)

        # If multiple assignees, store in context for parallel approval
        if len(assignees) > 1:
            self._store_parallel_assignees(node_id, assignees)

        return task

    def complete_task(
        self,
        task_name: str,
        action: str,
        comments: str = None,
        user: str = None
    ) -> dict:
        """
        Complete an approval task.

        Args:
            task_name: Approval Task document name
            action: The action taken
            comments: Optional comments
            user: User completing the task (defaults to session user)

        Returns:
            Dict with completion result
        """
        task = frappe.get_doc("Approval Task", task_name)

        if task.status != "Pending":
            frappe.throw(_("Task is not pending"))

        user = user or frappe.session.user

        # Validate user can complete
        if not task.can_user_complete(user):
            frappe.throw(_("You are not authorized to complete this task"))

        # Complete the task
        return task.complete(action, comments)

    def cancel_pending_tasks(self) -> int:
        """
        Cancel all pending tasks for the current workflow instance.

        Returns:
            Number of tasks cancelled
        """
        if not self.workflow_instance:
            return 0

        tasks = frappe.get_all(
            "Approval Task",
            filters={
                "workflow_instance": self.workflow_instance,
                "status": "Pending"
            },
            pluck="name"
        )

        for task_name in tasks:
            frappe.db.set_value(
                "Approval Task",
                task_name,
                {
                    "status": "Cancelled",
                    "comments": "Workflow cancelled or transitioned"
                }
            )

        return len(tasks)

    def get_pending_tasks(self) -> list[dict]:
        """
        Get all pending tasks for the current workflow instance.

        Returns:
            List of task dicts
        """
        if not self.workflow_instance:
            return []

        return frappe.get_all(
            "Approval Task",
            filters={
                "workflow_instance": self.workflow_instance,
                "status": "Pending"
            },
            fields=["name", "node_id", "node_label", "assigned_to", "due_date", "priority"]
        )

    def _get_tenant(self) -> str | None:
        """Get tenant from workflow instance or reference document."""
        if self.instance_doc:
            # Try to get from reference document
            try:
                ref_doc = frappe.get_doc(
                    self.instance_doc.reference_doctype,
                    self.instance_doc.reference_name
                )
                if hasattr(ref_doc, "company") and ref_doc.company:
                    return ref_doc.company
            except Exception:
                pass

        return None

    def _store_parallel_assignees(self, node_id: str, assignees: list[str]):
        """Store parallel assignees in workflow context."""
        if not self.instance_doc:
            return

        context = self.instance_doc.get_context_dict()
        if "_parallel_assignees" not in context:
            context["_parallel_assignees"] = {}

        context["_parallel_assignees"][node_id] = assignees
        self.instance_doc.set_context(context)
        self.instance_doc.save(ignore_permissions=True)


# Convenience functions

def create_approval_task(
    workflow_instance: str,
    node_id: str,
    node_label: str,
    assignees: list[str],
    available_actions: list[str] = None,
    sla_hours: float = None,
    priority: str = "Medium",
    tenant: str = None,
    assigned_role: str = None
) -> "Document":
    """
    Create an approval task.

    Convenience wrapper around ApprovalTaskManager.create_task.
    """
    manager = ApprovalTaskManager(workflow_instance)
    return manager.create_task(
        node_id=node_id,
        node_label=node_label,
        assignees=assignees,
        available_actions=available_actions,
        sla_hours=sla_hours,
        priority=priority,
        tenant=tenant,
        assigned_role=assigned_role
    )


def complete_approval_task(
    task_name: str,
    action: str,
    comments: str = None,
    user: str = None
) -> dict:
    """
    Complete an approval task.

    Convenience wrapper that loads the task and completes it.
    """
    task = frappe.get_doc("Approval Task", task_name)
    manager = ApprovalTaskManager(task.workflow_instance)
    return manager.complete_task(task_name, action, comments, user)


def cancel_pending_tasks(workflow_instance: str) -> int:
    """
    Cancel all pending tasks for a workflow instance.

    Args:
        workflow_instance: Workflow instance name

    Returns:
        Number of tasks cancelled
    """
    manager = ApprovalTaskManager(workflow_instance)
    return manager.cancel_pending_tasks()


def get_my_approval_tasks(
    user: str = None,
    status: str = "pending_with_me",
    limit: int = 20,
    offset: int = 0,
    filters: dict = None,
    order_by: str = None
) -> list[dict]:
    """
    Get approval tasks for a user with user-centric status filtering.

    Args:
        user: User ID (defaults to session user)
        status: User-centric status filter. Options:
            - "pending_with_me": Tasks assigned to user (direct or role) that are pending
            - "overdue_with_me": Pending tasks past due date
            - "completed_by_me": Tasks completed by this user
            - "escalated": Escalated tasks assigned to user
            - "in_progress_others": Workflows user participated in, currently with someone else
            - Legacy values ("Pending", "Completed", etc.) are also supported
        limit: Maximum number of tasks to return
        offset: Offset for pagination
        filters: Additional filters
        order_by: Sort order (e.g., "modified desc")

    Returns:
        List of task dicts
    """
    user = user or frappe.session.user
    user_roles = frappe.get_roles(user)
    is_system_manager = "System Manager" in user_roles

    # Handle new user-centric status types
    if status == "pending_with_me":
        # Tasks assigned to user (direct or role) that are pending
        # System Manager can see ALL pending tasks (can claim any)
        base_filters = {"status": "Pending"}
        if is_system_manager:
            or_filters = None  # No filter - show all pending tasks
        else:
            or_filters = [{"assigned_to": user}]
            if user_roles:
                or_filters.append({"assigned_role": ["in", user_roles]})

    elif status == "overdue_with_me":
        # Pending tasks that are past due date
        base_filters = {
            "status": "Pending",
            "due_date": ["<", now_datetime()]
        }
        or_filters = [{"assigned_to": user}]
        if user_roles:
            or_filters.append({"assigned_role": ["in", user_roles]})

    elif status == "completed_by_me":
        # Tasks completed by this user (regardless of original assignee)
        base_filters = {"completed_by": user, "status": "Completed"}
        or_filters = None

    elif status == "escalated":
        # Escalated tasks assigned to user
        base_filters = {"status": "Escalated"}
        or_filters = [{"assigned_to": user}]
        if user_roles:
            or_filters.append({"assigned_role": ["in", user_roles]})

    elif status == "in_progress_others":
        # Workflows user participated in, currently with someone else
        return _get_in_progress_others(user, user_roles, limit, offset, filters, order_by)

    else:
        # Legacy support: treat as direct status filter
        base_filters = {"status": status}
        or_filters = [{"assigned_to": user}]
        if user_roles:
            or_filters.append({"assigned_role": ["in", user_roles]})

    # Apply additional filters if provided
    if filters:
        base_filters.update(filters)

    # Determine sort order
    sort_order = order_by if order_by else "priority desc, due_date asc, creation asc"

    # Query tasks
    if or_filters:
        tasks = frappe.get_all(
            "Approval Task",
            filters=base_filters,
            or_filters=or_filters,
            fields=_get_task_fields(),
            order_by=sort_order,
            limit_page_length=limit,
            limit_start=offset
        )
    else:
        tasks = frappe.get_all(
            "Approval Task",
            filters=base_filters,
            fields=_get_task_fields(),
            order_by=sort_order,
            limit_page_length=limit,
            limit_start=offset
        )

    # Enrich tasks with additional details
    _enrich_tasks(tasks)

    return tasks


def _get_task_fields() -> list[str]:
    """Return the standard fields to fetch for approval tasks."""
    return [
        "name",
        "workflow_instance",
        "node_id",
        "node_label",
        "reference_doctype",
        "reference_name",
        "assigned_to",
        "assigned_role",
        "status",
        "priority",
        "due_date",
        "available_actions",
        "action_taken",
        "completed_by",
        "completed_at",
        "creation",
        "modified"
    ]


def _enrich_tasks(tasks: list[dict]) -> None:
    """Enrich tasks with additional details (modifies in place)."""
    for task in tasks:
        # Parse available_actions JSON
        if task.get("available_actions"):
            try:
                task["available_actions"] = json.loads(task.available_actions)
            except json.JSONDecodeError:
                task["available_actions"] = ["Approve", "Reject"]
        else:
            task["available_actions"] = ["Approve", "Reject"]

        # Calculate overdue status
        if task.get("due_date"):
            task["is_overdue"] = frappe.utils.get_datetime(task.due_date) < now_datetime()
        else:
            task["is_overdue"] = False

        # Fetch reference document details
        try:
            doc_info = frappe.db.get_value(
                task.reference_doctype,
                task.reference_name,
                ["creation", "modified", "owner"],
                as_dict=True
            )
            if doc_info:
                task["doc_created"] = doc_info.creation
                task["doc_modified"] = doc_info.modified
                task["doc_owner"] = doc_info.owner
                task["doc_owner_name"] = frappe.db.get_value(
                    "User", doc_info.owner, "full_name"
                ) or doc_info.owner
        except Exception:
            pass

        # Get completed_by full name for completed tasks
        if task.get("completed_by"):
            task["completed_by_name"] = frappe.db.get_value(
                "User", task.completed_by, "full_name"
            ) or task.completed_by

        # Get assigned_to full name
        if task.get("assigned_to"):
            task["assigned_to_name"] = frappe.db.get_value(
                "User", task.assigned_to, "full_name"
            ) or task.assigned_to

        # Get workflow submission date from Machine Instance
        if task.get("workflow_instance"):
            task["workflow_submitted"] = frappe.db.get_value(
                "Machine Instance", task.workflow_instance, "creation"
            )

        # Get last approver from previous completed tasks for this workflow
        try:
            last_approval = frappe.db.sql("""
                SELECT completed_by, action_taken, completed_at
                FROM `tabApproval Task`
                WHERE workflow_instance = %s
                AND status = 'Completed'
                AND name != %s
                ORDER BY completed_at DESC
                LIMIT 1
            """, (task.get("workflow_instance"), task.get("name")), as_dict=True)

            if last_approval:
                approver = last_approval[0]
                approver["completed_by_name"] = frappe.db.get_value(
                    "User", approver.completed_by, "full_name"
                ) or approver.completed_by
                task["last_approver"] = approver
        except Exception:
            pass


def _get_in_progress_others(
    user: str,
    user_roles: list[str],
    limit: int,
    offset: int,
    filters: dict = None,
    order_by: str = None
) -> list[dict]:
    """
    Get tasks in workflows user participated in, currently with someone else.

    This shows workflows where the user:
    1. Submitted/created the document, OR
    2. Previously approved (was assigned and completed a task)

    AND the workflow is still active with tasks assigned to others.

    Args:
        user: User ID
        user_roles: List of user's roles
        limit: Maximum number of tasks to return
        offset: Offset for pagination
        filters: Additional filters to apply
        order_by: Sort order (e.g., "modified desc")
    """
    # Get workflow instances user participated in (as assignee or completer)
    participated = frappe.db.sql("""
        SELECT DISTINCT workflow_instance
        FROM `tabApproval Task`
        WHERE (assigned_to = %s OR completed_by = %s)
        AND workflow_instance IS NOT NULL
    """, (user, user), as_list=True)

    if not participated:
        return []

    workflow_ids = [w[0] for w in participated]

    # Build query to get current pending tasks in those workflows NOT assigned to user
    # We need tasks where:
    # - workflow_instance in participated workflows
    # - status is active (Pending, In Progress, Escalated)
    # - NOT assigned to current user (directly or via role)

    # Build base filters
    task_filters = {
        "workflow_instance": ["in", workflow_ids],
        "status": ["in", ["Pending", "In Progress", "Escalated"]]
    }

    # Apply additional filters
    if filters:
        task_filters.update(filters)

    # Determine sort order
    sort_order = order_by if order_by else "creation desc"

    # First get all active tasks in participated workflows
    all_tasks = frappe.get_all(
        "Approval Task",
        filters=task_filters,
        fields=_get_task_fields(),
        order_by=sort_order
    )

    # Filter out tasks that ARE assigned to the current user
    tasks = []
    for task in all_tasks:
        is_assigned_to_user = False

        # Check direct assignment
        if task.assigned_to == user:
            is_assigned_to_user = True
        # Check role-based assignment
        elif task.assigned_role and task.assigned_role in user_roles:
            is_assigned_to_user = True

        if not is_assigned_to_user:
            tasks.append(task)

    # Apply pagination
    paginated_tasks = tasks[offset:offset + limit]

    # Enrich tasks
    _enrich_tasks(paginated_tasks)

    return paginated_tasks


def get_task_for_node(workflow_instance: str, node_id: str) -> "Document | None":
    """
    Get the pending approval task for a specific node.

    Args:
        workflow_instance: Workflow instance name
        node_id: Node ID in the workflow

    Returns:
        Approval Task document or None
    """
    task_name = frappe.db.get_value(
        "Approval Task",
        {
            "workflow_instance": workflow_instance,
            "node_id": node_id,
            "status": "Pending"
        },
        "name"
    )

    if task_name:
        return frappe.get_doc("Approval Task", task_name)

    return None


def reassign_task(
    task_name: str,
    new_user: str,
    reason: str = None
) -> dict:
    """
    Reassign an approval task to another user.

    Args:
        task_name: Approval Task document name
        new_user: User ID to reassign to
        reason: Optional reason for reassignment

    Returns:
        Dict with reassignment result
    """
    task = frappe.get_doc("Approval Task", task_name)
    return task.reassign(new_user, reason)


def escalate_task(
    task_name: str,
    escalate_to: str = None,
    reason: str = None
) -> "Document":
    """
    Escalate an approval task.

    Args:
        task_name: Approval Task document name
        escalate_to: Optional user to escalate to
        reason: Optional reason for escalation

    Returns:
        New escalated Approval Task document
    """
    task = frappe.get_doc("Approval Task", task_name)
    return task.escalate(escalate_to, reason)


def check_overdue_tasks():
    """
    Check for overdue tasks and handle escalation.

    Called by scheduler to process overdue approval tasks.
    """
    overdue_tasks = frappe.get_all(
        "Approval Task",
        filters={
            "status": "Pending",
            "due_date": ["<", now_datetime()]
        },
        fields=["name", "workflow_instance", "node_id", "escalation_level"]
    )

    for task_data in overdue_tasks:
        try:
            # Get task configuration from workflow
            task = frappe.get_doc("Approval Task", task_data.name)
            instance = frappe.get_doc("Machine Instance", task.workflow_instance)
            machine = frappe.get_doc("State Machine", instance.machine)

            # Check if escalation is configured for this node
            config = json.loads(machine.json_config or "{}")
            node_config = _find_node_config(config, task.node_id)

            if node_config and node_config.get("escalation"):
                escalation_config = node_config["escalation"]
                max_level = escalation_config.get("max_level", 3)

                if task.escalation_level < max_level:
                    # Escalate the task
                    escalate_to = _resolve_escalation_target(
                        task, instance, escalation_config
                    )
                    task.escalate(escalate_to, "Automatic escalation due to SLA breach")

                    frappe.log_error(
                        f"Escalated task {task.name} to {escalate_to}",
                        "Approval Task Escalation"
                    )

        except Exception as e:
            frappe.log_error(
                f"Error processing overdue task {task_data.name}: {e}",
                "Approval Task Scheduler"
            )


def _find_node_config(config: dict, node_id: str) -> dict | None:
    """Find configuration for a specific node in XState config."""
    states = config.get("states", {})

    def search_states(states_dict, target_id):
        for state_id, state_config in states_dict.items():
            if state_id == target_id:
                return state_config
            if "states" in state_config:
                result = search_states(state_config["states"], target_id)
                if result:
                    return result
        return None

    return search_states(states, node_id)


def _resolve_escalation_target(
    task: "Document",
    instance: "Document",
    escalation_config: dict
) -> str | None:
    """Resolve who to escalate to based on configuration."""
    escalation_type = escalation_config.get("type", "hierarchy")

    if escalation_type == "hierarchy":
        # Use hierarchy resolver to get next level
        from xstate_workflow.resolvers import resolve_assignment

        # Use ignore_permissions since this is called by scheduler for escalation
        ref_doc = frappe.get_doc(instance.reference_doctype, instance.reference_name, ignore_permissions=True)

        resolver_config = escalation_config.get("resolver", {
            "type": "hierarchy_walk",
            "hierarchy_doctype": "Employee",
            "parent_field": "reports_to",
            "user_field": "user_id",
            "start_from": "document_field",
            "start_field": task.assigned_to,
            "level_mode": "fixed",
            "levels_up": 1
        })

        try:
            users = resolve_assignment(ref_doc, resolver_config, {})
            if users:
                return users[0]
        except Exception:
            pass

    elif escalation_type == "static":
        return escalation_config.get("user")

    elif escalation_type == "role":
        from xstate_workflow.resolvers.base import get_users_with_role
        role = escalation_config.get("role")
        if role:
            users = get_users_with_role(role)
            if users:
                return users[0]

    return None
