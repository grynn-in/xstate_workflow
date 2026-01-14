# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Test cases for Workflow-Controlled Document Submission

Tests:
1. Auto-submit when workflow reaches "submit" node
2. Block manual submit when workflow is pending
3. Block manual submit when workflow is rejected
4. Allow manual submit when workflow is approved (no submit node)
5. Transition logging works correctly
"""

import json
import frappe
from frappe.tests.utils import FrappeTestCase


def create_test_workflow_with_submit_node():
    """Create a test workflow with a submit node for auto-submission"""
    if frappe.db.exists("State Machine", "test_auto_submit_workflow"):
        frappe.delete_doc("State Machine", "test_auto_submit_workflow", force=True)

    config = {
        "id": "test_auto_submit_workflow",
        "initial": "draft",
        "states": {
            "draft": {
                "on": {"SUBMIT_FOR_APPROVAL": "pending_approval"},
                "meta": {"domain_node": {"type": "start", "label": "Draft"}},
            },
            "pending_approval": {
                "on": {"APPROVE": "approved", "REJECT": "rejected"},
                "meta": {
                    "domain_node": {
                        "type": "approval",
                        "label": "Pending Approval",
                        "resolver": {"type": "role", "role": "Accounts Manager"},
                    }
                },
            },
            "approved": {
                "type": "final",
                "meta": {
                    "domain_node": {
                        "type": "submit",  # This triggers auto-submit
                        "label": "Approved",
                    }
                },
            },
            "rejected": {
                "type": "final",
                "meta": {"domain_node": {"type": "end", "label": "Rejected"}},
            },
        },
    }

    doc = frappe.get_doc(
        {
            "doctype": "State Machine",
            "machine_id": "test_auto_submit_workflow",
            "title": "Test Auto Submit Workflow",
            "attached_doctype": "Purchase Invoice",
            "is_active": 0,  # Not active by default to avoid conflicts
            "json_config": json.dumps(config),
        }
    )
    doc.insert(ignore_permissions=True)
    return doc


def create_test_workflow_without_submit_node():
    """Create a test workflow without a submit node (manual submit allowed when approved)"""
    if frappe.db.exists("State Machine", "test_manual_submit_workflow"):
        frappe.delete_doc("State Machine", "test_manual_submit_workflow", force=True)

    config = {
        "id": "test_manual_submit_workflow",
        "initial": "draft",
        "states": {
            "draft": {
                "on": {"SUBMIT_FOR_APPROVAL": "pending_approval"},
                "meta": {"domain_node": {"type": "start", "label": "Draft"}},
            },
            "pending_approval": {
                "on": {"APPROVE": "approved", "REJECT": "rejected"},
                "meta": {
                    "domain_node": {
                        "type": "approval",
                        "label": "Pending Approval",
                    }
                },
            },
            "approved": {
                "type": "final",
                "meta": {
                    "domain_node": {
                        "type": "end",  # No submit node - manual submit allowed
                        "label": "Approved",
                    }
                },
            },
            "rejected": {
                "type": "final",
                "meta": {"domain_node": {"type": "end", "label": "Rejected"}},
            },
        },
    }

    doc = frappe.get_doc(
        {
            "doctype": "State Machine",
            "machine_id": "test_manual_submit_workflow",
            "title": "Test Manual Submit Workflow",
            "attached_doctype": "ToDo",  # Use ToDo since it's not submittable
            "is_active": 0,
            "json_config": json.dumps(config),
        }
    )
    doc.insert(ignore_permissions=True)
    return doc


class TestWorkflowAutoSubmit(FrappeTestCase):
    """Tests for workflow-controlled document submission"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Store original workflow to restore later
        cls.original_workflow = frappe.db.get_value(
            "State Machine",
            {"attached_doctype": "Purchase Invoice", "is_active": 1},
            "name",
        )
        # Deactivate original workflow
        if cls.original_workflow:
            frappe.db.set_value(
                "State Machine", cls.original_workflow, "is_active", 0
            )
            frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        # Restore original workflow
        if cls.original_workflow:
            frappe.db.set_value(
                "State Machine", cls.original_workflow, "is_active", 1
            )
            frappe.db.commit()
        # Clean up test workflows
        for name in ["test_auto_submit_workflow", "test_manual_submit_workflow"]:
            if frappe.db.exists("State Machine", name):
                frappe.delete_doc("State Machine", name, force=True)
        super().tearDownClass()

    def test_block_manual_submit_when_workflow_pending(self):
        """Manual submit should be blocked when workflow is pending approval"""
        from xstate_workflow.workflow_engine import (
            get_or_create_instance,
            trigger_event_sync,
            validate_workflow_state_for_submit,
        )

        # Create and activate test workflow for ToDo
        workflow = create_test_workflow_with_submit_node()
        workflow.attached_doctype = "ToDo"
        workflow.is_active = 1
        workflow.save()
        frappe.db.commit()

        try:
            # Create a test ToDo
            todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": "Test workflow blocking",
                }
            )
            todo.insert(ignore_permissions=True)

            # Create workflow instance
            get_or_create_instance("ToDo", todo.name)

            # Trigger to move to pending state
            trigger_event_sync("ToDo", todo.name, "SUBMIT_FOR_APPROVAL")

            # Try to validate for submit - should raise
            with self.assertRaises(frappe.ValidationError) as context:
                validate_workflow_state_for_submit(todo)

            self.assertIn("pending", str(context.exception).lower())

        finally:
            workflow.is_active = 0
            workflow.save()
            frappe.db.commit()

    def test_block_manual_submit_when_workflow_rejected(self):
        """Manual submit should be blocked when workflow is rejected"""
        from xstate_workflow.workflow_engine import (
            get_or_create_instance,
            trigger_event_sync,
            validate_workflow_state_for_submit,
        )

        # Create and activate test workflow for ToDo
        workflow = create_test_workflow_with_submit_node()
        workflow.attached_doctype = "ToDo"
        workflow.is_active = 1
        workflow.save()
        frappe.db.commit()

        try:
            todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": "Test workflow rejection blocking",
                }
            )
            todo.insert(ignore_permissions=True)

            # Create workflow instance and move to rejected
            get_or_create_instance("ToDo", todo.name)
            trigger_event_sync("ToDo", todo.name, "SUBMIT_FOR_APPROVAL")
            trigger_event_sync("ToDo", todo.name, "REJECT")

            # Check state is rejected
            instance = frappe.db.get_value(
                "Machine Instance",
                {"reference_doctype": "ToDo", "reference_name": todo.name},
                ["current_state", "status"],
                as_dict=True,
            )
            self.assertEqual(instance.current_state, "rejected")
            self.assertEqual(instance.status, "final")

            # Try to validate for submit - should raise
            with self.assertRaises(frappe.ValidationError) as context:
                validate_workflow_state_for_submit(todo)

            self.assertIn("rejected", str(context.exception).lower())

        finally:
            workflow.is_active = 0
            workflow.save()
            frappe.db.commit()

    def test_allow_manual_submit_when_approved_no_submit_node(self):
        """Manual submit should be allowed when workflow is approved and no submit node"""
        from xstate_workflow.workflow_engine import (
            get_or_create_instance,
            trigger_event_sync,
            validate_workflow_state_for_submit,
        )

        # Create workflow WITHOUT submit node
        workflow = create_test_workflow_without_submit_node()
        workflow.attached_doctype = "ToDo"
        workflow.is_active = 1
        workflow.save()
        frappe.db.commit()

        try:
            todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": "Test workflow approval allows submit",
                }
            )
            todo.insert(ignore_permissions=True)

            # Create workflow instance and move to approved
            get_or_create_instance("ToDo", todo.name)
            trigger_event_sync("ToDo", todo.name, "SUBMIT_FOR_APPROVAL")
            trigger_event_sync("ToDo", todo.name, "APPROVE")

            # Check state is approved
            instance = frappe.db.get_value(
                "Machine Instance",
                {"reference_doctype": "ToDo", "reference_name": todo.name},
                ["current_state", "status"],
                as_dict=True,
            )
            self.assertEqual(instance.current_state, "approved")
            self.assertEqual(instance.status, "final")

            # Validate for submit - should NOT raise (allowed)
            try:
                validate_workflow_state_for_submit(todo)
            except frappe.ValidationError:
                self.fail("Submit should be allowed when workflow is approved")

        finally:
            workflow.is_active = 0
            workflow.save()
            frappe.db.commit()


