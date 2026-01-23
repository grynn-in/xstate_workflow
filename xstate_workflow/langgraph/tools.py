# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
LangGraph Tool Registry.

Provides tools for AI agents with proper security controls,
including whitelisted method verification and role-based access.
"""

import re
import signal
from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _

from xstate_workflow.langgraph.audit import RateLimiter, log_tool_call


# Dangerous patterns for code validation
DANGEROUS_CODE_PATTERNS = [
	# File system operations
	r"\bopen\s*\(",
	r"\bfile\s*\(",
	r"\bos\.(?:remove|unlink|rmdir|makedirs|mkdir|rename|chmod|chown)",
	r"\bshutil\.",
	r"\bpathlib\.",
	# Process/system operations
	r"\bos\.(?:system|popen|exec|spawn|fork)",
	r"\bsubprocess\.",
	r"\bcommands\.",
	# Network operations
	r"\bsocket\.",
	r"\burllib\.",
	r"\brequests\.",
	r"\bhttplib\.",
	r"\bhttp\.client\.",
	# Code execution
	r"\bexec\s*\(",
	r"\beval\s*\(",
	r"\bcompile\s*\(",
	r"\b__import__\s*\(",
	r"\bimportlib\.",
	# Dangerous attributes
	r"\b__(?:class|bases|subclasses|mro|globals|locals|builtins|code|getattribute)__",
	# Frappe database direct access
	r"\bfrappe\.db\.sql\s*\(",
	r"\bfrappe\.db\.commit\s*\(",
	r"\bfrappe\.db\.rollback\s*\(",
	# Module imports that could be dangerous
	r"\bimport\s+(?:os|sys|subprocess|socket|ctypes|pickle)",
	r"\bfrom\s+(?:os|sys|subprocess|socket|ctypes|pickle)\s+import",
]


def validate_code(code: str) -> tuple[bool, str | None]:
	"""
	Validate code for dangerous patterns before execution.

	Args:
		code: Python code to validate

	Returns:
		Tuple of (is_safe, error_message)
	"""
	for pattern in DANGEROUS_CODE_PATTERNS:
		if re.search(pattern, code, re.IGNORECASE):
			return (False, f"Code contains potentially dangerous pattern: {pattern}")

	return (True, None)


@contextmanager
def timeout_handler(seconds: int):
	"""
	Context manager for code execution timeout.

	Args:
		seconds: Maximum execution time in seconds
	"""
	def signal_handler(signum, frame):
		raise TimeoutError(f"Code execution timed out after {seconds} seconds")

	# Only use signal on Unix systems
	try:
		old_handler = signal.signal(signal.SIGALRM, signal_handler)
		signal.alarm(seconds)
		try:
			yield
		finally:
			signal.alarm(0)
			signal.signal(signal.SIGALRM, old_handler)
	except (ValueError, AttributeError):
		# signal.SIGALRM not available (Windows), just yield without timeout
		yield


class ToolRegistry:
	"""
	Registry of available tools with role-based access control.

	This class manages the creation of LangChain tools for use by AI agents,
	ensuring proper security through:
	- Frappe permission system integration
	- Whitelisted method verification
	- Role-based access control for specific methods
	- Rate limiting per tool
	- Audit logging
	- MCP server tool integration
	- REST endpoint tool support
	"""

	# Default rate limits per tool (calls per minute)
	DEFAULT_RATE_LIMITS = {
		"frappe_read": 60,
		"frappe_write": 20,
		"frappe_search": 30,
		"frappe_method": 20,
		"web_search": 10,
		"calculator": 100,
		"code_executor": 10,
		"rest_endpoint": 30,
		"twitter_post": 10,
		"linkedin_post": 10,
		"facebook_post": 10,
		"reddit_post": 5,
		"send_newsletter": 5,
	}

	def __init__(
		self,
		frappe_access: str,
		allowed_methods: list,
		doc: dict,
		doctype: str,
		docname: str,
		rate_limits: dict = None,
		enabled_mcps: list = None,
		rest_endpoints: list = None,
		context: dict = None,
	):
		"""
		Initialize the tool registry.

		Args:
			frappe_access: Access level ('none', 'read_only', 'full_crud')
			allowed_methods: List of allowed method configurations
			doc: Document data
			doctype: Document DocType
			docname: Document name
			rate_limits: Optional custom rate limits per tool
			enabled_mcps: List of enabled MCP server configs [{"connection_name": "...", "enabled": True}]
			rest_endpoints: List of REST endpoint configs for tool creation
			context: Workflow context for variable substitution
		"""
		self.frappe_access = frappe_access
		self.allowed_methods = allowed_methods or []
		self.doc = doc
		self.doctype = doctype
		self.docname = docname
		self.current_user = frappe.session.user
		self.user_roles = frappe.get_roles(self.current_user)
		self.enabled_mcps = enabled_mcps or []
		self.rest_endpoints = rest_endpoints or []
		self.context = context or {}

		# Initialize rate limiters for each tool
		self.rate_limits = {**self.DEFAULT_RATE_LIMITS, **(rate_limits or {})}
		self.rate_limiters = {
			tool_name: RateLimiter(max_calls=limit, period_seconds=60, key_prefix=tool_name)
			for tool_name, limit in self.rate_limits.items()
		}

	def _check_rate_limit(self, tool_name: str) -> tuple[bool, str | None]:
		"""
		Check if a tool call is within rate limits.

		Args:
			tool_name: Name of the tool

		Returns:
			Tuple of (is_allowed, error_message)
		"""
		limiter = self.rate_limiters.get(tool_name)
		if not limiter:
			return (True, None)

		if not limiter.is_allowed(tool_name):
			return (False, f"Rate limit exceeded for {tool_name}. Max {self.rate_limits.get(tool_name, 30)} calls per minute.")

		return (True, None)

	def _is_method_allowed(self, method: str) -> bool:
		"""
		Check if method is whitelisted and user has required role.

		Args:
			method: Full method path (e.g., 'frappe.client.get')

		Returns:
			True if method is allowed for current user
		"""
		for allowed in self.allowed_methods:
			if allowed.get("method") == method:
				# Check role restriction
				allowed_roles = allowed.get("allowed_roles", [])
				if allowed_roles:
					if not any(role in self.user_roles for role in allowed_roles):
						return False
				return True
		return False

	def _verify_whitelisted(self, method: str) -> bool:
		"""
		Verify the method has @frappe.whitelist() decorator.

		This provides an additional security layer by ensuring only
		properly whitelisted Frappe methods can be called.

		Args:
			method: Full method path

		Returns:
			True if method is whitelisted
		"""
		try:
			module_path, func_name = method.rsplit(".", 1)
			module = frappe.get_module(module_path)
			func = getattr(module, func_name, None)

			if func is None:
				return False

			# Check if function has whitelisted attribute
			return getattr(func, "is_whitelisted", False)
		except Exception:
			return False

	def get_tools(self, enabled_tools: list) -> list:
		"""
		Get list of enabled tools with proper access controls.

		Args:
			enabled_tools: List of tool configurations with name and enabled status

		Returns:
			List of LangChain tool instances
		"""
		tools = []

		# Standard Frappe tools
		for tool_config in enabled_tools:
			if not tool_config.get("enabled"):
				continue

			tool_name = tool_config["name"]

			if tool_name == "frappe_read" and self.frappe_access in ("read_only", "full_crud"):
				tools.append(self._create_frappe_read_tool())

			elif tool_name == "frappe_write" and self.frappe_access == "full_crud":
				tools.append(self._create_frappe_write_tool())

			elif tool_name == "frappe_search" and self.frappe_access in ("read_only", "full_crud"):
				tools.append(self._create_frappe_search_tool())

			elif tool_name == "frappe_method":
				tools.append(self._create_frappe_method_tool())

			elif tool_name == "web_search":
				tools.append(self._create_web_search_tool())

			elif tool_name == "calculator":
				tools.append(self._create_calculator_tool())

			elif tool_name == "code_executor":
				tools.append(self._create_code_executor_tool())

			elif tool_name == "twitter_post":
				tools.append(self._create_twitter_post_tool())

			elif tool_name == "linkedin_post":
				tools.append(self._create_linkedin_post_tool())

			elif tool_name == "facebook_post":
				tools.append(self._create_facebook_post_tool())

			elif tool_name == "reddit_post":
				tools.append(self._create_reddit_post_tool())

			elif tool_name == "send_newsletter":
				tools.append(self._create_send_newsletter_tool())

		# MCP tools from enabled MCP servers
		mcp_tools = self._get_mcp_tools()
		tools.extend(mcp_tools)

		# REST endpoint tools
		rest_tools = self._create_rest_tools()
		tools.extend(rest_tools)

		return tools

	def _get_mcp_tools(self) -> list:
		"""
		Get tools from enabled MCP servers.

		Returns:
			List of LangChain tools from MCP servers
		"""
		if not self.enabled_mcps:
			return []

		try:
			from xstate_workflow.langgraph.mcp_client import get_tools_from_mcps

			return get_tools_from_mcps(
				enabled_mcps=self.enabled_mcps,
				doctype=self.doctype,
				docname=self.docname,
				user=self.current_user,
			)
		except Exception as e:
			frappe.log_error(
				title="MCP Tools Error",
				message=f"Failed to load MCP tools: {e}",
			)
			return []

	def _create_rest_tools(self) -> list:
		"""
		Create tools from configured REST endpoints.

		Returns:
			List of LangChain tools for REST endpoints
		"""
		if not self.rest_endpoints:
			return []

		tools = []
		for endpoint in self.rest_endpoints:
			if not endpoint.get("name"):
				continue

			tool = self._create_rest_tool(endpoint)
			if tool:
				tools.append(tool)

		return tools

	def _create_rest_tool(self, config: dict):
		"""
		Create a LangChain tool for a REST endpoint.

		Args:
			config: REST endpoint configuration with name, url, method, etc.

		Returns:
			LangChain tool or None
		"""
		try:
			from langchain_core.tools import tool
		except ImportError:
			return None

		import time

		import requests

		# Capture for closure
		endpoint_name = config.get("name")
		endpoint_url = config.get("url", "")
		endpoint_method = config.get("method", "GET").upper()
		endpoint_auth_type = config.get("authType", "none")
		endpoint_auth_credential = config.get("authCredential", "")
		endpoint_headers = config.get("headers", {})
		endpoint_body = config.get("body")
		endpoint_description = config.get("description", f"REST endpoint: {endpoint_name}")
		endpoint_timeout = config.get("timeout", 30)

		doc_data = self.doc
		context_data = self.context
		doctype = self.doctype
		docname = self.docname
		registry = self

		tool_name = f"rest_{endpoint_name}"

		@tool(tool_name, description=f"{endpoint_description} Args: params - optional parameters for URL/body substitution.")
		def rest_endpoint_call(**params) -> dict:
			"""Call a configured REST endpoint."""
			start_time = time.time()

			# Check rate limit
			allowed, error_msg = registry._check_rate_limit("rest_endpoint")
			if not allowed:
				return {"error": error_msg}

			try:
				# Substitute {{field}} in URL
				url = _substitute_template(endpoint_url, doc_data, context_data, params)

				# Build headers
				headers = {"Content-Type": "application/json", "Accept": "application/json"}
				headers.update(endpoint_headers or {})

				# Add authentication
				headers = _add_rest_auth(
					headers, endpoint_auth_type, endpoint_auth_credential
				)

				# Substitute {{field}} in body for POST/PUT
				body = None
				if endpoint_body and endpoint_method in ("POST", "PUT", "PATCH"):
					body_str = _substitute_template(endpoint_body, doc_data, context_data, params)
					try:
						import json
						body = json.loads(body_str)
					except (json.JSONDecodeError, TypeError):
						body = body_str

				# Make request
				response = requests.request(
					method=endpoint_method,
					url=url,
					headers=headers,
					json=body if isinstance(body, dict) else None,
					data=body if isinstance(body, str) else None,
					timeout=endpoint_timeout,
				)

				duration_ms = (time.time() - start_time) * 1000

				# Log the call
				log_tool_call(
					tool_name=f"rest:{endpoint_name}",
					doctype=doctype,
					docname=docname,
					args={"url": url, "method": endpoint_method},
					result=f"Status: {response.status_code}",
					duration_ms=duration_ms,
					success=response.ok,
				)

				# Return response
				if response.ok:
					try:
						return response.json()
					except ValueError:
						return {
							"status": response.status_code,
							"content_type": response.headers.get("Content-Type", ""),
							"text": response.text[:1000],
						}
				else:
					return {
						"error": f"HTTP {response.status_code}",
						"status": response.status_code,
						"body": response.text[:500],
					}

			except requests.exceptions.Timeout:
				return {"error": f"Request timeout after {endpoint_timeout}s"}
			except requests.exceptions.ConnectionError as e:
				return {"error": f"Connection error: {e}"}
			except Exception as e:
				return {"error": str(e)}

		return rest_endpoint_call

	def _create_frappe_read_tool(self):
		"""Create tool for reading Frappe documents."""
		try:
			from langchain_core.tools import tool
		except ImportError:
			frappe.throw(_("langchain_core is not installed. Run: pip install langchain-core"))

		@tool
		def frappe_read(
			doctype: str, name: str = None, filters: dict = None, fields: list = None
		) -> Any:
			"""Read document(s) from Frappe.

			Args:
				doctype: The DocType to read from
				name: Specific document name (optional)
				filters: Filters for get_list (optional)
				fields: Fields to return (optional)

			Returns:
				Document data or list of documents
			"""
			# Permission check
			if not frappe.has_permission(doctype, "read"):
				return {"error": f"No read permission for {doctype}"}

			try:
				if name:
					return frappe.get_doc(doctype, name).as_dict()
				else:
					return frappe.get_list(
						doctype,
						filters=filters or {},
						fields=fields or ["name"],
						limit=100,
					)
			except Exception as e:
				return {"error": str(e)}

		return frappe_read

	def _create_frappe_write_tool(self):
		"""Create tool for writing Frappe documents."""
		try:
			from langchain_core.tools import tool
		except ImportError:
			frappe.throw(_("langchain_core is not installed. Run: pip install langchain-core"))

		@tool
		def frappe_write(doctype: str, name: str = None, data: dict = None) -> Any:
			"""Create or update a Frappe document.

			Args:
				doctype: The DocType to write to
				name: Document name for update (optional, omit for create)
				data: Document data

			Returns:
				Success status and document name
			"""
			perm_type = "write" if name else "create"
			if not frappe.has_permission(doctype, perm_type):
				return {"error": f"No {perm_type} permission for {doctype}"}

			try:
				if name:
					doc = frappe.get_doc(doctype, name)
					doc.update(data or {})
					doc.save()
				else:
					doc = frappe.get_doc({"doctype": doctype, **(data or {})})
					doc.insert()

				return {"success": True, "name": doc.name}
			except Exception as e:
				return {"error": str(e)}

		return frappe_write

	def _create_frappe_search_tool(self):
		"""Create tool for searching across Frappe."""
		try:
			from langchain_core.tools import tool
		except ImportError:
			frappe.throw(_("langchain_core is not installed. Run: pip install langchain-core"))

		@tool
		def frappe_search(doctype: str, query: str, fields: list = None, limit: int = 20) -> Any:
			"""Search for documents matching a query.

			Args:
				doctype: The DocType to search
				query: Search query string
				fields: Fields to search in (optional)
				limit: Max results (default 20)

			Returns:
				List of matching documents
			"""
			if not frappe.has_permission(doctype, "read"):
				return {"error": f"No read permission for {doctype}"}

			try:
				search_fields = fields or ["name"]
				or_filters = {f: ["like", f"%{query}%"] for f in search_fields}

				return frappe.get_list(
					doctype,
					or_filters=or_filters,
					limit=limit,
				)
			except Exception as e:
				return {"error": str(e)}

		return frappe_search

	def _create_frappe_method_tool(self):
		"""Create tool for calling whitelisted Frappe methods with role checks."""
		try:
			from langchain_core.tools import tool
		except ImportError:
			frappe.throw(_("langchain_core is not installed. Run: pip install langchain-core"))

		registry = self  # Capture reference for closure

		@tool
		def frappe_method(method: str, args: dict = None) -> Any:
			"""Call a whitelisted Frappe method.

			Args:
				method: Full method path (e.g., 'frappe.client.get')
				args: Arguments to pass to the method

			Returns:
				Method result or error

			Note: Only pre-approved methods can be called. Methods must be:
			1. Listed in the node's allowed_methods configuration
			2. Have @frappe.whitelist() decorator
			3. User must have the required role (if specified)
			"""
			# Check if method is in allowed list with role check
			if not registry._is_method_allowed(method):
				return {"error": f"Method '{method}' is not allowed or you don't have the required role"}

			# Verify the method is actually whitelisted with @frappe.whitelist()
			if not registry._verify_whitelisted(method):
				return {"error": f"Method '{method}' is not a whitelisted Frappe method"}

			# Call the method
			try:
				return frappe.call(method, **(args or {}))
			except Exception as e:
				return {"error": str(e)}

		return frappe_method

	def _create_web_search_tool(self):
		"""Create tool for web searching."""
		try:
			from langchain_core.tools import tool
		except ImportError:
			frappe.throw(_("langchain_core is not installed. Run: pip install langchain-core"))

		@tool
		def web_search(query: str) -> str:
			"""Search the web for information.

			Args:
				query: Search query

			Returns:
				Search results or error message
			"""
			# Try to use available search providers
			try:
				# Try SerpAPI if available
				from langchain_community.utilities import SerpAPIWrapper

				search = SerpAPIWrapper()
				return search.run(query)
			except ImportError:
				pass

			try:
				# Try DuckDuckGo as fallback
				from langchain_community.tools import DuckDuckGoSearchRun

				search = DuckDuckGoSearchRun()
				return search.run(query)
			except ImportError:
				pass

			return f"Web search not available. Query was: {query}"

		return web_search

	def _create_calculator_tool(self):
		"""Create tool for calculations."""
		try:
			from langchain_core.tools import tool
		except ImportError:
			frappe.throw(_("langchain_core is not installed. Run: pip install langchain-core"))

		@tool
		def calculator(expression: str) -> str:
			"""Evaluate a mathematical expression safely.

			Args:
				expression: Math expression (e.g., '2 + 2', 'sqrt(16)', '10 * 5.5')

			Returns:
				Calculation result or error message
			"""
			import ast
			import math
			import operator

			# Safe math operations
			ops = {
				ast.Add: operator.add,
				ast.Sub: operator.sub,
				ast.Mult: operator.mul,
				ast.Div: operator.truediv,
				ast.Pow: operator.pow,
				ast.USub: operator.neg,
				ast.UAdd: operator.pos,
			}

			# Safe math functions
			safe_functions = {
				"sqrt": math.sqrt,
				"sin": math.sin,
				"cos": math.cos,
				"tan": math.tan,
				"log": math.log,
				"log10": math.log10,
				"exp": math.exp,
				"abs": abs,
				"round": round,
				"floor": math.floor,
				"ceil": math.ceil,
			}

			safe_constants = {
				"pi": math.pi,
				"e": math.e,
			}

			def eval_expr(node):
				if isinstance(node, ast.Constant):
					return node.value
				elif isinstance(node, ast.Num):  # Python < 3.8 compatibility
					return node.n
				elif isinstance(node, ast.BinOp):
					return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
				elif isinstance(node, ast.UnaryOp):
					return ops[type(node.op)](eval_expr(node.operand))
				elif isinstance(node, ast.Call):
					func_name = node.func.id if isinstance(node.func, ast.Name) else None
					if func_name in safe_functions:
						args = [eval_expr(arg) for arg in node.args]
						return safe_functions[func_name](*args)
					else:
						raise ValueError(f"Unknown function: {func_name}")
				elif isinstance(node, ast.Name):
					if node.id in safe_constants:
						return safe_constants[node.id]
					raise ValueError(f"Unknown variable: {node.id}")
				else:
					raise ValueError(f"Unsupported operation: {type(node)}")

			try:
				tree = ast.parse(expression, mode="eval")
				result = eval_expr(tree.body)
				return str(result)
			except Exception as e:
				return f"Error: {e}"

		return calculator

	def _create_code_executor_tool(self):
		"""Create tool for executing Python code in a sandboxed environment."""
		try:
			from langchain_core.tools import tool
		except ImportError:
			frappe.throw(_("langchain_core is not installed. Run: pip install langchain-core"))

		doc_data = self.doc
		doctype = self.doctype
		docname = self.docname
		registry = self  # Capture reference for rate limiting

		@tool
		def code_executor(code: str) -> str:
			"""Execute Python code in a sandboxed environment.

			The code has access to:
			- doc: The current document data (read-only dict)
			- frappe.utils: Date/time utilities
			- math: Mathematical functions

			Args:
				code: Python code to execute

			Returns:
				Execution result or error message

			Note: Code execution is sandboxed with limited builtins.
			No file I/O, network access, or dangerous operations allowed.
			Maximum execution time: 5 seconds.
			"""
			import math
			import time

			start_time = time.time()

			# Check rate limit
			allowed, error_msg = registry._check_rate_limit("code_executor")
			if not allowed:
				log_tool_call(
					tool_name="code_executor",
					doctype=doctype,
					docname=docname,
					args={"code": code[:100] + "..." if len(code) > 100 else code},
					success=False,
					error=error_msg,
				)
				return error_msg

			# Validate code for dangerous patterns
			is_safe, validation_error = validate_code(code)
			if not is_safe:
				log_tool_call(
					tool_name="code_executor",
					doctype=doctype,
					docname=docname,
					args={"code": code[:100] + "..." if len(code) > 100 else code},
					success=False,
					error=validation_error,
				)
				return f"Code validation failed: {validation_error}"

			# Sandboxed globals with limited access
			safe_builtins = {
				"abs": abs,
				"all": all,
				"any": any,
				"bool": bool,
				"dict": dict,
				"enumerate": enumerate,
				"filter": filter,
				"float": float,
				"int": int,
				"len": len,
				"list": list,
				"map": map,
				"max": max,
				"min": min,
				"print": print,
				"range": range,
				"round": round,
				"set": set,
				"sorted": sorted,
				"str": str,
				"sum": sum,
				"tuple": tuple,
				"zip": zip,
				"True": True,
				"False": False,
				"None": None,
				"isinstance": isinstance,
				"type": type,
				"hasattr": hasattr,
				"getattr": getattr,
			}

			sandbox_globals = {
				"__builtins__": safe_builtins,
				"doc": doc_data.copy(),  # Read-only copy
				"doctype": doctype,
				"docname": docname,
				"math": math,
				"frappe_utils": frappe.utils,
			}

			# Capture output
			output_lines = []
			original_print = safe_builtins["print"]

			def capture_print(*args, **kwargs):
				output_lines.append(" ".join(str(a) for a in args))

			safe_builtins["print"] = capture_print

			try:
				# Execute code with timeout (5 seconds)
				with timeout_handler(5):
					exec(code, sandbox_globals)

				duration_ms = (time.time() - start_time) * 1000
				result = "\n".join(output_lines) if output_lines else "Code executed successfully (no output)"

				log_tool_call(
					tool_name="code_executor",
					doctype=doctype,
					docname=docname,
					args={"code": code[:100] + "..." if len(code) > 100 else code},
					result=result[:200] if len(result) > 200 else result,
					duration_ms=duration_ms,
					success=True,
				)

				return result

			except TimeoutError as e:
				log_tool_call(
					tool_name="code_executor",
					doctype=doctype,
					docname=docname,
					args={"code": code[:100] + "..." if len(code) > 100 else code},
					success=False,
					error=str(e),
				)
				return f"Execution error: {e}"
			except Exception as e:
				log_tool_call(
					tool_name="code_executor",
					doctype=doctype,
					docname=docname,
					args={"code": code[:100] + "..." if len(code) > 100 else code},
					success=False,
					error=str(e),
				)
				return f"Execution error: {e}"
			finally:
				safe_builtins["print"] = original_print

		return code_executor

	def _create_twitter_post_tool(self):
		"""Create Twitter/X posting tool."""
		try:
			from langchain_core.tools import tool
		except ImportError:
			frappe.throw(_("langchain_core is not installed. Run: pip install langchain-core"))

		import time

		import requests

		registry = self
		doctype = self.doctype
		docname = self.docname

		@tool
		def twitter_post(text: str, reply_to: str = None) -> dict:
			"""Post a tweet to Twitter/X.

			Args:
				text: Tweet text (max 280 characters)
				reply_to: Optional tweet ID to reply to

			Returns:
				dict with tweet_id and url on success, or error message
			"""
			start_time = time.time()

			# Rate limit check
			allowed, error_msg = registry._check_rate_limit("twitter_post")
			if not allowed:
				return {"success": False, "error": error_msg}

			# Validate input
			if not text or len(text) > 280:
				return {"success": False, "error": "Tweet must be 1-280 characters"}

			# Twitter POST /2/tweets requires OAuth 1.0a User Context
			consumer_key = _resolve_credential("config:twitter_consumer_key")
			consumer_secret = _resolve_credential("config:twitter_consumer_secret")
			access_token = _resolve_credential("config:twitter_access_token")
			access_token_secret = _resolve_credential("config:twitter_access_token_secret")

			if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
				return {
					"success": False,
					"error": "Twitter OAuth 1.0a credentials not configured in site_config.json. "
					"Required: twitter_consumer_key, twitter_consumer_secret, "
					"twitter_access_token, twitter_access_token_secret"
				}

			try:
				from requests_oauthlib import OAuth1
			except ImportError:
				return {"success": False, "error": "requests_oauthlib is not installed. Run: pip install requests-oauthlib"}

			try:
				payload = {"text": text}
				if reply_to:
					payload["reply"] = {"in_reply_to_tweet_id": reply_to}

				auth = OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)
				response = requests.post(
					"https://api.twitter.com/2/tweets",
					headers={"Content-Type": "application/json"},
					json=payload,
					auth=auth,
					timeout=30,
				)

				duration_ms = (time.time() - start_time) * 1000

				if response.ok:
					data = response.json()
					tweet_id = data.get("data", {}).get("id")
					result = {
						"success": True,
						"tweet_id": tweet_id,
						"url": f"https://twitter.com/i/status/{tweet_id}",
					}
					log_tool_call(
						"twitter_post", doctype, docname,
						{"text": text[:50]}, str(result), duration_ms, True
					)
					return result
				else:
					error = f"Twitter API error: {response.status_code} - {response.text}"
					log_tool_call(
						"twitter_post", doctype, docname,
						{"text": text[:50]}, None, duration_ms, False, error
					)
					return {"success": False, "error": error}

			except Exception as e:
				log_tool_call(
					"twitter_post", doctype, docname,
					{"text": text[:50]}, None, 0, False, str(e)
				)
				return {"success": False, "error": str(e)}

		return twitter_post

	def _create_linkedin_post_tool(self):
		"""Create LinkedIn posting tool."""
		try:
			from langchain_core.tools import tool
		except ImportError:
			frappe.throw(_("langchain_core is not installed. Run: pip install langchain-core"))

		import time

		import requests

		registry = self
		doctype = self.doctype
		docname = self.docname

		@tool
		def linkedin_post(text: str, visibility: str = "PUBLIC") -> dict:
			"""Post to LinkedIn.

			Args:
				text: Post content
				visibility: "PUBLIC", "CONNECTIONS", or "LOGGED_IN"

			Returns:
				dict with post_id on success, or error message
			"""
			start_time = time.time()

			# Rate limit check
			allowed, error_msg = registry._check_rate_limit("linkedin_post")
			if not allowed:
				return {"success": False, "error": error_msg}

			# Get credentials from site_config
			access_token = _resolve_credential("config:linkedin_access_token")
			person_urn = _resolve_credential("config:linkedin_person_urn")

			if not access_token or not person_urn:
				return {"success": False, "error": "LinkedIn credentials not configured in site_config.json"}

			try:
				payload = {
					"author": person_urn,
					"lifecycleState": "PUBLISHED",
					"specificContent": {
						"com.linkedin.ugc.ShareContent": {
							"shareCommentary": {"text": text},
							"shareMediaCategory": "NONE",
						}
					},
					"visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
				}

				response = requests.post(
					"https://api.linkedin.com/v2/ugcPosts",
					headers={
						"Authorization": f"Bearer {access_token}",
						"Content-Type": "application/json",
						"X-Restli-Protocol-Version": "2.0.0",
					},
					json=payload,
					timeout=30,
				)

				duration_ms = (time.time() - start_time) * 1000

				if response.ok:
					post_id = response.headers.get("x-restli-id", "")
					result = {"success": True, "post_id": post_id}
					log_tool_call(
						"linkedin_post", doctype, docname,
						{"text": text[:50]}, str(result), duration_ms, True
					)
					return result
				else:
					error = f"LinkedIn API error: {response.status_code} - {response.text}"
					log_tool_call(
						"linkedin_post", doctype, docname,
						{"text": text[:50]}, None, duration_ms, False, error
					)
					return {"success": False, "error": error}

			except Exception as e:
				log_tool_call(
					"linkedin_post", doctype, docname,
					{"text": text[:50]}, None, 0, False, str(e)
				)
				return {"success": False, "error": str(e)}

		return linkedin_post

	def _create_facebook_post_tool(self):
		"""Create Facebook page posting tool."""
		try:
			from langchain_core.tools import tool
		except ImportError:
			frappe.throw(_("langchain_core is not installed. Run: pip install langchain-core"))

		import time

		import requests

		registry = self
		doctype = self.doctype
		docname = self.docname

		@tool
		def facebook_post(message: str, link: str = None) -> dict:
			"""Post to a Facebook Page.

			Args:
				message: Post content
				link: Optional URL to share

			Returns:
				dict with post_id on success, or error message
			"""
			start_time = time.time()

			# Rate limit check
			allowed, error_msg = registry._check_rate_limit("facebook_post")
			if not allowed:
				return {"success": False, "error": error_msg}

			# Get credentials from site_config
			page_access_token = _resolve_credential("config:facebook_page_access_token")
			page_id = _resolve_credential("config:facebook_page_id")

			if not page_access_token or not page_id:
				return {"success": False, "error": "Facebook credentials not configured in site_config.json"}

			try:
				payload = {"message": message, "access_token": page_access_token}
				if link:
					payload["link"] = link

				response = requests.post(
					f"https://graph.facebook.com/v18.0/{page_id}/feed",
					data=payload,
					timeout=30,
				)

				duration_ms = (time.time() - start_time) * 1000

				if response.ok:
					data = response.json()
					post_id = data.get("id", "")
					result = {
						"success": True,
						"post_id": post_id,
						"url": f"https://facebook.com/{post_id}",
					}
					log_tool_call(
						"facebook_post", doctype, docname,
						{"message": message[:50]}, str(result), duration_ms, True
					)
					return result
				else:
					error = f"Facebook API error: {response.status_code} - {response.text}"
					log_tool_call(
						"facebook_post", doctype, docname,
						{"message": message[:50]}, None, duration_ms, False, error
					)
					return {"success": False, "error": error}

			except Exception as e:
				log_tool_call(
					"facebook_post", doctype, docname,
					{"message": message[:50]}, None, 0, False, str(e)
				)
				return {"success": False, "error": str(e)}

		return facebook_post

	def _create_reddit_post_tool(self):
		"""Create Reddit posting tool."""
		try:
			from langchain_core.tools import tool
		except ImportError:
			frappe.throw(_("langchain_core is not installed. Run: pip install langchain-core"))

		import time

		import requests

		registry = self
		doctype = self.doctype
		docname = self.docname

		@tool
		def reddit_post(subreddit: str, title: str, text: str = None, url: str = None) -> dict:
			"""Post to a Reddit subreddit.

			Args:
				subreddit: Subreddit name without r/ (e.g., "Accounting", "Big4")
				title: Post title
				text: Post body text (for text posts)
				url: URL to share (for link posts)

			Returns:
				dict with post_id and url on success, or error message
			"""
			start_time = time.time()

			# Validate input first (before rate limiting)
			if not subreddit or not title:
				return {"success": False, "error": "subreddit and title are required"}
			if not text and not url:
				return {"success": False, "error": "Either text or url is required"}

			# Rate limit check
			allowed, error_msg = registry._check_rate_limit("reddit_post")
			if not allowed:
				return {"success": False, "error": error_msg}

			# Get credentials from site_config
			client_id = _resolve_credential("config:reddit_client_id")
			client_secret = _resolve_credential("config:reddit_client_secret")
			username = _resolve_credential("config:reddit_username")
			password = _resolve_credential("config:reddit_password")

			if not all([client_id, client_secret, username, password]):
				return {"success": False, "error": "Reddit credentials not configured in site_config.json"}

			try:
				# Get OAuth token
				auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
				token_response = requests.post(
					"https://www.reddit.com/api/v1/access_token",
					auth=auth,
					data={
						"grant_type": "password",
						"username": username,
						"password": password,
					},
					headers={"User-Agent": "XStateWorkflow/1.0"},
					timeout=30,
				)

				if not token_response.ok:
					return {"success": False, "error": f"Reddit auth failed: {token_response.text}"}

				access_token = token_response.json().get("access_token")

				# Submit post
				post_data = {
					"sr": subreddit,
					"title": title,
					"kind": "link" if url else "self",
				}
				if url:
					post_data["url"] = url
				else:
					post_data["text"] = text

				response = requests.post(
					"https://oauth.reddit.com/api/submit",
					headers={
						"Authorization": f"Bearer {access_token}",
						"User-Agent": "XStateWorkflow/1.0",
					},
					data=post_data,
					timeout=30,
				)

				duration_ms = (time.time() - start_time) * 1000

				if response.ok:
					data = response.json()
					post_url = data.get("json", {}).get("data", {}).get("url", "")
					post_id = data.get("json", {}).get("data", {}).get("id", "")
					result = {
						"success": True,
						"post_id": post_id,
						"url": post_url,
					}
					log_tool_call(
						"reddit_post", doctype, docname,
						{"subreddit": subreddit, "title": title[:50]}, str(result), duration_ms, True
					)
					return result
				else:
					error = f"Reddit API error: {response.status_code} - {response.text}"
					log_tool_call(
						"reddit_post", doctype, docname,
						{"subreddit": subreddit, "title": title[:50]}, None, duration_ms, False, error
					)
					return {"success": False, "error": error}

			except Exception as e:
				log_tool_call(
					"reddit_post", doctype, docname,
					{"subreddit": subreddit}, None, 0, False, str(e)
				)
				return {"success": False, "error": str(e)}

		return reddit_post

	def _create_send_newsletter_tool(self):
		"""Create newsletter sending tool."""
		try:
			from langchain_core.tools import tool
		except ImportError:
			frappe.throw(_("langchain_core is not installed. Run: pip install langchain-core"))

		import time

		registry = self
		doctype = self.doctype
		docname = self.docname

		@tool
		def send_newsletter(subject: str, content: str, subscriber_list: str = "Default") -> dict:
			"""Send a newsletter email to subscribers.

			Args:
				subject: Email subject line
				content: Email body content (HTML supported)
				subscriber_list: Name of the Email Group to send to (default: "Default")

			Returns:
				dict with success status and number of recipients
			"""
			start_time = time.time()

			# Rate limit check
			allowed, error_msg = registry._check_rate_limit("send_newsletter")
			if not allowed:
				return {"success": False, "error": error_msg}

			# Validate input
			if not subject or not content:
				return {"success": False, "error": "Subject and content are required"}

			try:
				# Get subscribers from Email Group
				subscribers = frappe.get_all(
					"Email Group Member",
					filters={"email_group": subscriber_list, "unsubscribed": 0},
					pluck="email"
				)

				if not subscribers:
					return {
						"success": False,
						"error": f"No subscribers found in Email Group '{subscriber_list}'"
					}

				# Send the newsletter
				frappe.sendmail(
					recipients=subscribers,
					subject=subject,
					message=content,
					delayed=False,
					reference_doctype=doctype,
					reference_name=docname,
				)

				duration_ms = (time.time() - start_time) * 1000

				result = {
					"success": True,
					"sent_to": len(subscribers),
					"subscriber_list": subscriber_list,
				}

				log_tool_call(
					"send_newsletter", doctype, docname,
					{"subject": subject[:50], "subscriber_list": subscriber_list},
					str(result), duration_ms, True
				)

				return result

			except Exception as e:
				log_tool_call(
					"send_newsletter", doctype, docname,
					{"subject": subject[:50]}, None, 0, False, str(e)
				)
				return {"success": False, "error": str(e)}

		return send_newsletter


def get_frappe_tools(
	frappe_access: str,
	allowed_methods: list,
	doc: dict,
	doctype: str,
	docname: str,
	enabled_tools: list,
	enabled_mcps: list = None,
	rest_endpoints: list = None,
	context: dict = None,
) -> list:
	"""
	Convenience function to get Frappe tools.

	Args:
		frappe_access: Access level
		allowed_methods: List of allowed method configurations
		doc: Document data
		doctype: DocType name
		docname: Document name
		enabled_tools: List of enabled tool configurations
		enabled_mcps: List of enabled MCP server configurations
		rest_endpoints: List of REST endpoint configurations
		context: Workflow context for variable substitution

	Returns:
		List of LangChain tool instances
	"""
	registry = ToolRegistry(
		frappe_access=frappe_access,
		allowed_methods=allowed_methods,
		doc=doc,
		doctype=doctype,
		docname=docname,
		enabled_mcps=enabled_mcps,
		rest_endpoints=rest_endpoints,
		context=context,
	)
	return registry.get_tools(enabled_tools)


def _substitute_template(template: str, doc: dict, context: dict, params: dict = None) -> str:
	"""
	Substitute {{field}} patterns in a template string.

	Supports:
	- {{field}} - document field
	- {{doc.field}} - explicit document field
	- {{context.field}} - context variable
	- {{param.field}} - parameter from tool call

	Args:
		template: Template string with {{field}} patterns
		doc: Document data
		context: Workflow context
		params: Optional additional parameters

	Returns:
		Template with substituted values
	"""
	import re

	if not template:
		return template

	params = params or {}

	def replace_match(match):
		key = match.group(1).strip()

		# Check explicit prefixes
		if key.startswith("doc."):
			field = key[4:]
			return str(doc.get(field, ""))
		elif key.startswith("context."):
			field = key[8:]
			return str(context.get(field, ""))
		elif key.startswith("param."):
			field = key[6:]
			return str(params.get(field, ""))

		# Default: try params first, then doc, then context
		if key in params:
			return str(params[key])
		elif key in doc:
			return str(doc[key])
		elif key in context:
			return str(context[key])

		# Return empty string for missing values
		return ""

	# Match {{field}} pattern
	pattern = r"\{\{([^}]+)\}\}"
	return re.sub(pattern, replace_match, template)


def _add_rest_auth(headers: dict, auth_type: str, auth_credential: str) -> dict:
	"""
	Add authentication to REST headers.

	Args:
		headers: Existing headers dict
		auth_type: Authentication type (none, api_key, basic, bearer)
		auth_credential: Credential value or reference

	Returns:
		Headers dict with auth added
	"""
	import base64

	if auth_type == "none" or not auth_credential:
		return headers

	# Get actual credential value - could be a reference to a stored credential
	credential_value = _resolve_credential(auth_credential)

	if auth_type == "api_key":
		headers["X-API-Key"] = credential_value

	elif auth_type == "bearer":
		headers["Authorization"] = f"Bearer {credential_value}"

	elif auth_type == "basic":
		# Expect format "username:password"
		encoded = base64.b64encode(credential_value.encode()).decode()
		headers["Authorization"] = f"Basic {encoded}"

	return headers


def _resolve_credential(credential_ref: str) -> str:
	"""
	Resolve a credential reference to its actual value.

	Supports:
	- Direct values
	- References to site_config.json values (format: "config:key_name")
	- References to secrets (format: "secret:secret_name")

	Args:
		credential_ref: Credential reference string

	Returns:
		Resolved credential value
	"""
	if not credential_ref:
		return ""

	# Check if it's a config reference
	if credential_ref.startswith("config:"):
		key = credential_ref[7:]
		return frappe.conf.get(key, "")

	# Check if it's a secrets reference
	if credential_ref.startswith("secret:"):
		# Could integrate with a secrets manager in the future
		key = credential_ref[7:]
		return frappe.conf.get(f"secret_{key}", "")

	# Direct value
	return credential_ref
