# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase


class TestGuardEvaluation(FrappeTestCase):
    """Tests for guard condition evaluation"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_machine = create_guarded_machine()

    @classmethod
    def tearDownClass(cls):
        frappe.db.delete("Machine Instance", {"machine": cls.test_machine.name})
        frappe.db.delete("State Machine", {"name": cls.test_machine.name})
        frappe.db.commit()
        super().tearDownClass()

    def test_evaluate_simple_guard_true(self):
        """Test evaluating a simple guard that passes"""
        from xstate_workflow.workflow_engine import evaluate_guard

        context = {"amount": 5000}
        event = {"type": "APPROVE"}

        # The guard checks if amount > 1000
        result = evaluate_guard(
            self.test_machine,
            "amount_above_threshold",
            context,
            event
        )

        self.assertTrue(result)

    def test_evaluate_simple_guard_false(self):
        """Test evaluating a simple guard that fails"""
        from xstate_workflow.workflow_engine import evaluate_guard

        context = {"amount": 500}
        event = {"type": "APPROVE"}

        result = evaluate_guard(
            self.test_machine,
            "amount_above_threshold",
            context,
            event
        )

        self.assertFalse(result)

    def test_evaluate_missing_guard(self):
        """Test evaluating a non-existent guard defaults to True"""
        from xstate_workflow.workflow_engine import evaluate_guard

        context = {}
        event = {"type": "SUBMIT"}

        # Non-existent guards should default to True (permissive)
        result = evaluate_guard(
            self.test_machine,
            "nonexistent_guard",
            context,
            event
        )

        self.assertTrue(result)

    def test_evaluate_guard_with_doc_access(self):
        """Test guard that accesses document fields"""
        from xstate_workflow.workflow_engine import evaluate_guard

        # Create a test doc with known values
        todo = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test with priority",
            "priority": "High"
        }).insert()

        try:
            context = {"ref_doctype": "ToDo", "ref_docname": todo.name}
            event = {"type": "SUBMIT"}

            # Guard that checks doc priority
            result = evaluate_guard(
                self.test_machine,
                "is_high_priority",
                context,
                event
            )

            # Should be True for High priority
            self.assertTrue(result)
        finally:
            frappe.delete_doc("ToDo", todo.name, force=True)


class TestActionExecution(FrappeTestCase):
    """Tests for action execution"""

    def test_execute_single_action(self):
        """Test executing a single action"""
        from xstate_workflow.workflow_engine import execute_actions

        # Track if action was called
        action_called = []

        def test_action(context, event):
            action_called.append(True)
            return {**context, "action_executed": True}

        actions = {"test_action": test_action}
        context = {"initial": True}
        event = {"type": "TEST"}

        result = execute_actions(["test_action"], actions, context, event)

        self.assertEqual(len(action_called), 1)
        self.assertTrue(result.get("action_executed"))
        self.assertTrue(result.get("initial"))

    def test_execute_multiple_actions(self):
        """Test executing multiple actions in sequence"""
        from xstate_workflow.workflow_engine import execute_actions

        execution_order = []

        def action1(context, event):
            execution_order.append("action1")
            return {**context, "a1": True}

        def action2(context, event):
            execution_order.append("action2")
            return {**context, "a2": True}

        actions = {"action1": action1, "action2": action2}
        context = {}
        event = {"type": "TEST"}

        result = execute_actions(["action1", "action2"], actions, context, event)

        self.assertEqual(execution_order, ["action1", "action2"])
        self.assertTrue(result.get("a1"))
        self.assertTrue(result.get("a2"))

    def test_execute_missing_action(self):
        """Test executing a missing action is silently skipped"""
        from xstate_workflow.workflow_engine import execute_actions

        actions = {}
        context = {"original": True}
        event = {"type": "TEST"}

        # Should not raise, just skip the action
        result = execute_actions(["missing_action"], actions, context, event)

        self.assertEqual(result, context)

    def test_action_context_mutation(self):
        """Test that actions properly update context"""
        from xstate_workflow.workflow_engine import execute_actions

        def increment_counter(context, event):
            return {**context, "counter": context.get("counter", 0) + 1}

        actions = {"increment": increment_counter}
        context = {"counter": 5}
        event = {"type": "INCREMENT"}

        result = execute_actions(["increment"], actions, context, event)

        self.assertEqual(result["counter"], 6)


class TestConditionalTransitions(FrappeTestCase):
    """Tests for conditional transition resolution"""

    def test_resolve_simple_transition(self):
        """Test resolving a simple string transition"""
        from xstate_workflow.workflow_engine import resolve_transition

        transition = "next_state"
        context = {}
        event_data = {}
        guards = {}

        target, actions = resolve_transition(transition, context, event_data, guards)

        self.assertEqual(target, "next_state")
        self.assertEqual(actions, [])

    def test_resolve_object_transition(self):
        """Test resolving an object transition"""
        from xstate_workflow.workflow_engine import resolve_transition

        transition = {
            "target": "approved",
            "actions": ["log_approval"]
        }
        context = {}
        event_data = {}
        guards = {}

        target, actions = resolve_transition(transition, context, event_data, guards)

        self.assertEqual(target, "approved")
        self.assertEqual(actions, ["log_approval"])

    def test_resolve_guarded_transition_passes(self):
        """Test resolving a guarded transition that passes"""
        from xstate_workflow.workflow_engine import resolve_transition

        transition = {
            "target": "approved",
            "guard": "is_valid"
        }
        context = {}
        event_data = {}
        guards = {"is_valid": lambda ctx, evt: True}

        target, actions = resolve_transition(transition, context, event_data, guards)

        self.assertEqual(target, "approved")

    def test_resolve_guarded_transition_fails(self):
        """Test resolving a guarded transition that fails"""
        from xstate_workflow.workflow_engine import resolve_transition

        transition = {
            "target": "approved",
            "guard": "is_valid"
        }
        context = {}
        event_data = {}
        guards = {"is_valid": lambda ctx, evt: False}

        target, actions = resolve_transition(transition, context, event_data, guards)

        self.assertIsNone(target)

    def test_resolve_conditional_transitions(self):
        """Test resolving multiple conditional transitions"""
        from xstate_workflow.workflow_engine import resolve_transition

        transitions = [
            {"target": "high", "guard": "is_high"},
            {"target": "medium", "guard": "is_medium"},
            {"target": "low"}  # Default fallback
        ]

        context = {"priority": "medium"}

        guards = {
            "is_high": lambda ctx, evt: ctx.get("priority") == "high",
            "is_medium": lambda ctx, evt: ctx.get("priority") == "medium"
        }

        target, actions = resolve_transition(transitions, context, {}, guards)

        self.assertEqual(target, "medium")

    def test_resolve_conditional_fallback(self):
        """Test that default transition is used when guards fail"""
        from xstate_workflow.workflow_engine import resolve_transition

        transitions = [
            {"target": "special", "guard": "is_special"},
            {"target": "default"}
        ]

        context = {}
        guards = {"is_special": lambda ctx, evt: False}

        target, actions = resolve_transition(transitions, context, {}, guards)

        self.assertEqual(target, "default")


class TestInvokeService(FrappeTestCase):
    """Tests for invoke service functionality"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_service = create_test_service()

    @classmethod
    def tearDownClass(cls):
        if frappe.db.exists("XSM Service", cls.test_service.name):
            frappe.delete_doc("XSM Service", cls.test_service.name, force=True)
        frappe.db.commit()
        super().tearDownClass()

    def test_python_service_execution(self):
        """Test executing a Python service"""
        from xstate_workflow.workflow_engine import _execute_python_service_sync

        context = {"test": True, "value": 42}
        event = {"type": "TEST"}

        # This calls a simple test function
        result = _execute_python_service_sync(
            "xstate_workflow.tests.test_guards_actions.sample_service_function",
            context,
            event,
            None
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.get("processed"))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_guarded_machine():
    """Create a state machine with guards for testing"""
    machine_id = "test_guarded_workflow"

    if frappe.db.exists("State Machine", machine_id):
        frappe.db.delete("Machine Instance", {"machine": machine_id})
        frappe.db.delete("State Machine", {"name": machine_id})
        frappe.db.commit()

    config = {
        "id": machine_id,
        "initial": "draft",
        "states": {
            "draft": {
                "on": {
                    "SUBMIT": [
                        {"target": "needs_approval", "guard": "amount_above_threshold"},
                        {"target": "approved"}
                    ]
                }
            },
            "needs_approval": {
                "on": {
                    "APPROVE": {"target": "approved", "guard": "is_high_priority"},
                    "REJECT": "rejected"
                }
            },
            "approved": {"type": "final"},
            "rejected": {"type": "final"}
        }
    }

    machine = frappe.get_doc({
        "doctype": "State Machine",
        "machine_id": machine_id,
        "title": "Test Guarded Workflow",
        "json_config": json.dumps(config),
        "attached_doctype": "ToDo",
        "is_active": 1,
        "guards_table": [
            {
                "guard_name": "amount_above_threshold",
                "python_code": "context.get('amount', 0) > 1000"
            },
            {
                "guard_name": "is_high_priority",
                "python_code": "frappe.get_value(context.get('ref_doctype'), context.get('ref_docname'), 'priority') == 'High'"
            }
        ]
    }).insert()

    frappe.db.commit()

    return machine


def create_test_service():
    """Create a test XSM Service"""
    service_name = "test_python_service"

    if frappe.db.exists("XSM Service", service_name):
        frappe.delete_doc("XSM Service", service_name, force=True)
        frappe.db.commit()

    service = frappe.get_doc({
        "doctype": "XSM Service",
        "service_name": service_name,
        "service_type": "python",
        "python_path": "xstate_workflow.tests.test_guards_actions.sample_service_function",
        "is_active": 1
    }).insert()

    frappe.db.commit()

    return service


def sample_service_function(context, event, doc=None):
    """Sample service function for testing"""
    return {
        **context,
        "processed": True,
        "event_type": event.get("type")
    }


if __name__ == "__main__":
    unittest.main()
