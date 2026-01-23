# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, add_to_date


class ApprovalTask(Document):
    def before_insert(self):
        """Set default values and calculate due date."""
        if not self.status:
            self.status = "Pending"

        # Calculate due date from SLA if not set
        if self.sla_hours and not self.due_date:
            self.due_date = add_to_date(now_datetime(), hours=self.sla_hours)

        # Store original assignee if assigned_to is set
        if self.assigned_to and not self.original_assignee:
            self.original_assignee = self.assigned_to

    def validate(self):
        """Validate task data."""
        # Validate reference document exists
        if self.reference_doctype and self.reference_name:
            if not frappe.db.exists(self.reference_doctype, self.reference_name):
                frappe.throw(
                    _("Reference document {0} {1} does not exist").format(
                        self.reference_doctype, self.reference_name
                    )
                )

        # Validate workflow instance exists
        if self.workflow_instance:
            if not frappe.db.exists("Machine Instance", self.workflow_instance):
                frappe.throw(
                    _("Workflow Instance {0} does not exist").format(
                        self.workflow_instance
                    )
                )

    def after_insert(self):
        """Send notifications after task creation."""
        self.notify_assignee()

    def on_update(self):
        """Handle status changes and notifications."""
        if self.has_value_changed("status"):
            if self.status == "Completed":
                self.completed_at = now_datetime()
                self.completed_by = frappe.session.user

            # Invalidate approval counts cache for affected users
            self._invalidate_affected_caches()

            # Publish realtime update
            self.publish_realtime_update()

    def _invalidate_affected_caches(self):
        """Invalidate approval count caches for users affected by this task change."""
        from xstate_workflow.utils.cache import invalidate_approval_counts

        users_to_invalidate = set()
        if self.assigned_to:
            users_to_invalidate.add(self.assigned_to)
        if self.completed_by:
            users_to_invalidate.add(self.completed_by)

        for user in users_to_invalidate:
            invalidate_approval_counts(user)

    def notify_assignee(self):
        """Send notification to assigned user."""
        if not self.assigned_to:
            return

        try:
            frappe.publish_realtime(
                "approval_task_assigned",
                {
                    "task": self.name,
                    "node_label": self.node_label,
                    "reference_doctype": self.reference_doctype,
                    "reference_name": self.reference_name,
                },
                user=self.assigned_to,
            )
        except Exception:
            pass  # Don't fail if notification fails

    def publish_realtime_update(self):
        """Publish task update via realtime."""
        try:
            frappe.publish_realtime(
                "approval_task_updated",
                {
                    "task": self.name,
                    "status": self.status,
                    "action_taken": self.action_taken,
                },
                doctype=self.reference_doctype,
                docname=self.reference_name,
            )
        except Exception:
            pass

    def get_available_actions_list(self) -> list[str]:
        """Get available actions as a list."""
        if not self.available_actions:
            return ["Approve", "Reject"]

        try:
            return json.loads(self.available_actions)
        except json.JSONDecodeError:
            return ["Approve", "Reject"]

    def set_available_actions(self, actions: list[str]):
        """Set available actions from a list."""
        self.available_actions = json.dumps(actions)

    @frappe.whitelist()
    def complete(self, action: str, comments: str = None):
        """
        Complete the task with an action.

        Args:
            action: The action taken (must be in available_actions)
            comments: Optional comments

        Returns:
            dict with success status and next workflow state
        """
        # Validate user can complete this task
        if not self.can_user_complete(frappe.session.user):
            frappe.throw(_("You are not authorized to complete this task"))

        # Validate action is available
        available = self.get_available_actions_list()
        if action not in available:
            frappe.throw(
                _("Invalid action '{0}'. Available actions: {1}").format(
                    action, ", ".join(available)
                )
            )

        # Update task
        self.status = "Completed"
        self.action_taken = action
        self.comments = comments
        self.completed_at = now_datetime()
        self.completed_by = frappe.session.user
        self.save(ignore_permissions=True)

        # Resume workflow
        result = self.resume_workflow(action)

        return {
            "success": True,
            "action": action,
            "workflow_result": result
        }

    @frappe.whitelist()
    def reassign(self, new_user: str, reason: str = None):
        """
        Reassign the task to another user.

        Args:
            new_user: User ID to reassign to
            reason: Optional reason for reassignment

        Returns:
            dict with success status
        """
        # Check if user is authorized to reassign
        if not self.can_user_complete(frappe.session.user):
            frappe.throw(_("You are not authorized to reassign this task"))

        if not frappe.db.exists("User", new_user):
            frappe.throw(_("User {0} does not exist").format(new_user))

        if not frappe.db.get_value("User", new_user, "enabled"):
            frappe.throw(_("User {0} is disabled").format(new_user))

        old_user = self.assigned_to
        self.assigned_to = new_user
        # Keep status as Pending so the new assignee sees it in their task list
        # Only add a note about reassignment in comments

        if reason:
            self.comments = (self.comments or "") + f"\n\nReassigned from {old_user or 'unassigned'}: {reason}"
        else:
            self.comments = (self.comments or "") + f"\n\nReassigned from {old_user or 'unassigned'}"

        self.save(ignore_permissions=True)

        # Notify new assignee
        self.notify_assignee()

        return {
            "success": True,
            "old_user": old_user,
            "new_user": new_user
        }

    @frappe.whitelist()
    def escalate(self, escalate_to: str = None, reason: str = None):
        """
        Escalate the task.

        Args:
            escalate_to: Optional user to escalate to
            reason: Optional reason for escalation

        Returns:
            New Approval Task document
        """
        # Mark this task as escalated
        self.status = "Escalated"
        if reason:
            self.comments = (self.comments or "") + f"\n\nEscalated: {reason}"
        self.save(ignore_permissions=True)

        # Create new escalated task
        new_task = frappe.copy_doc(self)
        new_task.name = None
        new_task.status = "Pending"
        new_task.action_taken = None
        new_task.comments = None
        new_task.completed_at = None
        new_task.completed_by = None
        new_task.escalated_from = self.name
        new_task.escalation_level = (self.escalation_level or 0) + 1

        if escalate_to:
            new_task.assigned_to = escalate_to
            new_task.original_assignee = escalate_to

        new_task.insert()

        return new_task

    def can_user_complete(self, user: str) -> bool:
        """Check if user can complete this task."""
        # Direct assignment
        if self.assigned_to and self.assigned_to == user:
            return True

        # Role-based assignment (anyone with the role can complete)
        if self.assigned_role:
            if self.assigned_role in frappe.get_roles(user):
                return True

        # System Manager can always complete
        if "System Manager" in frappe.get_roles(user):
            return True

        return False

    def resume_workflow(self, action: str) -> dict:
        """Resume the workflow after task completion."""
        from xstate_workflow.workflow_engine import trigger_event_sync

        # Map action to event name
        event = action.upper().replace(" ", "_")

        # Check if this is a parallel approval task (node_id format: ParallelState.approver_id.pending)
        # If so, append the approver_id to the event: APPROVE_approver_id
        if self.node_id and "." in self.node_id:
            parts = self.node_id.split(".")
            if len(parts) >= 2 and parts[-1] == "pending":
                approver_id = parts[-2]
                if approver_id.startswith("approver_"):
                    event = f"{event}_{approver_id}"

        # Data must be JSON string
        data = json.dumps({
            "task_name": self.name,
            "action": action,
            "comments": self.comments,
            "completed_by": self.completed_by,
            "node_id": self.node_id
        })

        return trigger_event_sync(
            self.reference_doctype,
            self.reference_name,
            event,
            data
        )

    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date:
            return False

        if self.status in ["Completed", "Cancelled", "Escalated"]:
            return False

        return get_datetime(self.due_date) < now_datetime()

    def get_time_remaining(self) -> float | None:
        """Get time remaining in hours until due date."""
        if not self.due_date:
            return None

        now = now_datetime()
        due = get_datetime(self.due_date)

        if due < now:
            return 0

        delta = due - now
        return delta.total_seconds() / 3600
