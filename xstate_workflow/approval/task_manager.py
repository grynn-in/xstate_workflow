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
    status: str = "Pending",
    limit: int = 20,
    offset: int = 0,
    filters: dict = None
) -> list[dict]:
    """
    Get approval tasks for a user.

    Args:
        user: User ID (defaults to session user)
        status: Task status filter (default: "Pending")
        limit: Maximum number of tasks to return
        offset: Offset for pagination
        filters: Additional filters

    Returns:
        List of task dicts
    """
    user = user or frappe.session.user

    # Get user's roles for role-based task assignment
    user_roles = frappe.get_roles(user)

    # Build OR filters: assigned directly to user OR assigned to a role the user has
    or_filters = [
        {"assigned_to": user}
    ]

    # Add role-based filter if user has any roles
    if user_roles:
        or_filters.append({"assigned_role": ["in", user_roles]})

    # Additional filters for status
    base_filters = {"status": status}
    if filters:
        base_filters.update(filters)

    tasks = frappe.get_all(
        "Approval Task",
        filters=base_filters,
        or_filters=or_filters,
        fields=[
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
            "creation",
            "modified"
        ],
        order_by="priority desc, due_date asc, creation asc",
        limit_page_length=limit,
        limit_start=offset
    )

    # Parse available_actions JSON
    for task in tasks:
        if task.available_actions:
            try:
                task["available_actions"] = json.loads(task.available_actions)
            except json.JSONDecodeError:
                task["available_actions"] = ["Approve", "Reject"]
        else:
            task["available_actions"] = ["Approve", "Reject"]

        # Calculate overdue status
        if task.due_date:
            task["is_overdue"] = frappe.utils.get_datetime(task.due_date) < now_datetime()
        else:
            task["is_overdue"] = False

    return tasks


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

        ref_doc = frappe.get_doc(instance.reference_doctype, instance.reference_name)

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
