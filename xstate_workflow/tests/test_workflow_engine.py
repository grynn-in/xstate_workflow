# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase


class TestWorkflowEngine(FrappeTestCase):
    """Tests for XState Workflow Engine core functions"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        super().setUpClass()

        # Create a test State Machine
        cls.test_machine = create_test_machine()

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures"""
        # Delete all test instances
        frappe.db.delete("Machine Instance", {"machine": cls.test_machine.name})
        frappe.db.delete("State Machine", {"name": cls.test_machine.name})
        frappe.db.commit()

        super().tearDownClass()

    def tearDown(self):
        """Clean up after each test"""
        # Clean up any test instances created during tests
        frappe.db.delete("Machine Instance", {"ref_doctype": "ToDo"})
        frappe.db.commit()

    def test_save_machine(self):
        """Test saving a state machine configuration"""
        from xstate_workflow.workflow_engine import save_machine

        result = save_machine(
            machine_id="test_save_machine",
            json_config=json.dumps({
                "id": "test_save_machine",
                "initial": "idle",
                "states": {
                    "idle": {"on": {"START": "running"}},
                    "running": {"type": "final"}
                }
            }),
            title="Test Save Machine"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["name"], "test_save_machine")

        # Cleanup
        frappe.db.delete("State Machine", {"name": "test_save_machine"})
        frappe.db.commit()

    def test_get_machine(self):
        """Test retrieving a state machine configuration"""
        from xstate_workflow.workflow_engine import get_machine

        result = get_machine(self.test_machine.name)

        self.assertEqual(result["machine_id"], self.test_machine.name)
        self.assertEqual(result["title"], "Test Approval Workflow")
        self.assertIn("states", json.loads(result["json_config"]))

    def test_get_machine_not_found(self):
        """Test retrieving a non-existent machine raises error"""
        from xstate_workflow.workflow_engine import get_machine

        with self.assertRaises(frappe.ValidationError):
            get_machine("nonexistent_machine_xyz")

    def test_list_machines(self):
        """Test listing state machines"""
        from xstate_workflow.workflow_engine import list_machines

        machines = list_machines()

        # Should include our test machine
        machine_ids = [m["machine_id"] for m in machines]
        self.assertIn(self.test_machine.name, machine_ids)

    def test_list_machines_filtered(self):
        """Test listing machines filtered by attached doctype"""
        from xstate_workflow.workflow_engine import list_machines

        # Our test machine is attached to "ToDo"
        machines = list_machines(attached_to="ToDo")
        machine_ids = [m["machine_id"] for m in machines]
        self.assertIn(self.test_machine.name, machine_ids)

        # Filter by different doctype should not include our machine
        machines = list_machines(attached_to="User")
        machine_ids = [m["machine_id"] for m in machines]
        self.assertNotIn(self.test_machine.name, machine_ids)


