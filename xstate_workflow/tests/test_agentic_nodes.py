# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Integration Tests for Agentic Nodes.

Tests the AI agent workflow node functionality including:
- Handler integration
- Decision extraction
- Error classification
- Rate limiting
- Retry logic
"""

import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestAgenticNodeHandlers(FrappeTestCase):
	"""Tests for agentic node handlers."""

	def setUp(self):
		"""Set up test fixtures."""
		self.doctype = "ToDo"
		self.docname = None

		# Create a test document
		doc = frappe.get_doc({
			"doctype": "ToDo",
			"description": "Test agentic node document",
		})
		doc.insert()
		self.docname = doc.name
		frappe.db.commit()

	def tearDown(self):
		"""Clean up test fixtures."""
		if self.docname:
			frappe.delete_doc("ToDo", self.docname, force=True)
			frappe.db.commit()

	@patch("xstate_workflow.domain_nodes.handlers.frappe.enqueue")
	def test_handle_agentic_node_entry_enqueues_job(self, mock_enqueue):
		"""Test that handle_agentic_node_entry enqueues a background job."""
		from xstate_workflow.domain_nodes.handlers import handle_agentic_node_entry

		# Create mock instance
		mock_instance = MagicMock()
		mock_instance.name = "test-instance"
		mock_instance.context = "{}"
		mock_instance.status = "pending"

		# Create test node config
		node_config = {
			"id": "agentic_review",
			"meta": {
				"domain_node": {
					"type": "agentic",
					"agent_type": "react",
					"system_prompt": "Review the document and classify it.",
					"model": "gpt-4",
					"enabled_tools": [{"name": "frappe_read", "enabled": True}],
					"frappe_access": "read_only",
					"allowed_methods": [],
					"max_iterations": 10,
					"timeout_seconds": 300,
					"transition_mode": "decision",
					"decision_routes": [{"condition": "approved"}, {"condition": "rejected"}],
					"retry_on_failure": True,
					"max_retries": 3,
				}
			}
		}

		# Get test document
		ref_doc = frappe.get_doc(self.doctype, self.docname)

		# Call handler
		context = {}
		result = handle_agentic_node_entry(
			node_config=node_config,
			context=context,
			event={},
			ref_doc=ref_doc,
			instance=mock_instance
		)

		# Verify enqueue was called
		mock_enqueue.assert_called_once()
		call_kwargs = mock_enqueue.call_args[1]

		self.assertEqual(call_kwargs["executor_config"]["agent_type"], "react")
		self.assertEqual(call_kwargs["doctype"], self.doctype)
		self.assertEqual(call_kwargs["docname"], self.docname)
		self.assertEqual(call_kwargs["retry_config"]["retry_on_failure"], True)
		self.assertEqual(call_kwargs["retry_config"]["max_retries"], 3)

		# Verify context was updated
		self.assertTrue(result.get("_agent_started"))
		self.assertEqual(result.get("_agent_state"), "agentic_review")


class TestDecisionExtraction(FrappeTestCase):
	"""Tests for decision extraction from agent output."""

	def test_extract_decision_structured_json_block(self):
		"""Test extraction from JSON code block."""
		from xstate_workflow.langgraph.executor import extract_decision_structured

		# Create mock message with JSON block
		mock_message = MagicMock()
		mock_message.content = '''
Based on my analysis, here is my decision:

```json
{
  "decision": "approved",
  "reasoning": "The document meets all criteria"
}
```
'''

		decision, confidence = extract_decision_structured(mock_message, ["approved", "rejected"])

		self.assertEqual(decision, "approved")
		self.assertEqual(confidence, 1.0)

	def test_extract_decision_structured_inline_json(self):
		"""Test extraction from inline JSON object."""
		from xstate_workflow.langgraph.executor import extract_decision_structured

		mock_message = MagicMock()
		mock_message.content = 'After review: {"decision": "rejected", "reason": "missing fields"}'

		decision, confidence = extract_decision_structured(mock_message, ["approved", "rejected"])

		self.assertEqual(decision, "rejected")
		self.assertGreaterEqual(confidence, 0.9)

	def test_extract_decision_regex_fallback(self):
		"""Test extraction with regex patterns."""
		from xstate_workflow.langgraph.executor import extract_decision_structured

		mock_message = MagicMock()
		mock_message.content = "DECISION: needs_review"

		decision, confidence = extract_decision_structured(mock_message)

		self.assertEqual(decision, "needs_review")
		self.assertEqual(confidence, 1.0)

	def test_extract_decision_expected_match(self):
		"""Test extraction with expected decision matching."""
		from xstate_workflow.langgraph.executor import extract_decision_structured

		mock_message = MagicMock()
		mock_message.content = "This document should be approved based on the criteria."

		decision, confidence = extract_decision_structured(mock_message, ["approved", "rejected"])

		self.assertEqual(decision, "approved")
		self.assertGreaterEqual(confidence, 0.7)

	def test_fuzzy_match_decision(self):
		"""Test fuzzy matching for decisions."""
		from xstate_workflow.langgraph.executor import _fuzzy_match_decision

		# Exact match
		self.assertTrue(_fuzzy_match_decision("approved", "approved"))

		# Substring match
		self.assertTrue(_fuzzy_match_decision("approve", "approved"))

		# Similar strings
		self.assertTrue(_fuzzy_match_decision("approoved", "approved", threshold=0.8))

		# Different strings
		self.assertFalse(_fuzzy_match_decision("rejected", "approved"))


class TestErrorClassification(FrappeTestCase):
	"""Tests for error classification and retry logic."""

	def test_rate_limit_error_is_retryable(self):
		"""Test that rate limit errors are classified as retryable."""
		from xstate_workflow.langgraph.executor import classify_error

		error_type, is_retryable = classify_error("Error 429: Rate limit exceeded")
		self.assertEqual(error_type, "rate_limit")
		self.assertTrue(is_retryable)

		error_type, is_retryable = classify_error("Too many requests, please slow down")
		self.assertEqual(error_type, "rate_limit")
		self.assertTrue(is_retryable)

	def test_timeout_error_is_retryable(self):
		"""Test that timeout errors are classified as retryable."""
		from xstate_workflow.langgraph.executor import classify_error

		error_type, is_retryable = classify_error("Request timed out after 30 seconds")
		self.assertEqual(error_type, "timeout")
		self.assertTrue(is_retryable)

	def test_network_error_is_retryable(self):
		"""Test that network errors are classified as retryable."""
		from xstate_workflow.langgraph.executor import classify_error

		error_type, is_retryable = classify_error("Connection error: server refused")
		self.assertEqual(error_type, "network")
		self.assertTrue(is_retryable)

	def test_service_unavailable_is_retryable(self):
		"""Test that 503 errors are classified as retryable."""
		from xstate_workflow.langgraph.executor import classify_error

		error_type, is_retryable = classify_error("503 Service Unavailable")
		self.assertEqual(error_type, "service_unavailable")
		self.assertTrue(is_retryable)

	def test_auth_error_is_not_retryable(self):
		"""Test that authentication errors are not retryable."""
		from xstate_workflow.langgraph.executor import classify_error

		error_type, is_retryable = classify_error("Invalid API key provided")
		self.assertEqual(error_type, "auth")
		self.assertFalse(is_retryable)

		error_type, is_retryable = classify_error("401 Unauthorized")
		self.assertEqual(error_type, "auth")
		self.assertFalse(is_retryable)

	def test_permission_error_is_not_retryable(self):
		"""Test that permission errors are not retryable."""
		from xstate_workflow.langgraph.executor import classify_error

		error_type, is_retryable = classify_error("403 Permission denied")
		self.assertEqual(error_type, "permission")
		self.assertFalse(is_retryable)

	def test_config_error_is_not_retryable(self):
		"""Test that configuration errors are not retryable."""
		from xstate_workflow.langgraph.executor import classify_error

		error_type, is_retryable = classify_error("Invalid model specified")
		self.assertEqual(error_type, "config")
		self.assertFalse(is_retryable)

	def test_retry_delay_calculation(self):
		"""Test exponential backoff delay calculation."""
		from xstate_workflow.langgraph.executor import calculate_retry_delay

		# First retry: 2^0 * 10 = 10 seconds
		self.assertEqual(calculate_retry_delay(0), 10)

		# Second retry: 2^1 * 10 = 20 seconds
		self.assertEqual(calculate_retry_delay(1), 20)

		# Third retry: 2^2 * 10 = 40 seconds
		self.assertEqual(calculate_retry_delay(2), 40)

		# Cap at 300 seconds
		self.assertEqual(calculate_retry_delay(10), 300)


class TestRateLimiter(FrappeTestCase):
	"""Tests for the rate limiter."""

	def test_rate_limiter_allows_within_limit(self):
		"""Test that calls within limit are allowed."""
		from xstate_workflow.langgraph.audit import RateLimiter

		limiter = RateLimiter(max_calls=5, period_seconds=60, key_prefix="test")

		# First 5 calls should be allowed
		for i in range(5):
			self.assertTrue(limiter.is_allowed("test_bucket"))

	def test_rate_limiter_blocks_over_limit(self):
		"""Test that calls over limit are blocked."""
		from xstate_workflow.langgraph.audit import RateLimiter

		limiter = RateLimiter(max_calls=3, period_seconds=60, key_prefix="test_block")

		# First 3 calls should be allowed
		for i in range(3):
			self.assertTrue(limiter.is_allowed("test_bucket"))

		# 4th call should be blocked
		allowed, remaining = limiter.check_rate_limit("test_bucket")
		self.assertFalse(allowed)
		self.assertEqual(remaining, 0)


class TestCodeValidation(FrappeTestCase):
	"""Tests for code validation in the sandboxed executor."""

	def test_validate_code_blocks_dangerous_imports(self):
		"""Test that dangerous imports are blocked."""
		from xstate_workflow.langgraph.tools import validate_code

		# OS module
		is_safe, error = validate_code("import os\nos.system('rm -rf /')")
		self.assertFalse(is_safe)
		self.assertIn("dangerous", error.lower())

		# Subprocess
		is_safe, error = validate_code("import subprocess\nsubprocess.call(['ls'])")
		self.assertFalse(is_safe)

		# Socket
		is_safe, error = validate_code("import socket\nsocket.connect()")
		self.assertFalse(is_safe)

	def test_validate_code_blocks_dangerous_functions(self):
		"""Test that dangerous functions are blocked."""
		from xstate_workflow.langgraph.tools import validate_code

		# exec
		is_safe, error = validate_code("exec('print(1)')")
		self.assertFalse(is_safe)

		# eval
		is_safe, error = validate_code("eval('1+1')")
		self.assertFalse(is_safe)

		# open
		is_safe, error = validate_code("open('/etc/passwd', 'r')")
		self.assertFalse(is_safe)

	def test_validate_code_blocks_dunder_access(self):
		"""Test that __dunder__ attribute access is blocked."""
		from xstate_workflow.langgraph.tools import validate_code

		is_safe, error = validate_code("obj.__class__.__bases__")
		self.assertFalse(is_safe)

		is_safe, error = validate_code("''.__class__.__mro__[1].__subclasses__()")
		self.assertFalse(is_safe)

	def test_validate_code_allows_safe_code(self):
		"""Test that safe code is allowed."""
		from xstate_workflow.langgraph.tools import validate_code

		# Simple math
		is_safe, error = validate_code("x = 1 + 2\nprint(x)")
		self.assertTrue(is_safe)
		self.assertIsNone(error)

		# String operations
		is_safe, error = validate_code("s = 'hello'.upper()\nprint(s)")
		self.assertTrue(is_safe)

		# List operations
		is_safe, error = validate_code("lst = [1, 2, 3]\nlst.append(4)")
		self.assertTrue(is_safe)


class TestAuditLogging(FrappeTestCase):
	"""Tests for audit logging."""

	def test_sanitize_for_log_redacts_sensitive_fields(self):
		"""Test that sensitive fields are redacted."""
		from xstate_workflow.langgraph.audit import _sanitize_for_log

		data = {
			"user": "test@example.com",
			"password": "secret123",
			"api_key": "sk-12345",
			"result": "success"
		}

		sanitized = _sanitize_for_log(data)

		self.assertEqual(sanitized["user"], "test@example.com")
		self.assertEqual(sanitized["password"], "[REDACTED]")
		self.assertEqual(sanitized["api_key"], "[REDACTED]")
		self.assertEqual(sanitized["result"], "success")

	def test_sanitize_for_log_truncates_long_strings(self):
		"""Test that long strings are truncated."""
		from xstate_workflow.langgraph.audit import _sanitize_for_log

		long_string = "x" * 2000
		sanitized = _sanitize_for_log(long_string, max_length=100)

		self.assertLessEqual(len(sanitized), 150)  # 100 + truncation message
		self.assertIn("truncated", sanitized)


class TestDetermineTransitionEvent(FrappeTestCase):
	"""Tests for transition event determination."""

	def test_simple_mode_returns_success(self):
		"""Test that simple mode returns AGENT_SUCCESS."""
		from xstate_workflow.langgraph.executor import determine_transition_event

		result = {"messages": []}
		event = determine_transition_event(
			result=result,
			transition_mode="simple",
			decision_routes=[],
			custom_events=[]
		)

		self.assertEqual(event, "AGENT_SUCCESS")

	def test_decision_mode_returns_decision_event(self):
		"""Test that decision mode returns correct decision event."""
		from xstate_workflow.langgraph.executor import determine_transition_event

		mock_message = MagicMock()
		mock_message.content = "DECISION: approved"

		result = {"messages": [mock_message]}
		event = determine_transition_event(
			result=result,
			transition_mode="decision",
			decision_routes=[{"condition": "approved"}, {"condition": "rejected"}],
			custom_events=[]
		)

		self.assertEqual(event, "DECISION_APPROVED")

	def test_custom_events_mode_returns_event(self):
		"""Test that custom_events mode returns correct event."""
		from xstate_workflow.langgraph.executor import determine_transition_event

		mock_message = MagicMock()
		mock_message.content = "DECISION: escalate"

		result = {"messages": [mock_message]}
		event = determine_transition_event(
			result=result,
			transition_mode="custom_events",
			decision_routes=[],
			custom_events=[{"name": "escalate"}, {"name": "complete"}]
		)

		self.assertEqual(event, "ESCALATE")


if __name__ == "__main__":
	unittest.main()
