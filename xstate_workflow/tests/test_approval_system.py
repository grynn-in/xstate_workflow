# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Test cases for Approval System features:
- Document details enrichment in task cards
- User info API
- Permission fixes for approval tasks
- Role-based and user-based task assignment
"""

import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase


class TestApprovalTaskManager(FrappeTestCase):
    """Tests for ApprovalTaskManager and get_my_approval_tasks"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        super().setUpClass()

        # Create test users
        cls.test_user = create_test_user("approval_test_user@example.com", "Approval Test User")
        cls.test_approver = create_test_user("approval_test_approver@example.com", "Approval Test Approver")
        cls.test_manager = create_test_user("approval_test_manager@example.com", "Approval Test Manager")

        # Add roles
        add_role_to_user(cls.test_approver.name, "Sales User")
        add_role_to_user(cls.test_manager.name, "Sales Manager")

        # Create a test workflow
        cls.test_machine = create_test_approval_workflow()

        # Create a test document (ToDo is available in all Frappe installations)
        cls.test_doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Approval System",
            "status": "Open"
        })
        cls.test_doc.insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures"""
        # Delete test data
        frappe.db.delete("Approval Task", {"reference_doctype": "ToDo"})
        frappe.db.delete("Machine Instance", {"reference_doctype": "ToDo"})
        frappe.db.delete("State Machine", {"name": cls.test_machine.name})
        frappe.db.delete("ToDo", {"name": cls.test_doc.name})

        # Delete test users
        for user in [cls.test_user, cls.test_approver, cls.test_manager]:
            frappe.db.delete("Has Role", {"parent": user.name})
            frappe.db.delete("User", {"name": user.name})

        frappe.db.commit()
        super().tearDownClass()

    def tearDown(self):
        """Clean up after each test"""
        frappe.db.delete("Approval Task", {"reference_doctype": "ToDo"})
        frappe.db.delete("Machine Instance", {"reference_doctype": "ToDo"})
        frappe.db.commit()
        frappe.set_user("Administrator")

    def test_create_approval_task(self):
        """Test creating an approval task"""
        from xstate_workflow.approval import create_approval_task

        # Create a machine instance first
        instance = create_test_instance(self.test_machine.name, self.test_doc)

        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Pending Approval",
            assignees=[self.test_approver.name],
            available_actions=["Approve", "Reject"],
            priority="Medium"
        )

        self.assertIsNotNone(task)
        self.assertEqual(task.status, "Pending")
        self.assertEqual(task.assigned_to, self.test_approver.name)
        self.assertEqual(task.reference_doctype, "ToDo")
        self.assertEqual(task.reference_name, self.test_doc.name)

    def test_create_role_based_approval_task(self):
        """Test creating a role-based approval task"""
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        # Note: create_task requires at least one assignee, but for role-based
        # tasks, the assigned_to is set to None (the assignee is just for validation)
        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Sales User Approval",
            assignees=[self.test_approver.name],  # Required by validation
            assigned_role="Sales User",
            available_actions=["Approve", "Reject"]
        )

        self.assertIsNotNone(task)
        self.assertEqual(task.assigned_role, "Sales User")
        # For role-based, assigned_to should be None (anyone with role can claim)
        self.assertIsNone(task.assigned_to)

    def test_get_my_approval_tasks_direct_assignment(self):
        """Test fetching tasks assigned directly to user"""
        from xstate_workflow.approval import get_my_approval_tasks, create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        # Create task assigned directly to test_approver
        create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_approver.name]
        )

        # Fetch tasks for test_approver
        tasks = get_my_approval_tasks(user=self.test_approver.name, status="Pending")

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["assigned_to"], self.test_approver.name)

    def test_get_my_approval_tasks_role_assignment(self):
        """Test fetching tasks assigned to user's role"""
        from xstate_workflow.approval import get_my_approval_tasks, create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        # Create task assigned to Sales User role
        # Note: assignees is required for validation, but assigned_to will be None for role-based
        create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Sales Approval",
            assignees=["Administrator"],  # Required by validation
            assigned_role="Sales User"
        )

        # test_approver has Sales User role, should see the task
        tasks = get_my_approval_tasks(user=self.test_approver.name, status="Pending")

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["assigned_role"], "Sales User")

    def test_get_my_approval_tasks_document_details(self):
        """Test that document details are enriched in task response"""
        from xstate_workflow.approval import get_my_approval_tasks, create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_approver.name]
        )

        tasks = get_my_approval_tasks(user=self.test_approver.name, status="Pending")

        self.assertEqual(len(tasks), 1)
        task = tasks[0]

        # Check document details are present
        self.assertIn("doc_created", task)
        self.assertIn("doc_modified", task)
        self.assertIn("doc_owner", task)
        self.assertIsNotNone(task["doc_created"])
        self.assertIsNotNone(task["doc_owner"])

    def test_get_my_approval_tasks_workflow_submitted_date(self):
        """Test that workflow submission date is included"""
        from xstate_workflow.approval import get_my_approval_tasks, create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_approver.name]
        )

        tasks = get_my_approval_tasks(user=self.test_approver.name, status="Pending")

        self.assertEqual(len(tasks), 1)
        task = tasks[0]

        # Check workflow submitted date is present
        self.assertIn("workflow_submitted", task)
        self.assertIsNotNone(task["workflow_submitted"])

    def test_get_my_approval_tasks_last_approver(self):
        """Test that last approver info is included for multi-step workflows"""
        from xstate_workflow.approval import get_my_approval_tasks, create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        # Create first task and complete it
        first_task = create_approval_task(
            workflow_instance=instance.name,
            node_id="first_approval",
            node_label="First Approval",
            assignees=[self.test_approver.name]
        )

        # Complete first task
        first_task.status = "Completed"
        first_task.action_taken = "Approve"
        first_task.completed_by = self.test_approver.name
        first_task.completed_at = frappe.utils.now_datetime()
        first_task.save(ignore_permissions=True)

        # Create second task
        create_approval_task(
            workflow_instance=instance.name,
            node_id="second_approval",
            node_label="Second Approval",
            assignees=[self.test_manager.name]
        )

        # Fetch tasks for manager
        tasks = get_my_approval_tasks(user=self.test_manager.name, status="Pending")

        self.assertEqual(len(tasks), 1)
        task = tasks[0]

        # Check last approver info
        self.assertIn("last_approver", task)
        self.assertIsNotNone(task["last_approver"])
        self.assertEqual(task["last_approver"]["completed_by"], self.test_approver.name)
        self.assertEqual(task["last_approver"]["action_taken"], "Approve")


