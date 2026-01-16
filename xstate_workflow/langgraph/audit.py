# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Audit Logging Module for AI Agents.

Provides logging and monitoring for AI agent activities,
including tool calls, decisions, and errors.
"""

import json
import time
from functools import wraps
from typing import Any, Callable

import frappe


# Fields that should be redacted in logs
SENSITIVE_FIELDS = [
	"password",
	"api_key",
	"secret",
	"token",
	"auth",
	"credential",
	"private_key",
	"access_key",
	"session_id",
	"cookie",
]


def _sanitize_for_log(data: Any, max_length: int = 1000) -> Any:
	"""
	Sanitize data for logging by redacting sensitive fields.

	Args:
		data: Data to sanitize
		max_length: Maximum string length before truncation

	Returns:
		Sanitized data safe for logging
	"""
	if data is None:
		return None

	if isinstance(data, str):
		# Truncate long strings
		if len(data) > max_length:
			return data[:max_length] + f"... [truncated {len(data) - max_length} chars]"
		return data

	if isinstance(data, dict):
		sanitized = {}
		for key, value in data.items():
			key_lower = key.lower()
			# Check if key contains sensitive patterns
			if any(pattern in key_lower for pattern in SENSITIVE_FIELDS):
				sanitized[key] = "[REDACTED]"
			else:
				sanitized[key] = _sanitize_for_log(value, max_length)
		return sanitized

	if isinstance(data, (list, tuple)):
		return [_sanitize_for_log(item, max_length) for item in data[:50]]  # Limit list size

	# For other types, convert to string and truncate
	str_data = str(data)
	if len(str_data) > max_length:
		return str_data[:max_length] + "..."
	return data


def log_agent_activity(
	doctype: str,
	docname: str,
	activity_type: str,
	details: dict = None,
	success: bool = True,
	error: str = None,
) -> None:
	"""
	Log AI agent activity.

	Args:
		doctype: Document DocType
		docname: Document name
		activity_type: Type of activity (start, complete, tool_call, decision, error)
		details: Additional details to log
		success: Whether the activity succeeded
		error: Error message if failed
	"""
	try:
		log_entry = {
			"doctype": doctype,
			"docname": docname,
			"activity_type": activity_type,
			"user": frappe.session.user,
			"timestamp": str(frappe.utils.now_datetime()),
			"success": success,
		}

		if details:
			log_entry["details"] = _sanitize_for_log(details)

		if error:
			log_entry["error"] = _sanitize_for_log(error, max_length=500)

		# Log to frappe error log for now (could be upgraded to dedicated DocType)
		if not success or activity_type == "error":
			frappe.log_error(
				json.dumps(log_entry, indent=2, default=str),
				f"Agent Activity: {activity_type}"
			)
		else:
			# For successful activities, use debug logging
			frappe.logger().debug(f"Agent Activity: {json.dumps(log_entry, default=str)}")

	except Exception as e:
		# Don't let logging failures break the agent
		frappe.logger().error(f"Failed to log agent activity: {e}")


def log_tool_call(
	tool_name: str,
	doctype: str,
	docname: str,
	args: dict = None,
	result: Any = None,
	duration_ms: float = None,
	success: bool = True,
	error: str = None,
) -> None:
	"""
	Log a tool call by the agent.

	Args:
		tool_name: Name of the tool called
		doctype: Document DocType
		docname: Document name
		args: Arguments passed to the tool
		result: Result from the tool
		duration_ms: Execution time in milliseconds
		success: Whether the call succeeded
		error: Error message if failed
	"""
	details = {
		"tool": tool_name,
		"args": _sanitize_for_log(args),
	}

	if result is not None:
		details["result_preview"] = _sanitize_for_log(result, max_length=200)

	if duration_ms is not None:
		details["duration_ms"] = round(duration_ms, 2)

	log_agent_activity(
		doctype=doctype,
		docname=docname,
		activity_type="tool_call",
		details=details,
		success=success,
		error=error,
	)


def audit_tool_wrapper(tool_func: Callable, tool_name: str, doctype: str, docname: str) -> Callable:
	"""
	Wrap a tool function with audit logging.

	Args:
		tool_func: The tool function to wrap
		tool_name: Name of the tool
		doctype: Document DocType
		docname: Document name

	Returns:
		Wrapped function with audit logging
	"""
	@wraps(tool_func)
	def wrapper(*args, **kwargs):
		start_time = time.time()
		error_msg = None
		success = True
		result = None

		try:
			result = tool_func(*args, **kwargs)
			return result
		except Exception as e:
			error_msg = str(e)
			success = False
			raise
		finally:
			duration_ms = (time.time() - start_time) * 1000
			log_tool_call(
				tool_name=tool_name,
				doctype=doctype,
				docname=docname,
				args=kwargs or (args[0] if args else None),
				result=result,
				duration_ms=duration_ms,
				success=success,
				error=error_msg,
			)

	return wrapper


class RateLimiter:
	"""
	Distributed rate limiter for tool calls using Redis.

	Uses a sliding window approach with Redis-backed storage to track
	calls per time period across multiple workers.

	Falls back to in-memory storage if Redis is not available.
	"""

	# Class-level fallback storage for when Redis is unavailable
	_fallback_history: dict = {}

	def __init__(
		self,
		max_calls: int = 30,
		period_seconds: int = 60,
		key_prefix: str = "",
	):
		"""
		Initialize rate limiter.

		Args:
			max_calls: Maximum calls allowed in the period
			period_seconds: Time period in seconds
			key_prefix: Prefix for rate limit keys (e.g., tool name)
		"""
		self.max_calls = max_calls
		self.period_seconds = period_seconds
		self.key_prefix = key_prefix
		self._use_redis = self._check_redis_available()

	def _check_redis_available(self) -> bool:
		"""Check if Redis is available via frappe.cache."""
		try:
			# Try to ping the Redis connection
			cache = frappe.cache
			if cache and hasattr(cache, 'set_value'):
				# Test write and read
				test_key = "rate_limit:test"
				cache.set_value(test_key, "test", expires_in_sec=1)
				return True
		except Exception:
			pass
		return False

	def _get_key(self, identifier: str) -> str:
		"""Generate a unique key for rate limiting."""
		return f"rate_limit:{self.key_prefix}:{identifier}"

	def _get_redis_count(self, key: str) -> int:
		"""Get the current count from Redis using sorted set."""
		try:
			cache = frappe.cache
			redis_client = cache.get_redis()

			# Use Redis sorted set with timestamps as scores
			now = time.time()
			cutoff = now - self.period_seconds

			# Remove old entries
			redis_client.zremrangebyscore(key, 0, cutoff)

			# Get current count
			return redis_client.zcard(key) or 0
		except Exception as e:
			frappe.logger().debug(f"Redis rate limit error: {e}")
			return -1  # Signal to use fallback

	def _record_redis_call(self, key: str) -> bool:
		"""Record a call in Redis."""
		try:
			cache = frappe.cache
			redis_client = cache.get_redis()

			now = time.time()

			# Add timestamp to sorted set
			redis_client.zadd(key, {str(now): now})

			# Set expiry on the key to auto-cleanup
			redis_client.expire(key, self.period_seconds + 10)

			return True
		except Exception as e:
			frappe.logger().debug(f"Redis record error: {e}")
			return False

	def _clean_old_entries_fallback(self, key: str) -> None:
		"""Remove entries older than the period (fallback in-memory)."""
		if key not in self._fallback_history:
			return

		cutoff = time.time() - self.period_seconds
		self._fallback_history[key] = [
			ts for ts in self._fallback_history[key]
			if ts > cutoff
		]

	def check_rate_limit(self, identifier: str) -> tuple[bool, int]:
		"""
		Check if a call is allowed under the rate limit.

		Args:
			identifier: Unique identifier for the rate limit bucket

		Returns:
			Tuple of (is_allowed, remaining_calls)
		"""
		key = self._get_key(identifier)

		if self._use_redis:
			current_count = self._get_redis_count(key)
			if current_count >= 0:  # Redis succeeded
				remaining = max(0, self.max_calls - current_count)
				return (current_count < self.max_calls, remaining)

		# Fallback to in-memory
		self._clean_old_entries_fallback(key)

		if key not in self._fallback_history:
			self._fallback_history[key] = []

		current_count = len(self._fallback_history[key])
		remaining = max(0, self.max_calls - current_count)

		return (current_count < self.max_calls, remaining)

	def record_call(self, identifier: str) -> None:
		"""Record a call for rate limiting."""
		key = self._get_key(identifier)

		if self._use_redis:
			if self._record_redis_call(key):
				return

		# Fallback to in-memory
		if key not in self._fallback_history:
			self._fallback_history[key] = []
		self._fallback_history[key].append(time.time())

	def is_allowed(self, identifier: str) -> bool:
		"""
		Check if allowed and record the call if so.

		Args:
			identifier: Unique identifier for the rate limit bucket

		Returns:
			True if allowed, False if rate limited
		"""
		allowed, _ = self.check_rate_limit(identifier)
		if allowed:
			self.record_call(identifier)
		return allowed

	def get_remaining(self, identifier: str) -> int:
		"""
		Get remaining calls allowed for an identifier.

		Args:
			identifier: Unique identifier for the rate limit bucket

		Returns:
			Number of remaining calls allowed
		"""
		_, remaining = self.check_rate_limit(identifier)
		return remaining

	def reset(self, identifier: str) -> None:
		"""
		Reset rate limit for an identifier (admin use).

		Args:
			identifier: Unique identifier to reset
		"""
		key = self._get_key(identifier)

		if self._use_redis:
			try:
				cache = frappe.cache
				redis_client = cache.get_redis()
				redis_client.delete(key)
			except Exception:
				pass

		# Also clear fallback
		if key in self._fallback_history:
			del self._fallback_history[key]


def create_rate_limited_tool(
	tool_func: Callable,
	tool_name: str,
	max_calls: int = 30,
	period_seconds: int = 60,
) -> Callable:
	"""
	Wrap a tool function with rate limiting.

	Args:
		tool_func: The tool function to wrap
		tool_name: Name of the tool (used as rate limit key)
		max_calls: Maximum calls allowed in the period
		period_seconds: Time period in seconds

	Returns:
		Rate-limited wrapper function
	"""
	limiter = RateLimiter(
		max_calls=max_calls,
		period_seconds=period_seconds,
		key_prefix=tool_name,
	)

	@wraps(tool_func)
	def wrapper(*args, **kwargs):
		# Use tool name as identifier (rate limit per tool, not per document)
		if not limiter.is_allowed(tool_name):
			return {
				"error": f"Rate limit exceeded for {tool_name}. Please wait before trying again.",
				"rate_limited": True,
			}
		return tool_func(*args, **kwargs)

	return wrapper
