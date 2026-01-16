# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Tests for REST Fetch Node Handler.

Tests the REST Fetch domain node functionality including:
- Successful data fetching and storage in context
- URL and body template substitution
- Error handling and event triggering
- Timeout handling
"""

import json
import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestRestFetchNodeHandler(FrappeTestCase):
	"""Tests for the REST Fetch node handler."""

	def setUp(self):
		"""Set up test fixtures."""
		self.doctype = "ToDo"
		self.docname = None

		# Create a test document
		doc = frappe.get_doc(
			{
				"doctype": "ToDo",
				"description": "Test REST fetch node document",
			}
		)
		doc.insert()
		self.docname = doc.name
		frappe.db.commit()

	def tearDown(self):
		"""Clean up test fixtures."""
		if self.docname:
			frappe.delete_doc("ToDo", self.docname, force=True)
			frappe.db.commit()

	@patch("requests.request")
	def test_rest_fetch_stores_response_in_context(self, mock_request):
		"""Test successful fetch stores response in configured context key."""
		from xstate_workflow.domain_nodes.handlers import handle_rest_fetch_node_entry

		# Mock successful response
		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.ok = True
		mock_response.json.return_value = {"customer_name": "Acme Corp", "balance": 5000}
		mock_request.return_value = mock_response

		# Create mock instance
		mock_instance = MagicMock()
		mock_instance.name = "test-instance"
		mock_instance.context = "{}"

		# Node config for REST fetch
		node_config = {
			"id": "fetch_customer_data",
			"meta": {
				"domain_node": {
					"type": "rest_fetch",
					"url": "https://api.example.com/customers/{{owner}}",
					"method": "GET",
					"authType": "none",
					"saveResponseTo": "customer_data",
					"onSuccess": "DATA_FETCHED",
					"onError": "FETCH_FAILED",
					"timeoutSeconds": 30,
				}
			},
		}

		# Get test document
		ref_doc = frappe.get_doc(self.doctype, self.docname)

		# Call handler
		context = {}
		result = handle_rest_fetch_node_entry(
			node_config=node_config,
			context=context,
			event={},
			ref_doc=ref_doc,
			instance=mock_instance,
		)

		# Verify response was stored
		self.assertIn("customer_data", result)
		self.assertEqual(result["customer_data"]["customer_name"], "Acme Corp")
		self.assertEqual(result["customer_data"]["balance"], 5000)

		# Verify success event triggered
		self.assertEqual(result.get("_trigger_event"), "DATA_FETCHED")
		self.assertTrue(result.get("_rest_fetch_success"))

	@patch("requests.request")
	def test_rest_fetch_triggers_success_event(self, mock_request):
		"""Test successful fetch triggers onSuccess event."""
		from xstate_workflow.domain_nodes.handlers import handle_rest_fetch_node_entry

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.ok = True
		mock_response.json.return_value = {"data": "test"}
		mock_request.return_value = mock_response

		mock_instance = MagicMock()
		mock_instance.name = "test-instance"
		mock_instance.context = "{}"

		node_config = {
			"id": "fetch_node",
			"meta": {
				"domain_node": {
					"type": "rest_fetch",
					"url": "https://api.example.com/data",
					"method": "GET",
					"authType": "none",
					"saveResponseTo": "api_response",
					"onSuccess": "CUSTOM_SUCCESS_EVENT",
					"onError": "CUSTOM_ERROR_EVENT",
				}
			},
		}

		ref_doc = frappe.get_doc(self.doctype, self.docname)

		result = handle_rest_fetch_node_entry(
			node_config=node_config,
			context={},
			event={},
			ref_doc=ref_doc,
			instance=mock_instance,
		)

		self.assertEqual(result.get("_trigger_event"), "CUSTOM_SUCCESS_EVENT")

	@patch("requests.request")
	def test_rest_fetch_triggers_error_event_on_failure(self, mock_request):
		"""Test failed fetch triggers onError event."""
		from xstate_workflow.domain_nodes.handlers import handle_rest_fetch_node_entry

		# Mock failed response
		mock_response = MagicMock()
		mock_response.status_code = 500
		mock_response.ok = False
		mock_response.text = "Internal Server Error"
		mock_response.raise_for_status.side_effect = Exception("Server Error")
		mock_request.return_value = mock_response

		mock_instance = MagicMock()
		mock_instance.name = "test-instance"
		mock_instance.context = "{}"

		node_config = {
			"id": "fetch_node",
			"meta": {
				"domain_node": {
					"type": "rest_fetch",
					"url": "https://api.example.com/data",
					"method": "GET",
					"authType": "none",
					"saveResponseTo": "api_response",
					"onSuccess": "SUCCESS",
					"onError": "FETCH_FAILED",
				}
			},
		}

		ref_doc = frappe.get_doc(self.doctype, self.docname)

		result = handle_rest_fetch_node_entry(
			node_config=node_config,
			context={},
			event={},
			ref_doc=ref_doc,
			instance=mock_instance,
		)

		self.assertEqual(result.get("_trigger_event"), "FETCH_FAILED")
		self.assertFalse(result.get("_rest_fetch_success"))
		self.assertIn("_rest_fetch_error", result)

	@patch("requests.request")
	def test_rest_fetch_substitutes_url_fields(self, mock_request):
		"""Test that {{field}} in URL is replaced with document field."""
		from xstate_workflow.domain_nodes.handlers import handle_rest_fetch_node_entry

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.ok = True
		mock_response.json.return_value = {}
		mock_request.return_value = mock_response

		mock_instance = MagicMock()
		mock_instance.name = "test-instance"
		mock_instance.context = "{}"

		# Create a doc with a specific field value
		# Mock needs to support both as_dict() and attribute access (getattr)
		ref_doc = MagicMock()
		ref_doc.name = self.docname
		ref_doc.customer_id = "CUST123"
		ref_doc.order_id = "ORD456"
		ref_doc.as_dict.return_value = {
			"name": self.docname,
			"customer_id": "CUST123",
			"order_id": "ORD456",
		}

		node_config = {
			"id": "fetch_node",
			"meta": {
				"domain_node": {
					"type": "rest_fetch",
					"url": "https://api.example.com/customers/{{customer_id}}/orders/{{order_id}}",
					"method": "GET",
					"authType": "none",
					"saveResponseTo": "result",
					"onSuccess": "SUCCESS",
					"onError": "ERROR",
				}
			},
		}

		result = handle_rest_fetch_node_entry(
			node_config=node_config,
			context={},
			event={},
			ref_doc=ref_doc,
			instance=mock_instance,
		)

		# Verify the URL was correctly substituted
		call_kwargs = mock_request.call_args
		expected_url = "https://api.example.com/customers/CUST123/orders/ORD456"
		self.assertEqual(call_kwargs.kwargs["url"], expected_url)

	@patch("requests.request")
	def test_rest_fetch_respects_timeout(self, mock_request):
		"""Test request uses configured timeout."""
		from xstate_workflow.domain_nodes.handlers import handle_rest_fetch_node_entry

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.ok = True
		mock_response.json.return_value = {}
		mock_request.return_value = mock_response

		mock_instance = MagicMock()
		mock_instance.name = "test-instance"
		mock_instance.context = "{}"

		node_config = {
			"id": "fetch_node",
			"meta": {
				"domain_node": {
					"type": "rest_fetch",
					"url": "https://api.example.com/data",
					"method": "GET",
					"authType": "none",
					"saveResponseTo": "result",
					"onSuccess": "SUCCESS",
					"onError": "ERROR",
					"timeoutSeconds": 60,  # Custom timeout
				}
			},
		}

		ref_doc = frappe.get_doc(self.doctype, self.docname)

		result = handle_rest_fetch_node_entry(
			node_config=node_config,
			context={},
			event={},
			ref_doc=ref_doc,
			instance=mock_instance,
		)

		# Verify timeout was passed
		call_kwargs = mock_request.call_args
		self.assertEqual(call_kwargs.kwargs["timeout"], 60)

	@patch("requests.request")
	def test_rest_fetch_handles_timeout_exception(self, mock_request):
		"""Test timeout exception triggers error event."""
		from requests.exceptions import Timeout

		from xstate_workflow.domain_nodes.handlers import handle_rest_fetch_node_entry

		mock_request.side_effect = Timeout("Request timed out")

		mock_instance = MagicMock()
		mock_instance.name = "test-instance"
		mock_instance.context = "{}"

		node_config = {
			"id": "fetch_node",
			"meta": {
				"domain_node": {
					"type": "rest_fetch",
					"url": "https://slow.api.example.com/data",
					"method": "GET",
					"authType": "none",
					"saveResponseTo": "result",
					"onSuccess": "SUCCESS",
					"onError": "TIMEOUT_ERROR",
					"timeoutSeconds": 5,
				}
			},
		}

		ref_doc = frappe.get_doc(self.doctype, self.docname)

		result = handle_rest_fetch_node_entry(
			node_config=node_config,
			context={},
			event={},
			ref_doc=ref_doc,
			instance=mock_instance,
		)

		self.assertEqual(result.get("_trigger_event"), "TIMEOUT_ERROR")
		self.assertFalse(result.get("_rest_fetch_success"))
		self.assertIn("timed out", result.get("_rest_fetch_error", "").lower())

	@patch("requests.request")
	def test_rest_fetch_post_with_body(self, mock_request):
		"""Test POST request with substituted body."""
		from xstate_workflow.domain_nodes.handlers import handle_rest_fetch_node_entry

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.ok = True
		mock_response.json.return_value = {"created": True}
		mock_request.return_value = mock_response

		mock_instance = MagicMock()
		mock_instance.name = "test-instance"
		mock_instance.context = "{}"

		# Mock needs to support both as_dict() and attribute access (getattr)
		ref_doc = MagicMock()
		ref_doc.name = "DOC001"
		ref_doc.amount = 1500
		ref_doc.currency = "USD"
		ref_doc.as_dict.return_value = {
			"name": "DOC001",
			"amount": 1500,
			"currency": "USD",
		}

		body_template = json.dumps(
			{
				"document_id": "{{name}}",
				"total": "{{amount}}",
				"currency": "{{currency}}",
			}
		)

		node_config = {
			"id": "fetch_node",
			"meta": {
				"domain_node": {
					"type": "rest_fetch",
					"url": "https://api.example.com/submit",
					"method": "POST",
					"authType": "none",
					"body": body_template,
					"saveResponseTo": "result",
					"onSuccess": "SUCCESS",
					"onError": "ERROR",
				}
			},
		}

		result = handle_rest_fetch_node_entry(
			node_config=node_config,
			context={},
			event={},
			ref_doc=ref_doc,
			instance=mock_instance,
		)

		# Verify POST was made with correct body
		call_kwargs = mock_request.call_args
		self.assertEqual(call_kwargs.kwargs["method"], "POST")

		# Body should have been substituted
		sent_body = call_kwargs.kwargs.get("data") or call_kwargs.kwargs.get("json")
		self.assertIsNotNone(sent_body)

	@patch("requests.request")
	def test_rest_fetch_with_api_key_auth(self, mock_request):
		"""Test request with API key authentication."""
		from xstate_workflow.domain_nodes.handlers import handle_rest_fetch_node_entry

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.ok = True
		mock_response.json.return_value = {}
		mock_request.return_value = mock_response

		mock_instance = MagicMock()
		mock_instance.name = "test-instance"
		mock_instance.context = "{}"

		node_config = {
			"id": "fetch_node",
			"meta": {
				"domain_node": {
					"type": "rest_fetch",
					"url": "https://api.example.com/secure",
					"method": "GET",
					"authType": "api_key",
					"authCredential": "my-secret-api-key",
					"saveResponseTo": "result",
					"onSuccess": "SUCCESS",
					"onError": "ERROR",
				}
			},
		}

		ref_doc = frappe.get_doc(self.doctype, self.docname)

		result = handle_rest_fetch_node_entry(
			node_config=node_config,
			context={},
			event={},
			ref_doc=ref_doc,
			instance=mock_instance,
		)

		# Verify X-API-Key header was set (api_key auth uses X-API-Key, not Authorization)
		call_kwargs = mock_request.call_args
		self.assertIn("X-API-Key", call_kwargs.kwargs["headers"])
		self.assertEqual(call_kwargs.kwargs["headers"]["X-API-Key"], "my-secret-api-key")

	@patch("requests.request")
	def test_rest_fetch_preserves_existing_context(self, mock_request):
		"""Test that existing context variables are preserved."""
		from xstate_workflow.domain_nodes.handlers import handle_rest_fetch_node_entry

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.ok = True
		mock_response.json.return_value = {"new_data": "fetched"}
		mock_request.return_value = mock_response

		mock_instance = MagicMock()
		mock_instance.name = "test-instance"
		mock_instance.context = "{}"

		node_config = {
			"id": "fetch_node",
			"meta": {
				"domain_node": {
					"type": "rest_fetch",
					"url": "https://api.example.com/data",
					"method": "GET",
					"authType": "none",
					"saveResponseTo": "api_data",
					"onSuccess": "SUCCESS",
					"onError": "ERROR",
				}
			},
		}

		ref_doc = frappe.get_doc(self.doctype, self.docname)

		# Existing context
		existing_context = {
			"approval_level": 2,
			"previous_state": "pending",
		}

		result = handle_rest_fetch_node_entry(
			node_config=node_config,
			context=existing_context,
			event={},
			ref_doc=ref_doc,
			instance=mock_instance,
		)

		# Verify existing context preserved
		self.assertEqual(result.get("approval_level"), 2)
		self.assertEqual(result.get("previous_state"), "pending")

		# Verify new data added
		self.assertEqual(result.get("api_data"), {"new_data": "fetched"})


class TestRestFetchAction(FrappeTestCase):
	"""Tests for the REST Fetch action wrapper."""

	@patch("xstate_workflow.domain_nodes.handlers.handle_rest_fetch_node_entry")
	def test_rest_fetch_action_calls_handler(self, mock_handler):
		"""Test that the action wrapper calls the handler correctly."""
		from xstate_workflow.domain_nodes.handlers import _rest_fetch_action

		mock_handler.return_value = {"_trigger_event": "SUCCESS"}

		mock_instance = MagicMock()
		mock_ref_doc = MagicMock()

		# _rest_fetch_action takes (context, event, ref_doc, instance)
		# and gets node_config from event
		event = {"node_config": {"id": "test"}}
		context = {}

		result = _rest_fetch_action(
			context=context,
			event=event,
			ref_doc=mock_ref_doc,
			instance=mock_instance,
		)

		mock_handler.assert_called_once()
		# Result is the modified context
		self.assertEqual(result, context)


if __name__ == "__main__":
	unittest.main()