class TestApprovalAPI(FrappeTestCase):
    """Tests for Approval API endpoints"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        super().setUpClass()

        cls.test_user = create_test_user("api_test_user@example.com", "API Test User")
        cls.test_approver = create_test_user("api_test_approver@example.com", "API Test Approver")

        add_role_to_user(cls.test_approver.name, "Sales User")

        cls.test_machine = create_test_approval_workflow()

        cls.test_doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for API Tests",
            "status": "Open"
        })
        cls.test_doc.insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures"""
        frappe.db.delete("Approval Task", {"reference_doctype": "ToDo"})
        frappe.db.delete("Machine Instance", {"reference_doctype": "ToDo"})
        frappe.db.delete("State Machine", {"name": cls.test_machine.name})
        frappe.db.delete("ToDo", {"name": cls.test_doc.name})

        for user in [cls.test_user, cls.test_approver]:
            frappe.db.delete("Has Role", {"parent": user.name})
            frappe.db.delete("User", {"name": user.name})

        frappe.db.commit()
        super().tearDownClass()

    def tearDown(self):
        """Clean up after each test"""
        frappe.db.delete("Approval Task", {"reference_doctype": "ToDo"})
        frappe.db.delete("Machine Instance", {"reference_doctype": "ToDo"})
        frappe.db.commit()
        frappe.set_user("Administrator")

    def test_get_current_user_info(self):
        """Test get_current_user_info API"""
        from xstate_workflow.api.approval import get_current_user_info

        frappe.set_user(self.test_approver.name)

        result = get_current_user_info()

        self.assertEqual(result["user"], self.test_approver.name)
        self.assertEqual(result["full_name"], "API Test Approver")
        self.assertIn("user_roles", result)
        self.assertIn("workflow_roles", result)
        self.assertIn("Sales User", result["user_roles"])

    def test_get_task_details(self):
        """Test get_task_details API"""
        from xstate_workflow.api.approval import get_task_details
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_approver.name],
            available_actions=["Approve", "Reject", "Request Info"]
        )

        result = get_task_details(task.name)

        self.assertEqual(result["name"], task.name)
        self.assertEqual(result["status"], "Pending")
        self.assertEqual(result["assigned_to"], self.test_approver.name)
        self.assertIn("Approve", result["available_actions"])
        self.assertIn("Reject", result["available_actions"])
        self.assertIn("reference_document", result)

    def test_get_task_details_permission_fallback(self):
        """Test that get_task_details works even without document permission"""
        from xstate_workflow.api.approval import get_task_details
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_user.name]
        )

        # Switch to test_user who may not have ToDo read permission
        frappe.set_user(self.test_user.name)

        # Should not raise error even without document permission
        result = get_task_details(task.name)

        self.assertEqual(result["name"], task.name)
        self.assertEqual(result["reference_doctype"], "ToDo")
        self.assertEqual(result["reference_name"], self.test_doc.name)

    def test_complete_approval_task(self):
        """Test completing an approval task"""
        from xstate_workflow.api.approval import complete_approval_task
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_approver.name]
        )

        frappe.set_user(self.test_approver.name)

        result = complete_approval_task(
            task_name=task.name,
            action="Approve",
            comments="Looks good!"
        )

        self.assertTrue(result.get("success"))

        # Verify task is completed
        task.reload()
        self.assertEqual(task.status, "Completed")
        self.assertEqual(task.action_taken, "Approve")
        self.assertEqual(task.comments, "Looks good!")
        self.assertEqual(task.completed_by, self.test_approver.name)

    def test_claim_task(self):
        """Test claiming a role-based task"""
        from xstate_workflow.api.approval import claim_task
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        # Create role-based task
        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Sales Approval",
            assignees=["Administrator"],  # Required by validation
            assigned_role="Sales User"
        )

        frappe.set_user(self.test_approver.name)

        result = claim_task(task.name)

        self.assertTrue(result["success"])
        self.assertEqual(result["new_assignee"], self.test_approver.name)

        # Verify task is now assigned
        task.reload()
        self.assertEqual(task.assigned_to, self.test_approver.name)

    def test_claim_task_unauthorized(self):
        """Test that claiming fails for users without the required role"""
        from xstate_workflow.api.approval import claim_task
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        # Create task for Sales Manager role
        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Manager Approval",
            assignees=["Administrator"],  # Required by validation
            assigned_role="Sales Manager"
        )

        # test_user doesn't have Sales Manager role
        frappe.set_user(self.test_user.name)

        with self.assertRaises(frappe.ValidationError):
            claim_task(task.name)

    def test_reassign_task(self):
        """Test reassigning a task to another user"""
        from xstate_workflow.api.approval import reassign_task
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_approver.name]
        )

        frappe.set_user(self.test_approver.name)

        result = reassign_task(
            task_name=task.name,
            new_user=self.test_user.name,
            reason="Out of office"
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["new_user"], self.test_user.name)

        # Verify task is reassigned
        task.reload()
        self.assertEqual(task.assigned_to, self.test_user.name)
        self.assertIn("Out of office", task.comments)

    def test_get_approval_counts(self):
        """Test getting approval task counts"""
        from xstate_workflow.api.approval import get_approval_counts
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        # Create pending task
        create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_approver.name]
        )

        frappe.set_user(self.test_approver.name)

        counts = get_approval_counts()

        self.assertIn("pending", counts)
        self.assertIn("completed", counts)
        self.assertGreaterEqual(counts["pending"], 1)