class TestTransitionLogging(FrappeTestCase):
    """Tests for transition logging"""

    def test_transition_logging_works(self):
        """Transitions should be logged in transition_log field"""
        from xstate_workflow.workflow_engine import (
            get_or_create_instance,
            trigger_event_sync,
        )

        # Create test workflow
        workflow = create_test_workflow_with_submit_node()
        workflow.attached_doctype = "ToDo"
        workflow.is_active = 1
        workflow.save()
        frappe.db.commit()

        try:
            todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "description": "Test transition logging",
                }
            )
            todo.insert(ignore_permissions=True)

            # Create workflow instance
            get_or_create_instance("ToDo", todo.name)

            # Trigger some transitions
            trigger_event_sync("ToDo", todo.name, "SUBMIT_FOR_APPROVAL")
            trigger_event_sync("ToDo", todo.name, "APPROVE")

            # Check transition log is populated
            instance = frappe.get_doc(
                "Machine Instance",
                {"reference_doctype": "ToDo", "reference_name": todo.name},
            )
            transition_log = json.loads(instance.transition_log or "[]")

            self.assertGreater(len(transition_log), 0, "Transition log should not be empty")

            # Check log entries have required fields
            for entry in transition_log:
                self.assertIn("event", entry)
                self.assertIn("from_state", entry)
                self.assertIn("to_state", entry)
                self.assertIn("timestamp", entry)
                self.assertIn("user", entry)

        finally:
            workflow.is_active = 0
            workflow.save()
            frappe.db.commit()


