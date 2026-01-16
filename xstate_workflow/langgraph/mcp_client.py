# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
MCP (Model Context Protocol) Client.

Provides connectivity to MCP servers for tool discovery and execution.
MCP uses JSON-RPC 2.0 over HTTP/WebSocket/stdio.
"""

import base64
import json
import uuid
from typing import Any

import frappe
from frappe import _

from xstate_workflow.langgraph.audit import log_tool_call


class MCPError(Exception):
	"""Base exception for MCP errors."""

	pass


class MCPConnectionError(MCPError):
	"""Error connecting to MCP server."""

	pass


class MCPAuthError(MCPError):
	"""Authentication failed with MCP server."""

	pass


class MCPToolError(MCPError):
	"""Error calling MCP tool."""

	pass


class MCPClient:
	"""
	Client for connecting to MCP (Model Context Protocol) servers.

	MCP is a protocol for exposing tools to AI models. This client implements
	the client side of the protocol for:
	- Discovering available tools from MCP servers
	- Calling tools with parameters
	- Converting MCP tools to LangChain format
	"""

	# Token expiry buffer in seconds - refresh before actual expiry
	TOKEN_EXPIRY_BUFFER = 60

	def __init__(
		self,
		server_url: str,
		transport_type: str = "http",
		auth_config: dict | None = None,
		timeout: int = 30,
		connection_name: str = None,
	):
		"""
		Initialize MCP client.

		Args:
			server_url: MCP server URL or command path (for stdio)
			transport_type: 'http', 'websocket', or 'stdio'
			auth_config: Authentication configuration
			timeout: Request timeout in seconds
			connection_name: Name for logging purposes
		"""
		self.server_url = server_url
		self.transport_type = transport_type
		self.auth_config = auth_config or {}
		self.timeout = timeout
		self.connection_name = connection_name or server_url

		# Cached tools from discovery
		self._tools_cache: list[dict] | None = None

		# OAuth2 token state
		self._access_token: str | None = None
		self._token_expires_at: float | None = None

	def _build_headers(self) -> dict:
		"""Build HTTP headers including authentication."""
		headers = {
			"Content-Type": "application/json",
			"Accept": "application/json",
		}

		auth_type = self.auth_config.get("type", "none")

		if auth_type == "api_key":
			api_key = self.auth_config.get("api_key", "")
			headers["Authorization"] = f"Bearer {api_key}"

		elif auth_type == "basic":
			username = self.auth_config.get("username", "")
			password = self.auth_config.get("password", "")
			credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
			headers["Authorization"] = f"Basic {credentials}"

		elif auth_type == "oauth2":
			# Get or refresh OAuth2 token
			access_token = self._get_oauth_token()
			if access_token:
				headers["Authorization"] = f"Bearer {access_token}"

		return headers

	def _get_oauth_token(self) -> str | None:
		"""
		Get a valid OAuth2 access token, refreshing if necessary.

		Returns:
			Access token string or None if unavailable
		"""
		import time

		oauth_config = self.auth_config.get("oauth", {})

		# Check if we have a cached valid token
		if self._access_token and self._token_expires_at:
			# Refresh if within buffer of expiry
			if time.time() < self._token_expires_at - self.TOKEN_EXPIRY_BUFFER:
				return self._access_token

		# Check if we have a refresh token
		refresh_token = oauth_config.get("refresh_token")

		if refresh_token:
			# Try to refresh
			try:
				self._refresh_oauth_token(oauth_config, refresh_token)
				return self._access_token
			except MCPAuthError as e:
				frappe.log_error(
					title="OAuth Token Refresh Failed",
					message=f"Failed to refresh OAuth token for {self.connection_name}: {e}",
				)
				# Fall through to try existing token

		# Fall back to configured access token if no refresh available
		access_token = oauth_config.get("access_token")
		if access_token:
			self._access_token = access_token
			# Set a default expiry if not known (1 hour)
			if not self._token_expires_at:
				expires_in = oauth_config.get("expires_in", 3600)
				self._token_expires_at = time.time() + expires_in

		return self._access_token

	def _refresh_oauth_token(self, oauth_config: dict, refresh_token: str) -> None:
		"""
		Refresh the OAuth2 access token using the refresh token.

		Args:
			oauth_config: OAuth configuration containing token_url, client_id, etc.
			refresh_token: The refresh token to use

		Raises:
			MCPAuthError: If refresh fails
		"""
		import time

		import requests

		token_url = oauth_config.get("token_url")
		client_id = oauth_config.get("client_id")
		client_secret = oauth_config.get("client_secret")

		if not token_url:
			raise MCPAuthError("No token_url configured for OAuth2 refresh")

		# Build refresh request
		data = {
			"grant_type": "refresh_token",
			"refresh_token": refresh_token,
		}

		if client_id:
			data["client_id"] = client_id
		if client_secret:
			data["client_secret"] = client_secret

		try:
			response = requests.post(
				token_url,
				data=data,
				headers={"Content-Type": "application/x-www-form-urlencoded"},
				timeout=30,
			)

			if response.status_code != 200:
				raise MCPAuthError(f"Token refresh failed with status {response.status_code}: {response.text[:200]}")

			token_data = response.json()

			# Update cached token
			self._access_token = token_data.get("access_token")

			# Calculate expiry time
			expires_in = token_data.get("expires_in", 3600)
			self._token_expires_at = time.time() + expires_in

			# Update refresh token if a new one was issued
			new_refresh_token = token_data.get("refresh_token")
			if new_refresh_token:
				oauth_config["refresh_token"] = new_refresh_token
				# Persist to connection document if we have connection_name
				self._persist_refreshed_token(new_refresh_token, token_data)

			frappe.log_error(
				title="OAuth Token Refreshed",
				message=f"Successfully refreshed OAuth token for {self.connection_name}",
			)

		except requests.exceptions.RequestException as e:
			raise MCPAuthError(f"Token refresh request failed: {e}")

	def _persist_refreshed_token(self, refresh_token: str, token_data: dict) -> None:
		"""
		Persist refreshed token data to the MCP Server Connection document.

		Args:
			refresh_token: New refresh token
			token_data: Full token response data
		"""
		if not self.connection_name:
			return

		try:
			# Use cache key to store token data (Redis-backed for distributed)
			cache_key = f"mcp_oauth_token:{self.connection_name}"
			frappe.cache.set_value(
				cache_key,
				{
					"access_token": token_data.get("access_token"),
					"refresh_token": refresh_token,
					"expires_in": token_data.get("expires_in", 3600),
					"refreshed_at": frappe.utils.now(),
				},
				expires_in_sec=token_data.get("expires_in", 3600) + 3600,  # Cache longer than token life
			)
		except Exception as e:
			# Log but don't fail - token refresh was still successful
			frappe.log_error(
				title="Token Cache Update Failed",
				message=f"Failed to cache refreshed token for {self.connection_name}: {e}",
			)

	def _make_jsonrpc_request(self, method: str, params: dict | None = None) -> dict:
		"""
		Make a JSON-RPC 2.0 request to the MCP server.

		Args:
			method: JSON-RPC method name
			params: Method parameters

		Returns:
			JSON-RPC result

		Raises:
			MCPConnectionError: If server is unreachable
			MCPAuthError: If authentication fails
			MCPError: For other errors
		"""
		import requests
		from requests.exceptions import ConnectionError, Timeout

		request_id = str(uuid.uuid4())

		payload = {
			"jsonrpc": "2.0",
			"method": method,
			"id": request_id,
		}
		if params:
			payload["params"] = params

		try:
			response = requests.post(
				self.server_url,
				json=payload,
				headers=self._build_headers(),
				timeout=self.timeout,
			)

			if response.status_code == 401:
				raise MCPAuthError(f"Authentication failed for MCP server: {self.connection_name}")

			if response.status_code == 403:
				raise MCPAuthError(f"Access forbidden for MCP server: {self.connection_name}")

			if response.status_code >= 500:
				raise MCPConnectionError(f"MCP server error ({response.status_code}): {response.text[:200]}")

			response.raise_for_status()

			result = response.json()

			# Check for JSON-RPC error
			if "error" in result:
				error = result["error"]
				error_msg = error.get("message", "Unknown error")
				error_code = error.get("code", -1)
				raise MCPError(f"MCP error ({error_code}): {error_msg}")

			return result.get("result", {})

		except ConnectionError as e:
			raise MCPConnectionError(f"Cannot connect to MCP server {self.connection_name}: {e}")

		except Timeout:
			raise MCPConnectionError(f"Timeout connecting to MCP server {self.connection_name} (timeout: {self.timeout}s)")

		except requests.exceptions.RequestException as e:
			raise MCPError(f"Request failed for MCP server {self.connection_name}: {e}")

	def list_tools_sync(self) -> list[dict]:
		"""
		Discover available tools from the MCP server (synchronous).

		Returns:
			List of tool definitions with name, description, and parameters

		Raises:
			MCPConnectionError: If server is unreachable
		"""
		if self.transport_type == "http":
			return self._list_tools_http()
		elif self.transport_type == "websocket":
			return self._list_tools_websocket()
		elif self.transport_type == "stdio":
			return self._list_tools_stdio()
		else:
			raise MCPError(f"Unsupported transport type: {self.transport_type}")

	def _list_tools_http(self) -> list[dict]:
		"""List tools via HTTP transport."""
		result = self._make_jsonrpc_request("tools/list")
		tools = result.get("tools", [])

		# Validate and filter malformed tools
		valid_tools = []
		for tool in tools:
			if self._validate_tool_definition(tool):
				valid_tools.append(tool)
			else:
				frappe.log_error(
					title="MCP Tool Validation Warning",
					message=f"Skipping malformed tool from {self.connection_name}: {json.dumps(tool)[:200]}",
				)

		self._tools_cache = valid_tools
		return valid_tools

	def _list_tools_websocket(self) -> list[dict]:
		"""List tools via WebSocket transport."""
		try:
			import websocket

			ws = websocket.create_connection(self.server_url, timeout=self.timeout)

			request_id = str(uuid.uuid4())
			payload = {
				"jsonrpc": "2.0",
				"method": "tools/list",
				"id": request_id,
			}

			ws.send(json.dumps(payload))
			response = json.loads(ws.recv())
			ws.close()

			if "error" in response:
				error = response["error"]
				raise MCPError(f"MCP error: {error.get('message', 'Unknown error')}")

			tools = response.get("result", {}).get("tools", [])

			# Validate tools
			valid_tools = [t for t in tools if self._validate_tool_definition(t)]
			self._tools_cache = valid_tools
			return valid_tools

		except ImportError:
			raise MCPError("websocket-client not installed. Run: pip install websocket-client")

		except Exception as e:
			raise MCPConnectionError(f"WebSocket error for {self.connection_name}: {e}")

	def _list_tools_stdio(self) -> list[dict]:
		"""List tools via stdio transport (subprocess)."""
		import subprocess

		try:
			# For stdio, server_url is the command to run
			process = subprocess.Popen(
				self.server_url.split(),
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				text=True,
			)

			request_id = str(uuid.uuid4())
			payload = {
				"jsonrpc": "2.0",
				"method": "tools/list",
				"id": request_id,
			}

			stdout, stderr = process.communicate(input=json.dumps(payload) + "\n", timeout=self.timeout)

			if process.returncode != 0:
				raise MCPError(f"stdio process error: {stderr}")

			response = json.loads(stdout)

			if "error" in response:
				error = response["error"]
				raise MCPError(f"MCP error: {error.get('message', 'Unknown error')}")

			tools = response.get("result", {}).get("tools", [])

			# Validate tools
			valid_tools = [t for t in tools if self._validate_tool_definition(t)]
			self._tools_cache = valid_tools
			return valid_tools

		except subprocess.TimeoutExpired:
			raise MCPConnectionError(f"Timeout waiting for stdio MCP server: {self.connection_name}")

		except FileNotFoundError:
			raise MCPConnectionError(f"MCP command not found: {self.server_url}")

		except Exception as e:
			raise MCPConnectionError(f"stdio error for {self.connection_name}: {e}")

	def _validate_tool_definition(self, tool: dict) -> bool:
		"""
		Validate a tool definition is well-formed.

		Args:
			tool: Tool definition from MCP server

		Returns:
			True if valid, False otherwise
		"""
		# Must have a name
		if not tool.get("name"):
			return False

		# Name must be a string
		if not isinstance(tool["name"], str):
			return False

		# Description should be a string if present
		if "description" in tool and not isinstance(tool.get("description", ""), str):
			return False

		# Input schema should be a dict if present
		if "inputSchema" in tool and not isinstance(tool.get("inputSchema"), dict):
			return False

		return True

	def call_tool_sync(self, tool_name: str, params: dict | None = None) -> Any:
		"""
		Call a tool on the MCP server (synchronous).

		Args:
			tool_name: Name of the tool to call
			params: Tool parameters

		Returns:
			Tool execution result

		Raises:
			MCPToolError: If tool call fails
		"""
		if self.transport_type == "http":
			return self._call_tool_http(tool_name, params)
		elif self.transport_type == "websocket":
			return self._call_tool_websocket(tool_name, params)
		elif self.transport_type == "stdio":
			return self._call_tool_stdio(tool_name, params)
		else:
			raise MCPError(f"Unsupported transport type: {self.transport_type}")

	def _call_tool_http(self, tool_name: str, params: dict | None = None) -> Any:
		"""Call tool via HTTP transport."""
		result = self._make_jsonrpc_request(
			"tools/call",
			{
				"name": tool_name,
				"arguments": params or {},
			},
		)
		return result

	def _call_tool_websocket(self, tool_name: str, params: dict | None = None) -> Any:
		"""Call tool via WebSocket transport."""
		try:
			import websocket

			ws = websocket.create_connection(self.server_url, timeout=self.timeout)

			request_id = str(uuid.uuid4())
			payload = {
				"jsonrpc": "2.0",
				"method": "tools/call",
				"params": {
					"name": tool_name,
					"arguments": params or {},
				},
				"id": request_id,
			}

			ws.send(json.dumps(payload))
			response = json.loads(ws.recv())
			ws.close()

			if "error" in response:
				error = response["error"]
				raise MCPToolError(f"Tool {tool_name} error: {error.get('message', 'Unknown error')}")

			return response.get("result", {})

		except ImportError:
			raise MCPError("websocket-client not installed. Run: pip install websocket-client")

	def _call_tool_stdio(self, tool_name: str, params: dict | None = None) -> Any:
		"""Call tool via stdio transport."""
		import subprocess

		try:
			process = subprocess.Popen(
				self.server_url.split(),
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				text=True,
			)

			request_id = str(uuid.uuid4())
			payload = {
				"jsonrpc": "2.0",
				"method": "tools/call",
				"params": {
					"name": tool_name,
					"arguments": params or {},
				},
				"id": request_id,
			}

			stdout, stderr = process.communicate(input=json.dumps(payload) + "\n", timeout=self.timeout)

			if process.returncode != 0:
				raise MCPToolError(f"Tool {tool_name} error: {stderr}")

			response = json.loads(stdout)

			if "error" in response:
				error = response["error"]
				raise MCPToolError(f"Tool {tool_name} error: {error.get('message', 'Unknown error')}")

			return response.get("result", {})

		except subprocess.TimeoutExpired:
			raise MCPToolError(f"Timeout calling tool {tool_name}")

	def create_langchain_tools(self, doctype: str = None, docname: str = None) -> list:
		"""
		Convert MCP tools to LangChain tool format.

		Args:
			doctype: DocType for audit logging
			docname: Document name for audit logging

		Returns:
			List of LangChain tool instances
		"""
		try:
			from langchain_core.tools import StructuredTool
		except ImportError:
			frappe.throw(_("langchain_core is not installed. Run: pip install langchain-core"))

		# Ensure tools are discovered
		if self._tools_cache is None:
			try:
				self.list_tools_sync()
			except MCPError as e:
				frappe.log_error(
					title="MCP Tool Discovery Failed",
					message=f"Failed to discover tools from {self.connection_name}: {e}",
				)
				return []

		langchain_tools = []

		for mcp_tool in self._tools_cache or []:
			tool_name = mcp_tool.get("name")
			description = mcp_tool.get("description", f"MCP tool: {tool_name}")
			input_schema = mcp_tool.get("inputSchema", {})

			# Create wrapper function for this tool
			lc_tool = self._create_tool_wrapper(
				tool_name=tool_name,
				description=description,
				input_schema=input_schema,
				doctype=doctype,
				docname=docname,
			)

			if lc_tool:
				langchain_tools.append(lc_tool)

		return langchain_tools

	def _create_tool_wrapper(
		self,
		tool_name: str,
		description: str,
		input_schema: dict,
		doctype: str = None,
		docname: str = None,
	):
		"""
		Create a LangChain tool wrapper for an MCP tool.

		Args:
			tool_name: MCP tool name
			description: Tool description
			input_schema: JSON Schema for tool input
			doctype: DocType for audit logging
			docname: Document name for audit logging

		Returns:
			LangChain StructuredTool or None if creation fails
		"""
		try:
			from langchain_core.tools import StructuredTool
			from pydantic import create_model
			from pydantic.fields import FieldInfo
		except ImportError:
			return None

		# Capture for closure
		mcp_client = self
		connection_name = self.connection_name

		# Build Pydantic model from JSON schema
		field_definitions = {}
		properties = input_schema.get("properties", {})
		required = set(input_schema.get("required", []))

		for prop_name, prop_schema in properties.items():
			# Map JSON schema types to Python types
			json_type = prop_schema.get("type", "string")
			python_type = {
				"string": str,
				"integer": int,
				"number": float,
				"boolean": bool,
				"array": list,
				"object": dict,
			}.get(json_type, str)

			# Set default for optional fields
			if prop_name in required:
				field_definitions[prop_name] = (python_type, FieldInfo(description=prop_schema.get("description", "")))
			else:
				field_definitions[prop_name] = (
					python_type | None,
					FieldInfo(default=None, description=prop_schema.get("description", "")),
				)

		# Create args schema if there are properties
		args_schema = None
		if field_definitions:
			try:
				args_schema = create_model(f"{tool_name}Input", **field_definitions)
			except Exception as e:
				frappe.log_error(
					title="MCP Tool Schema Error",
					message=f"Failed to create schema for {tool_name}: {e}",
				)

		def tool_func(**kwargs) -> Any:
			"""Execute MCP tool."""
			import time

			start_time = time.time()

			try:
				result = mcp_client.call_tool_sync(tool_name, kwargs)
				duration_ms = (time.time() - start_time) * 1000

				# Log successful call
				log_tool_call(
					tool_name=f"mcp:{connection_name}:{tool_name}",
					doctype=doctype,
					docname=docname,
					args=kwargs,
					result=str(result)[:500] if result else None,
					duration_ms=duration_ms,
					success=True,
				)

				return result

			except MCPError as e:
				duration_ms = (time.time() - start_time) * 1000

				# Log failed call
				log_tool_call(
					tool_name=f"mcp:{connection_name}:{tool_name}",
					doctype=doctype,
					docname=docname,
					args=kwargs,
					success=False,
					error=str(e),
					duration_ms=duration_ms,
				)

				return {"error": str(e)}

		# Prefix tool name with connection to avoid conflicts
		prefixed_name = f"mcp_{tool_name}"

		return StructuredTool.from_function(
			func=tool_func,
			name=prefixed_name,
			description=f"[MCP: {connection_name}] {description}",
			args_schema=args_schema,
		)


def get_mcp_client_for_connection(connection_name: str) -> MCPClient | None:
	"""
	Get an MCP client for a named connection.

	Args:
		connection_name: Name of the MCP Server Connection document

	Returns:
		MCPClient instance or None if not found/inactive
	"""
	try:
		conn_doc = frappe.get_doc("MCP Server Connection", connection_name)

		if not conn_doc.is_active:
			frappe.log_error(
				title="MCP Connection Inactive",
				message=f"MCP connection '{connection_name}' is not active",
			)
			return None

		return MCPClient(
			server_url=conn_doc.server_url,
			transport_type=conn_doc.transport_type,
			auth_config=conn_doc.get_auth_config(),
			timeout=conn_doc.timeout_seconds or 30,
			connection_name=connection_name,
		)

	except frappe.DoesNotExistError:
		frappe.log_error(
			title="MCP Connection Not Found",
			message=f"MCP connection '{connection_name}' does not exist",
		)
		return None


def get_tools_from_mcps(
	enabled_mcps: list[dict],
	doctype: str = None,
	docname: str = None,
	user: str = None,
) -> list:
	"""
	Get LangChain tools from multiple MCP connections.

	Args:
		enabled_mcps: List of MCP configurations [{"connection_name": "...", "enabled": True}]
		doctype: DocType for audit logging
		docname: Document name for audit logging
		user: User to check access for (defaults to current user)

	Returns:
		List of LangChain tools from all enabled MCPs
	"""
	tools = []

	for mcp_config in enabled_mcps or []:
		if not mcp_config.get("enabled", True):
			continue

		connection_name = mcp_config.get("connection_name") or mcp_config.get("connectionName")
		if not connection_name:
			continue

		# Check user access
		try:
			conn_doc = frappe.get_doc("MCP Server Connection", connection_name)
			if not conn_doc.can_user_access(user):
				frappe.log_error(
					title="MCP Access Denied",
					message=f"User {user or frappe.session.user} cannot access MCP '{connection_name}'",
				)
				continue
		except frappe.DoesNotExistError:
			continue

		# Get client and tools
		client = get_mcp_client_for_connection(connection_name)
		if client:
			try:
				mcp_tools = client.create_langchain_tools(doctype=doctype, docname=docname)
				tools.extend(mcp_tools)
			except Exception as e:
				# Log but don't fail - agent should continue with other tools
				frappe.log_error(
					title="MCP Tool Discovery Error",
					message=f"Failed to get tools from {connection_name}: {e}",
				)

	return tools
