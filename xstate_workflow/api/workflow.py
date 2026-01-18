# Copyright (c) 2024, Grynn GmbH and contributors
# For license information, please see license.txt

"""
Workflow API Endpoints

This module provides RESTful API endpoints for workflow operations.
All endpoints are whitelisted and can be called via frappe.call() or HTTP.

API Documentation
=================

Base URL: /api/method/xstate_workflow.xstate_workflow.api.workflow

Endpoints:
----------

1. GET /get_workflow_state
   Get the current workflow state for a document.

   Parameters:
   - doctype (str): Document type name
   - docname (str): Document name

   Returns:
   {
       "has_workflow": bool,
       "current_state": str,
       "available_events": [
           {"event": str, "target": str, "enabled": bool, "guards": [str]}
       ],
       "context": dict,
       "instance_name": str
   }

2. POST /trigger_workflow_event
   Trigger a workflow event/transition.

   Parameters:
   - doctype (str): Document type name
   - docname (str): Document name
   - event (str): Event name to trigger
   - data (dict, optional): Event payload data

   Returns:
   {
       "success": bool,
       "previous_state": str,
       "new_state": str,
       "context": dict,
       "error": str (if failed)
   }

3. POST /reset_workflow
   Reset a workflow instance to its initial state.

   Parameters:
   - doctype (str): Document type name
   - docname (str): Document name

   Returns:
   {
       "success": bool,
       "new_state": str
   }

4. GET /list_workflows
   List all available workflow definitions.

   Parameters:
   - attached_to (str, optional): Filter by attached DocType

   Returns:
   [
       {
           "machine_id": str,
           "title": str,
           "attached_doctype": str,
           "is_active": bool
       }
   ]

5. GET /get_workflow_definition
   Get a workflow definition (state machine configuration).

   Parameters:
   - machine_id (str): State machine ID

   Returns:
   {
       "machine_id": str,
       "title": str,
       "json_config": str (XState JSON),
       "attached_doctype": str
   }

6. POST /save_workflow_definition
   Save or update a workflow definition.

   Parameters:
   - machine_id (str): State machine ID
   - title (str): Human-readable title
   - json_config (str): XState JSON configuration
   - attached_doctype (str, optional): DocType to attach workflow to
   - workflow_builder_config (str, optional): Visual builder config

   Returns:
   {
       "success": bool,
       "name": str
   }

7. GET /get_workflow_history
   Get transition history for a document.

   Parameters:
   - doctype (str): Document type name
   - docname (str): Document name
   - limit (int, optional): Max records (default 20)

   Returns:
   [
       {
           "from_state": str,
           "to_state": str,
           "event": str,
           "timestamp": str,
           "user": str
       }
   ]

8. GET /get_doctype_fields
   Get fields for a DocType (for guard builder).

   Parameters:
   - doctype (str): DocType name

   Returns:
   [
       {
           "fieldname": str,
           "fieldtype": str,
           "label": str,
           "options": str
       }
   ]

9. GET /get_mcp_connections
   Get available MCP server connections for the current user.

   Returns:
   [
       {
           "connection_name": str,
           "description": str,
           "transport_type": str,
           "is_active": bool,
           "tool_count": int (optional, if cached)
       }
   ]

10. GET /get_mcp_tools
    Get available tools from an MCP server connection.

    Parameters:
    - connection_name (str): Name of the MCP Server Connection

    Returns:
    {
        "success": bool,
        "tools": [
            {
                "name": str,
                "description": str,
                "parameters": dict
            }
        ],
        "error": str (if failed)
    }
"""

import json
import frappe
from frappe import _


@frappe.whitelist()
def get_workflow_state(doctype: str, docname: str) -> dict:
    """Get current workflow state for a document."""
    from xstate_workflow.workflow_engine import get_machine_state
    return get_machine_state(doctype, docname)


