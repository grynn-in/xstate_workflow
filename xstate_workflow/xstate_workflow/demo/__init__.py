# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
XState Workflow Demo Package

This package provides demo setup and examples for the XState Workflow system.
"""

from xstate_workflow.xstate_workflow.demo.setup_demo import (
    setup_all,
    create_demo_users,
    create_state_machine,
    create_sample_orders,
    cleanup_demo,
    test_workflow,
)

__all__ = [
    "setup_all",
    "create_demo_users",
    "create_state_machine",
    "create_sample_orders",
    "cleanup_demo",
    "test_workflow",
]
