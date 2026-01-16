# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Domain Node Handlers.

Provides handlers for domain-specific workflow nodes.
These handlers are called by the workflow engine when processing
domain-specific node types.
"""

import json
from typing import TYPE_CHECKING

import frappe
from frappe import _

if TYPE_CHECKING:
    from frappe.model.document import Document


def get_domain_node_actions(machine_doc, ref_doc, instance) -> dict:
    """
    Get built-in action functions for domain nodes.

    These actions are added to the workflow engine's action registry
    to handle domain-specific node behaviors.

    Args:
        machine_doc: State Machine document
        ref_doc: Reference document
        instance: Machine Instance

    Returns:
        Dict of action_name -> function
    """
    return {
        # Approval node actions
        "create_approval_task": lambda ctx, evt: _create_approval_task_action(
            ctx, evt, ref_doc, instance
        ),
        "cancel_approval_tasks": lambda ctx, evt: _cancel_approval_tasks_action(
            ctx, evt, instance
        ),

        # Auto-action node actions
        "submit_document": lambda ctx, evt: _submit_document_action(
            ctx, evt, ref_doc
        ),
        "cancel_document": lambda ctx, evt: _cancel_document_action(
            ctx, evt, ref_doc
        ),
        "update_field": lambda ctx, evt: _update_field_action(
            ctx, evt, ref_doc
        ),
        "update_status": lambda ctx, evt: _update_status_action(
            ctx, evt, ref_doc, instance
        ),
        "send_notification": lambda ctx, evt: _send_notification_action(
            ctx, evt, ref_doc
        ),
        "call_api": lambda ctx, evt: _call_api_action(
            ctx, evt, ref_doc
        ),
        "run_method": lambda ctx, evt: _run_method_action(
            ctx, evt, ref_doc
        ),

        # Assignment resolver action
        "resolve_assignment": lambda ctx, evt: _resolve_assignment_action(
            ctx, evt, ref_doc, instance
        ),

        # Agentic node actions
        "start_agent": lambda ctx, evt: _start_agent_action(
            ctx, evt, ref_doc, instance
        ),
    }


def handle_approval_node_entry(
    node_config: dict,
    context: dict,
    event: dict,
    ref_doc: "Document",
    instance: "Document"
) -> dict:
    """
    Handle entry into an approval node.

    Creates an approval task and pauses the workflow.

    Args:
        node_config: The approval node configuration
        context: Current workflow context
        event: Triggering event data
        ref_doc: Reference document
        instance: Machine Instance

    Returns:
        Updated context
    """
    from xstate_workflow.resolvers import resolve_assignment
    from xstate_workflow.approval import create_approval_task

    # Extract approval node configuration
    node_data = node_config.get("meta", {}).get("domain_node", {})
    if not node_data:
        # Fall back to checking for approval-specific entry actions
        return context

    resolver_config = node_data.get("resolver", {})
    available_actions = node_data.get("available_actions", ["Approve", "Reject"])
    sla_hours = node_data.get("sla_hours")
    priority = node_data.get("priority", "Medium")
    node_id = node_config.get("id") or context.get("_current_state", "")
    node_label = node_data.get("label") or node_config.get("label", node_id)

    # Resolve assignees
    try:
        assignees = resolve_assignment(ref_doc, resolver_config, context)
    except Exception as e:
        frappe.log_error(
            f"Failed to resolve assignment: {e}",
            "Approval Node Entry"
        )
        # Use fallback if configured
        fallback = node_data.get("fallback_user")
        if fallback:
            assignees = [fallback]
        else:
            raise

    if not assignees:
        frappe.throw(_("No assignees found for approval node"))

    # Create approval task
    task = create_approval_task(
        workflow_instance=instance.name,
        node_id=node_id,
        node_label=node_label,
        assignees=assignees,
        available_actions=available_actions,
        sla_hours=sla_hours,
        priority=priority
    )

    # Store task reference in context
    context["_current_approval_task"] = task.name
    context["_approval_assignees"] = assignees

    # Mark instance as waiting for approval
    instance.status = "active"
    instance.save(ignore_permissions=True)

    return context


def handle_approval_node_exit(
    node_config: dict,
    context: dict,
    event: dict,
    ref_doc: "Document",
    instance: "Document"
) -> dict:
    """
    Handle exit from an approval node.

    Records the approval decision in context.

    Args:
        node_config: The approval node configuration
        context: Current workflow context
        event: The approval action event
        ref_doc: Reference document
        instance: Machine Instance

    Returns:
        Updated context
    """
    # Record approval in context
    if "_approval_history" not in context:
        context["_approval_history"] = []

    context["_approval_history"].append({
        "node_id": node_config.get("id"),
        "action": event.get("type", "UNKNOWN"),
        "user": event.get("completed_by") or frappe.session.user,
        "comments": event.get("comments"),
        "timestamp": str(frappe.utils.now_datetime())
    })

    # Clear current task reference
    context.pop("_current_approval_task", None)
    context.pop("_approval_assignees", None)

    return context


def handle_auto_action(
    action_type: str,
    action_config: dict,
    context: dict,
    event: dict,
    ref_doc: "Document",
    instance: "Document"
) -> dict:
    """
    Handle execution of an auto-action node.

    Args:
        action_type: Type of action (submit, cancel, update_field, etc.)
        action_config: Action-specific configuration
        context: Current workflow context
        event: Triggering event
        ref_doc: Reference document
        instance: Machine Instance

    Returns:
        Updated context
    """
    action_handlers = {
        "submit_document": _submit_document_action,
        "cancel_document": _cancel_document_action,
        "update_field": _update_field_action,
        "update_status": _update_status_action,
        "send_notification": _send_notification_action,
        "call_api": _call_api_action,
        "run_method": _run_method_action,
    }

    handler = action_handlers.get(action_type)
    if handler:
        return handler(context, {**event, **action_config}, ref_doc)

    frappe.log_error(
        f"Unknown auto-action type: {action_type}",
        "Auto Action Handler"
    )
    return context


def evaluate_threshold_condition(
    condition_config: dict,
    context: dict,
    ref_doc: "Document"
) -> bool:
    """
    Evaluate a threshold gate condition.

    Args:
        condition_config: Threshold configuration with field, operator, value
        context: Current workflow context
        ref_doc: Reference document

    Returns:
        True if condition passes, False otherwise
    """
    from xstate_workflow.resolvers.base import get_field_value

    field = condition_config.get("field")
    operator = condition_config.get("operator", "gt")
    threshold = condition_config.get("value", 0)

    # Get field value
    value = get_field_value(ref_doc, field)
    if value is None:
        value = 0

    # Convert to float for comparison
    try:
        value = float(value)
        threshold = float(threshold)
    except (ValueError, TypeError):
        return False

    # Evaluate based on operator
    operators = {
        "gt": value > threshold,
        "gte": value >= threshold,
        "lt": value < threshold,
        "lte": value <= threshold,
        "eq": value == threshold,
        "ne": value != threshold,
    }

    return operators.get(operator, False)


def evaluate_classification_branch(
    branch_config: dict,
    context: dict,
    ref_doc: "Document"
) -> str | None:
    """
    Evaluate a classification branch and return the matching branch target.

    Args:
        branch_config: Branch configuration with field and branches
        context: Current workflow context
        ref_doc: Reference document

    Returns:
        Target state/event for matching branch, or default if no match
    """
    from xstate_workflow.resolvers.base import get_field_value

    field = branch_config.get("field")
    branches = branch_config.get("branches", [])
    default = branch_config.get("default")

    # Get field value
    value = get_field_value(ref_doc, field)

    # Find matching branch
    for branch in branches:
        branch_value = branch.get("value")
        if value == branch_value:
            return branch.get("target") or branch.get("event")

    return default


# Private action implementations

def _create_approval_task_action(context: dict, event: dict, ref_doc, instance) -> dict:
    """Create approval task action."""
    handle_approval_node_entry(
        node_config=event.get("node_config", {}),
        context=context,
        event=event,
        ref_doc=ref_doc,
        instance=instance
    )
    return context


def _cancel_approval_tasks_action(context: dict, event: dict, instance) -> dict:
    """Cancel pending approval tasks action."""
    from xstate_workflow.approval import cancel_pending_tasks
    cancel_pending_tasks(instance.name)
    return context


def _submit_document_action(context: dict, event: dict, ref_doc) -> dict:
    """Submit document action."""
    if ref_doc.docstatus == 0:
        ref_doc.submit()
        context["_submitted"] = True
    return context


def _cancel_document_action(context: dict, event: dict, ref_doc) -> dict:
    """Cancel document action."""
    if ref_doc.docstatus == 1:
        ref_doc.cancel()
        context["_cancelled"] = True
    return context


def _update_field_action(context: dict, event: dict, ref_doc) -> dict:
    """Update field action."""
    field = event.get("field")
    value = event.get("value")

    if field and value is not None:
        # Support dynamic values from context
        if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
            context_key = value[2:-2].strip()
            value = context.get(context_key, value)

        frappe.db.set_value(
            ref_doc.doctype,
            ref_doc.name,
            field,
            value,
            update_modified=True
        )
        ref_doc.reload()

    return context


def _update_status_action(context: dict, event: dict, ref_doc, instance) -> dict:
    """Update workflow status action."""
    status = event.get("status") or event.get("value")

    if status:
        # Update custom workflow_state field if it exists
        meta = frappe.get_meta(ref_doc.doctype)
        if meta.has_field("workflow_state"):
            frappe.db.set_value(
                ref_doc.doctype,
                ref_doc.name,
                "workflow_state",
                status
            )
            ref_doc.reload()

    return context


def _send_notification_action(context: dict, event: dict, ref_doc) -> dict:
    """Send notification action."""
    notification_type = event.get("notification_type", "System")
    recipients = event.get("recipients", [])
    subject = event.get("subject", "")
    message = event.get("message", "")

    # Template substitution
    subject = _substitute_template(subject, context, ref_doc)
    message = _substitute_template(message, context, ref_doc)

    if notification_type == "Email":
        for recipient in recipients:
            try:
                frappe.sendmail(
                    recipients=[recipient],
                    subject=subject,
                    message=message,
                    reference_doctype=ref_doc.doctype,
                    reference_name=ref_doc.name
                )
            except Exception as e:
                frappe.log_error(f"Failed to send email: {e}", "Workflow Notification")

    elif notification_type == "System":
        for recipient in recipients:
            try:
                frappe.publish_realtime(
                    "workflow_notification",
                    {
                        "subject": subject,
                        "message": message,
                        "doctype": ref_doc.doctype,
                        "docname": ref_doc.name
                    },
                    user=recipient
                )
            except Exception:
                pass

    return context


def _call_api_action(context: dict, event: dict, ref_doc) -> dict:
    """Call external API action."""
    import requests

    url = event.get("url")
    method = event.get("method", "POST")
    headers = event.get("headers", {})
    payload = event.get("payload", {})

    if not url:
        return context

    # Template substitution in payload
    payload = _substitute_dict_template(payload, context, ref_doc)

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=payload,
            timeout=30
        )

        context["_api_response"] = {
            "status_code": response.status_code,
            "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        }

    except Exception as e:
        context["_api_error"] = str(e)
        frappe.log_error(f"API call failed: {e}", "Workflow API Action")

    return context


def _run_method_action(context: dict, event: dict, ref_doc) -> dict:
    """Run document method action."""
    method_name = event.get("method")
    args = event.get("args", {})

    if not method_name:
        return context

    if hasattr(ref_doc, method_name):
        method = getattr(ref_doc, method_name)
        if callable(method):
            try:
                result = method(**args)
                context["_method_result"] = result
            except Exception as e:
                context["_method_error"] = str(e)
                frappe.log_error(f"Method call failed: {e}", "Workflow Method Action")

    return context


def _resolve_assignment_action(context: dict, event: dict, ref_doc, instance) -> dict:
    """Resolve assignment and store in context."""
    from xstate_workflow.resolvers import resolve_assignment

    resolver_config = event.get("resolver_config", {})

    try:
        assignees = resolve_assignment(ref_doc, resolver_config, context)
        context["_resolved_assignees"] = assignees
    except Exception as e:
        context["_resolver_error"] = str(e)

    return context


def _substitute_template(template: str, context: dict, ref_doc) -> str:
    """Substitute template variables."""
    if not template:
        return template

    # Simple substitution for {{variable}} patterns
    import re

    def replace_var(match):
        var_name = match.group(1).strip()

        # Check context first
        if var_name in context:
            return str(context[var_name])

        # Check document fields
        if hasattr(ref_doc, var_name):
            return str(getattr(ref_doc, var_name))

        return match.group(0)  # Return original if not found

    return re.sub(r"\{\{(\w+)\}\}", replace_var, template)


def _substitute_dict_template(d: dict, context: dict, ref_doc) -> dict:
    """Recursively substitute template variables in dict values."""
    result = {}
    for key, value in d.items():
        if isinstance(value, str):
            result[key] = _substitute_template(value, context, ref_doc)
        elif isinstance(value, dict):
            result[key] = _substitute_dict_template(value, context, ref_doc)
        else:
            result[key] = value
    return result


# Agentic Node Handlers

def handle_agentic_node_entry(
    node_config: dict,
    context: dict,
    event: dict,
    ref_doc: "Document",
    instance: "Document"
) -> dict:
    """
    Handle entry into an agentic (AI agent) node.

    Starts AI agent execution as a background job.

    Args:
        node_config: The agentic node configuration
        context: Current workflow context
        event: Triggering event data
        ref_doc: Reference document
        instance: Machine Instance

    Returns:
        Updated context
    """
    from xstate_workflow.langgraph.executor import AgentExecutor

    # Extract agentic node configuration from meta
    meta = node_config.get("meta", {})
    domain_node = meta.get("domain_node", {})

    if not domain_node or domain_node.get("type") != "agentic":
        # Not an agentic node, skip
        return context

    # Build executor configuration
    executor = AgentExecutor(
        agent_type=domain_node.get("agent_type", "react"),
        system_prompt=domain_node.get("system_prompt", ""),
        model=domain_node.get("model"),
        enabled_tools=domain_node.get("enabled_tools", []),
        frappe_access=domain_node.get("frappe_access", "none"),
        allowed_methods=domain_node.get("allowed_methods", []),
        max_iterations=domain_node.get("max_iterations", 10),
        timeout_seconds=domain_node.get("timeout_seconds", 300),
    )

    # Get transition configuration
    transition_mode = domain_node.get("transition_mode", "simple")
    decision_routes = domain_node.get("decision_routes", [])
    custom_events = domain_node.get("custom_events", [])

    # Get retry configuration
    retry_config = {
        "retry_on_failure": domain_node.get("retry_on_failure", False),
        "max_retries": domain_node.get("max_retries", 3),
    }

    # Get document data
    doc_data = ref_doc.as_dict()

    # Get current state name
    state_name = node_config.get("id") or context.get("_current_state", "")

    # Calculate timeout with buffer
    timeout = domain_node.get("timeout_seconds", 300) + 60

    # Enqueue agent execution as background job
    frappe.enqueue(
        "xstate_workflow.langgraph.executor.run_agent",
        queue="default",
        timeout=timeout,
        executor_config=executor.to_dict(),
        doc=doc_data,
        doctype=ref_doc.doctype,
        docname=ref_doc.name,
        state_name=state_name,
        transition_mode=transition_mode,
        decision_routes=decision_routes,
        custom_events=custom_events,
        retry_config=retry_config,
        attempt=0,
    )

    # Mark in context that agent is running
    context["_agent_started"] = True
    context["_agent_state"] = state_name

    # Update instance status
    instance.status = "active"
    instance.save(ignore_permissions=True)

    return context


def _start_agent_action(context: dict, event: dict, ref_doc, instance) -> dict:
    """Start agent action - delegates to handle_agentic_node_entry."""
    handle_agentic_node_entry(
        node_config=event.get("node_config", {}),
        context=context,
        event=event,
        ref_doc=ref_doc,
        instance=instance
    )
    return context