@frappe.whitelist()
def trigger_workflow_event(
    doctype: str,
    docname: str,
    event: str,
    data: dict | str = None
) -> dict:
    """Trigger a workflow event on a document."""
    from xstate_workflow.workflow_engine import trigger_event_sync

    if isinstance(data, str):
        data = json.loads(data) if data else {}

    return trigger_event_sync(doctype, docname, event, json.dumps(data or {}))


@frappe.whitelist()
def reset_workflow(doctype: str, docname: str) -> dict:
    """Reset a workflow instance to initial state."""
    from xstate_workflow.workflow_engine import reset_instance
    return reset_instance(doctype, docname)


@frappe.whitelist()
def start_workflow(doctype: str, docname: str) -> dict:
    """
    Manually start a workflow for a document.

    Used when auto_start_on_create is disabled on the State Machine,
    allowing users to explicitly start the workflow via a button.
    Also works to restart a cancelled workflow.

    Parameters:
    - doctype (str): Document type name
    - docname (str): Document name

    Returns:
    {
        "success": bool,
        "instance_name": str,
        "current_state": str,
        "message": str
    }
    """
    from xstate_workflow.workflow_engine import get_or_create_instance, get_machine_state

    # Check if document exists
    if not frappe.db.exists(doctype, docname):
        return {
            "success": False,
            "message": _("Document {0} {1} not found").format(doctype, docname)
        }

    # Check if instance already exists
    existing = frappe.db.get_value(
        "Machine Instance",
        {"reference_doctype": doctype, "reference_name": docname},
        ["name", "status"],
        as_dict=True
    )

    if existing:
        if existing.status == "cancelled":
            # Reset the cancelled instance instead of failing
            instance = frappe.get_doc("Machine Instance", existing.name)
            instance.reset()

            # Trigger the always transition if present (e.g., Start -> first state)
            from xstate_workflow.workflow_engine import trigger_event_sync
            try:
                trigger_event_sync(doctype, docname, "xstate.always")
            except Exception:
                pass  # Ignore if no always transition configured

            state = get_machine_state(doctype, docname)
            return {
                "success": True,
                "instance_name": existing.name,
                "current_state": state.get("current_state"),
                "message": _("Workflow restarted successfully")
            }
        else:
            return {
                "success": False,
                "message": _("Workflow already started for this document"),
                "instance_name": existing.name
            }

    # Check if there's an active workflow for this doctype
    machine = frappe.db.get_value(
        "State Machine",
        {"attached_doctype": doctype, "is_active": 1},
        "name"
    )

    if not machine:
        return {
            "success": False,
            "message": _("No active workflow configured for {0}").format(doctype)
        }

    # Create the instance
    try:
        instance_name = get_or_create_instance(doctype, docname)

        if instance_name:
            state = get_machine_state(doctype, docname)
            return {
                "success": True,
                "instance_name": instance_name,
                "current_state": state.get("current_state"),
                "message": _("Workflow started successfully")
            }
    except Exception as e:
        frappe.log_error(f"Failed to start workflow: {e}")
        return {
            "success": False,
            "message": _("Failed to start workflow: {0}").format(str(e))
        }

    return {
        "success": False,
        "message": _("Failed to start workflow")
    }


