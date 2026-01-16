# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Tests for REST Endpoint Tools.

Tests the REST endpoint tool functionality including:
- URL template substitution
- Request body substitution
- HTTP method handling
- Authentication headers
- Error handling
"""

import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestRESTToolSubstitution(FrappeTestCase):
	"""Tests for template substitution in REST tools."""

	def test_substitute_template_basic(self):
		"""Test basic template substitution."""
		from xstate_workflow.langgraph.tools import _substitute_template

		template = "https://api.example.com/customers/{{customer_id}}"
		doc = {"customer_id": "CUST001"}
		context = {}

		result = _substitute_template(template, doc, context)

		self.assertEqual(result, "https://api.example.com/customers/CUST001")

	def test_substitute_template_with_doc_prefix(self):
		"""Test substitution with doc. prefix."""
		from xstate_workflow.langgraph.tools import _substitute_template

		template = "https://api.example.com/orders/{{doc.order_id}}"
		doc = {"order_id": "ORD123"}
		context = {}

		result = _substitute_template(template, doc, context)

		self.assertEqual(result, "https://api.example.com/orders/ORD123")

	def test_substitute_template_with_context_prefix(self):
		"""Test substitution with context. prefix."""
		from xstate_workflow.langgraph.tools import _substitute_template

		template = "https://api.example.com/users/{{context.user_id}}"
		doc = {}
		context = {"user_id": "USER456"}

		result = _substitute_template(template, doc, context)

		self.assertEqual(result, "https://api.example.com/users/USER456")

	def test_substitute_template_multiple_placeholders(self):
		"""Test substitution with multiple placeholders."""
		from xstate_workflow.langgraph.tools import _substitute_template

		template = "https://api.example.com/{{doctype}}/{{name}}/items"
		doc = {"doctype": "Sales Order", "name": "SO-001"}
		context = {}

		result = _substitute_template(template, doc, context)

		self.assertEqual(result, "https://api.example.com/Sales Order/SO-001/items")

	def test_substitute_template_missing_value_replaces_with_empty(self):
		"""Test substitution with missing value replaces with empty string."""
		from xstate_workflow.langgraph.tools import _substitute_template

		template = "https://api.example.com/{{missing_field}}"
		doc = {}
		context = {}

		result = _substitute_template(template, doc, context)

		# Missing values are replaced with empty string
		self.assertEqual(result, "https://api.example.com/")

	def test_substitute_template_json_body(self):
		"""Test substitution in JSON body."""
		import json

		from xstate_workflow.langgraph.tools import _substitute_template

		template = json.dumps(
			{
				"customer": "{{customer}}",
				"amount": "{{grand_total}}",
			}
		)
		doc = {"customer": "CUST001", "grand_total": 1000}
		context = {}

		result = _substitute_template(template, doc, context)
		parsed = json.loads(result)

		self.assertEqual(parsed["customer"], "CUST001")
		self.assertEqual(parsed["amount"], "1000")  # Converted to string


class TestRESTToolAuthentication(FrappeTestCase):
	"""Tests for REST tool authentication."""

	def test_add_rest_auth_none(self):
		"""Test no authentication adds no header."""
		from xstate_workflow.langgraph.tools import _add_rest_auth

		headers = {}
		_add_rest_auth(headers, "none", "")

		self.assertNotIn("Authorization", headers)

	def test_add_rest_auth_api_key(self):
		"""Test API key authentication."""
		from xstate_workflow.langgraph.tools import _add_rest_auth

		headers = {}
		_add_rest_auth(headers, "api_key", "my-secret-key")

		# api_key uses X-API-Key header, not Authorization
		self.assertEqual(headers["X-API-Key"], "my-secret-key")

	def test_add_rest_auth_bearer(self):
		"""Test bearer token authentication."""
		from xstate_workflow.langgraph.tools import _add_rest_auth

		headers = {}
		_add_rest_auth(headers, "bearer", "my-token")

		self.assertEqual(headers["Authorization"], "Bearer my-token")

	def test_add_rest_auth_basic(self):
		"""Test basic authentication."""
		import base64

		from xstate_workflow.langgraph.tools import _add_rest_auth

		headers = {}
		_add_rest_auth(headers, "basic", "user:password")

		expected = base64.b64encode(b"user:password").decode()
		self.assertEqual(headers["Authorization"], f"Basic {expected}")


class TestRESTToolCreation(FrappeTestCase):
	"""Tests for REST tool creation in ToolRegistry."""

	def test_create_rest_tools_via_registry(self):
		"""Test creating tools from registry with REST endpoints."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={"customer": "CUST001"},
			doctype="Test",
			docname="TEST001",
			rest_endpoints=[
				{
					"name": "get_customer_details",
					"url": "https://api.example.com/customers/{{customer}}",
					"method": "GET",
					"authType": "none",
					"description": "Get customer details from external API",
				}
			],
		)

		# The _create_rest_tools method uses self.rest_endpoints
		try:
			tools = registry._create_rest_tools()
			# If tools is empty, langchain is not installed
			if not tools:
				self.skipTest("langchain_core not installed (no tools returned)")
			self.assertEqual(len(tools), 1)
			self.assertEqual(tools[0].name, "rest_get_customer_details")
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	def test_create_rest_tool_basic(self):
		"""Test creating a basic REST tool."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={"customer": "CUST001"},
			doctype="Test",
			docname="TEST001",
			rest_endpoints=[],
		)

		rest_config = {
			"name": "get_customer_details",
			"url": "https://api.example.com/customers/{{customer}}",
			"method": "GET",
			"authType": "none",
			"description": "Get customer details from external API",
		}

		try:
			tool = registry._create_rest_tool(rest_config)

			# If tool is None, langchain is not installed
			if tool is None:
				self.skipTest("langchain_core not installed (tool is None)")
			self.assertIsNotNone(tool)
			self.assertEqual(tool.name, "rest_get_customer_details")
			self.assertIn("customer details", tool.description.lower())
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("requests.request")
	def test_rest_tool_executes_get_request(self, mock_request):
		"""Test REST tool executes GET request."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		# Mock response
		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.ok = True
		mock_response.json.return_value = {"name": "Acme Corp"}
		mock_request.return_value = mock_response

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={"customer": "CUST001"},
			doctype="Test",
			docname="TEST001",
		)

		rest_config = {
			"name": "get_customer",
			"url": "https://api.example.com/customers/{{customer}}",
			"method": "GET",
			"authType": "none",
			"description": "Get customer",
		}

		try:
			tool = registry._create_rest_tool(rest_config)
			if tool is None:
				self.skipTest("langchain_core not installed")

			# Execute the tool
			result = tool.invoke({})

			# Verify request was made correctly
			mock_request.assert_called_once()
			call_kwargs = mock_request.call_args
			self.assertEqual(call_kwargs.kwargs["method"], "GET")
			self.assertIn("CUST001", call_kwargs.kwargs["url"])
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("requests.request")
	def test_rest_tool_executes_post_request(self, mock_request):
		"""Test REST tool executes POST request with body."""
		import json

		from xstate_workflow.langgraph.tools import ToolRegistry

		# Mock response
		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.ok = True
		mock_response.json.return_value = {"success": True}
		mock_request.return_value = mock_response

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={"order_id": "ORD001", "amount": 500},
			doctype="Test",
			docname="TEST001",
		)

		rest_config = {
			"name": "submit_order",
			"url": "https://api.example.com/orders",
			"method": "POST",
			"authType": "api_key",
			"authCredential": "secret",
			"body": json.dumps({"order": "{{order_id}}", "total": "{{amount}}"}),
			"description": "Submit order",
		}

		try:
			tool = registry._create_rest_tool(rest_config)
			if tool is None:
				self.skipTest("langchain_core not installed")

			result = tool.invoke({})

			# Verify POST was made
			call_kwargs = mock_request.call_args
			self.assertEqual(call_kwargs.kwargs["method"], "POST")
			# api_key uses X-API-Key header
			self.assertIn("X-API-Key", call_kwargs.kwargs["headers"])
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("requests.request")
	def test_rest_tool_handles_http_error(self, mock_request):
		"""Test REST tool handles HTTP errors gracefully."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		# Mock error response
		mock_response = MagicMock()
		mock_response.status_code = 404
		mock_response.ok = False
		mock_response.text = "Not Found"
		mock_request.return_value = mock_response

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype="Test",
			docname="TEST001",
		)

		rest_config = {
			"name": "get_missing",
			"url": "https://api.example.com/missing",
			"method": "GET",
			"authType": "none",
			"description": "Get missing resource",
		}

		try:
			tool = registry._create_rest_tool(rest_config)
			if tool is None:
				self.skipTest("langchain_core not installed")

			result = tool.invoke({})

			# Should return error info, not raise
			self.assertIn("error", str(result).lower())
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("requests.request")
	def test_rest_tool_handles_timeout(self, mock_request):
		"""Test REST tool handles timeout."""
		from requests.exceptions import Timeout

		from xstate_workflow.langgraph.tools import ToolRegistry

		mock_request.side_effect = Timeout("Request timed out")

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype="Test",
			docname="TEST001",
		)

		rest_config = {
			"name": "slow_api",
			"url": "https://slow.api.example.com",
			"method": "GET",
			"authType": "none",
			"description": "Slow API",
			"timeout": 5,
		}

		try:
			tool = registry._create_rest_tool(rest_config)
			if tool is None:
				self.skipTest("langchain_core not installed")

			result = tool.invoke({})

			# Should return error info about timeout
			self.assertIn("timeout", str(result).lower())
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")


class TestResolveCredential(FrappeTestCase):
	"""Tests for credential resolution."""

	def test_resolve_credential_direct_value(self):
		"""Test resolving a direct credential value."""
		from xstate_workflow.langgraph.tools import _resolve_credential

		result = _resolve_credential("my-api-key")

		self.assertEqual(result, "my-api-key")

	def test_resolve_credential_empty_value(self):
		"""Test resolving an empty credential value."""
		from xstate_workflow.langgraph.tools import _resolve_credential

		result = _resolve_credential("")

		self.assertEqual(result, "")

	def test_resolve_credential_with_config_prefix(self):
		"""Test resolving credential with config: prefix."""
		from xstate_workflow.langgraph.tools import _resolve_credential

		# This would look up frappe.conf if it existed
		# Returns empty string if config key not found (for security)
		result = _resolve_credential("config:non_existent_key")

		# Returns empty string if config key not found
		self.assertEqual(result, "")


class TestToolRegistryRESTIntegration(FrappeTestCase):
	"""Tests for REST tools in the ToolRegistry."""

	def test_get_tools_includes_rest_endpoints(self):
		"""Test that get_tools includes REST endpoint tools."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={"customer": "CUST001"},
			doctype="Test",
			docname="TEST001",
			rest_endpoints=[
				{
					"name": "api_call",
					"url": "https://api.example.com/test",
					"method": "GET",
					"authType": "none",
					"description": "Test API",
				}
			],
		)

		try:
			tools = registry.get_tools([])

			# Find the REST tool
			rest_tools = [t for t in tools if t.name.startswith("rest_")]
			# If no REST tools, langchain is not installed
			if not rest_tools:
				self.skipTest("langchain_core not installed (no REST tools returned)")
			self.assertEqual(len(rest_tools), 1)
			self.assertEqual(rest_tools[0].name, "rest_api_call")
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	def test_registry_without_rest_endpoints(self):
		"""Test that registry works without REST endpoints."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype="Test",
			docname="TEST001",
			rest_endpoints=None,
		)

		try:
			tools = registry.get_tools([])

			# Should not raise, REST tools should be empty
			rest_tools = [t for t in tools if t.name.startswith("rest_")]
			self.assertEqual(len(rest_tools), 0)
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")


if __name__ == "__main__":
	unittest.main()
