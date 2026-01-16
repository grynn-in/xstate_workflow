# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Tests for Data Input Resolver.

Tests the data input resolution functionality including:
- Document field selection
- Linked document fetching
- Context variable resolution
- Nested field access
- Error handling for missing fields
"""

import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestDataInputResolver(FrappeTestCase):
	"""Tests for the DataInputResolver class."""

	def test_resolve_empty_config_returns_full_document(self):
		"""Test that empty config returns full document data."""
		from xstate_workflow.langgraph.data_input import DataInputResolver

		resolver = DataInputResolver()

		doc_data = {
			"name": "TEST001",
			"doctype": "ToDo",
			"description": "Test todo",
			"status": "Open",
		}

		result = resolver.resolve(
			config=None,
			ref_doc=doc_data,
			context={"key": "value"},
		)

		self.assertEqual(result["document"], doc_data)
		self.assertEqual(result["context"], {"key": "value"})
		self.assertEqual(result["metadata"]["doctype"], "ToDo")
		self.assertEqual(result["metadata"]["docname"], "TEST001")

	def test_resolve_document_fields_returns_selected_only(self):
		"""Test that only configured fields are returned."""
		from xstate_workflow.langgraph.data_input import DataInputResolver

		resolver = DataInputResolver()

		doc_data = {
			"name": "TEST001",
			"doctype": "ToDo",
			"description": "Test todo",
			"status": "Open",
			"owner": "admin@example.com",
			"priority": "Medium",
		}

		config = {
			"documentFields": ["description", "status"],
		}

		result = resolver.resolve(
			config=config,
			ref_doc=doc_data,
			context={},
		)

		# Should only have the selected fields
		self.assertEqual(len(result["document"]), 2)
		self.assertEqual(result["document"]["description"], "Test todo")
		self.assertEqual(result["document"]["status"], "Open")
		self.assertNotIn("owner", result["document"])
		self.assertNotIn("priority", result["document"])

	def test_resolve_missing_field_skips_gracefully(self):
		"""Test that missing fields are skipped without error."""
		from xstate_workflow.langgraph.data_input import DataInputResolver

		resolver = DataInputResolver()

		doc_data = {
			"name": "TEST001",
			"description": "Test",
		}

		config = {
			"documentFields": ["description", "non_existent_field"],
		}

		result = resolver.resolve(
			config=config,
			ref_doc=doc_data,
			context={},
		)

		# Should have description but not non_existent_field
		self.assertIn("description", result["document"])
		self.assertNotIn("non_existent_field", result["document"])

	def test_resolve_context_variables_returns_selected_only(self):
		"""Test that only configured context variables are returned."""
		from xstate_workflow.langgraph.data_input import DataInputResolver

		resolver = DataInputResolver()

		context = {
			"approval_level": 2,
			"previous_approver": "john@example.com",
			"internal_state": "processing",
			"timestamp": "2024-01-01",
		}

		config = {
			"contextVariables": ["approval_level", "previous_approver"],
		}

		result = resolver.resolve(
			config=config,
			ref_doc={},
			context=context,
		)

		self.assertEqual(len(result["context"]), 2)
		self.assertEqual(result["context"]["approval_level"], 2)
		self.assertEqual(result["context"]["previous_approver"], "john@example.com")
		self.assertNotIn("internal_state", result["context"])

	def test_resolve_missing_context_var_skips_gracefully(self):
		"""Test that missing context variables are skipped."""
		from xstate_workflow.langgraph.data_input import DataInputResolver

		resolver = DataInputResolver()

		context = {"existing": "value"}

		config = {
			"contextVariables": ["existing", "missing"],
		}

		result = resolver.resolve(
			config=config,
			ref_doc={},
			context=context,
		)

		self.assertIn("existing", result["context"])
		self.assertNotIn("missing", result["context"])

	def test_get_nested_value_dict_access(self):
		"""Test nested dictionary access."""
		from xstate_workflow.langgraph.data_input import DataInputResolver

		resolver = DataInputResolver()

		data = {
			"customer": {
				"name": "John Doe",
				"address": {
					"city": "Berlin",
				},
			},
		}

		# First level
		self.assertEqual(
			resolver._get_nested_value(data, "customer.name"),
			"John Doe",
		)

		# Second level
		self.assertEqual(
			resolver._get_nested_value(data, "customer.address.city"),
			"Berlin",
		)

	def test_get_nested_value_array_access(self):
		"""Test nested array access."""
		from xstate_workflow.langgraph.data_input import DataInputResolver

		resolver = DataInputResolver()

		data = {
			"items": [
				{"item_code": "ITEM001", "qty": 10},
				{"item_code": "ITEM002", "qty": 5},
			],
		}

		# Access specific index
		self.assertEqual(
			resolver._get_nested_value(data, "items.0.item_code"),
			"ITEM001",
		)

		# Access field from all items
		result = resolver._get_nested_value(data, "items.item_code")
		self.assertEqual(result, ["ITEM001", "ITEM002"])

	def test_get_nested_value_returns_none_for_invalid_path(self):
		"""Test that invalid paths return None."""
		from xstate_workflow.langgraph.data_input import DataInputResolver

		resolver = DataInputResolver()

		data = {"a": {"b": "value"}}

		self.assertIsNone(resolver._get_nested_value(data, "a.c.d"))
		self.assertIsNone(resolver._get_nested_value(data, "x.y.z"))

	def test_resolve_with_document_object(self):
		"""Test resolve with Frappe document object."""
		from xstate_workflow.langgraph.data_input import DataInputResolver

		resolver = DataInputResolver()

		# Mock a Frappe document
		mock_doc = MagicMock()
		mock_doc.as_dict.return_value = {
			"name": "TEST001",
			"doctype": "ToDo",
			"description": "Test",
		}

		result = resolver.resolve(
			config=None,
			ref_doc=mock_doc,
			context={},
		)

		self.assertEqual(result["document"]["name"], "TEST001")
		mock_doc.as_dict.assert_called_once()

	def test_resolve_snake_case_config_keys(self):
		"""Test that snake_case config keys are supported."""
		from xstate_workflow.langgraph.data_input import DataInputResolver

		resolver = DataInputResolver()

		doc_data = {
			"field_a": "A",
			"field_b": "B",
		}

		context = {"ctx_a": "X"}

		# Use snake_case keys (Python style)
		config = {
			"document_fields": ["field_a"],
			"context_variables": ["ctx_a"],
		}

		result = resolver.resolve(
			config=config,
			ref_doc=doc_data,
			context=context,
		)

		self.assertEqual(result["document"]["field_a"], "A")
		self.assertEqual(result["context"]["ctx_a"], "X")

	def test_resolve_camelCase_config_keys(self):
		"""Test that camelCase config keys are supported."""
		from xstate_workflow.langgraph.data_input import DataInputResolver

		resolver = DataInputResolver()

		doc_data = {
			"field_a": "A",
			"field_b": "B",
		}

		context = {"ctx_a": "X"}

		# Use camelCase keys (JavaScript style)
		config = {
			"documentFields": ["field_a"],
			"contextVariables": ["ctx_a"],
		}

		result = resolver.resolve(
			config=config,
			ref_doc=doc_data,
			context=context,
		)

		self.assertEqual(result["document"]["field_a"], "A")
		self.assertEqual(result["context"]["ctx_a"], "X")


class TestDataInputLinkedDocuments(FrappeTestCase):
	"""Tests for linked document resolution."""

	def setUp(self):
		"""Set up test fixtures."""
		# Create a test user if not exists
		if not frappe.db.exists("User", "test_linked@example.com"):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": "test_linked@example.com",
					"first_name": "Test",
					"last_name": "Linked",
					"enabled": 1,
				}
			)
			user.insert(ignore_permissions=True)
			frappe.db.commit()
			self.created_user = True
		else:
			self.created_user = False

	def tearDown(self):
		"""Clean up test fixtures."""
		if self.created_user:
			try:
				frappe.delete_doc("User", "test_linked@example.com", force=True)
				frappe.db.commit()
			except Exception:
				pass

	@patch.object(frappe, "get_meta")
	@patch.object(frappe, "get_value")
	def test_resolve_linked_document(self, mock_get_value, mock_get_meta):
		"""Test linked document resolution."""
		from xstate_workflow.langgraph.data_input import DataInputResolver

		resolver = DataInputResolver()

		# Mock the metadata lookup
		mock_field = MagicMock()
		mock_field.fieldtype = "Link"
		mock_field.options = "Supplier"

		mock_meta = MagicMock()
		mock_meta.get_field.return_value = mock_field
		mock_get_meta.return_value = mock_meta

		# Mock the linked document fetch
		mock_get_value.return_value = {
			"supplier_name": "Acme Corp",
			"tax_id": "TAX123",
		}

		doc_data = {
			"name": "PO001",
			"doctype": "Purchase Order",
			"supplier": "SUPP001",
		}

		config = {
			"linkedDocuments": [
				{
					"linkField": "supplier",
					"fields": ["supplier_name", "tax_id"],
				}
			],
		}

		result = resolver.resolve(
			config=config,
			ref_doc=doc_data,
			context={},
			doctype="Purchase Order",
		)

		self.assertIn("supplier", result["linked"])
		self.assertEqual(result["linked"]["supplier"]["supplier_name"], "Acme Corp")
		self.assertEqual(result["linked"]["supplier"]["tax_id"], "TAX123")

	def test_resolve_linked_document_missing_value(self):
		"""Test that missing linked document returns None."""
		from xstate_workflow.langgraph.data_input import DataInputResolver

		resolver = DataInputResolver()

		doc_data = {
			"name": "PO001",
			"supplier": None,  # No supplier linked
		}

		config = {
			"linkedDocuments": [
				{
					"linkField": "supplier",
					"fields": ["supplier_name"],
				}
			],
		}

		result = resolver.resolve(
			config=config,
			ref_doc=doc_data,
			context={},
			doctype="Purchase Order",
		)

		self.assertIn("supplier", result["linked"])
		self.assertIsNone(result["linked"]["supplier"])


class TestFormatDataForAgent(FrappeTestCase):
	"""Tests for formatting resolved data for agent prompts."""

	def test_format_data_for_agent_basic(self):
		"""Test basic data formatting."""
		from xstate_workflow.langgraph.data_input import format_data_for_agent

		resolved_data = {
			"document": {"status": "Open", "amount": 1000},
			"linked": {},
			"context": {},
			"metadata": {"doctype": "Invoice", "docname": "INV001"},
		}

		formatted = format_data_for_agent(resolved_data)

		self.assertIn("Invoice: INV001", formatted)
		self.assertIn("Current Document Data", formatted)
		self.assertIn("status", formatted)
		self.assertIn("Open", formatted)

	def test_format_data_for_agent_with_linked(self):
		"""Test formatting with linked documents."""
		from xstate_workflow.langgraph.data_input import format_data_for_agent

		resolved_data = {
			"document": {"status": "Open"},
			"linked": {
				"customer": {"customer_name": "Acme Corp"},
			},
			"context": {},
			"metadata": {"doctype": "Invoice", "docname": "INV001"},
		}

		formatted = format_data_for_agent(resolved_data)

		self.assertIn("Linked Document Data", formatted)
		self.assertIn("customer", formatted)
		self.assertIn("Acme Corp", formatted)

	def test_format_data_for_agent_with_context(self):
		"""Test formatting with context variables."""
		from xstate_workflow.langgraph.data_input import format_data_for_agent

		resolved_data = {
			"document": {},
			"linked": {},
			"context": {
				"approval_level": 2,
				"previous_decision": "approved",
			},
			"metadata": {"doctype": "Invoice", "docname": "INV001"},
		}

		formatted = format_data_for_agent(resolved_data)

		self.assertIn("Workflow Context", formatted)
		self.assertIn("approval_level", formatted)
		self.assertIn("previous_decision", formatted)

	def test_format_data_for_agent_missing_linked(self):
		"""Test formatting with missing linked document."""
		from xstate_workflow.langgraph.data_input import format_data_for_agent

		resolved_data = {
			"document": {},
			"linked": {"supplier": None},
			"context": {},
			"metadata": {},
		}

		formatted = format_data_for_agent(resolved_data)

		self.assertIn("No linked document found", formatted)


class TestResolveDataInputFunction(FrappeTestCase):
	"""Tests for the resolve_data_input convenience function."""

	def test_resolve_data_input_function(self):
		"""Test the convenience function."""
		from xstate_workflow.langgraph.data_input import resolve_data_input

		doc_data = {
			"name": "TEST001",
			"field_a": "A",
			"field_b": "B",
		}

		config = {"documentFields": ["field_a"]}

		result = resolve_data_input(
			config=config,
			ref_doc=doc_data,
			context={"key": "value"},
			doctype="Test",
			docname="TEST001",
		)

		self.assertEqual(result["document"]["field_a"], "A")
		self.assertEqual(result["context"]["key"], "value")
		self.assertEqual(result["metadata"]["doctype"], "Test")


if __name__ == "__main__":
	unittest.main()