@frappe.whitelist()
def cancel_workflow(doctype: str, docname: str, reason: str = None) -> dict:
    """
    Cancel a workflow instance.

    Cancels all pending approval tasks and marks the workflow as cancelled.
    After cancellation, start_workflow() can be called to restart.

    Permission: Write access on the referenced document OR Workflow Manager role

    Parameters:
    - doctype (str): Document type name
    - docname (str): Document name
    - reason (str, optional): Reason for cancellation

    Returns:
    {
        "success": bool,
        "tasks_cancelled": int,
        "message": str
    }
    """
    # Check if document exists
    if not frappe.db.exists(doctype, docname):
        return {
            "success": False,
            "message": _("Document {0} {1} not found").format(doctype, docname)
        }

    # Check permissions
    if not _can_cancel_workflow(doctype, docname):
        frappe.throw(_("You do not have permission to cancel this workflow"), frappe.PermissionError)

    # Get the workflow instance
    instance_name = frappe.db.get_value(
        "Machine Instance",
        {"reference_doctype": doctype, "reference_name": docname},
        "name"
    )

    if not instance_name:
        return {
            "success": False,
            "message": _("No workflow instance found for this document")
        }

    # Get instance and check status
    instance = frappe.get_doc("Machine Instance", instance_name)

    if instance.status == "cancelled":
        return {
            "success": False,
            "message": _("Workflow is already cancelled")
        }

    if instance.status == "final":
        return {
            "success": False,
            "message": _("Cannot cancel a completed workflow")
        }

    # Cancel the workflow
    try:
        result = instance.cancel(reason)
        return {
            "success": True,
            "tasks_cancelled": result.get("tasks_cancelled", 0),
            "message": _("Workflow cancelled successfully")
        }
    except Exception as e:
        frappe.log_error(f"Failed to cancel workflow: {e}")
        return {
            "success": False,
            "message": _("Failed to cancel workflow: {0}").format(str(e))
        }


def _can_cancel_workflow(doctype: str, docname: str) -> bool:
    """
    Check if current user can cancel the workflow.

    Returns True if user has:
    - Workflow Manager role, OR
    - Write access on the document
    """
    # Workflow Manager can always cancel
    if "Workflow Manager" in frappe.get_roles():
        return True

    # Otherwise, need write access on the document
    return frappe.has_permission(doctype, "write", docname)


@frappe.whitelist()
def list_workflows(attached_to: str = None) -> list:
    """List all available workflow definitions."""
    from xstate_workflow.workflow_engine import list_machines
    return list_machines(attached_to)


@frappe.whitelist()
def get_workflow_definition(machine_id: str) -> dict:
    """Get a workflow definition by ID."""
    from xstate_workflow.workflow_engine import get_machine
    return get_machine(machine_id)


@frappe.whitelist()
def save_workflow_definition(
    machine_id: str,
    title: str,
    json_config: str,
    attached_doctype: str = None,
    workflow_builder_config: str = None
) -> dict:
    """Save or update a workflow definition."""
    from xstate_workflow.workflow_engine import save_machine
    return save_machine(
        machine_id,
        json_config,
        title,
        workflow_builder_config,
        attached_doctype
    )


@frappe.whitelist()
def get_workflow_history(
    doctype: str,
    docname: str,
    limit: int = 20
) -> list:
    """Get transition history for a document."""
    from xstate_workflow.workflow_engine import get_instance_for_doc

    instance = get_instance_for_doc(doctype, docname)
    if not instance:
        return []

    # Get from Transition Log if we have one
    logs = frappe.get_all(
        "XSM Transition Log",
        filters={"instance": instance.name},
        fields=["from_state", "to_state", "event", "creation", "owner"],
        order_by="creation desc",
        limit=limit
    )

    return [
        {
            "from_state": log.from_state,
            "to_state": log.to_state,
            "event": log.event,
            "timestamp": str(log.creation),
            "user": log.owner
        }
        for log in logs
    ]


@frappe.whitelist()
def get_doctype_fields(doctype: str) -> list:
    """Get fields for a DocType (for guard builder)."""
    if not frappe.db.exists("DocType", doctype):
        frappe.throw(_("DocType {0} not found").format(doctype))

    meta = frappe.get_meta(doctype)

    # Filter to useful field types
    data_field_types = [
        "Data", "Link", "Select", "Int", "Float", "Currency",
        "Date", "Datetime", "Time", "Check", "Text", "Small Text",
        "Long Text", "Read Only", "Rating", "Duration", "Percent",
        "Dynamic Link"
    ]

    return [
        {
            "fieldname": f.fieldname,
            "fieldtype": f.fieldtype,
            "label": f.label or f.fieldname,
            "options": f.options,
            "reqd": f.reqd
        }
        for f in meta.fields
        if f.fieldtype in data_field_types
    ]


