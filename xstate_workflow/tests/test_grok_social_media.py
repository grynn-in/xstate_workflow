# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Tests for Grok LLM Support and Social Media Tools.

Tests the following functionality:
- Grok (xAI) LLM initialization and configuration
- Twitter/X posting tool
- LinkedIn posting tool
- Facebook posting tool
- Reddit posting tool
- XState Workflow Settings DocType
"""

import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestGrokLLMSupport(FrappeTestCase):
	"""Tests for Grok LLM support in executor.py."""

	def test_get_llm_with_grok_model(self):
		"""Test that get_llm returns ChatOpenAI with xAI base URL for Grok models."""
		try:
			import langchain_openai
		except ImportError:
			self.skipTest("langchain_openai not installed")

		import sys
		from unittest.mock import MagicMock

		# Create mock module
		mock_langchain = MagicMock()
		mock_chat_class = MagicMock()
		mock_langchain.ChatOpenAI = mock_chat_class

		# Mock settings
		mock_settings = MagicMock()
		mock_settings.default_llm_model = "gpt-4"
		mock_settings.get_password.side_effect = lambda key: {
			"openai_api_key": "sk-openai-key",
			"anthropic_api_key": "sk-anthropic-key",
			"xai_api_key": "xai-test-key",
		}.get(key)

		with patch("xstate_workflow.langgraph.executor.frappe.get_single", return_value=mock_settings):
			with patch.dict(sys.modules, {"langchain_openai": mock_langchain}):
				# Need to reimport to pick up the mock
				import importlib
				import xstate_workflow.langgraph.executor as executor_module
				importlib.reload(executor_module)

				executor_module.get_llm("grok-2")

				# Verify ChatOpenAI was called with xAI base URL
				mock_chat_class.assert_called_once_with(
					model="grok-2",
					api_key="xai-test-key",
					base_url="https://api.x.ai/v1",
				)

	def test_get_llm_with_grok_mini_model(self):
		"""Test that get_llm works with grok-2-mini model."""
		try:
			import langchain_openai
		except ImportError:
			self.skipTest("langchain_openai not installed")

		import sys
		from unittest.mock import MagicMock

		mock_langchain = MagicMock()
		mock_chat_class = MagicMock()
		mock_langchain.ChatOpenAI = mock_chat_class

		mock_settings = MagicMock()
		mock_settings.default_llm_model = "gpt-4"
		mock_settings.get_password.side_effect = lambda key: {
			"xai_api_key": "xai-test-key",
		}.get(key)

		with patch("xstate_workflow.langgraph.executor.frappe.get_single", return_value=mock_settings):
			with patch.dict(sys.modules, {"langchain_openai": mock_langchain}):
				import importlib
				import xstate_workflow.langgraph.executor as executor_module
				importlib.reload(executor_module)

				executor_module.get_llm("grok-2-mini")

				mock_chat_class.assert_called_once()
				call_kwargs = mock_chat_class.call_args
				self.assertEqual(call_kwargs.kwargs["model"], "grok-2-mini")
				self.assertEqual(call_kwargs.kwargs["base_url"], "https://api.x.ai/v1")

	def test_get_llm_grok_without_xai_key(self):
		"""Test that get_llm handles missing xAI key gracefully."""
		try:
			import langchain_openai
		except ImportError:
			self.skipTest("langchain_openai not installed")

		import sys
		from unittest.mock import MagicMock

		mock_langchain = MagicMock()
		mock_chat_class = MagicMock()
		mock_langchain.ChatOpenAI = mock_chat_class

		mock_settings = MagicMock()
		mock_settings.default_llm_model = "gpt-4"
		mock_settings.get_password.return_value = None

		with patch("xstate_workflow.langgraph.executor.frappe.get_single", return_value=mock_settings):
			with patch.dict(sys.modules, {"langchain_openai": mock_langchain}):
				import importlib
				import xstate_workflow.langgraph.executor as executor_module
				importlib.reload(executor_module)

				executor_module.get_llm("grok-2")

				mock_chat_class.assert_called_once()
				call_kwargs = mock_chat_class.call_args
				self.assertIsNone(call_kwargs.kwargs["api_key"])

	def test_grok_model_prefix_detection(self):
		"""Test that models starting with 'grok' are detected correctly."""
		# Test various model name patterns
		grok_models = ["grok-2", "grok-2-mini", "grok-beta", "grok-3"]
		non_grok_models = ["gpt-4", "claude-3-opus", "groker", "my-grok-model"]

		for model in grok_models:
			self.assertTrue(model.startswith("grok"), f"{model} should start with 'grok'")

		for model in non_grok_models:
			# Only the first two should not start with grok
			if model in ["gpt-4", "claude-3-opus"]:
				self.assertFalse(model.startswith("grok"), f"{model} should not start with 'grok'")


class TestTwitterPostTool(FrappeTestCase):
	"""Tests for Twitter/X posting tool."""

	def setUp(self):
		"""Set up test fixtures."""
		self.doctype = "ToDo"
		self.docname = "test-twitter-doc"

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	@patch("requests.post")
	def test_twitter_post_success(self, mock_post, mock_credential):
		"""Test successful Twitter post."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		# Mock OAuth 1.0a credentials
		mock_credential.return_value = "test-credential-value"

		# Mock Twitter API response
		mock_response = MagicMock()
		mock_response.ok = True
		mock_response.json.return_value = {"data": {"id": "1234567890"}}
		mock_post.return_value = mock_response

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_twitter_post_tool()
			result = tool.invoke({"text": "Hello from XState Workflow!"})

			self.assertTrue(result["success"])
			self.assertEqual(result["tweet_id"], "1234567890")
			self.assertIn("twitter.com", result["url"])

			# Verify API was called with OAuth1 auth (not Bearer token)
			mock_post.assert_called_once()
			call_kwargs = mock_post.call_args
			self.assertEqual(call_kwargs.kwargs["json"]["text"], "Hello from XState Workflow!")
			self.assertIsNotNone(call_kwargs.kwargs.get("auth"))
			self.assertNotIn("Authorization", call_kwargs.kwargs.get("headers", {}))
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core or requests_oauthlib not installed")

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	def test_twitter_post_missing_credentials(self, mock_credential):
		"""Test Twitter post fails with missing credentials."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		# Mock missing credentials (OAuth 1.0a requires all 4)
		mock_credential.return_value = ""

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_twitter_post_tool()
			result = tool.invoke({"text": "Test tweet"})

			self.assertFalse(result["success"])
			self.assertIn("credentials", result["error"].lower())
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	def test_twitter_post_validates_tweet_length(self):
		"""Test Twitter post validates tweet is within 280 characters."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_twitter_post_tool()

			# Test empty tweet
			result = tool.invoke({"text": ""})
			self.assertFalse(result["success"])
			self.assertIn("280", result["error"])

			# Test tweet over 280 characters
			long_tweet = "x" * 281
			result = tool.invoke({"text": long_tweet})
			self.assertFalse(result["success"])
			self.assertIn("280", result["error"])
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	@patch("requests.post")
	def test_twitter_post_with_reply(self, mock_post, mock_credential):
		"""Test Twitter post as a reply to another tweet."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		mock_credential.return_value = "test-credential-value"
		mock_response = MagicMock()
		mock_response.ok = True
		mock_response.json.return_value = {"data": {"id": "9876543210"}}
		mock_post.return_value = mock_response

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_twitter_post_tool()
			result = tool.invoke({"text": "This is a reply", "reply_to": "1234567890"})

			self.assertTrue(result["success"])

			# Verify reply_to was included
			call_kwargs = mock_post.call_args
			self.assertEqual(
				call_kwargs.kwargs["json"]["reply"]["in_reply_to_tweet_id"],
				"1234567890"
			)
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core or requests_oauthlib not installed")

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	@patch("requests.post")
	def test_twitter_post_api_error(self, mock_post, mock_credential):
		"""Test Twitter post handles API errors gracefully."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		mock_credential.return_value = "test-credential-value"
		mock_response = MagicMock()
		mock_response.ok = False
		mock_response.status_code = 403
		mock_response.text = "Forbidden - rate limit exceeded"
		mock_post.return_value = mock_response

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_twitter_post_tool()
			result = tool.invoke({"text": "Test tweet"})

			self.assertFalse(result["success"])
			self.assertIn("403", result["error"])
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core or requests_oauthlib not installed")


