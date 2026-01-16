# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document


class MCPServerConnection(Document):
	"""MCP Server Connection - stores configuration for connecting to MCP servers."""

	def validate(self):
		self.validate_server_url()
		self.validate_auth_config()
		self.validate_oauth_config()
		self.validate_timeout()

	def validate_server_url(self):
		"""Validate server URL format."""
		if not self.server_url:
			return

		url = self.server_url.strip()

		# For HTTP transport, validate URL format
		if self.transport_type == "http":
			if not (url.startswith("http://") or url.startswith("https://")):
				frappe.throw(_("Server URL must start with http:// or https:// for HTTP transport"))

		# For stdio, it should be a command path
		elif self.transport_type == "stdio":
			if url.startswith("http"):
				frappe.throw(_("Server URL for stdio transport should be a command path, not HTTP URL"))

		# For websocket, validate URL format
		elif self.transport_type == "websocket":
			if not (url.startswith("ws://") or url.startswith("wss://")):
				frappe.throw(_("Server URL must start with ws:// or wss:// for WebSocket transport"))

	def validate_auth_config(self):
		"""Validate authentication configuration."""
		if self.auth_type == "api_key" and not self.api_key:
			frappe.throw(_("API Key is required when auth type is 'api_key'"))

		if self.auth_type == "basic":
			if not self.basic_auth_username:
				frappe.throw(_("Username is required for basic authentication"))
			if not self.basic_auth_password:
				frappe.throw(_("Password is required for basic authentication"))

	def validate_oauth_config(self):
		"""Validate OAuth2 configuration if selected."""
		if self.auth_type != "oauth2":
			return

		if not self.oauth_config:
			frappe.throw(_("OAuth configuration is required when auth type is 'oauth2'"))

		try:
			config = json.loads(self.oauth_config)

			required_fields = ["client_id", "client_secret", "token_url"]
			for field in required_fields:
				if not config.get(field):
					frappe.throw(_("OAuth config missing required field: {0}").format(field))

		except json.JSONDecodeError as e:
			frappe.throw(_("Invalid JSON in OAuth config: {0}").format(str(e)))

	def validate_timeout(self):
		"""Validate timeout value."""
		if self.timeout_seconds and self.timeout_seconds < 1:
			frappe.throw(_("Timeout must be at least 1 second"))

		if self.timeout_seconds and self.timeout_seconds > 300:
			frappe.msgprint(
				_("Timeout of {0} seconds is quite long. Consider a shorter timeout.").format(
					self.timeout_seconds
				),
				indicator="orange",
			)

	def get_auth_config(self) -> dict:
		"""Get authentication configuration as a dictionary.

		Returns:
			dict: Authentication config with type and credentials
		"""
		config = {"type": self.auth_type}

		if self.auth_type == "api_key":
			config["api_key"] = self.get_password("api_key")

		elif self.auth_type == "basic":
			config["username"] = self.basic_auth_username
			config["password"] = self.get_password("basic_auth_password")

		elif self.auth_type == "oauth2":
			oauth_config = json.loads(self.oauth_config or "{}")
			# Get client_secret from password field if stored there
			if "client_secret" in oauth_config and oauth_config["client_secret"].startswith("*"):
				oauth_config["client_secret"] = self.get_password("oauth_client_secret")
			config["oauth"] = oauth_config

		return config

	def can_user_access(self, user: str = None) -> bool:
		"""Check if a user can access this MCP connection.

		Args:
			user: Username to check. Defaults to current user.

		Returns:
			bool: True if user can access, False otherwise
		"""
		if not user:
			user = frappe.session.user

		# System Manager can access everything
		if "System Manager" in frappe.get_roles(user):
			return True

		# If no roles configured, allow all
		if not self.allowed_roles:
			return True

		# Check if user has any of the allowed roles
		user_roles = set(frappe.get_roles(user))
		allowed = {r.role for r in self.allowed_roles}

		return bool(user_roles & allowed)

	@frappe.whitelist()
	def test_connection(self):
		"""Test the MCP server connection.

		Returns:
			dict: Test results with success status and discovered tools
		"""
		from xstate_workflow.langgraph.mcp_client import MCPClient

		try:
			client = MCPClient(
				server_url=self.server_url,
				transport_type=self.transport_type,
				auth_config=self.get_auth_config(),
				timeout=self.timeout_seconds or 30,
			)

			# Try to list tools
			tools = client.list_tools_sync()

			# Update status
			self.last_tested_at = frappe.utils.now()
			self.last_test_result = "Success"
			self.tools_discovered = len(tools)
			self.save()

			return {
				"success": True,
				"tools_count": len(tools),
				"tools": [{"name": t.get("name"), "description": t.get("description", "")} for t in tools],
			}

		except Exception as e:
			self.last_tested_at = frappe.utils.now()
			self.last_test_result = "Failed"
			self.save()

			return {"success": False, "error": str(e)}


def get_active_connections(user: str = None) -> list:
	"""Get all active MCP connections accessible by a user.

	Args:
		user: Username to check access for. Defaults to current user.

	Returns:
		list: List of MCP Server Connection documents
	"""
	if not user:
		user = frappe.session.user

	connections = frappe.get_all(
		"MCP Server Connection", filters={"is_active": 1}, fields=["name", "connection_name", "description"]
	)

	accessible = []
	for conn in connections:
		doc = frappe.get_doc("MCP Server Connection", conn.name)
		if doc.can_user_access(user):
			accessible.append(
				{
					"name": doc.name,
					"connection_name": doc.connection_name,
					"description": doc.description,
					"tools_discovered": doc.tools_discovered or 0,
				}
			)

	return accessible