@frappe.whitelist()
def get_roles() -> list:
    """Get all active roles for permission configuration."""
    return [r.name for r in frappe.get_all(
        "Role",
        filters={"disabled": 0},
        fields=["name"],
        order_by="name asc"
    )]


@frappe.whitelist()
def get_transition_history(
    doctype: str,
    docname: str,
    limit: int = 20
) -> list:
    """
    Get transition history for a document from Machine Instance.

    This reads from the Machine Instance's transition_log JSON field.
    """
    from xstate_workflow.workflow_engine import get_instance_for_doc

    instance = get_instance_for_doc(doctype, docname)
    if not instance:
        return []

    # Parse transition log from instance
    history = []

    if instance.transition_log:
        try:
            logs = json.loads(instance.transition_log) if isinstance(instance.transition_log, str) else instance.transition_log
            # Reverse to get most recent first and limit
            logs = list(reversed(logs[-limit:]))

            for log in logs:
                history.append({
                    "from_state": log.get("from_state", ""),
                    "to_state": log.get("to_state", ""),
                    "event": log.get("event", ""),
                    "timestamp": log.get("timestamp", ""),
                    "user": log.get("user", ""),
                    "success": log.get("success", True)
                })
        except (json.JSONDecodeError, TypeError):
            pass

    return history


@frappe.whitelist()
def bulk_get_workflow_states(doc_refs: str | list) -> dict:
    """
    Batch get workflow states for multiple documents.

    Parameters:
    - doc_refs: JSON array of [doctype, docname] tuples or list

    Returns:
    Dict mapping "doctype:docname" to state info
    """
    if isinstance(doc_refs, str):
        doc_refs = json.loads(doc_refs)

    from xstate_workflow.utils import batch_get_instances

    instances = batch_get_instances([tuple(ref) for ref in doc_refs])

    result = {}
    for key, inst in instances.items():
        if inst:
            result[key] = {
                "has_workflow": True,
                "current_state": inst.current_state,
                "status": inst.status
            }
        else:
            result[key] = {"has_workflow": False}

    return result


@frappe.whitelist()
def cleanup_duplicate_instances(doctype: str = None, docname: str = None, dry_run: bool = True):
    """
    Clean up duplicate Machine Instance records.

    For each document with multiple instances, keeps only the most relevant one:
    - Prefers active (non-final) instances over final ones
    - Among same status, keeps the most recently created

    Args:
        doctype: Optional - limit cleanup to specific DocType
        docname: Optional - limit cleanup to specific document
        dry_run: If True, only reports what would be deleted (default: True)

    Returns:
        Dict with cleanup results
    """
    if not frappe.has_permission("Machine Instance", "delete"):
        frappe.throw(_("No permission to delete Machine Instances"), frappe.PermissionError)

    filters = {}
    if doctype:
        filters["reference_doctype"] = doctype
    if docname:
        filters["reference_name"] = docname

    # Find all instances grouped by document
    all_instances = frappe.get_all(
        "Machine Instance",
        filters=filters,
        fields=["name", "reference_doctype", "reference_name", "status", "current_state", "creation"],
        order_by="reference_doctype, reference_name, creation desc"
    )

    # Group by document
    docs = {}
    for inst in all_instances:
        key = f"{inst.reference_doctype}:{inst.reference_name}"
        if key not in docs:
            docs[key] = []
        docs[key].append(inst)

    # Find duplicates and determine which to delete
    to_delete = []
    kept = []

    for key, instances in docs.items():
        if len(instances) <= 1:
            continue

        # Sort: active instances first, then by creation desc
        def sort_key(i):
            is_active = 0 if i.status in ("final", "archived") else 1
            return (is_active, i.creation)

        sorted_instances = sorted(instances, key=sort_key, reverse=True)

        # Keep first (best), delete rest
        kept.append({
            "document": key,
            "instance": sorted_instances[0].name,
            "state": sorted_instances[0].current_state,
            "status": sorted_instances[0].status
        })

        for inst in sorted_instances[1:]:
            to_delete.append({
                "name": inst.name,
                "document": key,
                "state": inst.current_state,
                "status": inst.status
            })

    # Perform deletion if not dry run
    deleted = []
    if not dry_run and to_delete:
        for item in to_delete:
            try:
                frappe.delete_doc("Machine Instance", item["name"], force=True)
                deleted.append(item)
            except Exception as e:
                frappe.log_error(f"Failed to delete Machine Instance {item['name']}: {e}")

        frappe.db.commit()

    return {
        "dry_run": dry_run,
        "duplicates_found": len(to_delete),
        "to_delete": to_delete if dry_run else None,
        "deleted": deleted if not dry_run else None,
        "kept": kept
    }