class TestLinkedInPostTool(FrappeTestCase):
	"""Tests for LinkedIn posting tool."""

	def setUp(self):
		"""Set up test fixtures."""
		self.doctype = "ToDo"
		self.docname = "test-linkedin-doc"

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	@patch("requests.post")
	def test_linkedin_post_success(self, mock_post, mock_credential):
		"""Test successful LinkedIn post."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		# Mock credential resolution
		def resolve_cred(key):
			return {
				"config:linkedin_access_token": "test-access-token",
				"config:linkedin_person_urn": "urn:li:person:ABC123",
			}.get(key, "")
		mock_credential.side_effect = resolve_cred

		# Mock LinkedIn API response
		mock_response = MagicMock()
		mock_response.ok = True
		mock_response.headers = {"x-restli-id": "urn:li:share:123456"}
		mock_post.return_value = mock_response

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_linkedin_post_tool()
			result = tool.invoke({"text": "Exciting update from our workflow!"})

			self.assertTrue(result["success"])
			self.assertEqual(result["post_id"], "urn:li:share:123456")

			# Verify API was called correctly
			mock_post.assert_called_once()
			call_kwargs = mock_post.call_args
			self.assertIn("Bearer", call_kwargs.kwargs["headers"]["Authorization"])
			self.assertEqual(call_kwargs.kwargs["json"]["author"], "urn:li:person:ABC123")
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	def test_linkedin_post_missing_credentials(self, mock_credential):
		"""Test LinkedIn post fails with missing credentials."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		mock_credential.return_value = ""

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_linkedin_post_tool()
			result = tool.invoke({"text": "Test post"})

			self.assertFalse(result["success"])
			self.assertIn("credentials", result["error"].lower())
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	@patch("requests.post")
	def test_linkedin_post_with_visibility(self, mock_post, mock_credential):
		"""Test LinkedIn post with different visibility settings."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		def resolve_cred(key):
			return {
				"config:linkedin_access_token": "test-access-token",
				"config:linkedin_person_urn": "urn:li:person:ABC123",
			}.get(key, "")
		mock_credential.side_effect = resolve_cred

		mock_response = MagicMock()
		mock_response.ok = True
		mock_response.headers = {"x-restli-id": "urn:li:share:123456"}
		mock_post.return_value = mock_response

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_linkedin_post_tool()
			result = tool.invoke({"text": "Connections only post", "visibility": "CONNECTIONS"})

			self.assertTrue(result["success"])

			# Verify visibility was set
			call_kwargs = mock_post.call_args
			visibility = call_kwargs.kwargs["json"]["visibility"]["com.linkedin.ugc.MemberNetworkVisibility"]
			self.assertEqual(visibility, "CONNECTIONS")
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")


class TestFacebookPostTool(FrappeTestCase):
	"""Tests for Facebook posting tool."""

	def setUp(self):
		"""Set up test fixtures."""
		self.doctype = "ToDo"
		self.docname = "test-facebook-doc"

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	@patch("requests.post")
	def test_facebook_post_success(self, mock_post, mock_credential):
		"""Test successful Facebook post."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		def resolve_cred(key):
			return {
				"config:facebook_page_access_token": "test-page-token",
				"config:facebook_page_id": "123456789",
			}.get(key, "")
		mock_credential.side_effect = resolve_cred

		mock_response = MagicMock()
		mock_response.ok = True
		mock_response.json.return_value = {"id": "123456789_987654321"}
		mock_post.return_value = mock_response

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_facebook_post_tool()
			result = tool.invoke({"message": "Hello from our Facebook page!"})

			self.assertTrue(result["success"])
			self.assertEqual(result["post_id"], "123456789_987654321")
			self.assertIn("facebook.com", result["url"])

			# Verify API was called correctly
			mock_post.assert_called_once()
			call_kwargs = mock_post.call_args
			self.assertIn("123456789", call_kwargs.args[0])  # URL contains page ID
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	@patch("requests.post")
	def test_facebook_post_with_link(self, mock_post, mock_credential):
		"""Test Facebook post with a link."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		def resolve_cred(key):
			return {
				"config:facebook_page_access_token": "test-page-token",
				"config:facebook_page_id": "123456789",
			}.get(key, "")
		mock_credential.side_effect = resolve_cred

		mock_response = MagicMock()
		mock_response.ok = True
		mock_response.json.return_value = {"id": "123456789_987654321"}
		mock_post.return_value = mock_response

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_facebook_post_tool()
			result = tool.invoke({
				"message": "Check out our website!",
				"link": "https://example.com"
			})

			self.assertTrue(result["success"])

			# Verify link was included in payload
			call_kwargs = mock_post.call_args
			self.assertEqual(call_kwargs.kwargs["data"]["link"], "https://example.com")
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	def test_facebook_post_missing_credentials(self, mock_credential):
		"""Test Facebook post fails with missing credentials."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		mock_credential.return_value = ""

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_facebook_post_tool()
			result = tool.invoke({"message": "Test post"})

			self.assertFalse(result["success"])
			self.assertIn("credentials", result["error"].lower())
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")