class TestMachineInstance(FrappeTestCase):
    """Tests for Machine Instance operations"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_machine = create_test_machine()
        cls.test_todo = create_test_todo()

    @classmethod
    def tearDownClass(cls):
        frappe.db.delete("Machine Instance", {"machine": cls.test_machine.name})
        frappe.db.delete("State Machine", {"name": cls.test_machine.name})
        frappe.db.delete("ToDo", {"name": cls.test_todo.name})
        frappe.db.commit()
        super().tearDownClass()

    def tearDown(self):
        frappe.db.delete("Machine Instance", {"ref_doctype": "ToDo"})
        frappe.db.commit()

    def test_get_or_create_instance(self):
        """Test creating a workflow instance for a document"""
        from xstate_workflow.workflow_engine import get_or_create_instance

        instance_name = get_or_create_instance("ToDo", self.test_todo.name)

        self.assertIsNotNone(instance_name)

        # Verify instance was created
        instance = frappe.get_doc("Machine Instance", instance_name)
        self.assertEqual(instance.ref_doctype, "ToDo")
        self.assertEqual(instance.ref_docname, self.test_todo.name)
        self.assertEqual(instance.current_state, "draft")  # Initial state
        self.assertEqual(instance.status, "Active")

    def test_get_machine_state(self):
        """Test getting workflow state for a document"""
        from xstate_workflow.workflow_engine import (
            get_machine_state,
            get_or_create_instance
        )

        # Create instance first
        get_or_create_instance("ToDo", self.test_todo.name)

        result = get_machine_state("ToDo", self.test_todo.name)

        self.assertTrue(result["has_workflow"])
        self.assertEqual(result["current_state"], "draft")
        self.assertEqual(result["status"], "Active")
        self.assertIn("available_events", result)

        # Should have SUBMIT event available in draft state
        event_names = [e["event"] for e in result["available_events"]]
        self.assertIn("SUBMIT", event_names)

    def test_get_machine_state_no_workflow(self):
        """Test getting state for document without workflow"""
        from xstate_workflow.workflow_engine import get_machine_state

        # Create a todo that won't have a workflow attached
        todo = frappe.get_doc({
            "doctype": "ToDo",
            "description": "No workflow test"
        }).insert()

        try:
            # Delete any auto-created instance
            frappe.db.delete("Machine Instance", {
                "ref_doctype": "ToDo",
                "ref_docname": todo.name
            })
            frappe.db.commit()

            result = get_machine_state("ToDo", todo.name)
            self.assertFalse(result["has_workflow"])
        finally:
            frappe.delete_doc("ToDo", todo.name, force=True)


class TestTransitions(FrappeTestCase):
    """Tests for state transitions"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_machine = create_test_machine()

    @classmethod
    def tearDownClass(cls):
        frappe.db.delete("Machine Instance", {"machine": cls.test_machine.name})
        frappe.db.delete("State Machine", {"name": cls.test_machine.name})
        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        self.test_todo = create_test_todo()

    def tearDown(self):
        frappe.db.delete("Machine Instance", {"ref_docname": self.test_todo.name})
        frappe.db.delete("ToDo", {"name": self.test_todo.name})
        frappe.db.commit()

    def test_trigger_event_sync(self):
        """Test synchronous event triggering"""
        from xstate_workflow.workflow_engine import (
            get_or_create_instance,
            trigger_event_sync
        )

        get_or_create_instance("ToDo", self.test_todo.name)

        result = trigger_event_sync(
            doctype="ToDo",
            docname=self.test_todo.name,
            event="SUBMIT",
            data="{}"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["previous_state"], "draft")
        self.assertEqual(result["new_state"], "pending_approval")

    def test_trigger_event_sync_invalid(self):
        """Test triggering an invalid event"""
        from xstate_workflow.workflow_engine import (
            get_or_create_instance,
            trigger_event_sync
        )

        get_or_create_instance("ToDo", self.test_todo.name)

        # APPROVE is not valid in draft state
        result = trigger_event_sync(
            doctype="ToDo",
            docname=self.test_todo.name,
            event="APPROVE",
            data="{}"
        )

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_transition_sequence(self):
        """Test a sequence of transitions"""
        from xstate_workflow.workflow_engine import (
            get_or_create_instance,
            trigger_event_sync,
            get_machine_state
        )

        get_or_create_instance("ToDo", self.test_todo.name)

        # Draft -> Pending Approval
        result1 = trigger_event_sync("ToDo", self.test_todo.name, "SUBMIT")
        self.assertTrue(result1["success"])
        self.assertEqual(result1["new_state"], "pending_approval")

        # Pending Approval -> Approved
        result2 = trigger_event_sync("ToDo", self.test_todo.name, "APPROVE")
        self.assertTrue(result2["success"])
        self.assertEqual(result2["new_state"], "approved")

        # Verify final state
        state = get_machine_state("ToDo", self.test_todo.name)
        self.assertEqual(state["current_state"], "approved")

    def test_reset_instance(self):
        """Test resetting an instance to initial state"""
        from xstate_workflow.workflow_engine import (
            get_or_create_instance,
            trigger_event_sync,
            reset_instance,
            get_machine_state
        )

        get_or_create_instance("ToDo", self.test_todo.name)

        # Move to pending
        trigger_event_sync("ToDo", self.test_todo.name, "SUBMIT")

        state = get_machine_state("ToDo", self.test_todo.name)
        self.assertEqual(state["current_state"], "pending_approval")

        # Reset
        reset_instance("ToDo", self.test_todo.name)

        # Verify back to initial
        state = get_machine_state("ToDo", self.test_todo.name)
        self.assertEqual(state["current_state"], "draft")


