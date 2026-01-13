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