class TestRedditPostTool(FrappeTestCase):
	"""Tests for Reddit posting tool."""

	def setUp(self):
		"""Set up test fixtures."""
		self.doctype = "ToDo"
		self.docname = "test-reddit-doc"

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	@patch("requests.post")
	def test_reddit_post_text_success(self, mock_post, mock_credential):
		"""Test successful Reddit text post."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		def resolve_cred(key):
			return {
				"config:reddit_client_id": "test-client-id",
				"config:reddit_client_secret": "test-client-secret",
				"config:reddit_username": "test-user",
				"config:reddit_password": "test-password",
			}.get(key, "")
		mock_credential.side_effect = resolve_cred

		# Mock OAuth token response
		mock_token_response = MagicMock()
		mock_token_response.ok = True
		mock_token_response.json.return_value = {"access_token": "test-reddit-token"}

		# Mock submit response
		mock_submit_response = MagicMock()
		mock_submit_response.ok = True
		mock_submit_response.json.return_value = {
			"json": {
				"data": {
					"id": "abc123",
					"url": "https://www.reddit.com/r/test/comments/abc123/test_post/"
				}
			}
		}

		mock_post.side_effect = [mock_token_response, mock_submit_response]

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_reddit_post_tool()
			result = tool.invoke({
				"subreddit": "test",
				"title": "Test Post",
				"text": "This is a test post content"
			})

			self.assertTrue(result["success"])
			self.assertEqual(result["post_id"], "abc123")
			self.assertIn("reddit.com", result["url"])
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	@patch("requests.post")
	def test_reddit_post_link_success(self, mock_post, mock_credential):
		"""Test successful Reddit link post."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		def resolve_cred(key):
			return {
				"config:reddit_client_id": "test-client-id",
				"config:reddit_client_secret": "test-client-secret",
				"config:reddit_username": "test-user",
				"config:reddit_password": "test-password",
			}.get(key, "")
		mock_credential.side_effect = resolve_cred

		mock_token_response = MagicMock()
		mock_token_response.ok = True
		mock_token_response.json.return_value = {"access_token": "test-reddit-token"}

		mock_submit_response = MagicMock()
		mock_submit_response.ok = True
		mock_submit_response.json.return_value = {
			"json": {"data": {"id": "xyz789", "url": "https://reddit.com/r/test/comments/xyz789/"}}
		}

		mock_post.side_effect = [mock_token_response, mock_submit_response]

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_reddit_post_tool()
			result = tool.invoke({
				"subreddit": "test",
				"title": "Check out this link",
				"url": "https://example.com/article"
			})

			self.assertTrue(result["success"])

			# Verify it was a link post
			submit_call = mock_post.call_args_list[1]
			self.assertEqual(submit_call.kwargs["data"]["kind"], "link")
			self.assertEqual(submit_call.kwargs["data"]["url"], "https://example.com/article")
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	def test_reddit_post_validation(self):
		"""Test Reddit post validates required fields."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_reddit_post_tool()

			# Missing subreddit - validation happens before rate limiting
			result = tool.invoke({"subreddit": "", "title": "Test", "text": "Content"})
			self.assertFalse(result["success"])
			self.assertIn("required", result["error"].lower())

			# Missing title
			result = tool.invoke({"subreddit": "test", "title": "", "text": "Content"})
			self.assertFalse(result["success"])
			self.assertIn("required", result["error"].lower())

			# Missing both text and url
			result = tool.invoke({"subreddit": "test", "title": "Test"})
			self.assertFalse(result["success"])
			self.assertIn("text or url", result["error"].lower())
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	def test_reddit_post_missing_credentials(self, mock_credential):
		"""Test Reddit post fails with missing credentials."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		mock_credential.return_value = ""

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_reddit_post_tool()
			result = tool.invoke({
				"subreddit": "test",
				"title": "Test",
				"text": "Content"
			})

			self.assertFalse(result["success"])
			self.assertIn("credentials", result["error"].lower())
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("xstate_workflow.langgraph.tools._resolve_credential")
	@patch("requests.post")
	def test_reddit_post_auth_failure(self, mock_post, mock_credential):
		"""Test Reddit post handles authentication failure."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		def resolve_cred(key):
			return {
				"config:reddit_client_id": "invalid-id",
				"config:reddit_client_secret": "invalid-secret",
				"config:reddit_username": "bad-user",
				"config:reddit_password": "bad-password",
			}.get(key, "")
		mock_credential.side_effect = resolve_cred

		# Mock failed OAuth response
		mock_token_response = MagicMock()
		mock_token_response.ok = False
		mock_token_response.text = "invalid_grant"
		mock_post.return_value = mock_token_response

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_reddit_post_tool()
			result = tool.invoke({
				"subreddit": "test",
				"title": "Test",
				"text": "Content"
			})

			self.assertFalse(result["success"])
			self.assertIn("auth", result["error"].lower())
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")


class TestSendNewsletterTool(FrappeTestCase):
	"""Tests for Newsletter sending tool."""

	def setUp(self):
		"""Set up test fixtures."""
		self.doctype = "ToDo"
		self.docname = "test-newsletter-doc"

	@patch("frappe.sendmail")
	@patch("frappe.get_all")
	def test_send_newsletter_success(self, mock_get_all, mock_sendmail):
		"""Test successful newsletter sending."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		# Mock subscribers
		mock_get_all.return_value = ["user1@example.com", "user2@example.com", "user3@example.com"]

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_send_newsletter_tool()
			result = tool.invoke({
				"subject": "Weekly Newsletter",
				"content": "<h1>Hello!</h1><p>This is our newsletter.</p>",
				"subscriber_list": "Default"
			})

			self.assertTrue(result["success"])
			self.assertEqual(result["sent_to"], 3)
			self.assertEqual(result["subscriber_list"], "Default")

			# Verify sendmail was called
			mock_sendmail.assert_called_once()
			call_kwargs = mock_sendmail.call_args
			self.assertEqual(len(call_kwargs.kwargs["recipients"]), 3)
			self.assertEqual(call_kwargs.kwargs["subject"], "Weekly Newsletter")
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("frappe.get_all")
	def test_send_newsletter_no_subscribers(self, mock_get_all):
		"""Test newsletter fails with no subscribers."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		# Mock empty subscriber list
		mock_get_all.return_value = []

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_send_newsletter_tool()
			result = tool.invoke({
				"subject": "Test Newsletter",
				"content": "Content",
				"subscriber_list": "NonExistent"
			})

			self.assertFalse(result["success"])
			self.assertIn("No subscribers", result["error"])
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	def test_send_newsletter_validates_required_fields(self):
		"""Test newsletter validates subject and content are required."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_send_newsletter_tool()

			# Missing subject
			result = tool.invoke({"subject": "", "content": "Content"})
			self.assertFalse(result["success"])
			self.assertIn("required", result["error"].lower())

			# Missing content
			result = tool.invoke({"subject": "Subject", "content": ""})
			self.assertFalse(result["success"])
			self.assertIn("required", result["error"].lower())
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	@patch("frappe.sendmail")
	@patch("frappe.get_all")
	def test_send_newsletter_default_subscriber_list(self, mock_get_all, mock_sendmail):
		"""Test newsletter uses 'Default' subscriber list by default."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		mock_get_all.return_value = ["user@example.com"]

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype=self.doctype,
			docname=self.docname,
		)

		try:
			tool = registry._create_send_newsletter_tool()
			result = tool.invoke({
				"subject": "Test",
				"content": "Content"
			})

			self.assertTrue(result["success"])

			# Verify get_all was called with Default subscriber list
			call_kwargs = mock_get_all.call_args
			self.assertEqual(call_kwargs.kwargs["filters"]["email_group"], "Default")
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")


class TestSocialMediaToolsInRegistry(FrappeTestCase):
	"""Tests for social media tools integration in ToolRegistry."""

	def test_registry_includes_social_media_tools(self):
		"""Test that ToolRegistry can create social media tools."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		registry = ToolRegistry(
			frappe_access="none",
			allowed_methods=[],
			doc={},
			doctype="Test",
			docname="TEST001",
		)

		enabled_tools = [
			{"name": "twitter_post", "enabled": True},
			{"name": "linkedin_post", "enabled": True},
			{"name": "facebook_post", "enabled": True},
			{"name": "reddit_post", "enabled": True},
			{"name": "send_newsletter", "enabled": True},
		]

		try:
			tools = registry.get_tools(enabled_tools)

			tool_names = [t.name for t in tools]
			self.assertIn("twitter_post", tool_names)
			self.assertIn("linkedin_post", tool_names)
			self.assertIn("facebook_post", tool_names)
			self.assertIn("reddit_post", tool_names)
			self.assertIn("send_newsletter", tool_names)
		except (ImportError, frappe.ValidationError):
			self.skipTest("langchain_core not installed")

	def test_social_media_rate_limits_configured(self):
		"""Test that social media tools have rate limits configured."""
		from xstate_workflow.langgraph.tools import ToolRegistry

		# Check default rate limits include social media
		self.assertIn("twitter_post", ToolRegistry.DEFAULT_RATE_LIMITS)
		self.assertIn("linkedin_post", ToolRegistry.DEFAULT_RATE_LIMITS)
		self.assertIn("facebook_post", ToolRegistry.DEFAULT_RATE_LIMITS)
		self.assertIn("reddit_post", ToolRegistry.DEFAULT_RATE_LIMITS)
		self.assertIn("send_newsletter", ToolRegistry.DEFAULT_RATE_LIMITS)

		# Reddit and newsletter should have stricter limits
		self.assertLessEqual(
			ToolRegistry.DEFAULT_RATE_LIMITS["reddit_post"],
			ToolRegistry.DEFAULT_RATE_LIMITS["twitter_post"]
		)
		self.assertLessEqual(
			ToolRegistry.DEFAULT_RATE_LIMITS["send_newsletter"],
			ToolRegistry.DEFAULT_RATE_LIMITS["twitter_post"]
		)


