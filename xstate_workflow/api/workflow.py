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
def start_workflow(doctype: str, docname: str) -> dict:
    """
    Manually start a workflow for a document.

    Used when auto_start_on_create is disabled on the State Machine,
    allowing users to explicitly start the workflow via a button.

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
        "name"
    )

    if existing:
        return {
            "success": False,
            "message": _("Workflow already started for this document"),
            "instance_name": existing
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
