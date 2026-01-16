# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
LangGraph Agent Executor.

Provides the AgentExecutor class and run_agent function for executing
AI agents within workflow states.
"""

import json
import re
from difflib import SequenceMatcher
from typing import Any

import frappe
from frappe import _


# Error classification for retry logic
RETRYABLE_ERROR_PATTERNS = [
	"rate limit",
	"rate_limit",
	"429",
	"too many requests",
	"timeout",
	"timed out",
	"connection error",
	"connection refused",
	"network error",
	"temporarily unavailable",
	"service unavailable",
	"503",
	"502",
	"504",
	"overloaded",
	"capacity",
]

NON_RETRYABLE_ERROR_PATTERNS = [
	"authentication",
	"auth error",
	"invalid api key",
	"api_key",
	"unauthorized",
	"401",
	"403",
	"permission denied",
	"access denied",
	"invalid model",
	"model not found",
	"configuration error",
	"invalid request",
	"bad request",
	"400",
]


def classify_error(error: Exception | str) -> tuple[str, bool]:
	"""
	Classify an error as retryable or non-retryable.

	Args:
		error: The error to classify

	Returns:
		Tuple of (error_type, is_retryable)
		error_type: "rate_limit", "timeout", "network", "auth", "config", "unknown"
	"""
	error_str = str(error).lower()

	# Check non-retryable patterns first (more specific)
	for pattern in NON_RETRYABLE_ERROR_PATTERNS:
		if pattern in error_str:
			# Check auth patterns (check api key with both space and underscore)
			if "auth" in pattern or "api key" in pattern or "api_key" in pattern or "401" in pattern:
				return ("auth", False)
			# Check permission patterns
			if "403" in pattern or "permission" in pattern or "access" in pattern:
				return ("permission", False)
			# Check config patterns (must come after auth check)
			if "config" in pattern or "invalid" in pattern or "400" in pattern:
				return ("config", False)
			return ("non_retryable", False)

	# Check retryable patterns
	for pattern in RETRYABLE_ERROR_PATTERNS:
		if pattern in error_str:
			if "rate" in pattern or "429" in pattern or "too many" in pattern:
				return ("rate_limit", True)
			if "timeout" in pattern or "timed out" in pattern:
				return ("timeout", True)
			if "connection" in pattern or "network" in pattern:
				return ("network", True)
			if "503" in pattern or "502" in pattern or "504" in pattern or "unavailable" in pattern:
				return ("service_unavailable", True)
			return ("retryable", True)

	# Default to non-retryable for unknown errors
	return ("unknown", False)


def calculate_retry_delay(attempt: int) -> int:
	"""
	Calculate retry delay with exponential backoff.

	Args:
		attempt: Current attempt number (0-based)

	Returns:
		Delay in seconds (capped at 300)
	"""
	delay = min(300, (2**attempt) * 10)
	return delay


class AgentExecutor:
	"""
	Configuration holder for LangGraph agent execution.

	Stores agent configuration and provides serialization for background jobs.
	"""

	def __init__(
		self,
		agent_type: str,
		system_prompt: str,
		model: str | None,
		enabled_tools: list,
		frappe_access: str,
		allowed_methods: list,
		max_iterations: int,
		timeout_seconds: int,
	):
		self.agent_type = agent_type
		self.system_prompt = system_prompt
		self.model = model
		self.enabled_tools = enabled_tools
		self.frappe_access = frappe_access
		self.allowed_methods = allowed_methods
		self.max_iterations = max_iterations
		self.timeout_seconds = timeout_seconds

	def to_dict(self) -> dict:
		"""Serialize executor configuration for background job."""
		return {
			"agent_type": self.agent_type,
			"system_prompt": self.system_prompt,
			"model": self.model,
			"enabled_tools": self.enabled_tools,
			"frappe_access": self.frappe_access,
			"allowed_methods": self.allowed_methods,
			"max_iterations": self.max_iterations,
			"timeout_seconds": self.timeout_seconds,
		}

	@classmethod
	def from_dict(cls, data: dict) -> "AgentExecutor":
		"""Create executor from serialized configuration."""
		return cls(
			agent_type=data.get("agent_type", "react"),
			system_prompt=data.get("system_prompt", ""),
			model=data.get("model"),
			enabled_tools=data.get("enabled_tools", []),
			frappe_access=data.get("frappe_access", "none"),
			allowed_methods=data.get("allowed_methods", []),
			max_iterations=data.get("max_iterations", 10),
			timeout_seconds=data.get("timeout_seconds", 300),
		)


def get_llm(model: str | None):
	"""
	Get LLM instance based on model name.

	Args:
		model: Model identifier (e.g., "gpt-4", "claude-3-opus")

	Returns:
		LangChain LLM instance
	"""
	# Try to get settings, fall back to defaults if not configured
	try:
		settings = frappe.get_single("XState Workflow Settings")
		default_model = getattr(settings, "default_llm_model", None) or "gpt-4"
		openai_key = settings.get_password("openai_api_key") if hasattr(settings, "openai_api_key") else None
		anthropic_key = (
			settings.get_password("anthropic_api_key") if hasattr(settings, "anthropic_api_key") else None
		)
	except Exception:
		default_model = "gpt-4"
		openai_key = None
		anthropic_key = None

	if not model:
		model = default_model

	if model.startswith("gpt"):
		try:
			from langchain_openai import ChatOpenAI

			return ChatOpenAI(
				model=model,
				api_key=openai_key,
			)
		except ImportError:
			frappe.throw(_("langchain_openai is not installed. Run: pip install langchain-openai"))

	elif model.startswith("claude"):
		try:
			from langchain_anthropic import ChatAnthropic

			return ChatAnthropic(
				model=model,
				api_key=anthropic_key,
			)
		except ImportError:
			frappe.throw(_("langchain_anthropic is not installed. Run: pip install langchain-anthropic"))

	else:
		# Default to OpenAI for unknown models
		try:
			from langchain_openai import ChatOpenAI

			return ChatOpenAI(model=model, api_key=openai_key)
		except ImportError:
			frappe.throw(_("langchain_openai is not installed. Run: pip install langchain-openai"))


def _save_agent_checkpoint(
	doctype: str,
	docname: str,
	state_name: str,
	checkpoint_data: dict,
) -> None:
	"""
	Save agent checkpoint to Machine Instance context.

	Args:
		doctype: Document DocType
		docname: Document name
		state_name: Current state name
		checkpoint_data: Checkpoint data to save
	"""
	try:
		from xstate_workflow.workflow_engine import get_instance_for_doc

		instance = get_instance_for_doc(doctype, docname)
		if not instance:
			return

		context = json.loads(instance.context or "{}")
		context["_agent_checkpoint"] = {
			"state": state_name,
			"data": checkpoint_data,
			"timestamp": str(frappe.utils.now_datetime()),
		}
		instance.context = json.dumps(context)
		instance.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Failed to save agent checkpoint: {e}", "Agentic Node")


def _load_agent_checkpoint(doctype: str, docname: str, state_name: str) -> dict | None:
	"""
	Load agent checkpoint from Machine Instance context.

	Args:
		doctype: Document DocType
		docname: Document name
		state_name: Current state name

	Returns:
		Checkpoint data if valid, None otherwise
	"""
	try:
		from xstate_workflow.workflow_engine import get_instance_for_doc

		instance = get_instance_for_doc(doctype, docname)
		if not instance:
			return None

		context = json.loads(instance.context or "{}")
		checkpoint = context.get("_agent_checkpoint")

		if checkpoint and checkpoint.get("state") == state_name:
			return checkpoint.get("data")
	except Exception:
		pass

	return None


def _clear_agent_checkpoint(doctype: str, docname: str) -> None:
	"""Clear agent checkpoint after successful completion."""
	try:
		from xstate_workflow.workflow_engine import get_instance_for_doc

		instance = get_instance_for_doc(doctype, docname)
		if not instance:
			return

		context = json.loads(instance.context or "{}")
		if "_agent_checkpoint" in context:
			del context["_agent_checkpoint"]
			instance.context = json.dumps(context)
			instance.save(ignore_permissions=True)
			frappe.db.commit()
	except Exception:
		pass


def run_agent(
	executor_config: dict,
	doc: dict,
	doctype: str,
	docname: str,
	state_name: str,
	transition_mode: str,
	decision_routes: list,
	custom_events: list,
	retry_config: dict = None,
	attempt: int = 0,
) -> None:
	"""
	Background job to run LangGraph agent.

	This function is enqueued as a background job and executes the configured
	AI agent, then triggers the appropriate workflow transition based on results.

	Args:
		executor_config: Serialized AgentExecutor configuration
		doc: Document data as dict
		doctype: Document DocType
		docname: Document name
		state_name: Current workflow state name
		transition_mode: How to determine transition (simple, decision, custom_events, all)
		decision_routes: List of decision route configurations
		custom_events: List of custom event configurations
		retry_config: Retry configuration (retry_on_failure, max_retries)
		attempt: Current attempt number (0-based)
	"""
	retry_config = retry_config or {}
	retry_on_failure = retry_config.get("retry_on_failure", False)
	max_retries = retry_config.get("max_retries", 3)

	try:
		from langgraph.prebuilt import create_react_agent
	except ImportError:
		frappe.log_error("langgraph is not installed. Run: pip install langgraph", "Agentic Node Error")
		_trigger_failure_event(doctype, docname, "langgraph is not installed")
		return

	from xstate_workflow.langgraph.tools import ToolRegistry

	executor = AgentExecutor.from_dict(executor_config)

	# Get LLM
	try:
		llm = get_llm(executor.model)
	except Exception as e:
		error_type, is_retryable = classify_error(e)
		frappe.log_error(f"Failed to initialize LLM (type={error_type}): {e}", "Agentic Node Error")

		if is_retryable and retry_on_failure and attempt < max_retries:
			_schedule_retry(
				executor_config, doc, doctype, docname, state_name,
				transition_mode, decision_routes, custom_events,
				retry_config, attempt
			)
		else:
			_trigger_failure_event(doctype, docname, str(e))
		return

	# Build tools with role-based access control
	tool_registry = ToolRegistry(
		frappe_access=executor.frappe_access,
		allowed_methods=executor.allowed_methods,
		doc=doc,
		doctype=doctype,
		docname=docname,
	)
	tools = tool_registry.get_tools(executor.enabled_tools)

	# Create agent based on type
	try:
		if executor.agent_type == "react":
			agent = create_react_agent(llm, tools, state_modifier=executor.system_prompt)
		elif executor.agent_type == "tool_executor":
			from langgraph.prebuilt import ToolNode

			agent = ToolNode(tools)
		elif executor.agent_type == "plan_execute":
			# Plan and execute uses the same react agent with planning prompt
			planning_prompt = (
				f"{executor.system_prompt}\n\n"
				"Before taking any action, first create a step-by-step plan. "
				"Then execute the plan systematically, checking results at each step."
			)
			agent = create_react_agent(llm, tools, state_modifier=planning_prompt)
		else:
			# Default to react agent
			agent = create_react_agent(llm, tools, state_modifier=executor.system_prompt)
	except Exception as e:
		frappe.log_error(f"Failed to create agent: {e}", "Agentic Node Error")
		_trigger_failure_event(doctype, docname, str(e))
		return

	# Load checkpoint if retrying
	checkpoint = None
	if attempt > 0:
		checkpoint = _load_agent_checkpoint(doctype, docname, state_name)

	# Prepare input
	doc_summary = _format_doc_for_agent(doc, doctype, docname)
	input_data = {
		"messages": [
			("system", executor.system_prompt),
			("human", f"Process document {doctype}/{docname}.\n\nDocument data:\n{doc_summary}"),
		]
	}

	# Add checkpoint context if available
	if checkpoint and checkpoint.get("messages"):
		input_data["messages"] = checkpoint["messages"]

	# Run agent
	try:
		result = agent.invoke(input_data, config={"recursion_limit": executor.max_iterations})

		# Determine next event based on transition mode and result
		event = determine_transition_event(
			result=result,
			transition_mode=transition_mode,
			decision_routes=decision_routes,
			custom_events=custom_events,
		)

		# Clear checkpoint on success
		_clear_agent_checkpoint(doctype, docname)

		# Store result in context and trigger workflow transition
		_trigger_success_event(doctype, docname, event, result)

	except Exception as e:
		error_type, is_retryable = classify_error(e)
		frappe.log_error(
			f"Agent execution failed (attempt={attempt + 1}, type={error_type}): {e}",
			"Agentic Node Error"
		)

		# Save checkpoint for potential retry
		if retry_on_failure and attempt < max_retries:
			_save_agent_checkpoint(doctype, docname, state_name, {
				"attempt": attempt,
				"error": str(e),
				"error_type": error_type,
			})

		if is_retryable and retry_on_failure and attempt < max_retries:
			_schedule_retry(
				executor_config, doc, doctype, docname, state_name,
				transition_mode, decision_routes, custom_events,
				retry_config, attempt
			)
		else:
			_trigger_failure_event(doctype, docname, str(e))


def _schedule_retry(
	executor_config: dict,
	doc: dict,
	doctype: str,
	docname: str,
	state_name: str,
	transition_mode: str,
	decision_routes: list,
	custom_events: list,
	retry_config: dict,
	attempt: int,
) -> None:
	"""Schedule a retry with exponential backoff."""
	next_attempt = attempt + 1
	delay = calculate_retry_delay(attempt)

	frappe.log_error(
		f"Scheduling retry {next_attempt} for {doctype}/{docname} in {delay}s",
		"Agentic Node Retry"
	)

	# Get timeout from executor config
	timeout = executor_config.get("timeout_seconds", 300) + 60

	frappe.enqueue(
		"xstate_workflow.langgraph.executor.run_agent",
		queue="default",
		timeout=timeout,
		enqueue_after_commit=True,
		at_front=False,
		executor_config=executor_config,
		doc=doc,
		doctype=doctype,
		docname=docname,
		state_name=state_name,
		transition_mode=transition_mode,
		decision_routes=decision_routes,
		custom_events=custom_events,
		retry_config=retry_config,
		attempt=next_attempt,
		job_id=f"agent_retry_{doctype}_{docname}_{next_attempt}",
	)


def determine_transition_event(
	result: Any,
	transition_mode: str,
	decision_routes: list,
	custom_events: list,
) -> str:
	"""
	Determine which event to trigger based on agent result.

	Args:
		result: Agent execution result
		transition_mode: How to determine transition
		decision_routes: List of decision route configurations
		custom_events: List of custom event configurations

	Returns:
		Event name to trigger
	"""
	if transition_mode == "simple":
		return "AGENT_SUCCESS"

	# Extract decision from result
	last_message = result.get("messages", [])[-1] if result.get("messages") else None

	# Get expected decisions for fuzzy matching
	expected_decisions = []
	if transition_mode in ("decision", "all"):
		expected_decisions.extend([r.get("condition", "") for r in decision_routes])
	if transition_mode in ("custom_events", "all"):
		expected_decisions.extend([e.get("name", "") for e in custom_events])

	# Extract decision with structured parsing and fuzzy matching
	decision, confidence = extract_decision_structured(last_message, expected_decisions)

	if transition_mode in ("decision", "all"):
		for route in decision_routes:
			condition = route.get("condition", "")
			if condition.lower() == decision.lower():
				return f"DECISION_{condition.upper()}"
			# Try fuzzy match if no exact match
			if _fuzzy_match_decision(decision, condition):
				return f"DECISION_{condition.upper()}"

	if transition_mode in ("custom_events", "all"):
		for event in custom_events:
			name = event.get("name", "")
			if name.lower() == decision.lower():
				return name.upper()
			# Try fuzzy match if no exact match
			if _fuzzy_match_decision(decision, name):
				return name.upper()

	return "AGENT_SUCCESS"


def _fuzzy_match_decision(extracted: str, expected: str, threshold: float = 0.8) -> bool:
	"""
	Check if extracted decision fuzzy-matches expected decision.

	Args:
		extracted: The extracted decision string
		expected: The expected decision string
		threshold: Similarity threshold (0-1)

	Returns:
		True if similarity is above threshold
	"""
	if not extracted or not expected:
		return False

	extracted_lower = extracted.lower().strip()
	expected_lower = expected.lower().strip()

	# Exact match
	if extracted_lower == expected_lower:
		return True

	# Check if one contains the other
	if extracted_lower in expected_lower or expected_lower in extracted_lower:
		return True

	# Use sequence matcher for fuzzy matching
	ratio = SequenceMatcher(None, extracted_lower, expected_lower).ratio()
	return ratio >= threshold


def extract_decision_structured(message: Any, expected_decisions: list = None) -> tuple[str, float]:
	"""
	Extract decision/classification from agent's last message with structured parsing.

	Tries multiple extraction methods in order of preference:
	1. JSON block parsing (```json ... ```)
	2. Inline JSON object detection
	3. Structured decision markers (DECISION: xxx)
	4. Regex patterns for common formats
	5. Fuzzy matching against expected decisions

	Args:
		message: Last message from agent
		expected_decisions: List of expected decision values for fuzzy matching

	Returns:
		Tuple of (extracted decision, confidence 0-1)
	"""
	if not message:
		return ("success", 0.0)

	content = message.content if hasattr(message, "content") else str(message)
	expected_decisions = expected_decisions or []

	# Method 1: JSON block extraction (```json ... ```)
	json_block_match = re.search(r"```json\s*\n?(.*?)\n?```", content, re.DOTALL | re.IGNORECASE)
	if json_block_match:
		try:
			data = json.loads(json_block_match.group(1))
			# Look for decision-like keys
			for key in ["decision", "result", "outcome", "route", "action", "classification"]:
				if key in data:
					return (str(data[key]), 1.0)
			# Check for nested decision object
			if isinstance(data, dict):
				for key, value in data.items():
					if isinstance(value, str) and len(value) < 50:
						return (value, 0.9)
		except json.JSONDecodeError:
			pass

	# Method 2: Inline JSON object detection
	json_obj_match = re.search(r'\{[^{}]*"(?:decision|result|outcome)"[^{}]*\}', content, re.IGNORECASE)
	if json_obj_match:
		try:
			data = json.loads(json_obj_match.group(0))
			for key in ["decision", "result", "outcome"]:
				if key in data:
					return (str(data[key]), 0.95)
		except json.JSONDecodeError:
			pass

	# Method 3: Structured decision markers
	decision_patterns = [
		(r"DECISION:\s*['\"]?(\w+)['\"]?", 1.0),
		(r"(?:final\s+)?decision:\s*['\"]?(\w+)['\"]?", 0.95),
		(r"result:\s*['\"]?(\w+)['\"]?", 0.9),
		(r"outcome:\s*['\"]?(\w+)['\"]?", 0.9),
		(r"routing\s+to:\s*['\"]?(\w+)['\"]?", 0.85),
		(r"classified\s+as:\s*['\"]?(\w+)['\"]?", 0.85),
		(r"recommendation:\s*['\"]?(\w+)['\"]?", 0.8),
	]

	for pattern, confidence in decision_patterns:
		match = re.search(pattern, content, re.IGNORECASE)
		if match:
			return (match.group(1), confidence)

	# Method 4: Look for expected decisions mentioned in content
	if expected_decisions:
		content_lower = content.lower()
		for expected in expected_decisions:
			if not expected:
				continue
			expected_lower = expected.lower()
			# Check for exact word match (not substring)
			if re.search(rf"\b{re.escape(expected_lower)}\b", content_lower):
				return (expected, 0.7)

	# Method 5: Last resort - look for any capitalized word that might be a decision
	caps_match = re.search(r"\b([A-Z][A-Z_]+)\b", content)
	if caps_match:
		word = caps_match.group(1)
		if word not in ("I", "THE", "AND", "OR", "NOT", "FOR", "WITH"):
			return (word.lower(), 0.5)

	return ("success", 0.0)


def extract_decision(message: Any) -> str:
	"""
	Extract decision/classification from agent's last message.

	This is a backwards-compatible wrapper around extract_decision_structured.

	Args:
		message: Last message from agent

	Returns:
		Extracted decision string or "success" as default
	"""
	decision, _ = extract_decision_structured(message)
	return decision


def _format_doc_for_agent(doc: dict, doctype: str, docname: str) -> str:
	"""
	Format document data for agent consumption.

	Args:
		doc: Document data
		doctype: DocType name
		docname: Document name

	Returns:
		Formatted string representation
	"""
	# Filter out internal fields
	filtered_doc = {k: v for k, v in doc.items() if not k.startswith("_") and k not in ("modified", "creation")}

	lines = [f"DocType: {doctype}", f"Name: {docname}", "Fields:"]

	for key, value in filtered_doc.items():
		if value is not None and value != "":
			lines.append(f"  {key}: {value}")

	return "\n".join(lines)


def _trigger_success_event(doctype: str, docname: str, event: str, result: Any) -> None:
	"""Trigger success transition event."""
	from xstate_workflow.workflow_engine import trigger_event_sync

	# Extract useful info from result for context
	agent_output = None
	if result and result.get("messages"):
		last_msg = result["messages"][-1]
		if hasattr(last_msg, "content"):
			agent_output = last_msg.content
		else:
			agent_output = str(last_msg)

	try:
		trigger_event_sync(
			doctype,
			docname,
			event,
			{
				"agent_result": agent_output,
				"agent_success": True,
			},
		)
	except Exception as e:
		frappe.log_error(f"Failed to trigger success event: {e}", "Agentic Node Error")


def _trigger_failure_event(doctype: str, docname: str, error: str) -> None:
	"""Trigger failure transition event."""
	from xstate_workflow.workflow_engine import trigger_event_sync

	try:
		trigger_event_sync(
			doctype,
			docname,
			"AGENT_FAILURE",
			{
				"agent_error": error,
				"agent_success": False,
			},
		)
	except Exception as e:
		frappe.log_error(f"Failed to trigger failure event: {e}", "Agentic Node Error")
