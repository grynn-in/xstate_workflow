# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Tests for MCP (Model Context Protocol) Client.

Tests the MCP client functionality including:
- Tool discovery from MCP servers
- Tool execution
- Error handling for unreachable servers, auth failures, timeouts
- LangChain tool conversion
"""

import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestMCPClient(FrappeTestCase):
	"""Tests for the MCP client."""

	def test_build_headers_no_auth(self):
		"""Test header building with no authentication."""
		from xstate_workflow.langgraph.mcp_client import MCPClient

		client = MCPClient(
			server_url="http://localhost:8080",
			auth_config={"type": "none"},
		)

		headers = client._build_headers()

		self.assertEqual(headers["Content-Type"], "application/json")
		self.assertNotIn("Authorization", headers)

	def test_build_headers_api_key_auth(self):
		"""Test header building with API key authentication."""
		from xstate_workflow.langgraph.mcp_client import MCPClient

		client = MCPClient(
			server_url="http://localhost:8080",
			auth_config={"type": "api_key", "api_key": "test-key-123"},
		)

		headers = client._build_headers()

		self.assertIn("Authorization", headers)
		self.assertEqual(headers["Authorization"], "Bearer test-key-123")

	def test_build_headers_basic_auth(self):
		"""Test header building with basic authentication."""
		import base64

		from xstate_workflow.langgraph.mcp_client import MCPClient

		client = MCPClient(
			server_url="http://localhost:8080",
			auth_config={"type": "basic", "username": "user", "password": "pass"},
		)

		headers = client._build_headers()

		self.assertIn("Authorization", headers)
		expected = base64.b64encode(b"user:pass").decode()
		self.assertEqual(headers["Authorization"], f"Basic {expected}")

	def test_validate_tool_definition_valid(self):
		"""Test that valid tool definitions pass validation."""
		from xstate_workflow.langgraph.mcp_client import MCPClient

		client = MCPClient(server_url="http://localhost:8080")

		valid_tool = {
			"name": "get_customer",
			"description": "Get customer details",
			"inputSchema": {
				"type": "object",
				"properties": {
					"customer_id": {"type": "string"},
				},
			},
		}

		self.assertTrue(client._validate_tool_definition(valid_tool))

	def test_validate_tool_definition_missing_name(self):
		"""Test that tools without name fail validation."""
		from xstate_workflow.langgraph.mcp_client import MCPClient

		client = MCPClient(server_url="http://localhost:8080")

		invalid_tool = {
			"description": "Some tool",
		}

		self.assertFalse(client._validate_tool_definition(invalid_tool))

	def test_validate_tool_definition_invalid_name_type(self):
		"""Test that tools with non-string name fail validation."""
		from xstate_workflow.langgraph.mcp_client import MCPClient

		client = MCPClient(server_url="http://localhost:8080")

		invalid_tool = {
			"name": 123,  # Should be string
			"description": "Some tool",
		}

		self.assertFalse(client._validate_tool_definition(invalid_tool))

	def test_validate_tool_definition_invalid_schema_type(self):
		"""Test that tools with non-dict inputSchema fail validation."""
		from xstate_workflow.langgraph.mcp_client import MCPClient

		client = MCPClient(server_url="http://localhost:8080")

		invalid_tool = {
			"name": "some_tool",
			"inputSchema": "not a dict",
		}

		self.assertFalse(client._validate_tool_definition(invalid_tool))

	@patch("requests.post")
	def test_list_tools_http_success(self, mock_post):
		"""Test successful tool listing via HTTP."""
		from xstate_workflow.langgraph.mcp_client import MCPClient

		# Mock successful response
		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {
			"jsonrpc": "2.0",
			"result": {
				"tools": [
					{"name": "tool_a", "description": "Tool A"},
					{"name": "tool_b", "description": "Tool B"},
				]
			},
			"id": "test-id",
		}
		mock_post.return_value = mock_response

		client = MCPClient(server_url="http://localhost:8080")
		tools = client.list_tools_sync()

		self.assertEqual(len(tools), 2)
		self.assertEqual(tools[0]["name"], "tool_a")
		self.assertEqual(tools[1]["name"], "tool_b")

	@patch("requests.post")
	def test_list_tools_http_skips_malformed(self, mock_post):
		"""Test that malformed tools are skipped."""
		from xstate_workflow.langgraph.mcp_client import MCPClient

		# Mock response with malformed tools
		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {
			"jsonrpc": "2.0",
			"result": {
				"tools": [
					{"name": "valid_tool"},
					{"description": "missing name"},  # Invalid - no name
					{"name": 123},  # Invalid - wrong type
					{"name": "another_valid"},
				]
			},
			"id": "test-id",
		}
		mock_post.return_value = mock_response

		client = MCPClient(server_url="http://localhost:8080")
		tools = client.list_tools_sync()

		# Only valid tools should be returned
		self.assertEqual(len(tools), 2)
		valid_names = [t["name"] for t in tools]
		self.assertIn("valid_tool", valid_names)
		self.assertIn("another_valid", valid_names)

	@patch("requests.post")
	def test_list_tools_http_connection_error(self, mock_post):
		"""Test connection error handling."""
		from requests.exceptions import ConnectionError

		from xstate_workflow.langgraph.mcp_client import MCPClient, MCPConnectionError

		mock_post.side_effect = ConnectionError("Connection refused")

		client = MCPClient(server_url="http://localhost:8080")

		with self.assertRaises(MCPConnectionError):
			client.list_tools_sync()

	@patch("requests.post")
	def test_list_tools_http_timeout(self, mock_post):
		"""Test timeout error handling."""
		from requests.exceptions import Timeout

		from xstate_workflow.langgraph.mcp_client import MCPClient, MCPConnectionError

		mock_post.side_effect = Timeout("Request timed out")

		client = MCPClient(server_url="http://localhost:8080", timeout=5)

		with self.assertRaises(MCPConnectionError) as ctx:
			client.list_tools_sync()

		self.assertIn("Timeout", str(ctx.exception))

	@patch("requests.post")
	def test_list_tools_http_auth_failure(self, mock_post):
		"""Test authentication failure handling."""
		from xstate_workflow.langgraph.mcp_client import MCPAuthError, MCPClient

		mock_response = MagicMock()
		mock_response.status_code = 401
		mock_post.return_value = mock_response

		client = MCPClient(
			server_url="http://localhost:8080",
			auth_config={"type": "api_key", "api_key": "wrong-key"},
		)

		with self.assertRaises(MCPAuthError):
			client.list_tools_sync()

	@patch("requests.post")
	def test_list_tools_http_forbidden(self, mock_post):
		"""Test 403 forbidden handling."""
		from xstate_workflow.langgraph.mcp_client import MCPAuthError, MCPClient

		mock_response = MagicMock()
		mock_response.status_code = 403
		mock_post.return_value = mock_response

		client = MCPClient(server_url="http://localhost:8080")

		with self.assertRaises(MCPAuthError):
			client.list_tools_sync()

	@patch("requests.post")
	def test_call_tool_http_success(self, mock_post):
		"""Test successful tool execution via HTTP."""
		from xstate_workflow.langgraph.mcp_client import MCPClient

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {
			"jsonrpc": "2.0",
			"result": {"customer_name": "Acme Corp", "balance": 1000},
			"id": "test-id",
		}
		mock_post.return_value = mock_response

		client = MCPClient(server_url="http://localhost:8080")
		result = client.call_tool_sync("get_customer", {"customer_id": "CUST001"})

		self.assertEqual(result["customer_name"], "Acme Corp")
		self.assertEqual(result["balance"], 1000)

	@patch("requests.post")
	def test_call_tool_http_error_response(self, mock_post):
		"""Test tool call with JSON-RPC error."""
		from xstate_workflow.langgraph.mcp_client import MCPClient, MCPError

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {
			"jsonrpc": "2.0",
			"error": {
				"code": -32602,
				"message": "Invalid params: customer_id is required",
			},
			"id": "test-id",
		}
		mock_post.return_value = mock_response

		client = MCPClient(server_url="http://localhost:8080")

		with self.assertRaises(MCPError) as ctx:
			client.call_tool_sync("get_customer", {})

		self.assertIn("Invalid params", str(ctx.exception))

	def test_unsupported_transport_type(self):
		"""Test that unsupported transport types raise error."""
		from xstate_workflow.langgraph.mcp_client import MCPClient, MCPError

		client = MCPClient(
			server_url="http://localhost:8080",
			transport_type="unsupported",
		)

		with self.assertRaises(MCPError) as ctx:
			client.list_tools_sync()

		self.assertIn("Unsupported transport", str(ctx.exception))


class TestMCPClientLangChainConversion(FrappeTestCase):
	"""Tests for converting MCP tools to LangChain format."""

	@patch("requests.post")
	def test_create_langchain_tools_basic(self, mock_post):
		"""Test basic LangChain tool creation."""
		from xstate_workflow.langgraph.mcp_client import MCPClient

		# Mock tool discovery
		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {
			"jsonrpc": "2.0",
			"result": {
				"tools": [
					{
						"name": "simple_tool",
						"description": "A simple tool",
						"inputSchema": {
							"type": "object",
							"properties": {},
						},
					}
				]
			},
			"id": "test-id",
		}
		mock_post.return_value = mock_response

		client = MCPClient(
			server_url="http://localhost:8080",
			connection_name="test_mcp",
		)

		# This requires langchain_core - skip if not installed
		try:
			tools = client.create_langchain_tools(doctype="Test", docname="TEST001")

			self.assertEqual(len(tools), 1)
			self.assertEqual(tools[0].name, "mcp_simple_tool")
			self.assertIn("test_mcp", tools[0].description)
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("requests.post")
	def test_create_langchain_tools_with_schema(self, mock_post):
		"""Test LangChain tool creation with input schema."""
		from xstate_workflow.langgraph.mcp_client import MCPClient

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {
			"jsonrpc": "2.0",
			"result": {
				"tools": [
					{
						"name": "get_order",
						"description": "Get order details",
						"inputSchema": {
							"type": "object",
							"properties": {
								"order_id": {
									"type": "string",
									"description": "Order ID",
								},
								"include_items": {
									"type": "boolean",
									"description": "Include line items",
								},
							},
							"required": ["order_id"],
						},
					}
				]
			},
			"id": "test-id",
		}
		mock_post.return_value = mock_response

		client = MCPClient(
			server_url="http://localhost:8080",
			connection_name="test_mcp",
		)

		try:
			tools = client.create_langchain_tools()

			self.assertEqual(len(tools), 1)
			# Tool should have schema
			self.assertIsNotNone(tools[0].args_schema)
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")


class TestMCPHelperFunctions(FrappeTestCase):
	"""Tests for MCP helper functions."""

	@classmethod
	def setUpClass(cls):
		"""Check if MCP Server Connection DocType exists."""
		super().setUpClass()
		cls.doctype_exists = frappe.db.exists("DocType", "MCP Server Connection")

	def setUp(self):
		"""Set up test fixtures."""
		self.created_connection = False

		# Skip DocType-dependent setup if DocType doesn't exist
		if not self.doctype_exists:
			return

		# Create a test MCP connection if it doesn't exist
		if not frappe.db.exists("MCP Server Connection", "Test MCP"):
			try:
				doc = frappe.get_doc(
					{
						"doctype": "MCP Server Connection",
						"connection_name": "Test MCP",
						"server_url": "http://localhost:8080/mcp",
						"transport_type": "http",
						"auth_type": "none",
						"is_active": 1,
						"timeout_seconds": 30,
					}
				)
				doc.insert(ignore_permissions=True)
				frappe.db.commit()
				self.created_connection = True
			except Exception:
				self.created_connection = False

	def tearDown(self):
		"""Clean up test fixtures."""
		if not self.doctype_exists:
			return

		if self.created_connection and frappe.db.exists("MCP Server Connection", "Test MCP"):
			frappe.delete_doc("MCP Server Connection", "Test MCP", force=True)
			frappe.db.commit()

	def test_get_mcp_client_for_connection_not_found(self):
		"""Test getting client for non-existent connection."""
		if not self.doctype_exists:
			self.skipTest("MCP Server Connection DocType not installed (run migrate)")

		from xstate_workflow.langgraph.mcp_client import get_mcp_client_for_connection

		client = get_mcp_client_for_connection("Non Existent Connection")

		self.assertIsNone(client)

	def test_get_mcp_client_for_connection_success(self):
		"""Test getting client for valid connection."""
		if not self.doctype_exists:
			self.skipTest("MCP Server Connection DocType not installed (run migrate)")

		from xstate_workflow.langgraph.mcp_client import get_mcp_client_for_connection

		if not frappe.db.exists("MCP Server Connection", "Test MCP"):
			self.skipTest("Test MCP connection not created")

		client = get_mcp_client_for_connection("Test MCP")

		self.assertIsNotNone(client)
		self.assertEqual(client.server_url, "http://localhost:8080/mcp")
		self.assertEqual(client.transport_type, "http")

	def test_get_tools_from_mcps_empty_list(self):
		"""Test getting tools with empty MCP list."""
		from xstate_workflow.langgraph.mcp_client import get_tools_from_mcps

		tools = get_tools_from_mcps([])

		self.assertEqual(tools, [])

	def test_get_tools_from_mcps_skips_disabled(self):
		"""Test that disabled MCPs are skipped."""
		if not self.doctype_exists:
			self.skipTest("MCP Server Connection DocType not installed (run migrate)")

		from xstate_workflow.langgraph.mcp_client import get_tools_from_mcps

		enabled_mcps = [
			{"connectionName": "Test MCP", "enabled": False},
		]

		tools = get_tools_from_mcps(enabled_mcps)

		self.assertEqual(tools, [])


if __name__ == "__main__":
	unittest.main()