@frappe.whitelist()
def test_agentic_node(
    doctype: str,
    docname: str,
    agent_config: str | dict,
) -> dict:
    """
    Test an agentic node configuration synchronously.

    Runs the agent with capped iterations (5) and timeout (2 minutes)
    to allow quick testing without full workflow execution.

    Parameters:
    - doctype (str): Document type to test against
    - docname (str): Document name to test against
    - agent_config (dict): Agent configuration from the node panel

    Returns:
    {
        "success": bool,
        "decision": str,
        "confidence": float,
        "reasoning": str,
        "iterations_used": int,
        "duration_ms": float,
        "error": str (if failed)
    }
    """
    import time

    # Parse config if string
    if isinstance(agent_config, str):
        agent_config = json.loads(agent_config)

    # Validate document exists and user has permission
    if not frappe.db.exists(doctype, docname):
        return {
            "success": False,
            "error": _("Document {0} {1} not found").format(doctype, docname)
        }

    if not frappe.has_permission(doctype, "read", docname):
        return {
            "success": False,
            "error": _("You don't have permission to read this document")
        }

    start_time = time.time()

    try:
        # Import executor components
        from xstate_workflow.langgraph.executor import (
            AgentExecutor,
            get_llm,
            extract_decision_structured,
            _format_doc_for_agent,
        )
        from xstate_workflow.langgraph.tools import ToolRegistry

        # Build executor with test limits
        executor = AgentExecutor(
            agent_type=agent_config.get("agentType", "react"),
            system_prompt=agent_config.get("systemPrompt", ""),
            model=agent_config.get("model"),
            enabled_tools=agent_config.get("enabledTools", []),
            frappe_access=agent_config.get("frappeAccess", "none"),
            allowed_methods=agent_config.get("allowedMethods", []),
            max_iterations=min(agent_config.get("maxIterations", 5), 5),  # Cap at 5 for testing
            timeout_seconds=min(agent_config.get("timeoutSeconds", 120), 120),  # Cap at 2 min
        )

        # Get LLM
        llm = get_llm(executor.model)

        # Get document
        doc = frappe.get_doc(doctype, docname)
        doc_data = doc.as_dict()

        # Build tools
        tool_registry = ToolRegistry(
            frappe_access=executor.frappe_access,
            allowed_methods=executor.allowed_methods,
            doc=doc_data,
            doctype=doctype,
            docname=docname,
        )
        tools = tool_registry.get_tools(executor.enabled_tools)

        # Create agent
        try:
            from langgraph.prebuilt import create_react_agent
        except ImportError:
            return {
                "success": False,
                "error": "langgraph is not installed. Run: pip install langgraph"
            }

        if executor.agent_type == "react":
            agent = create_react_agent(llm, tools, state_modifier=executor.system_prompt)
        elif executor.agent_type == "plan_execute":
            planning_prompt = (
                f"{executor.system_prompt}\n\n"
                "Before taking any action, first create a step-by-step plan. "
                "Then execute the plan systematically, checking results at each step."
            )
            agent = create_react_agent(llm, tools, state_modifier=planning_prompt)
        else:
            agent = create_react_agent(llm, tools, state_modifier=executor.system_prompt)

        # Prepare input
        doc_summary = _format_doc_for_agent(doc_data, doctype, docname)
        input_data = {
            "messages": [
                ("system", executor.system_prompt),
                ("human", f"Process document {doctype}/{docname}.\n\nDocument data:\n{doc_summary}"),
            ]
        }

        # Run agent synchronously
        result = agent.invoke(input_data, config={"recursion_limit": executor.max_iterations})

        # Extract decision
        last_message = result.get("messages", [])[-1] if result.get("messages") else None
        expected_decisions = [r.get("condition", "") for r in agent_config.get("decisionRoutes", [])]
        expected_decisions.extend([e.get("name", "") for e in agent_config.get("customEvents", [])])

        decision, confidence = extract_decision_structured(last_message, expected_decisions)

        # Extract reasoning from last message
        reasoning = ""
        if last_message:
            content = last_message.content if hasattr(last_message, "content") else str(last_message)
            # Truncate for response
            reasoning = content[:500] + "..." if len(content) > 500 else content

        duration_ms = (time.time() - start_time) * 1000

        return {
            "success": True,
            "decision": decision,
            "confidence": confidence,
            "reasoning": reasoning,
            "iterations_used": len(result.get("messages", [])) // 2,  # Rough estimate
            "duration_ms": duration_ms,
        }

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        frappe.log_error(f"Agentic node test failed: {e}", "Test Agentic Node")
        return {
            "success": False,
            "error": str(e),
            "duration_ms": duration_ms,
        }


