# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Domain Node Handlers.

Provides handlers for domain-specific workflow nodes:
- Approval nodes (create tasks, pause workflow)
- Auto-action nodes (submit, update, notify)
- Threshold gate nodes
- Classification branch nodes
"""

from .handlers import (
    handle_approval_node_entry,
    handle_approval_node_exit,
    handle_auto_action,
    evaluate_threshold_condition,
    evaluate_classification_branch,
    get_domain_node_actions,
)

__all__ = [
    "handle_approval_node_entry",
    "handle_approval_node_exit",
    "handle_auto_action",
    "evaluate_threshold_condition",
    "evaluate_classification_branch",
    "get_domain_node_actions",
]