class TestGetNextEvents(FrappeTestCase):
    """Tests for available events calculation"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_machine = create_test_machine()

    @classmethod
    def tearDownClass(cls):
        frappe.db.delete("Machine Instance", {"machine": cls.test_machine.name})
        frappe.db.delete("State Machine", {"name": cls.test_machine.name})
        frappe.db.commit()
        super().tearDownClass()

    def test_get_next_events_draft_state(self):
        """Test available events in draft state"""
        from xstate_workflow.workflow_engine import get_next_events

        events = get_next_events(
            self.test_machine.name,
            "draft",
            {}
        )

        event_names = [e["event"] for e in events]
        self.assertIn("SUBMIT", event_names)
        self.assertNotIn("APPROVE", event_names)

    def test_get_next_events_pending_state(self):
        """Test available events in pending_approval state"""
        from xstate_workflow.workflow_engine import get_next_events

        events = get_next_events(
            self.test_machine.name,
            "pending_approval",
            {}
        )

        event_names = [e["event"] for e in events]
        self.assertIn("APPROVE", event_names)
        self.assertIn("REJECT", event_names)

    def test_get_next_events_final_state(self):
        """Test no events available in final state"""
        from xstate_workflow.workflow_engine import get_next_events

        events = get_next_events(
            self.test_machine.name,
            "approved",
            {}
        )

        # Final state should have no outgoing transitions
        self.assertEqual(len(events), 0)


class TestFindStateConfig(FrappeTestCase):
    """Tests for state configuration lookup"""

    def test_find_top_level_state(self):
        """Test finding a top-level state"""
        from xstate_workflow.workflow_engine import find_state_config

        config = {
            "states": {
                "idle": {"on": {"START": "running"}},
                "running": {"on": {"STOP": "idle"}}
            }
        }

        result = find_state_config(config, "idle")

        self.assertIsNotNone(result)
        self.assertIn("on", result)
        self.assertIn("START", result["on"])

    def test_find_nested_state(self):
        """Test finding a nested state"""
        from xstate_workflow.workflow_engine import find_state_config

        config = {
            "states": {
                "parent": {
                    "states": {
                        "child1": {"on": {"NEXT": "child2"}},
                        "child2": {}
                    }
                }
            }
        }

        # Using dot notation for nested path
        result = find_state_config(config, "parent.child1")

        self.assertIsNotNone(result)
        self.assertIn("on", result)

    def test_find_nonexistent_state(self):
        """Test finding a state that doesn't exist"""
        from xstate_workflow.workflow_engine import find_state_config

        config = {
            "states": {
                "idle": {}
            }
        }

        result = find_state_config(config, "nonexistent")

        self.assertIsNone(result)


class TestParseDelay(FrappeTestCase):
    """Tests for delay parsing"""

    def test_parse_numeric_ms(self):
        """Test parsing numeric milliseconds"""
        from xstate_workflow.workflow_engine import parse_delay

        result = parse_delay(5000, {})
        self.assertEqual(result, 5000)

    def test_parse_seconds_string(self):
        """Test parsing seconds string"""
        from xstate_workflow.workflow_engine import parse_delay

        result = parse_delay("30s", {})
        self.assertEqual(result, 30000)

    def test_parse_minutes_string(self):
        """Test parsing minutes string"""
        from xstate_workflow.workflow_engine import parse_delay

        result = parse_delay("5m", {})
        self.assertEqual(result, 300000)

    def test_parse_hours_string(self):
        """Test parsing hours string"""
        from xstate_workflow.workflow_engine import parse_delay

        result = parse_delay("2h", {})
        self.assertEqual(result, 7200000)

    def test_parse_context_reference(self):
        """Test parsing delay from context"""
        from xstate_workflow.workflow_engine import parse_delay

        context = {
            "delays": {
                "approval": 60000
            }
        }

        result = parse_delay("delays.approval", context)
        self.assertEqual(result, 60000)


# ============================================================================
# TEST FIXTURES
# ============================================================================

def create_test_machine():
    """Create a test state machine for approval workflow"""
    machine_id = "test_approval_workflow"

    # Delete if exists
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
                    "SUBMIT": "pending_approval"
                }
            },
            "pending_approval": {
                "on": {
                    "APPROVE": "approved",
                    "REJECT": "rejected"
                }
            },
            "approved": {
                "type": "final"
            },
            "rejected": {
                "on": {
                    "RESUBMIT": "draft"
                }
            }
        }
    }

    machine = frappe.get_doc({
        "doctype": "State Machine",
        "machine_id": machine_id,
        "title": "Test Approval Workflow",
        "json_config": json.dumps(config),
        "attached_doctype": "ToDo",
        "is_active": 1
    }).insert()

    frappe.db.commit()

    return machine


def create_test_todo():
    """Create a test ToDo document"""
    todo = frappe.get_doc({
        "doctype": "ToDo",
        "description": f"Test workflow todo {frappe.utils.now()}"
    }).insert()

    frappe.db.commit()

    return todo


if __name__ == "__main__":
    unittest.main()
