# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Approval Task Management Module.

Provides functions for creating, managing, and completing approval tasks
within the XState workflow system.
"""

from .task_manager import (
    ApprovalTaskManager,
    create_approval_task,
    complete_approval_task,
    cancel_pending_tasks,
    get_my_approval_tasks,
    get_task_for_node,
    reassign_task,
    escalate_task,
)

__all__ = [
    "ApprovalTaskManager",
    "create_approval_task",
    "complete_approval_task",
    "cancel_pending_tasks",
    "get_my_approval_tasks",
    "get_task_for_node",
    "reassign_task",
    "escalate_task",
]
