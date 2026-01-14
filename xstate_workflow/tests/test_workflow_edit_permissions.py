# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Test cases for Workflow-based Document Edit Permissions (TDD)

These tests verify:
1. Bug fix: Administrator can save documents with active workflow (no PermissionError)
2. Configurable edit restrictions based on workflow state and task assignment
3. Different restriction modes: None, Assigned Only, Role Only, Assigned or Role
4. System Manager override behavior
5. Edge cases: idle workflow, final workflow, no pending task
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase


class TestWorkflowEditPermissions(FrappeTestCase):
    """Test cases for workflow-based document edit permissions."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        super().setUpClass()

        # Create test users with different roles
        cls.admin_user = "Administrator"
        cls.approver_user = create_test_user(
            "edit_perm_approver@example.com", "Edit Perm Approver", ["Accounts Manager"]
        )
        cls.regular_user = create_test_user(
            "edit_perm_regular@example.com", "Edit Perm Regular", []
        )

        # Create test workflow with edit_restriction_mode
        cls.test_machine = create_test_workflow_with_edit_restriction()

        # Create a test document (ToDo is available in all Frappe installations)
        cls.test_doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Edit Permission Tests",
            "status": "Open"
        })
        cls.test_doc.insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures"""
        frappe.db.delete("Approval Task", {"reference_doctype": "ToDo"})
        frappe.db.delete("Machine Instance", {"reference_doctype": "ToDo"})
        if cls.test_machine:
            frappe.db.delete("State Machine", {"name": cls.test_machine.name})
        frappe.db.delete("ToDo", {"name": cls.test_doc.name})

        # Delete test users
        for user in [cls.approver_user, cls.regular_user]:
            if user:
                frappe.db.delete("Has Role", {"parent": user.name})
                frappe.db.delete("User", {"name": user.name})

        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        """Set up before each test"""
        frappe.set_user("Administrator")
        # Reset edit_restriction_mode to None for each test
        if self.test_machine:
            self.test_machine.reload()
            if hasattr(self.test_machine, 'edit_restriction_mode'):
                self.test_machine.edit_restriction_mode = "None"
                self.test_machine.save(ignore_permissions=True)

    def tearDown(self):
        """Clean up after each test"""
        frappe.db.delete("Approval Task", {"reference_doctype": "ToDo"})
        frappe.db.delete("Machine Instance", {"reference_doctype": "ToDo"})
        frappe.db.commit()
        frappe.set_user("Administrator")

    # ========== Bug Fix Tests ==========

    def test_admin_can_save_document_with_active_workflow(self):
        """Test that Administrator can save a document when workflow is active.

        This is the main bug fix test - previously, saving would fail with
        PermissionError when the on_update hook called trigger_event().
        """
        # Create a fresh test document for this test
        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Admin Save Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            # Start workflow on the document
            instance = start_workflow_on_doc(doc, self.test_machine)

            frappe.set_user(self.admin_user)
            doc.reload()
            doc.description = "Updated by admin"
            doc.save()  # Should NOT throw error

            doc.reload()
            self.assertEqual(doc.description, "Updated by admin")
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    def test_save_does_not_throw_permission_error_during_hook(self):
        """Test that on_update hook doesn't throw PermissionError.

        The bug was in check_and_trigger() calling trigger_event() which
        has a permission check that fails during hook execution.
        """
        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Hook Permission Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            instance = start_workflow_on_doc(doc, self.test_machine)

            frappe.set_user(self.admin_user)
            doc.reload()
            doc.description = "Updated"

            # This should not raise any exception
            try:
                doc.save()
            except frappe.PermissionError:
                self.fail("PermissionError raised during save with active workflow")
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    # ========== Edit Restriction Mode: None ==========

    def test_mode_none_allows_anyone_to_edit(self):
        """With edit_restriction_mode='None', any user with doctype permission can edit."""
        # Skip if edit_restriction_mode field doesn't exist yet
        if not hasattr(self.test_machine, 'edit_restriction_mode'):
            self.skipTest("edit_restriction_mode field not yet implemented")

        self.test_machine.edit_restriction_mode = "None"
        self.test_machine.save(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Mode None Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            instance = start_workflow_on_doc(doc, self.test_machine)
            assign_task_to_user(instance, self.approver_user.name)

            # Regular user (not assigned) should be able to edit
            frappe.set_user(self.regular_user.name)
            doc.reload()
            doc.description = "Updated by regular user"
            doc.save()  # Should succeed

            doc.reload()
            self.assertEqual(doc.description, "Updated by regular user")
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    # ========== Edit Restriction Mode: Assigned Only ==========

    def test_mode_assigned_only_allows_assigned_user_to_edit(self):
        """With edit_restriction_mode='Assigned Only', only assigned user can edit."""
        if not hasattr(self.test_machine, 'edit_restriction_mode'):
            self.skipTest("edit_restriction_mode field not yet implemented")

        self.test_machine.edit_restriction_mode = "Assigned Only"
        self.test_machine.save(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Assigned Only Allow Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            instance = start_workflow_on_doc(doc, self.test_machine)
            assign_task_to_user(instance, self.approver_user.name)

            # Assigned user should be able to edit
            frappe.set_user(self.approver_user.name)
            doc.reload()
            doc.description = "Updated by approver"
            doc.save()  # Should succeed

            doc.reload()
            self.assertEqual(doc.description, "Updated by approver")
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    def test_mode_assigned_only_blocks_non_assigned_user(self):
        """With edit_restriction_mode='Assigned Only', non-assigned user cannot edit."""
        if not hasattr(self.test_machine, 'edit_restriction_mode'):
            self.skipTest("edit_restriction_mode field not yet implemented")

        self.test_machine.edit_restriction_mode = "Assigned Only"
        self.test_machine.save(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Assigned Only Block Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            instance = start_workflow_on_doc(doc, self.test_machine)
            assign_task_to_user(instance, self.approver_user.name)

            # Regular user (not assigned) should be blocked
            frappe.set_user(self.regular_user.name)
            doc.reload()
            doc.description = "Attempted update"

            with self.assertRaises(frappe.ValidationError):
                doc.save()
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    # ========== Edit Restriction Mode: Role Only ==========

    def test_mode_role_only_allows_user_with_role_to_edit(self):
        """With edit_restriction_mode='Role Only', user with assigned role can edit."""
        if not hasattr(self.test_machine, 'edit_restriction_mode'):
            self.skipTest("edit_restriction_mode field not yet implemented")

        self.test_machine.edit_restriction_mode = "Role Only"
        self.test_machine.save(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Role Only Allow Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            instance = start_workflow_on_doc(doc, self.test_machine)
            assign_task_to_role(instance, "Accounts Manager")

            # User with role should be able to edit
            frappe.set_user(self.approver_user.name)  # Has Accounts Manager role
            doc.reload()
            doc.description = "Updated by role holder"
            doc.save()  # Should succeed

            doc.reload()
            self.assertEqual(doc.description, "Updated by role holder")
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    def test_mode_role_only_blocks_user_without_role(self):
        """With edit_restriction_mode='Role Only', user without role cannot edit."""
        if not hasattr(self.test_machine, 'edit_restriction_mode'):
            self.skipTest("edit_restriction_mode field not yet implemented")

        self.test_machine.edit_restriction_mode = "Role Only"
        self.test_machine.save(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Role Only Block Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            instance = start_workflow_on_doc(doc, self.test_machine)
            assign_task_to_role(instance, "Accounts Manager")

            # User without role should be blocked
            frappe.set_user(self.regular_user.name)  # No Accounts Manager role
            doc.reload()
            doc.description = "Attempted update"

            with self.assertRaises(frappe.ValidationError):
                doc.save()
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    # ========== Edit Restriction Mode: Assigned or Role ==========

    def test_mode_assigned_or_role_allows_assigned_user(self):
        """With 'Assigned or Role', assigned user can edit even without role."""
        if not hasattr(self.test_machine, 'edit_restriction_mode'):
            self.skipTest("edit_restriction_mode field not yet implemented")

        self.test_machine.edit_restriction_mode = "Assigned or Role"
        self.test_machine.save(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Assigned or Role User Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            instance = start_workflow_on_doc(doc, self.test_machine)
            assign_task_to_user(instance, self.regular_user.name)  # User without role

            frappe.set_user(self.regular_user.name)
            doc.reload()
            doc.description = "Updated"
            doc.save()  # Should succeed because user is assigned

            doc.reload()
            self.assertEqual(doc.description, "Updated")
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    def test_mode_assigned_or_role_allows_user_with_role(self):
        """With 'Assigned or Role', user with role can edit even if not assigned."""
        if not hasattr(self.test_machine, 'edit_restriction_mode'):
            self.skipTest("edit_restriction_mode field not yet implemented")

        self.test_machine.edit_restriction_mode = "Assigned or Role"
        self.test_machine.save(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Assigned or Role Role Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            instance = start_workflow_on_doc(doc, self.test_machine)
            assign_task_to_role(instance, "Accounts Manager")
            # Note: Not directly assigned to approver_user, but role matches

            frappe.set_user(self.approver_user.name)
            doc.reload()
            doc.description = "Updated"
            doc.save()  # Should succeed because user has role

            doc.reload()
            self.assertEqual(doc.description, "Updated")
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    def test_mode_assigned_or_role_blocks_unauthorized_user(self):
        """With 'Assigned or Role', user without assignment or role cannot edit."""
        if not hasattr(self.test_machine, 'edit_restriction_mode'):
            self.skipTest("edit_restriction_mode field not yet implemented")

        self.test_machine.edit_restriction_mode = "Assigned or Role"
        self.test_machine.save(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Assigned or Role Block Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            instance = start_workflow_on_doc(doc, self.test_machine)
            # Assign to approver_user, not regular_user
            assign_task_to_user(instance, self.approver_user.name)

            # Regular user is neither assigned nor has the required role
            frappe.set_user(self.regular_user.name)
            doc.reload()
            doc.description = "Attempted update"

            with self.assertRaises(frappe.ValidationError):
                doc.save()
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    # ========== System Manager Override ==========

    def test_system_manager_can_always_edit(self):
        """System Manager can edit regardless of restriction mode."""
        if not hasattr(self.test_machine, 'edit_restriction_mode'):
            self.skipTest("edit_restriction_mode field not yet implemented")

        self.test_machine.edit_restriction_mode = "Assigned Only"
        self.test_machine.save(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for System Manager Override Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            instance = start_workflow_on_doc(doc, self.test_machine)
            assign_task_to_user(instance, self.approver_user.name)  # Not admin

            frappe.set_user(self.admin_user)  # System Manager
            doc.reload()
            doc.description = "Updated by admin"
            doc.save()  # Should always succeed

            doc.reload()
            self.assertEqual(doc.description, "Updated by admin")
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    # ========== Workflow State Edge Cases ==========

    def test_idle_workflow_allows_editing(self):
        """When workflow is idle (not started), no restrictions apply."""
        if not hasattr(self.test_machine, 'edit_restriction_mode'):
            self.skipTest("edit_restriction_mode field not yet implemented")

        self.test_machine.edit_restriction_mode = "Assigned Only"
        self.test_machine.save(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Idle Workflow Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            # Create workflow instance but leave it in idle state
            instance = create_idle_workflow_instance(doc, self.test_machine)

            frappe.set_user(self.regular_user.name)
            doc.reload()
            doc.description = "Updated"
            doc.save()  # Should succeed - workflow is idle

            doc.reload()
            self.assertEqual(doc.description, "Updated")
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    def test_final_workflow_allows_editing(self):
        """When workflow is final (completed), no restrictions apply."""
        if not hasattr(self.test_machine, 'edit_restriction_mode'):
            self.skipTest("edit_restriction_mode field not yet implemented")

        self.test_machine.edit_restriction_mode = "Assigned Only"
        self.test_machine.save(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Final Workflow Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            instance = start_workflow_on_doc(doc, self.test_machine)
            # Mark workflow as final/completed
            instance.status = "final"
            instance.current_state = "approved"
            instance.save(ignore_permissions=True)

            frappe.set_user(self.regular_user.name)
            doc.reload()
            doc.description = "Updated"
            doc.save()  # Should succeed - workflow is final

            doc.reload()
            self.assertEqual(doc.description, "Updated")
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    def test_no_pending_task_allows_editing(self):
        """When no pending approval task, no restrictions apply."""
        if not hasattr(self.test_machine, 'edit_restriction_mode'):
            self.skipTest("edit_restriction_mode field not yet implemented")

        self.test_machine.edit_restriction_mode = "Assigned Only"
        self.test_machine.save(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for No Pending Task Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            instance = start_workflow_on_doc(doc, self.test_machine)
            # Don't create any approval tasks - workflow is active but no pending task

            frappe.set_user(self.regular_user.name)
            doc.reload()
            doc.description = "Updated"
            doc.save()  # Should succeed - no pending task

            doc.reload()
            self.assertEqual(doc.description, "Updated")
        finally:
            frappe.db.delete("Approval Task", {"reference_name": doc.name})
            frappe.db.delete("Machine Instance", {"reference_name": doc.name})
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()

    def test_no_workflow_instance_allows_editing(self):
        """When no workflow instance exists, no restrictions apply."""
        if not hasattr(self.test_machine, 'edit_restriction_mode'):
            self.skipTest("edit_restriction_mode field not yet implemented")

        self.test_machine.edit_restriction_mode = "Assigned Only"
        self.test_machine.save(ignore_permissions=True)

        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for No Instance Test",
            "status": "Open"
        })
        doc.insert(ignore_permissions=True)

        try:
            # Don't create any workflow instance

            frappe.set_user(self.regular_user.name)
            doc.reload()
            doc.description = "Updated"
            doc.save()  # Should succeed - no workflow instance

            doc.reload()
            self.assertEqual(doc.description, "Updated")
        finally:
            frappe.db.delete("ToDo", {"name": doc.name})
            frappe.db.commit()


# ============ Helper Functions ============

def create_test_user(email, full_name, roles=None):
    """Create a test user with specified roles."""
    if frappe.db.exists("User", email):
        return frappe.get_doc("User", email)

    # Split full name properly
    name_parts = full_name.split()
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "enabled": 1,
        "user_type": "System User"
    })
    user.insert(ignore_permissions=True)

    # Add roles
    if roles:
        for role in roles:
            if role not in [r.role for r in user.roles]:
                user.append("roles", {"role": role})
        user.save(ignore_permissions=True)

    return user


def create_test_workflow_with_edit_restriction():
    """Create a test approval workflow with edit_restriction_mode field."""
    machine_id = "test_edit_restriction_workflow_" + frappe.generate_hash()[:8]

    if frappe.db.exists("State Machine", machine_id):
        return frappe.get_doc("State Machine", machine_id)

    config = {
        "id": machine_id,
        "initial": "pending_approval",
        "states": {
            "pending_approval": {
                "meta": {
                    "domain_node": {
                        "type": "approval",
                        "label": "Pending Approval",
                        "resolver": {
                            "type": "static_user"
                        },
                        "available_actions": ["Approve", "Reject"]
                    }
                },
                "on": {
                    "APPROVE": "approved",
                    "REJECT": "rejected"
                }
            },
            "approved": {
                "type": "final",
                "meta": {
                    "domain_node": {
                        "type": "end",
                        "label": "Approved",
                        "final_status": "Approved"
                    }
                }
            },
            "rejected": {
                "type": "final",
                "meta": {
                    "domain_node": {
                        "type": "end",
                        "label": "Rejected",
                        "final_status": "Rejected"
                    }
                }
            }
        }
    }

    machine = frappe.get_doc({
        "doctype": "State Machine",
        "machine_id": machine_id,
        "title": "Test Edit Restriction Workflow",
        "is_active": 1,
        "version": 1,
        "attached_doctype": "ToDo",
        "json_config": json.dumps(config)
    })
    machine.insert(ignore_permissions=True)
    return machine


def start_workflow_on_doc(doc, machine):
    """Start a workflow on a document by creating an active Machine Instance."""
    instance = frappe.get_doc({
        "doctype": "Machine Instance",
        "machine": machine.name,
        "reference_doctype": doc.doctype,
        "reference_name": doc.name,
        "current_state": "pending_approval",
        "status": "active",
        "context": "{}"
    })
    instance.insert(ignore_permissions=True)
    return instance


def create_idle_workflow_instance(doc, machine):
    """Create a workflow instance in idle state (not started)."""
    instance = frappe.get_doc({
        "doctype": "Machine Instance",
        "machine": machine.name,
        "reference_doctype": doc.doctype,
        "reference_name": doc.name,
        "current_state": "pending_approval",
        "status": "idle",  # Idle - not started
        "context": "{}"
    })
    instance.insert(ignore_permissions=True)
    return instance


def assign_task_to_user(instance, user):
    """Create an approval task assigned to a specific user."""
    task = frappe.get_doc({
        "doctype": "Approval Task",
        "workflow_instance": instance.name,
        "node_id": "pending_approval",
        "node_label": "Pending Approval",
        "assigned_to": user,
        "assigned_role": None,
        "status": "Pending",
        "reference_doctype": instance.reference_doctype,
        "reference_name": instance.reference_name,
        "available_actions": json.dumps(["Approve", "Reject"]),
        "priority": "Medium"
    })
    task.insert(ignore_permissions=True)
    return task


def assign_task_to_role(instance, role):
    """Create an approval task assigned to a role (not a specific user)."""
    task = frappe.get_doc({
        "doctype": "Approval Task",
        "workflow_instance": instance.name,
        "node_id": "pending_approval",
        "node_label": "Pending Approval",
        "assigned_to": None,  # No specific user
        "assigned_role": role,
        "status": "Pending",
        "reference_doctype": instance.reference_doctype,
        "reference_name": instance.reference_name,
        "available_actions": json.dumps(["Approve", "Reject"]),
        "priority": "Medium"
    })
    task.insert(ignore_permissions=True)
    return task
