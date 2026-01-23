# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Sandboxed execution environment for guard and action code.

Provides restricted access to frappe APIs and validates code
for dangerous patterns before execution.
"""

import re
import signal
from contextlib import contextmanager

import frappe


# ============================================================================
# DANGEROUS PATTERN DETECTION
# ============================================================================

GUARD_ACTION_DANGEROUS_PATTERNS = [
	# File system operations
	r"\bopen\s*\(",
	r"\bfile\s*\(",
	r"\bos\.(?:remove|unlink|rmdir|makedirs|mkdir|rename|chmod|chown)",
	r"\bshutil\.",
	r"\bpathlib\.",
	# Process/system operations
	r"\bos\.(?:system|popen|exec|spawn|fork)",
	r"\bsubprocess\.",
	# Network operations
	r"\bsocket\.",
	r"\burllib\.",
	r"\brequests\.",
	r"\bhttplib\.",
	r"\bhttp\.client\.",
	# Code execution (nested)
	r"\bexec\s*\(",
	r"\beval\s*\(",
	r"\bcompile\s*\(",
	r"\b__import__\s*\(",
	r"\bimportlib\.",
	# Dangerous attributes
	r"\b__(?:class|bases|subclasses|mro|globals|locals|builtins|code|getattribute)__",
	# Frappe database direct SQL / write operations
	r"\bfrappe\.db\.sql\s*\(",
	r"\bfrappe\.db\.commit\s*\(",
	r"\bfrappe\.db\.rollback\s*\(",
	# Module imports that could be dangerous
	r"\bimport\s+(?:os|sys|subprocess|socket|ctypes|pickle)",
	r"\bfrom\s+(?:os|sys|subprocess|socket|ctypes|pickle)\s+import",
]


def validate_guard_action_code(code: str) -> tuple[bool, str | None]:
	"""
	Validate guard/action code for dangerous patterns.

	Args:
		code: Python code to validate

	Returns:
		Tuple of (is_safe, error_message). If is_safe is True, error_message is None.
	"""
	for pattern in GUARD_ACTION_DANGEROUS_PATTERNS:
		match = re.search(pattern, code, re.IGNORECASE)
		if match:
			return (False, f"Code contains blocked pattern: {match.group()}")

	return (True, None)


# ============================================================================
# EXECUTION TIMEOUT
# ============================================================================

class ExecutionTimeoutError(Exception):
	"""Raised when code execution exceeds the allowed timeout."""
	pass


@contextmanager
def execution_timeout(seconds: int):
	"""
	Context manager that limits code execution time using SIGALRM.

	Args:
		seconds: Maximum execution time in seconds

	Raises:
		ExecutionTimeoutError: If execution exceeds the timeout

	Note: Only works on Unix systems. On Windows, this is a no-op.
	"""
	def _handler(signum, frame):
		raise ExecutionTimeoutError(f"Code execution exceeded {seconds}s timeout")

	# SIGALRM is Unix-only
	if not hasattr(signal, "SIGALRM"):
		yield
		return

	old_handler = signal.signal(signal.SIGALRM, _handler)
	signal.alarm(seconds)
	try:
		yield
	finally:
		signal.alarm(0)
		signal.signal(signal.SIGALRM, old_handler)


# ============================================================================
# RESTRICTED FRAPPE PROXY
# ============================================================================

class RestrictedDB:
	"""
	Read-only proxy for frappe.db that only exposes safe query methods.
	"""

	def get_value(self, *args, **kwargs):
		return frappe.db.get_value(*args, **kwargs)

	def get_list(self, *args, **kwargs):
		return frappe.db.get_list(*args, **kwargs)

	def exists(self, *args, **kwargs):
		return frappe.db.exists(*args, **kwargs)

	def count(self, *args, **kwargs):
		return frappe.db.count(*args, **kwargs)

	def __getattr__(self, name):
		raise AttributeError(
			f"frappe.db.{name} is not allowed in guard/action code. "
			f"Use get_value, get_list, exists, or count instead."
		)


class RestrictedFrappe:
	"""
	Restricted proxy for frappe module that only exposes safe APIs.

	Guards have access to:
		- frappe.utils.*, frappe.session, frappe._
		- frappe.get_value, frappe.db.get_value, frappe.db.get_list,
		  frappe.db.exists, frappe.db.count
		- frappe.log_error

	Actions additionally have access to:
		- frappe.sendmail
	"""

	def __init__(self, allow_actions: bool = False):
		self._allow_actions = allow_actions
		self.db = RestrictedDB()
		self.utils = frappe.utils
		self.session = frappe.session
		self._ = frappe._

	def get_value(self, *args, **kwargs):
		return frappe.db.get_value(*args, **kwargs)

	def log_error(self, *args, **kwargs):
		return frappe.log_error(*args, **kwargs)

	def sendmail(self, *args, **kwargs):
		if not self._allow_actions:
			raise PermissionError("frappe.sendmail is not allowed in guard code")
		return frappe.sendmail(*args, **kwargs)

	def get_roles(self, *args, **kwargs):
		return frappe.get_roles(*args, **kwargs)

	def __getattr__(self, name):
		raise AttributeError(
			f"frappe.{name} is not allowed in guard/action code. "
			f"Only frappe.db.get_value, get_list, exists, count, "
			f"frappe.utils, frappe.session, and frappe.log_error are available."
		)


# ============================================================================
# AUDIT LOGGING
# ============================================================================

def log_guard_execution(machine_name: str, guard_name: str, result: bool, error: str = None):
	"""
	Log guard execution for audit trail.

	Only logs errors and failures to avoid excessive logging.
	"""
	if error:
		frappe.log_error(
			f"Guard '{guard_name}' on machine '{machine_name}' failed: {error}",
			"Guard Execution Error"
		)


def log_action_execution(machine_name: str, action_name: str, error: str = None):
	"""
	Log action execution for audit trail.

	Only logs errors to avoid excessive logging.
	"""
	if error:
		frappe.log_error(
			f"Action '{action_name}' on machine '{machine_name}' failed: {error}",
			"Action Execution Error"
		)