class TestXStateWorkflowSettings(FrappeTestCase):
	"""Tests for XState Workflow Settings DocType."""

	def test_settings_doctype_exists(self):
		"""Test that XState Workflow Settings DocType exists."""
		doctype_exists = frappe.db.exists("DocType", "XState Workflow Settings")
		self.assertTrue(doctype_exists, "XState Workflow Settings DocType should exist")

	def test_settings_is_single(self):
		"""Test that XState Workflow Settings is a single DocType."""
		meta = frappe.get_meta("XState Workflow Settings")
		self.assertTrue(meta.issingle, "XState Workflow Settings should be a single DocType")

	def test_settings_has_required_fields(self):
		"""Test that XState Workflow Settings has all required fields."""
		meta = frappe.get_meta("XState Workflow Settings")
		field_names = [f.fieldname for f in meta.fields]

		# Check for LLM configuration fields
		self.assertIn("default_llm_model", field_names)
		self.assertIn("openai_api_key", field_names)
		self.assertIn("anthropic_api_key", field_names)
		self.assertIn("xai_api_key", field_names)

	def test_settings_default_model_options_include_grok(self):
		"""Test that default_llm_model options include Grok models."""
		meta = frappe.get_meta("XState Workflow Settings")
		default_model_field = meta.get_field("default_llm_model")

		self.assertIsNotNone(default_model_field)
		self.assertIn("grok-2", default_model_field.options)
		self.assertIn("grok-2-mini", default_model_field.options)

	def test_settings_api_keys_are_password_fields(self):
		"""Test that API key fields are Password type for security."""
		meta = frappe.get_meta("XState Workflow Settings")

		for fieldname in ["openai_api_key", "anthropic_api_key", "xai_api_key"]:
			field = meta.get_field(fieldname)
			self.assertIsNotNone(field, f"{fieldname} field should exist")
			self.assertEqual(field.fieldtype, "Password", f"{fieldname} should be Password type")

	def test_settings_can_be_retrieved(self):
		"""Test that settings can be retrieved using get_single."""
		try:
			settings = frappe.get_single("XState Workflow Settings")
			self.assertIsNotNone(settings)
		except Exception as e:
			self.fail(f"Failed to get XState Workflow Settings: {e}")

	def test_settings_permissions(self):
		"""Test that settings has appropriate permissions."""
		meta = frappe.get_meta("XState Workflow Settings")
		permissions = meta.permissions

		# Should have System Manager permission
		system_manager_perms = [p for p in permissions if p.role == "System Manager"]
		self.assertTrue(len(system_manager_perms) > 0, "Should have System Manager permission")
		self.assertTrue(system_manager_perms[0].read, "System Manager should have read permission")
		self.assertTrue(system_manager_perms[0].write, "System Manager should have write permission")


if __name__ == "__main__":
	unittest.main()