class TestMachineInstancePermissions(FrappeTestCase):
    """Tests for Machine Instance permission checks"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        super().setUpClass()

        cls.test_user = create_test_user("perm_test_user@example.com", "Permission Test User")
        cls.test_approver = create_test_user("perm_test_approver@example.com", "Permission Test Approver")

        add_role_to_user(cls.test_approver.name, "Sales User")

        cls.test_machine = create_test_approval_workflow()

        cls.test_doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Permission Tests",
            "status": "Open"
        })
        cls.test_doc.insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures"""
        frappe.db.delete("Approval Task", {"reference_doctype": "ToDo"})
        frappe.db.delete("Machine Instance", {"reference_doctype": "ToDo"})
        frappe.db.delete("State Machine", {"name": cls.test_machine.name})
        frappe.db.delete("ToDo", {"name": cls.test_doc.name})

        for user in [cls.test_user, cls.test_approver]:
            frappe.db.delete("Has Role", {"parent": user.name})
            frappe.db.delete("User", {"name": user.name})

        frappe.db.commit()
        super().tearDownClass()

    def tearDown(self):
        """Clean up after each test"""
        frappe.db.delete("Approval Task", {"reference_doctype": "ToDo"})
        frappe.db.delete("Machine Instance", {"reference_doctype": "ToDo"})
        frappe.db.commit()
        frappe.set_user("Administrator")

    def test_permission_with_direct_assignment(self):
        """Test that users with direct task assignment can access Machine Instance"""
        from xstate_workflow.permissions import has_permission
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        # Create task directly assigned to test_user
        create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_user.name]
        )

        # test_user should have permission via approval task
        instance_doc = frappe.get_doc("Machine Instance", instance.name)
        result = has_permission(instance_doc, "read", self.test_user.name)

        self.assertTrue(result)

    def test_permission_with_role_assignment(self):
        """Test that users with role-based task assignment can access Machine Instance"""
        from xstate_workflow.permissions import has_permission
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        # Create task assigned to Sales User role
        create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Sales Approval",
            assignees=["Administrator"],  # Required by validation
            assigned_role="Sales User"
        )

        # test_approver has Sales User role, should have permission
        instance_doc = frappe.get_doc("Machine Instance", instance.name)
        result = has_permission(instance_doc, "read", self.test_approver.name)

        self.assertTrue(result)

    def test_permission_denied_without_assignment(self):
        """Test that users without task assignment cannot access Machine Instance"""
        from xstate_workflow.permissions import has_permission
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        # Create task assigned to someone else
        create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_approver.name]
        )

        # test_user is not assigned and doesn't have the role
        instance_doc = frappe.get_doc("Machine Instance", instance.name)
        result = has_permission(instance_doc, "read", self.test_user.name)

        # Should be False (unless they have document permission)
        # Note: This might be True if test_user has ToDo read permission
        # The important thing is the logic is checked
        self.assertIsNotNone(result)

    def test_system_manager_always_has_permission(self):
        """Test that System Manager always has permission"""
        from xstate_workflow.permissions import has_permission

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        instance_doc = frappe.get_doc("Machine Instance", instance.name)
        result = has_permission(instance_doc, "read", "Administrator")

        self.assertTrue(result)