@frappe.whitelist()
def get_mcp_connections() -> list:
    """
    Get available MCP server connections for the current user.

    Returns connections where the user has access based on allowed_roles.
    """
    from xstate_workflow.xstate_workflow.doctype.mcp_server_connection.mcp_server_connection import (
        get_active_connections
    )

    user = frappe.session.user

    # Get active connections the user can access
    connections = get_active_connections(user)

    return [
        {
            "name": conn.get("name", ""),
            "connection_name": conn.get("connection_name", ""),
            "description": conn.get("description", ""),
            "tools_discovered": conn.get("tools_discovered", 0),
        }
        for conn in connections
    ]


@frappe.whitelist()
def get_mcp_tools(connection_name: str) -> dict:
    """
    Get available tools from an MCP server connection.

    This connects to the MCP server and discovers available tools.
    Results are cached for performance.

    Parameters:
    - connection_name (str): Name of the MCP Server Connection

    Returns:
    {
        "success": bool,
        "tools": [...] or "error": str
    }
    """
    # Validate connection exists
    if not frappe.db.exists("MCP Server Connection", connection_name):
        return {
            "success": False,
            "error": _("MCP Connection {0} not found").format(connection_name)
        }

    # Get connection doc and validate access
    conn_doc = frappe.get_doc("MCP Server Connection", connection_name)

    if not conn_doc.can_user_access():
        return {
            "success": False,
            "error": _("You don't have permission to access this MCP connection")
        }

    if not conn_doc.is_active:
        return {
            "success": False,
            "error": _("MCP Connection {0} is not active").format(connection_name)
        }

    try:
        from xstate_workflow.langgraph.mcp_client import MCPClient

        # Build auth config
        auth_config = conn_doc.get_auth_config()

        # Create client and list tools
        client = MCPClient(
            server_url=conn_doc.server_url,
            auth_config=auth_config,
            transport_type=conn_doc.transport_type,
            timeout=conn_doc.timeout_seconds or 30
        )

        tools = client.list_tools_sync()

        return {
            "success": True,
            "tools": [
                {
                    "name": tool.get("name", ""),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("inputSchema", tool.get("parameters", {}))
                }
                for tool in tools
            ]
        }

    except Exception as e:
        frappe.log_error(f"Failed to get MCP tools from {connection_name}: {e}", "MCP Tool Discovery")
        return {
            "success": False,
            "error": str(e)
        }
