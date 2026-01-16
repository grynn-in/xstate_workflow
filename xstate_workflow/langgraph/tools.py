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
	}

	def __init__(
		self,
		frappe_access: str,
		allowed_methods: list,
		doc: dict,
		doctype: str,
		docname: str,
		rate_limits: dict = None,
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
		"""
		self.frappe_access = frappe_access
		self.allowed_methods = allowed_methods or []
		self.doc = doc
		self.doctype = doctype
		self.docname = docname
		self.current_user = frappe.session.user
		self.user_roles = frappe.get_roles(self.current_user)

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

		return tools

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


def get_frappe_tools(
	frappe_access: str,
	allowed_methods: list,
	doc: dict,
	doctype: str,
	docname: str,
	enabled_tools: list,
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

	Returns:
		List of LangChain tool instances
	"""
	registry = ToolRegistry(
		frappe_access=frappe_access,
		allowed_methods=allowed_methods,
		doc=doc,
		doctype=doctype,
		docname=docname,
	)
	return registry.get_tools(enabled_tools)