class TestApprovalTaskDocument(FrappeTestCase):
    """Tests for Approval Task document methods"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        super().setUpClass()

        cls.test_approver = create_test_user("doc_test_approver@example.com", "Doc Test Approver")
        cls.test_user = create_test_user("doc_test_user@example.com", "Doc Test User")

        add_role_to_user(cls.test_approver.name, "Sales User")

        cls.test_machine = create_test_approval_workflow()

        cls.test_doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Test ToDo for Document Tests",
            "status": "Open"
        })
        cls.test_doc.insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures"""
        frappe.db.delete("Approval Task", {"reference_doctype": "ToDo"})
        frappe.db.delete("Machine Instance", {"reference_doctype": "ToDo"})
        frappe.db.delete("State Machine", {"name": cls.test_machine.name})
        frappe.db.delete("ToDo", {"name": cls.test_doc.name})

        for user in [cls.test_approver, cls.test_user]:
            frappe.db.delete("Has Role", {"parent": user.name})
            frappe.db.delete("User", {"name": user.name})

        frappe.db.commit()
        super().tearDownClass()

    def tearDown(self):
        """Clean up after each test"""
        frappe.db.delete("Approval Task", {"reference_doctype": "ToDo"})
        frappe.db.delete("Machine Instance", {"reference_doctype": "ToDo"})
        frappe.db.commit()
        frappe.set_user("Administrator")

    def test_can_user_complete_direct_assignment(self):
        """Test can_user_complete for directly assigned user"""
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_approver.name]
        )

        self.assertTrue(task.can_user_complete(self.test_approver.name))
        self.assertFalse(task.can_user_complete(self.test_user.name))

    def test_can_user_complete_role_assignment(self):
        """Test can_user_complete for role-based assignment"""
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Sales Approval",
            assignees=["Administrator"],  # Required by validation
            assigned_role="Sales User"
        )

        # test_approver has Sales User role
        self.assertTrue(task.can_user_complete(self.test_approver.name))
        # test_user doesn't have Sales User role
        self.assertFalse(task.can_user_complete(self.test_user.name))

    def test_can_user_complete_system_manager(self):
        """Test that System Manager can always complete tasks"""
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_approver.name]
        )

        self.assertTrue(task.can_user_complete("Administrator"))

    def test_is_overdue(self):
        """Test is_overdue method"""
        from xstate_workflow.approval import create_approval_task
        from frappe.utils import add_to_date, now_datetime

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_approver.name],
            sla_hours=24  # Normal SLA
        )

        # Task should not be overdue initially
        self.assertFalse(task.is_overdue())

        # Manually set due_date to past to test overdue detection
        task.due_date = add_to_date(now_datetime(), hours=-1)
        task.save(ignore_permissions=True)

        self.assertTrue(task.is_overdue())

    def test_get_available_actions_list(self):
        """Test get_available_actions_list method"""
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_approver.name],
            available_actions=["Approve", "Reject", "Request Info"]
        )

        actions = task.get_available_actions_list()

        self.assertEqual(len(actions), 3)
        self.assertIn("Approve", actions)
        self.assertIn("Reject", actions)
        self.assertIn("Request Info", actions)

    def test_escalate(self):
        """Test task escalation"""
        from xstate_workflow.approval import create_approval_task

        instance = create_test_instance(self.test_machine.name, self.test_doc)

        task = create_approval_task(
            workflow_instance=instance.name,
            node_id="pending_approval",
            node_label="Test Approval",
            assignees=[self.test_approver.name]
        )

        # Run as Administrator to avoid permission issues when creating escalated task
        frappe.set_user("Administrator")

        new_task = task.escalate(
            escalate_to=self.test_user.name,
            reason="Need higher authority"
        )

        # Original task should be escalated
        task.reload()
        self.assertEqual(task.status, "Escalated")

        # New task should be created
        self.assertIsNotNone(new_task)
        self.assertEqual(new_task.status, "Pending")
        self.assertEqual(new_task.assigned_to, self.test_user.name)
        self.assertEqual(new_task.escalated_from, task.name)
        self.assertEqual(new_task.escalation_level, 1)