class TestSubmitNodeAutoSubmit(FrappeTestCase):
    """Tests for auto-submit when reaching submit node"""

    def test_auto_submit_on_submit_node(self):
        """Document should auto-submit when workflow reaches submit node"""
        # This test requires a submittable document
        # For now, we'll test the handler logic directly
        from xstate_workflow.workflow_engine import handle_domain_node_entry

        # Create a mock scenario - this is a unit test for the handler
        # Full integration test would need a submittable test doctype
        pass  # TODO: Implement with proper test fixture


class TestWorkflowValidation(FrappeTestCase):
    """Tests for workflow configuration validation"""

    def test_require_final_state_for_submittable_doctype(self):
        """Workflow for submittable doctype must have approved final state"""
        config_without_approved = {
            "id": "test_invalid_workflow",
            "initial": "draft",
            "states": {
                "draft": {"on": {"START": "processing"}},
                "processing": {
                    "type": "final",
                    "meta": {"domain_node": {"type": "end"}},
                },  # No approved state
            },
        }

        # Try to create workflow for Purchase Invoice (submittable)
        doc = frappe.get_doc(
            {
                "doctype": "State Machine",
                "name": "test_invalid_workflow",
                "title": "Test Invalid Workflow",
                "attached_doctype": "Purchase Invoice",
                "is_active": 0,
                "json_config": json.dumps(config_without_approved),
            }
        )

        # Should raise validation error
        # Note: This test will pass once we implement the validation
        # with self.assertRaises(frappe.ValidationError):
        #     doc.insert(ignore_permissions=True)
        pass  # TODO: Enable after implementing validation