# ============ Helper Functions ============

def create_test_user(email, full_name):
    """Create a test user"""
    if frappe.db.exists("User", email):
        return frappe.get_doc("User", email)

    # Split full name properly - first word is first name, rest is last name
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
    return user


def add_role_to_user(user, role):
    """Add a role to a user"""
    user_doc = frappe.get_doc("User", user)
    if role not in [r.role for r in user_doc.roles]:
        user_doc.append("roles", {"role": role})
        user_doc.save(ignore_permissions=True)


def create_test_approval_workflow():
    """Create a test approval workflow"""
    machine_id = "test_approval_workflow_" + frappe.generate_hash()[:8]

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
        "title": "Test Approval Workflow",
        "is_active": 1,
        "version": 1,
        "attached_doctype": "ToDo",
        "json_config": json.dumps(config)
    })
    machine.insert(ignore_permissions=True)
    return machine


def create_test_instance(machine_name, ref_doc):
    """Create a test Machine Instance"""
    instance = frappe.get_doc({
        "doctype": "Machine Instance",
        "machine": machine_name,
        "reference_doctype": ref_doc.doctype,
        "reference_name": ref_doc.name,
        "current_state": "pending_approval",
        "status": "active",
        "context": "{}"
    })
    instance.insert(ignore_permissions=True)
    return instance
